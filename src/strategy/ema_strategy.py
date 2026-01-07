"""
EMA Trading Strategy
Trading strategy based on price comparisons with one or more EMAs.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

import MetaTrader5 as mt5

from .base_strategy import BaseStrategy
from ..indicators.ema import EMA

logger = logging.getLogger(__name__)


class EMACondition:
    """Represents a single EMA-based condition (Current Price vs EMA)."""

    def __init__(
        self,
        price_reference: str,
        operator: str,
        ema_field: Optional[str] = None,
        value: Optional[float] = None,
        left_field: Optional[str] = None,
        right_field: Optional[str] = None,
        connector: str = "OR",
    ):
        """
        Args:
            price_reference: Typically "Current Price"
            operator: ">", "<", ">=", "<=", "==", "Crosses Above", "Crosses Under"
            ema_field: One of "ema_1" | "ema_2" | "ema_3" | "ema_4"
            value: Optional explicit numeric value (fallback)
            left_field/right_field: operands selected in UI
            connector: logical connector to next condition
        """
        self.price_reference = price_reference
        self.operator = operator
        self.ema_field = ema_field
        self.value = value
        self.left_field = left_field or "price"
        self.right_field = right_field or ema_field
        self.connector = connector or "OR"
        self.previous_state = None  # For cross detection

    def _resolve_operand(self, field: str, current_price: float, ema_values: Dict, market_data: Optional[Dict] = None) -> Optional[float]:
        """
        Resolve operand using unified indicator resolver.
        Falls back to legacy behavior if unified resolver fails.
        """
        # Build context for unified resolver
        context = {
            "price": current_price,
            "ema": ema_values if ema_values else {},
        }
        
        # Add market_data context if available
        if market_data:
            context["ohlc"] = market_data.get("ohlc", {})
            context["smc_pivots"] = market_data.get("smc_pivots", {})
            context["vwap"] = market_data.get("vwap")
            context["indicators"] = market_data.get("indicators", {})
            context["ema_periods"] = market_data.get("ema_periods")  # Add ema_periods for period-based mapping
        
        # #region agent log
        import json
        try:
            with open(r'c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A",
                    "location": "ema_strategy.py:_resolve_operand",
                    "message": "Resolving operand field",
                    "data": {
                        "field": field,
                        "has_ema_periods_in_context": "ema_periods" in context,
                        "ema_periods": context.get("ema_periods"),
                        "ema_keys": list(ema_values.keys()) if ema_values else [],
                        "market_data_keys": list(market_data.keys()) if market_data else []
                    },
                    "timestamp": __import__("time").time() * 1000
                }) + "\n")
        except: pass
        # #endregion
        
        # Try unified resolver first
        from .unified_indicator_resolver import resolve_operand
        result = resolve_operand(field, context)
        
        # #region agent log
        try:
            with open(r'c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "B",
                    "location": "ema_strategy.py:_resolve_operand",
                    "message": "Unified resolver result",
                    "data": {
                        "field": field,
                        "result": result,
                        "result_is_none": result is None
                    },
                    "timestamp": __import__("time").time() * 1000
                }) + "\n")
        except: pass
        # #endregion
        
        if result is not None:
            return result
        
        # Fallback to legacy behavior for backward compatibility
        if field == "price" or field == "current_price":
            return current_price
        
        # Handle period-based EMA field names (e.g., "ema_20") by mapping to position-based names (e.g., "ema_1")
        if field and field.startswith("ema_"):
            # Check if it's a period-based name (e.g., "ema_20")
            try:
                period_str = field.replace("ema_", "")
                period = int(period_str)
                # #region agent log
                try:
                    with open(r'c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "C",
                            "location": "ema_strategy.py:_resolve_operand",
                            "message": "Attempting period-based mapping",
                            "data": {
                                "field": field,
                                "extracted_period": period,
                                "has_market_data": market_data is not None,
                                "has_ema_periods": market_data.get("ema_periods") if market_data else None
                            },
                            "timestamp": __import__("time").time() * 1000
                        }) + "\n")
                except: pass
                # #endregion
                # This is a period-based name, need to find which ema_X has this period
                # Check if we have ema_periods mapping in market_data
                if market_data and "ema_periods" in market_data:
                    ema_periods = market_data["ema_periods"]
                    # Find which ema_X has this period
                    for ema_key, ema_period in ema_periods.items():
                        if ema_period == period:
                            # Found the matching ema_X, return its value
                            mapped_value = ema_values.get(ema_key)
                            # #region agent log
                            try:
                                with open(r'c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log', 'a') as f:
                                    f.write(json.dumps({
                                        "sessionId": "debug-session",
                                        "runId": "run1",
                                        "hypothesisId": "C",
                                        "location": "ema_strategy.py:_resolve_operand",
                                        "message": "Period-based mapping success",
                                        "data": {
                                            "field": field,
                                            "period": period,
                                            "mapped_to": ema_key,
                                            "mapped_value": mapped_value
                                        },
                                        "timestamp": __import__("time").time() * 1000
                                    }) + "\n")
                            except: pass
                            # #endregion
                            return mapped_value
            except ValueError:
                # Not a period-based name, treat as position-based (e.g., "ema_1")
                pass
            
            # Try direct lookup (position-based name like "ema_1")
            direct_value = ema_values.get(field)
            # #region agent log
            try:
                with open(r'c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "D",
                        "location": "ema_strategy.py:_resolve_operand",
                        "message": "Direct lookup fallback",
                        "data": {
                            "field": field,
                            "direct_value": direct_value
                        },
                        "timestamp": __import__("time").time() * 1000
                    }) + "\n")
            except: pass
            # #endregion
            return direct_value
        
        # Fallback to legacy value if field couldn't be resolved
        return self.value

    def evaluate(self, current_price: float, ema_values: Dict, previous_price: Optional[float] = None, market_data: Optional[Dict] = None, previous_ema_values: Optional[Dict] = None) -> bool:
        """
        Evaluate condition against latest EMA snapshot.
        Matches MT5 indicator logic exactly.
        
        For cross detection, compares:
        - Previous bar's close with previous bar's EMA
        - Current bar's close with current bar's EMA
        """
        # Use current EMA values for regular comparisons
        left_field = self.left_field or "price"
        right_field = self.right_field or (self.ema_field or "price")
        left_val = self._resolve_operand(left_field, current_price, ema_values, market_data)
        right_val = self._resolve_operand(right_field, current_price, ema_values, market_data)
        
        # #region agent log
        import json
        try:
            with open(r'c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "G",
                    "location": "ema_strategy.py:evaluate",
                    "message": "Operand resolution results",
                    "data": {
                        "left_field": self.left_field,
                        "right_field": self.right_field,
                        "operator": self.operator,
                        "left_val": left_val,
                        "right_val": right_val,
                        "both_resolved": left_val is not None and right_val is not None
                    },
                    "timestamp": __import__("time").time() * 1000
                }) + "\n")
        except: pass
        # #endregion
        
        if left_val is None or right_val is None:
            return False

        # For cross detection, use previous EMA if available (matches MT5 exactly)
        if self.operator in ["Crosses Above", "Crosses Under", "Any_Cross"]:
            if previous_price is not None:
                # Use previous EMA value for the right operand if available
                if previous_ema_values:
                    prev_right_val = self._resolve_operand(right_field, previous_price, previous_ema_values, market_data)
                    if prev_right_val is not None:
                        right_val_for_cross = prev_right_val
                    else:
                        right_val_for_cross = right_val
                else:
                    # Fallback to current EMA if previous not available
                    right_val_for_cross = right_val
                
                if self.operator == "Crosses Above":
                    # MT5 logic: previous close < previous EMA AND current close >= current EMA
                    was_below = previous_price < right_val_for_cross
                    is_above = left_val >= right_val
                    
                    # Enhanced Debug Logging
                    if self.ema_field == "ema_1" or self.right_field == "ema_20": # Only log for likely candidate
                         logger.info(f"EMA Cross Check: Price={left_val:.2f}, EMA={right_val:.2f}, PrevPrice={previous_price:.2f}, PrevEMA={right_val_for_cross:.2f} | WasBelow={was_below}, IsAbove={is_above}")

                    if was_below and is_above:
                        self.previous_state = True
                        return True
                    self.previous_state = left_val >= right_val
                    return False
                
                if self.operator == "Crosses Under":
                    # MT5 logic: previous close > previous EMA AND current close <= current EMA
                    was_above = previous_price > right_val_for_cross
                    is_below = left_val <= right_val
                    
                    if self.ema_field == "ema_1" or self.right_field == "ema_20":
                        logger.info(f"EMA Cross Check (Under): Price={left_val:.2f}, EMA={right_val:.2f}, PrevPrice={previous_price:.2f}, PrevEMA={right_val_for_cross:.2f} | WasAbove={was_above}, IsBelow={is_below}")

                    if was_above and is_below:
                        self.previous_state = False
                        return True
                    self.previous_state = left_val > right_val
                    return False
                
                if self.operator == "Any_Cross":
                    # MT5 logic: either crosses above or crosses under
                    crossed_up = previous_price < right_val_for_cross and left_val >= right_val
                    crossed_down = previous_price > right_val_for_cross and left_val <= right_val
                    if crossed_up or crossed_down:
                        self.previous_state = left_val >= right_val
                        return True
                    self.previous_state = left_val >= right_val
                    return False
            else:

                # No previous price available, can't detect cross
                if self.operator == "Crosses Above":
                    self.previous_state = left_val >= right_val
                elif self.operator == "Crosses Under":
                    self.previous_state = left_val > right_val
                elif self.operator == "Any_Cross":
                    self.previous_state = left_val >= right_val
                return False

        # Regular comparison operators (matches MT5 exactly)
        if self.operator == ">":
            return left_val > right_val
        if self.operator == "<":
            return left_val < right_val
        if self.operator == ">=":
            return left_val >= right_val
        if self.operator == "<=":
            return left_val <= right_val
        if self.operator == "==":
            epsilon = 0.00001
            return abs(left_val - right_val) < epsilon

        return False

    def to_dict(self) -> Dict:
        return {
            "price_reference": self.price_reference,
            "operator": self.operator,
            "ema_field": self.ema_field,
            "value": self.value,
            "left_field": self.left_field,
            "right_field": self.right_field,
            "connector": self.connector,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "EMACondition":
        return cls(
            price_reference=data.get("price_reference", "Current Price"),
            operator=data.get("operator", ">"),
            ema_field=data.get("ema_field") if data.get("ema_field") is not None else None,
            value=data.get("value") if data.get("value") is not None else None,
            left_field=data.get("left_field") if data.get("left_field") is not None else None,
            right_field=data.get("right_field") if data.get("right_field") is not None else None,
            connector=data.get("connector", data.get("logical_connector", "OR")),
        )


class EMAStrategy(BaseStrategy):
    """Trading strategy that generates signals based on EMA conditions."""

    def __init__(
        self,
        name: str,
        symbol: str,
        timeframe: Optional[int] = None,
        ema_periods: Optional[Dict[str, int]] = None,
    ):
        super().__init__(name, symbol)
        self.timeframe = timeframe if timeframe is not None else mt5.TIMEFRAME_M1

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
    
    def _compute_ema_values_with_previous(self, candles: List[Dict]) -> Tuple[Dict[str, Optional[float]], Dict[str, Optional[float]]]:
        """
        Compute current and previous EMA values for accurate cross detection.
        Returns: (current_ema_values, previous_ema_values)
        """
        current_ema_values: Dict[str, Optional[float]] = {}
        previous_ema_values: Dict[str, Optional[float]] = {}

        for field, ind in self._ema_indicators.items():
            series = ind.calculate(candles)
            if series:
                current_ema_values[field] = series[-1] if len(series) > 0 else None
                previous_ema_values[field] = series[-2] if len(series) > 1 else None
            else:
                current_ema_values[field] = None
                previous_ema_values[field] = None

        return current_ema_values, previous_ema_values

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

    def _evaluate_condition_chain(self, conditions: List[EMACondition], current_price: float, ema_values: Dict, market_data: Optional[Dict] = None, previous_price: Optional[float] = None, previous_ema_values: Optional[Dict] = None) -> bool:
        if not conditions:
            return False
        cumulative = None
        prev_connector = None
        # Use provided previous_price, fallback to self.previous_price
        prev_price = previous_price if previous_price is not None else self.previous_price
        for cond in conditions:
            result = cond.evaluate(current_price, ema_values, prev_price, market_data, previous_ema_values)
            if cumulative is None:
                cumulative = result
            else:
                connector = prev_connector or "OR"
                if connector == "AND":
                    cumulative = cumulative and result
                else:
                    cumulative = cumulative or result
            prev_connector = cond.connector or "OR"
        return bool(cumulative)

    def generate_signal(self, market_data: Dict) -> Optional[str]:
        tick = market_data.get("tick")
        if not tick:
            return None

        candles = self._get_candles(count=300)
        if not candles:
            return None

        # For cross detection, use candle closes to match chart logic
        # Get current candle's close (even if candle is still forming)
        current_candle_close = candles[-1].get('close') if candles else None
        
        # Get previous candle's close for cross detection (matches chart logic)
        previous_candle_close = None
        if len(candles) >= 2:
            previous_candle_close = candles[-2].get('close')
        elif len(candles) >= 1:
            # If only one candle, use current candle's close as fallback
            previous_candle_close = candles[-1].get('close')
        
        # Use candle closes for cross detection, fallback to tick price
        current_price = current_candle_close if current_candle_close is not None else (tick.get("bid", 0) + tick.get("ask", 0)) / 2.0
        if current_price == 0:
            current_price = tick.get("bid", tick.get("ask", 0))
        if current_price == 0:
            return None
        
        # Use previous candle close for cross detection, fallback to stored previous_price
        previous_price_for_cross = previous_candle_close if previous_candle_close is not None else self.previous_price

        # Compute both current and previous EMA values for accurate cross detection (matches MT5)
        ema_values, previous_ema_values = self._compute_ema_values_with_previous(candles)

        # Build market_data context for unified resolver
        strategy_market_data = {
            "ema": ema_values,
            "ema_periods": self.ema_periods,  # Pass period mapping for period-based field name resolution
            "ohlc": market_data.get("ohlc", {}) if isinstance(market_data, dict) else {},
            "smc_pivots": market_data.get("smc_pivots", {}) if isinstance(market_data, dict) else {},
            "vwap": market_data.get("vwap") if isinstance(market_data, dict) else None,
            "indicators": market_data.get("indicators", {}) if isinstance(market_data, dict) else {}
        }
        
        # #region agent log
        import json
        try:
            with open(r'c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log', 'a') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "F",
                    "location": "ema_strategy.py:generate_signal",
                    "message": "Building strategy_market_data context",
                    "data": {
                        "ema_periods": self.ema_periods,
                        "ema_values_keys": list(ema_values.keys()) if ema_values else [],
                        "has_buy_conditions": len(self.buy_conditions) > 0,
                        "has_sell_conditions": len(self.sell_conditions) > 0
                    },
                    "timestamp": __import__("time").time() * 1000
                }) + "\n")
        except: pass
        # #endregion
        
        # BUY conditions take priority over SELL, consistent with OHLC strategy
        try:
            if self._evaluate_condition_chain(self.buy_conditions, current_price, ema_values, strategy_market_data, previous_price_for_cross, previous_ema_values):
                logger.info(f"EMAStrategy {self.name}: ✅ Buy conditions met")
                self.previous_price = current_price
                return "BUY"
        except Exception as e:
            logger.error(f"EMAStrategy {self.name}: Error evaluating buy conditions: {e}", exc_info=True)

        try:
            if self._evaluate_condition_chain(self.sell_conditions, current_price, ema_values, strategy_market_data, previous_price_for_cross, previous_ema_values):
                logger.info(f"EMAStrategy {self.name}: ✅ Sell conditions met")
                self.previous_price = current_price
                return "SELL"
        except Exception as e:
            logger.error(f"EMAStrategy {self.name}: Error evaluating sell conditions: {e}", exc_info=True)

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
        timeframe = data.get("timeframe")
        strategy = cls(
            name=data["name"],
            symbol=data["symbol"],
            timeframe=timeframe if timeframe is not None else None,
            ema_periods=data.get("ema_periods"),
        )
        strategy.enabled = data.get("enabled", False)
        strategy.set_mt5_connector(mt5_connector)

        # Restore common configuration (backward compatible)
        strategy.trade_monitoring_mode = data.get("trade_monitoring_mode", getattr(strategy, "trade_monitoring_mode", "LTP"))
        strategy.lot_size = data.get("lot_size", getattr(strategy, "lot_size", None))
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

        # Position Preservation
        strategy.preserve_position = data.get("preserve_position", getattr(strategy, "preserve_position", False))

        for cond_data in data.get("buy_conditions", []):
            strategy.add_buy_condition(EMACondition.from_dict(cond_data))
        for cond_data in data.get("sell_conditions", []):
            strategy.add_sell_condition(EMACondition.from_dict(cond_data))

        return strategy


