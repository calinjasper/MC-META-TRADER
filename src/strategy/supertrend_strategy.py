"""
SuperTrend Strategy
Trend-following strategy based on ATR bands (Pine Script style Supertrend).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

import MetaTrader5 as mt5

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


@dataclass
class SuperTrendSnapshot:
    trend: int  # 1 (up) or -1 (down)
    atr: Optional[float]
    upper_band: Optional[float]  # "up_final" in the common Pine implementations
    lower_band: Optional[float]  # "dn_final"
    time: Optional[datetime]


def _true_range(high: float, low: float, prev_close: float) -> float:
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def _atr_wilder(tr_values: List[float], period: int) -> List[Optional[float]]:
    """
    Wilder's ATR (RMA/TR), matching Pine's `atr(period)` behavior.
    Returns a list aligned with tr_values length, with None until enough data.
    """
    n = len(tr_values)
    if n == 0:
        return []
    if period <= 1:
        return [float(x) for x in tr_values]

    atr: List[Optional[float]] = [None] * n

    # Seed ATR at index period-1 as SMA of first `period` TRs
    if n < period:
        return atr

    seed = sum(tr_values[:period]) / float(period)
    atr[period - 1] = seed

    # Wilder smoothing thereafter
    alpha = 1.0 / float(period)
    prev = seed
    for i in range(period, n):
        prev = prev + alpha * (tr_values[i] - prev)
        atr[i] = prev
    return atr


def _atr_sma(tr_values: List[float], period: int) -> List[Optional[float]]:
    n = len(tr_values)
    if n == 0:
        return []
    if period <= 1:
        return [float(x) for x in tr_values]

    atr: List[Optional[float]] = [None] * n
    running_sum = 0.0
    for i, tr in enumerate(tr_values):
        running_sum += tr
        if i >= period:
            running_sum -= tr_values[i - period]
        if i >= period - 1:
            atr[i] = running_sum / float(period)
    return atr


def compute_supertrend(
    candles: List[Dict],
    period: int = 10,
    multiplier: float = 3.0,
    use_wilder_atr: bool = True,
) -> Tuple[List[int], List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """
    Faithful conversion of the common Pine v4 Supertrend implementation:
    - src = hl2
    - basic up/dn bands
    - trailing band adjustment based on prior close vs prior band
    - trend flip rules based on prior band levels

    Returns:
      trend: list[int] (+1/-1)
      atr: list[Optional[float]]
      up_final: list[Optional[float]]
      dn_final: list[Optional[float]]
    """
    if not candles:
        return ([], [], [], [])

    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    closes = [float(c["close"]) for c in candles]
    src = [(h + l) / 2.0 for h, l in zip(highs, lows)]

    # True Range
    tr: List[float] = []
    for i in range(len(candles)):
        prev_close = closes[i - 1] if i > 0 else closes[i]
        tr.append(_true_range(highs[i], lows[i], prev_close))

    atr = _atr_wilder(tr, int(period)) if use_wilder_atr else _atr_sma(tr, int(period))

    # Basic bands (Pine: up = src - mult*atr; dn = src + mult*atr)
    up: List[Optional[float]] = [None] * len(candles)
    dn: List[Optional[float]] = [None] * len(candles)
    for i in range(len(candles)):
        if atr[i] is None:
            continue
        up[i] = src[i] - (multiplier * atr[i])
        dn[i] = src[i] + (multiplier * atr[i])

    up_final: List[Optional[float]] = up.copy()
    dn_final: List[Optional[float]] = dn.copy()

    for i in range(1, len(candles)):
        if up[i] is None or dn[i] is None:
            continue
        if up_final[i - 1] is None or dn_final[i - 1] is None:
            # Not enough history to trail yet
            up_final[i] = up[i]
            dn_final[i] = dn[i]
            continue

        # Trailing logic (Pine style)
        up_final[i] = max(up[i], up_final[i - 1]) if closes[i - 1] > up_final[i - 1] else up[i]
        dn_final[i] = min(dn[i], dn_final[i - 1]) if closes[i - 1] < dn_final[i - 1] else dn[i]

    trend: List[int] = [1] * len(candles)
    for i in range(1, len(candles)):
        # Only flip if prior bands exist
        if dn_final[i - 1] is None or up_final[i - 1] is None:
            trend[i] = trend[i - 1]
            continue

        if trend[i - 1] == -1 and closes[i] > dn_final[i - 1]:
            trend[i] = 1
        elif trend[i - 1] == 1 and closes[i] < up_final[i - 1]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]

    return (trend, atr, up_final, dn_final)


class SuperTrendStrategy(BaseStrategy):
    """
    Strategy that emits BUY/SELL when SuperTrend flips direction.
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        timeframe: int = None,
        period: int = 10,
        multiplier: float = 3.0,
        use_wilder_atr: bool = True,
    ):
        super().__init__(name, symbol)
        self.timeframe = timeframe or mt5.TIMEFRAME_M1
        self.period = int(period)
        self.multiplier = float(multiplier)
        self.use_wilder_atr = bool(use_wilder_atr)

        self.mt5_connector = None

        # For de-dup / flip detection across updates
        self._last_trend: Optional[int] = None

        # Snapshot caching for UI
        self._last_snapshot_at: Optional[datetime] = None
        self._last_snapshot: Optional[SuperTrendSnapshot] = None

    def set_mt5_connector(self, mt5_connector) -> None:
        self.mt5_connector = mt5_connector

    def _get_candles(self, count: int = 350) -> List[Dict]:
        if not self.mt5_connector or not self.mt5_connector.is_connected():
            return []
        try:
            rates = self.mt5_connector.get_rates(self.symbol, self.timeframe, count, 0)
            if rates is None or len(rates) == 0:
                return []
            candles: List[Dict] = []
            for r in rates:
                candles.append(
                    {
                        "time": r["time"],
                        "open": float(r["open"]),
                        "high": float(r["high"]),
                        "low": float(r["low"]),
                        "close": float(r["close"]),
                        "tick_volume": float(r.get("tick_volume", 0)),
                        "spread": float(r.get("spread", 0)),
                        "real_volume": float(r.get("real_volume", 0)),
                    }
                )
            return candles
        except Exception as e:
            logger.error(f"SuperTrendStrategy {self.name}: Failed to fetch candles: {e}", exc_info=True)
            return []

    def _compute_snapshot(self, current_price: Optional[float]) -> Optional[SuperTrendSnapshot]:
        """
        Compute a lightweight snapshot for UI and signal generation.
        Optionally includes a synthetic "current" bar using the latest price.
        """
        candles = self._get_candles(count=max(200, self.period * 10 + 50))
        if not candles:
            return None

        # Append a synthetic current bar for real-time responsiveness (matches MT5 RSI style)
        if current_price is not None and current_price > 0:
            last_close = float(candles[-1]["close"])
            candles = candles + [
                {
                    "time": datetime.now(),
                    "open": last_close,
                    "high": max(last_close, current_price),
                    "low": min(last_close, current_price),
                    "close": float(current_price),
                    "tick_volume": 0.0,
                    "spread": 0.0,
                    "real_volume": 0.0,
                }
            ]

        trend, atr, up_final, dn_final = compute_supertrend(
            candles=candles,
            period=self.period,
            multiplier=self.multiplier,
            use_wilder_atr=self.use_wilder_atr,
        )
        if not trend:
            return None

        i = len(trend) - 1
        t = int(trend[i])
        return SuperTrendSnapshot(
            trend=t,
            atr=atr[i] if i < len(atr) else None,
            upper_band=up_final[i] if i < len(up_final) else None,
            lower_band=dn_final[i] if i < len(dn_final) else None,
            time=candles[i].get("time") if i < len(candles) else None,
        )

    def get_supertrend_snapshot(self) -> Optional[Dict]:
        now = datetime.now()
        if self._last_snapshot_at and self._last_snapshot and (now - self._last_snapshot_at).total_seconds() < 2.0:
            s = self._last_snapshot
            return {
                "trend": s.trend,
                "atr": s.atr,
                "upper_band": s.upper_band,
                "lower_band": s.lower_band,
                "time": s.time,
                "period": self.period,
                "multiplier": self.multiplier,
                "atr_method": "Wilder ATR" if self.use_wilder_atr else "SMA(TR)",
            }

        snap = self._compute_snapshot(current_price=None)
        if not snap:
            return None
        self._last_snapshot = snap
        self._last_snapshot_at = now
        return {
            "trend": snap.trend,
            "atr": snap.atr,
            "upper_band": snap.upper_band,
            "lower_band": snap.lower_band,
            "time": snap.time,
            "period": self.period,
            "multiplier": self.multiplier,
            "atr_method": "Wilder ATR" if self.use_wilder_atr else "SMA(TR)",
        }

    def generate_signal(self, market_data: Dict) -> Optional[str]:
        tick = market_data.get("tick")
        if not tick:
            return None

        current_price = (tick.get("bid", 0) + tick.get("ask", 0)) / 2.0
        if current_price == 0:
            current_price = tick.get("bid", tick.get("ask", 0))
        if current_price == 0:
            return None

        snap = self._compute_snapshot(current_price=current_price)
        if not snap:
            return None

        # Cache for UI too
        self._last_snapshot = snap
        self._last_snapshot_at = datetime.now()

        if self._last_trend is None:
            self._last_trend = snap.trend
            return None

        # Flip signals
        if self._last_trend == -1 and snap.trend == 1:
            self._last_trend = snap.trend
            logger.info(f"SuperTrendStrategy {self.name}: Trend flip DOWN->UP => BUY")
            return "BUY"
        if self._last_trend == 1 and snap.trend == -1:
            self._last_trend = snap.trend
            logger.info(f"SuperTrendStrategy {self.name}: Trend flip UP->DOWN => SELL")
            return "SELL"

        self._last_trend = snap.trend
        return None

    def to_dict(self) -> Dict:
        base_dict = super().to_dict()
        base_dict.update(
            {
                "strategy_type": "supertrend",
                "timeframe": self.timeframe,
                "period": self.period,
                "multiplier": self.multiplier,
                "use_wilder_atr": self.use_wilder_atr,
            }
        )
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict, mt5_connector=None) -> "SuperTrendStrategy":
        strategy = cls(
            name=data["name"],
            symbol=data["symbol"],
            timeframe=data.get("timeframe"),
            period=int(data.get("period", 10)),
            multiplier=float(data.get("multiplier", 3.0)),
            use_wilder_atr=bool(data.get("use_wilder_atr", True)),
        )
        strategy.enabled = data.get("enabled", False)
        strategy.set_mt5_connector(mt5_connector)

        # Restore common configuration (backward compatible)
        strategy.trade_monitoring_mode = data.get("trade_monitoring_mode", getattr(strategy, "trade_monitoring_mode", "LTP"))
        strategy.lot_size = data.get("lot_size", getattr(strategy, "lot_size", None))
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


