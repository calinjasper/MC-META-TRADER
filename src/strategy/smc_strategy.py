"""
Smart Money Concepts (SMC) Strategy

This is a lightweight, trading-engine-oriented implementation:
- Tracks swing/internal pivots (simple fractal pivots)
- Detects BOS / CHoCH based on pivot breaks and current bias
- Maintains a small state machine (bias + last structure levels)
- Emits BUY/SELL signals (no TradingView drawing objects)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import logging

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


@dataclass
class Pivot:
    kind: str  # "high" | "low"
    price: float
    index: int


def _extract_ohlc_arrays(rates: List[Dict]) -> Tuple[List[float], List[float], List[float], List[float]]:
    opens, highs, lows, closes = [], [], [], []
    for r in rates:
        # supports both dicts from MT5Connector and data_feed.get_rates()
        opens.append(float(r.get("open")))
        highs.append(float(r.get("high")))
        lows.append(float(r.get("low")))
        closes.append(float(r.get("close")))
    return opens, highs, lows, closes


def _fractal_pivot_high(highs: List[float], i: int, left: int, right: int) -> bool:
    if i - left < 0 or i + right >= len(highs):
        return False
    h = highs[i]
    return all(h > highs[j] for j in range(i - left, i)) and all(h >= highs[j] for j in range(i + 1, i + right + 1))


def _fractal_pivot_low(lows: List[float], i: int, left: int, right: int) -> bool:
    if i - left < 0 or i + right >= len(lows):
        return False
    l = lows[i]
    return all(l < lows[j] for j in range(i - left, i)) and all(l <= lows[j] for j in range(i + 1, i + right + 1))


class SMCStrategy(BaseStrategy):
    """
    SMC Strategy (simplified)

    Signal logic (pragmatic default):
    - Maintain a "bias" (BULLISH/BEARISH/None)
    - Detect pivot highs/lows on the selected timeframe
    - If close breaks last pivot high/low:
        - If bias matches direction => BOS
        - If bias opposes direction => CHoCH and bias flips
    - Emit signal on CHoCH only (reversal-style) by default
      (This matches the typical "bias changes on CHoCH, not BOS" heuristic.)
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        timeframe: int,
        pivot_left: int = 2,
        pivot_right: int = 2,
        emit_on: str = "CHoCH",  # "CHoCH" | "BOS" | "BOTH"
        buy_filters: Optional[List[Dict]] = None,
        sell_filters: Optional[List[Dict]] = None,
    ):
        super().__init__(name, symbol)
        self.timeframe = timeframe

        # Pivot settings
        self.pivot_left = int(pivot_left)
        self.pivot_right = int(pivot_right)
        self.emit_on = emit_on

        # Post-filter chains (AND/OR) for buy/sell
        self.buy_filters: List[Dict] = buy_filters or []
        self.sell_filters: List[Dict] = sell_filters or []

        # Display-friendly description (used by StrategyPanel if present)
        self.entry_conditions_text = [f"SMC: emit={self.emit_on}, pivots={self.pivot_left}/{self.pivot_right}"]

        # State
        self.bias: Optional[str] = None  # "BULLISH" | "BEARISH" | None
        self.last_pivot_high: Optional[Pivot] = None
        self.last_pivot_low: Optional[Pivot] = None
        self.last_structure_event: Optional[str] = None  # "BOS" | "CHoCH" | None

        # For filter cross detection
        self._prev_filter_price: Optional[float] = None

        # Optional MT5 connector (for fetching correct timeframe candles)
        self.mt5_connector = None

    def set_mt5_connector(self, mt5_connector) -> None:
        self.mt5_connector = mt5_connector

    def set_filters(self, buy_filters: List[Dict], sell_filters: List[Dict]) -> None:
        self.buy_filters = buy_filters or []
        self.sell_filters = sell_filters or []

    def _get_candles(self, count: int = 300) -> List[Dict]:
        """Get candles on the strategy timeframe. Uses MT5Connector if available, else falls back to market_data rates."""
        if self.mt5_connector and hasattr(self.mt5_connector, "is_connected") and self.mt5_connector.is_connected():
            try:
                rates = self.mt5_connector.get_rates(self.symbol, self.timeframe, count, 0)
                if rates is None:
                    return []
                return list(rates)
            except Exception as e:
                logger.error(f"SMCStrategy {self.name}: Error fetching candles via MT5Connector: {e}", exc_info=True)
                return []
        return []

    def _update_pivots(self, highs: List[float], lows: List[float]) -> None:
        """
        Update last pivot high/low using the most recently *confirmed* fractal pivot.
        A pivot at index i is confirmed only after 'right' bars have printed.
        """
        left, right = self.pivot_left, self.pivot_right
        if len(highs) < left + right + 3:
            return

        # Only check newly confirmable region near the end for performance:
        # last confirmable index = len-1-right
        start = max(left, len(highs) - right - 10)
        end = len(highs) - right

        for i in range(start, end):
            if _fractal_pivot_high(highs, i, left, right):
                self.last_pivot_high = Pivot(kind="high", price=highs[i], index=i)
            if _fractal_pivot_low(lows, i, left, right):
                self.last_pivot_low = Pivot(kind="low", price=lows[i], index=i)

    def _detect_structure(self, close: float) -> Optional[Tuple[str, str]]:
        """
        Returns (event, direction) where:
        - event: "BOS" | "CHoCH"
        - direction: "UP" | "DOWN"
        """
        # Need both pivots to do anything meaningful
        ph = self.last_pivot_high.price if self.last_pivot_high else None
        pl = self.last_pivot_low.price if self.last_pivot_low else None
        if ph is None and pl is None:
            return None

        # Prefer strongest break (rare both in one bar)
        if ph is not None and close > ph:
            if self.bias == "BEARISH":
                return ("CHoCH", "UP")
            if self.bias == "BULLISH":
                return ("BOS", "UP")
            # bias unknown => treat as BOS (trend discovery)
            return ("BOS", "UP")

        if pl is not None and close < pl:
            if self.bias == "BULLISH":
                return ("CHoCH", "DOWN")
            if self.bias == "BEARISH":
                return ("BOS", "DOWN")
            return ("BOS", "DOWN")

        return None

    def _resolve_operand(self, field: str, current_price: float, ohlc: Dict, market_data: Dict = None) -> Optional[float]:
        """
        Resolve operand using unified indicator resolver.
        Falls back to internal SMC pivot tracking if unified resolver doesn't have SMC pivots.
        """
        # Build context for unified resolver
        context = {
            "price": current_price,
            "ohlc": ohlc if ohlc else {},
        }
        
        # Add SMC pivots from internal state (if not in market_data)
        smc_pivots = {}
        if self.last_pivot_high:
            smc_pivots["pivot_high"] = self.last_pivot_high.price
        if self.last_pivot_low:
            smc_pivots["pivot_low"] = self.last_pivot_low.price
        context["smc_pivots"] = smc_pivots
        
        # Add market_data context if available (may override internal pivots)
        if market_data:
            # Use market_data SMC pivots if available, otherwise use internal
            if "smc_pivots" in market_data and market_data["smc_pivots"]:
                context["smc_pivots"] = market_data["smc_pivots"]
            context["vwap"] = market_data.get("vwap")
            context["ema"] = market_data.get("ema")
            context["indicators"] = market_data.get("indicators", {})
        
        # Try unified resolver first
        from .unified_indicator_resolver import resolve_operand
        result = resolve_operand(field, context)
        if result is not None:
            return result
        
        return None

    def _evaluate_filter_condition(self, cond: Dict, current_price: float, ohlc: Dict, prev_price: Optional[float], market_data: Dict = None) -> bool:
        left = self._resolve_operand(cond.get("left_field"), current_price, ohlc, market_data)
        right = self._resolve_operand(cond.get("right_field"), current_price, ohlc, market_data)
        if left is None or right is None:
            return False
        op = cond.get("operator")
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
        if op == "==":
            return abs(left - right) < 1e-5
        if op == "Crosses Above":
            if prev_price is None:
                return False
            return prev_price < right <= left
        if op == "Crosses Under":
            if prev_price is None:
                return False
            return prev_price > right >= left
        if op == "Any_Cross":
            if prev_price is None:
                return False
            return (prev_price < right <= left) or (prev_price > right >= left)
        return False

    def _evaluate_filter_chain(self, filters: List[Dict], current_price: float, ohlc: Dict, market_data: Dict = None) -> bool:
        if not filters:
            return True
        cumulative = None
        prev_connector = None
        for cond in filters:
            res = self._evaluate_filter_condition(cond, current_price, ohlc, self._prev_filter_price, market_data)
            if cumulative is None:
                cumulative = res
            else:
                connector = prev_connector or "OR"
                if connector == "AND":
                    cumulative = cumulative and res
                else:
                    cumulative = cumulative or res
            prev_connector = cond.get("connector", "OR")
        return bool(cumulative)

    def generate_signal(self, market_data: Dict) -> Optional[str]:
        # Candle source
        candles = self._get_candles(count=300)
        if not candles:
            # fallback to the rates provided by the engine (might be on M1)
            candles = market_data.get("rates") or []

        if not candles or len(candles) < 20:
            return None

        opens, highs, lows, closes = _extract_ohlc_arrays(candles)
        self._update_pivots(highs, lows)

        close = float(closes[-1])
        structure = self._detect_structure(close)
        if not structure:
            self._prev_filter_price = close
            return None

        event, direction = structure
        self.last_structure_event = event

        # Update bias only on CHoCH (core heuristic)
        if event == "CHoCH":
            self.bias = "BULLISH" if direction == "UP" else "BEARISH"
        elif self.bias is None:
            # bootstrap bias on first BOS discovery
            self.bias = "BULLISH" if direction == "UP" else "BEARISH"

        # Emit signals
        if self.emit_on == "CHoCH" and event != "CHoCH":
            self._prev_filter_price = close
            return None
        if self.emit_on == "BOS" and event != "BOS":
            self._prev_filter_price = close
            return None

        # Post filter on current bar using last candle ohlc
        last_ohlc = {
            "open": float(opens[-1]) if opens else None,
            "high": float(highs[-1]) if highs else None,
            "low": float(lows[-1]) if lows else None,
            "close": close,
        }
        filters = self.buy_filters if direction == "UP" else self.sell_filters
        # Build market_data context for unified resolver
        strategy_market_data = {
            "smc_pivots": {
                "pivot_high": self.last_pivot_high.price if self.last_pivot_high else None,
                "pivot_low": self.last_pivot_low.price if self.last_pivot_low else None
            },
            "ohlc": last_ohlc,
            "indicators": market_data.get("indicators", {}) if isinstance(market_data, dict) else {}
        }
        if not self._evaluate_filter_chain(filters, close, last_ohlc, strategy_market_data):
            self._prev_filter_price = close
            return None

        self._prev_filter_price = close
        return "BUY" if direction == "UP" else "SELL"

    def to_dict(self) -> Dict:
        base = super().to_dict()
        base.update(
            {
                "strategy_type": "smc",
                "timeframe": self.timeframe,
                "pivot_left": self.pivot_left,
                "pivot_right": self.pivot_right,
                "emit_on": self.emit_on,
                "buy_filters": self.buy_filters,
                "sell_filters": self.sell_filters,
                # Persisted state is optional; we keep only configuration.
            }
        )
        return base

    @classmethod
    def from_dict(cls, data: Dict, mt5_connector=None) -> "SMCStrategy":
        strategy = cls(
            name=data["name"],
            symbol=data["symbol"],
            timeframe=data.get("timeframe"),
            pivot_left=data.get("pivot_left", 2),
            pivot_right=data.get("pivot_right", 2),
            emit_on=data.get("emit_on", "CHoCH"),
            buy_filters=data.get("buy_filters", []),
            sell_filters=data.get("sell_filters", []),
        )
        strategy.enabled = data.get("enabled", False)
        strategy.set_mt5_connector(mt5_connector)
        strategy.entry_conditions_text = [f"SMC: emit={strategy.emit_on}, pivots={strategy.pivot_left}/{strategy.pivot_right}"]

        # Restore common configuration (backward compatible)
        strategy.trade_monitoring_mode = data.get("trade_monitoring_mode", getattr(strategy, "trade_monitoring_mode", "LTP"))
        strategy.sl_type = data.get("sl_type", getattr(strategy, "sl_type", None))
        strategy.sl_value = data.get("sl_value", getattr(strategy, "sl_value", 20.0))
        strategy.sl_enabled = data.get("sl_enabled", getattr(strategy, "sl_enabled", True))
        strategy.use_ratio = data.get("use_ratio", getattr(strategy, "use_ratio", True))
        strategy.tp_value = data.get("tp_value", getattr(strategy, "tp_value", 40.0))
        strategy.tp_enabled = data.get("tp_enabled", getattr(strategy, "tp_enabled", True))

        # Advanced Risk Management
        strategy.enable_trailing_sl = data.get("enable_trailing_sl", getattr(strategy, "enable_trailing_sl", False))
        strategy.trailing_sl_gap = data.get("trailing_sl_gap", getattr(strategy, "trailing_sl_gap", 0.0))
        strategy.enable_profit_lock = data.get("enable_profit_lock", getattr(strategy, "enable_profit_lock", False))
        strategy.profit_lock_trigger = data.get("profit_lock_trigger", getattr(strategy, "profit_lock_trigger", 0.0))
        strategy.profit_lock_value = data.get("profit_lock_value", getattr(strategy, "profit_lock_value", 0.0))
        strategy.profit_trail_step = data.get("profit_trail_step", getattr(strategy, "profit_trail_step", 0.0))
        strategy.profit_trail_amount = data.get("profit_trail_amount", getattr(strategy, "profit_trail_amount", 0.0))

        # Trail Wait & Trade (W&T)
        strategy.enable_wt = data.get("enable_wt", getattr(strategy, "enable_wt", False))
        strategy.wt_value = data.get("wt_value", getattr(strategy, "wt_value", 0.0))
        strategy.wt_is_percentage = data.get("wt_is_percentage", getattr(strategy, "wt_is_percentage", False))

        # Position preservation
        strategy.preserve_position = data.get("preserve_position", getattr(strategy, "preserve_position", False))

        return strategy


