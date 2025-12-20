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
    ):
        super().__init__(name, symbol)
        self.timeframe = timeframe

        # Pivot settings
        self.pivot_left = int(pivot_left)
        self.pivot_right = int(pivot_right)
        self.emit_on = emit_on

        # Display-friendly description (used by StrategyPanel if present)
        self.entry_conditions_text = [f"SMC: emit={self.emit_on}, pivots={self.pivot_left}/{self.pivot_right}"]

        # State
        self.bias: Optional[str] = None  # "BULLISH" | "BEARISH" | None
        self.last_pivot_high: Optional[Pivot] = None
        self.last_pivot_low: Optional[Pivot] = None
        self.last_structure_event: Optional[str] = None  # "BOS" | "CHoCH" | None

        # Optional MT5 connector (for fetching correct timeframe candles)
        self.mt5_connector = None

    def set_mt5_connector(self, mt5_connector) -> None:
        self.mt5_connector = mt5_connector

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

    def generate_signal(self, market_data: Dict) -> Optional[str]:
        # Candle source
        candles = self._get_candles(count=300)
        if not candles:
            # fallback to the rates provided by the engine (might be on M1)
            candles = market_data.get("rates") or []

        if not candles or len(candles) < 20:
            return None

        _, highs, lows, closes = _extract_ohlc_arrays(candles)
        self._update_pivots(highs, lows)

        close = float(closes[-1])
        structure = self._detect_structure(close)
        if not structure:
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
            return None
        if self.emit_on == "BOS" and event != "BOS":
            return None

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
        )
        strategy.enabled = data.get("enabled", False)
        strategy.set_mt5_connector(mt5_connector)
        strategy.entry_conditions_text = [f"SMC: emit={strategy.emit_on}, pivots={strategy.pivot_left}/{strategy.pivot_right}"]

        # Restore common configuration (backward compatible)
        strategy.trade_monitoring_mode = data.get("trade_monitoring_mode", getattr(strategy, "trade_monitoring_mode", "LTP"))
        strategy.sl_type = data.get("sl_type", getattr(strategy, "sl_type", None))
        strategy.sl_value = data.get("sl_value", getattr(strategy, "sl_value", 20.0))
        strategy.use_ratio = data.get("use_ratio", getattr(strategy, "use_ratio", True))
        strategy.tp_value = data.get("tp_value", getattr(strategy, "tp_value", 40.0))

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


