"""
EMA Trading Strategy
Trading strategy based on price comparisons with one or more EMAs.
"""

from __future__ import annotations

from typing import Dict, List, Optional
import logging
from datetime import datetime

import MetaTrader5 as mt5

from .base_strategy import BaseStrategy
from ..indicators.ema import EMA

logger = logging.getLogger(__name__)


class EMACondition:
    """Represents a single EMA-based condition (Current Price vs EMA)."""

    def __init__(self, price_reference: str, operator: str, ema_field: str = None, value: float = None):
        """
        Args:
            price_reference: Typically "Current Price"
            operator: ">", "<", ">=", "<=", "==", "Crosses Above", "Crosses Under"
            ema_field: One of "ema_1" | "ema_2" | "ema_3" | "ema_4"
            value: Optional explicit numeric value (fallback)
        """
        self.price_reference = price_reference
        self.operator = operator
        self.ema_field = ema_field
        self.value = value
        self.previous_state = None  # For cross detection

    def get_threshold(self, ema_values: Dict) -> Optional[float]:
        """Get the threshold value for comparison."""
        if self.ema_field:
            return ema_values.get(self.ema_field)
        if self.value is not None:
            return self.value
        return None

    def evaluate(self, current_price: float, ema_values: Dict, previous_price: Optional[float] = None) -> bool:
        """Evaluate condition against latest EMA snapshot."""
        threshold = self.get_threshold(ema_values)
        if threshold is None:
            return False

        if self.operator == "Crosses Above":
            if previous_price is not None:
                was_below = previous_price < threshold
                is_above = current_price >= threshold
                if was_below and is_above:
                    self.previous_state = True
                    return True
            self.previous_state = current_price >= threshold
            return False

        if self.operator == "Crosses Under":
            if previous_price is not None:
                was_above = previous_price > threshold
                is_below = current_price <= threshold
                if was_above and is_below:
                    self.previous_state = False
                    return True
            self.previous_state = current_price > threshold
            return False

        if self.operator == ">":
            return current_price > threshold
        if self.operator == "<":
            return current_price < threshold
        if self.operator == ">=":
            return current_price >= threshold
        if self.operator == "<=":
            return current_price <= threshold
        if self.operator == "==":
            epsilon = 0.00001
            return abs(current_price - threshold) < epsilon

        return False

    def to_dict(self) -> Dict:
        return {
            "price_reference": self.price_reference,
            "operator": self.operator,
            "ema_field": self.ema_field,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "EMACondition":
        return cls(
            price_reference=data.get("price_reference", "Current Price"),
            operator=data.get("operator", ">"),
            ema_field=data.get("ema_field"),
            value=data.get("value"),
        )


class EMAStrategy(BaseStrategy):
    """Trading strategy that generates signals based on EMA conditions."""

    def __init__(
        self,
        name: str,
        symbol: str,
        timeframe: int = None,
        ema_periods: Optional[Dict[str, int]] = None,
    ):
        super().__init__(name, symbol)
        self.timeframe = timeframe or mt5.TIMEFRAME_M1

        self.ema_periods: Dict[str, int] = ema_periods or {
            "ema_1": 20,
            "ema_2": 50,
            "ema_3": 100,
            "ema_4": 200,
        }

        # EMA indicators (kept in sync with ema_periods)
        self._ema_indicators: Dict[str, EMA] = {}
        self._rebuild_indicators()

        self.buy_conditions: List[EMACondition] = []
        self.sell_conditions: List[EMACondition] = []

        self.previous_price: Optional[float] = None
        self.mt5_connector = None

        # Snapshot caching for UI status
        self._last_snapshot_at: Optional[datetime] = None
        self._last_snapshot: Optional[Dict] = None

    def _rebuild_indicators(self) -> None:
        self._ema_indicators.clear()
        # Reset indicators registry to match new EMA config
        for field, period in self.ema_periods.items():
            ind = EMA(int(period))
            self._ema_indicators[field] = ind
            self.add_indicator(f"EMA_{field}", ind)

    def set_mt5_connector(self, mt5_connector) -> None:
        self.mt5_connector = mt5_connector

    def add_buy_condition(self, condition: EMACondition) -> None:
        self.buy_conditions.append(condition)

    def add_sell_condition(self, condition: EMACondition) -> None:
        self.sell_conditions.append(condition)

    def _get_candles(self, count: int = 250) -> List[Dict]:
        """Get historical candles from MT5 using MT5Connector (handles symbol resolution)."""
        if not self.mt5_connector or not self.mt5_connector.is_connected():
            return []

        try:
            rates = self.mt5_connector.get_rates(self.symbol, self.timeframe, count, 0)
            if rates is None or len(rates) == 0:
                return []

            candles: List[Dict] = []
            for rate in rates:
                candles.append(
                    {
                        "time": rate["time"],
                        "open": float(rate["open"]),
                        "high": float(rate["high"]),
                        "low": float(rate["low"]),
                        "close": float(rate["close"]),
                        "tick_volume": float(rate.get("tick_volume", 0)),
                        "spread": float(rate.get("spread", 0)),
                        "real_volume": float(rate.get("real_volume", 0)),
                    }
                )
            return candles
        except Exception as e:
            logger.error(f"EMAStrategy {self.name}: Failed to fetch candles: {e}", exc_info=True)
            return []

    def _compute_ema_values(self, candles: List[Dict]) -> Dict[str, Optional[float]]:
        """Compute latest EMA values for configured periods."""
        ema_values: Dict[str, Optional[float]] = {}

        # Ensure indicators match periods (in case config was changed after construction)
        for field, period in self.ema_periods.items():
            ind = self._ema_indicators.get(field)
            if not ind or ind.period != int(period):
                self._rebuild_indicators()
                break

        for field, ind in self._ema_indicators.items():
            series = ind.calculate(candles)
            ema_values[field] = series[-1] if series else None

        return ema_values

    def get_ema_snapshot(self) -> Optional[Dict]:
        """
        Get a lightweight EMA snapshot for UI display.
        Returns:
            {"periods": {...}, "values": {...}} or None
        """
        now = datetime.now()
        if self._last_snapshot_at and self._last_snapshot and (now - self._last_snapshot_at).total_seconds() < 2.0:
            return self._last_snapshot

        candles = self._get_candles(count=300)
        if not candles:
            return None

        values = self._compute_ema_values(candles)
        snap = {"periods": dict(self.ema_periods), "values": values}
        self._last_snapshot = snap
        self._last_snapshot_at = now
        return snap

    def generate_signal(self, market_data: Dict) -> Optional[str]:
        tick = market_data.get("tick")
        if not tick:
            return None

        current_price = (tick.get("bid", 0) + tick.get("ask", 0)) / 2.0
        if current_price == 0:
            current_price = tick.get("bid", tick.get("ask", 0))
        if current_price == 0:
            return None

        candles = self._get_candles(count=300)
        if not candles:
            return None

        ema_values = self._compute_ema_values(candles)

        # BUY conditions take priority over SELL, consistent with OHLC strategy
        for idx, condition in enumerate(self.buy_conditions):
            try:
                threshold = condition.get_threshold(ema_values)
                if condition.evaluate(current_price, ema_values, self.previous_price):
                    threshold_str = f"{threshold:.5f}" if threshold is not None else "N/A"
                    logger.info(
                        f"EMAStrategy {self.name}: ✅ Buy condition {idx+1} MET! "
                        f"Current={current_price:.5f} {condition.operator} EMA={threshold_str}"
                    )
                    self.previous_price = current_price
                    return "BUY"
            except Exception as e:
                logger.error(f"EMAStrategy {self.name}: Error evaluating buy condition {idx+1}: {e}", exc_info=True)

        for idx, condition in enumerate(self.sell_conditions):
            try:
                threshold = condition.get_threshold(ema_values)
                if condition.evaluate(current_price, ema_values, self.previous_price):
                    threshold_str = f"{threshold:.5f}" if threshold is not None else "N/A"
                    logger.info(
                        f"EMAStrategy {self.name}: ✅ Sell condition {idx+1} MET! "
                        f"Current={current_price:.5f} {condition.operator} EMA={threshold_str}"
                    )
                    self.previous_price = current_price
                    return "SELL"
            except Exception as e:
                logger.error(f"EMAStrategy {self.name}: Error evaluating sell condition {idx+1}: {e}", exc_info=True)

        self.previous_price = current_price
        return None

    def to_dict(self) -> Dict:
        base_dict = super().to_dict()
        base_dict.update(
            {
                "strategy_type": "ema",
                "timeframe": self.timeframe,
                "ema_periods": self.ema_periods,
                "buy_conditions": [c.to_dict() for c in self.buy_conditions],
                "sell_conditions": [c.to_dict() for c in self.sell_conditions],
            }
        )
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict, mt5_connector=None) -> "EMAStrategy":
        strategy = cls(
            name=data["name"],
            symbol=data["symbol"],
            timeframe=data.get("timeframe"),
            ema_periods=data.get("ema_periods"),
        )
        strategy.enabled = data.get("enabled", False)
        strategy.set_mt5_connector(mt5_connector)

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

        # Position Preservation
        strategy.preserve_position = data.get("preserve_position", getattr(strategy, "preserve_position", False))

        for cond_data in data.get("buy_conditions", []):
            strategy.add_buy_condition(EMACondition.from_dict(cond_data))
        for cond_data in data.get("sell_conditions", []):
            strategy.add_sell_condition(EMACondition.from_dict(cond_data))

        return strategy


