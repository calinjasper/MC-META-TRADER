"""
Mixed condition evaluator.

Supports operands from:
- price/tick
- OHLC (open, high, low, close, hl2, hlc3, ohlc4)
- VWAP (vwap, upper/lower bands)
- EMA values (ema_1..ema_4)

The evaluator is intentionally self contained so it can be reused by
different strategy UIs without wiring to a specific strategy class yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def _resolve_ohlc(field: str, ohlc: Optional[Dict]) -> Optional[float]:
    if not ohlc:
        return None
    if field == "open":
        return ohlc.get("open")
    if field == "high":
        return ohlc.get("high")
    if field == "low":
        return ohlc.get("low")
    if field == "close":
        return ohlc.get("close")
    if field == "hl2":
        h, l = ohlc.get("high"), ohlc.get("low")
        return (h + l) / 2.0 if h is not None and l is not None else None
    if field == "hlc3":
        h, l, c = ohlc.get("high"), ohlc.get("low"), ohlc.get("close")
        return (h + l + c) / 3.0 if None not in (h, l, c) else None
    if field == "ohlc4":
        o, h, l, c = ohlc.get("open"), ohlc.get("high"), ohlc.get("low"), ohlc.get("close")
        return (o + h + l + c) / 4.0 if None not in (o, h, l, c) else None
    return None


def _resolve_vwap(field: str, vwap_data: Optional[Dict]) -> Optional[float]:
    if not vwap_data:
        return None
    if field == "vwap":
        return vwap_data.get("vwap")
    if field.startswith("upper_band_"):
        try:
            std = float(field.replace("upper_band_", ""))
        except ValueError:
            return None
        return vwap_data.get("bands", {}).get(std, {}).get("upper")
    if field.startswith("lower_band_"):
        try:
            std = float(field.replace("lower_band_", ""))
        except ValueError:
            return None
        return vwap_data.get("bands", {}).get(std, {}).get("lower")
    return None


def _resolve_ema(field: str, ema_values: Optional[Dict]) -> Optional[float]:
    if not ema_values:
        return None
    if field.startswith("ema_"):
        return ema_values.get(field)
    return None


def _resolve_indicators(field: str, indicators: Optional[Dict]) -> Optional[float]:
    """Resolve indicator values (Volume, RSI, Stochastic, etc.)"""
    if not indicators:
        return None
    
    # Direct indicator name lookup (case-insensitive)
    field_lower = field.lower()
    for key, value in indicators.items():
        if key.lower() == field_lower:
            # Get the latest value if it's a list/series
            if isinstance(value, list) and len(value) > 0:
                # Get last non-None value
                for v in reversed(value):
                    if v is not None:
                        return float(v)
                return None
            elif value is not None:
                return float(value)
    
    # Special handling for Volume_MA (volume moving average)
    if field_lower == "volume_ma":
        volume_ind = indicators.get("Volume") or indicators.get("volume")
        if volume_ind and hasattr(volume_ind, 'get_volume_ma'):
            ma = volume_ind.get_volume_ma()
            return float(ma) if ma is not None else None
        # Try to get from indicators dict directly
        volume_ma = indicators.get("Volume_MA") or indicators.get("volume_ma")
        if volume_ma is not None:
            return float(volume_ma)
    
    # Special handling for Stochastic %K and %D
    if field_lower in ["stochastic_k", "stochastic"]:
        stoch_ind = indicators.get("Stochastic") or indicators.get("stochastic")
        if stoch_ind and hasattr(stoch_ind, 'percent_k'):
            k_values = stoch_ind.percent_k
            if isinstance(k_values, list) and len(k_values) > 0:
                # Get last non-None value
                for v in reversed(k_values):
                    if v is not None:
                        return float(v)
            elif k_values is not None:
                return float(k_values)
        # Try direct lookup
        stoch_k = indicators.get("Stochastic_K") or indicators.get("stochastic_k")
        if stoch_k is not None:
            if isinstance(stoch_k, list) and len(stoch_k) > 0:
                for v in reversed(stoch_k):
                    if v is not None:
                        return float(v)
            else:
                return float(stoch_k)
    
    if field_lower == "stochastic_d":
        stoch_ind = indicators.get("Stochastic") or indicators.get("stochastic")
        if stoch_ind and hasattr(stoch_ind, 'percent_d'):
            d_values = stoch_ind.percent_d
            if isinstance(d_values, list) and len(d_values) > 0:
                # Get last non-None value
                for v in reversed(d_values):
                    if v is not None:
                        return float(v)
            elif d_values is not None:
                return float(d_values)
        # Try direct lookup
        stoch_d = indicators.get("Stochastic_D") or indicators.get("stochastic_d")
        if stoch_d is not None:
            if isinstance(stoch_d, list) and len(stoch_d) > 0:
                for v in reversed(stoch_d):
                    if v is not None:
                        return float(v)
            else:
                return float(stoch_d)
    
    return None


@dataclass
class MixedCondition:
    """
    A generic condition that can mix operands across price/OHLC/VWAP/EMA.

    left_field/right_field are operand identifiers (e.g., price, open, vwap,
    upper_band_1.5, ema_1, etc.). connector is stored to chain conditions
    externally.
    """

    operator: str
    left_field: str = "price"
    right_field: Optional[str] = None
    connector: str = "OR"
    price_reference: str = "Current Price"
    value: Optional[float] = None
    previous_state: Optional[bool] = None

    def _resolve_operand(self, field: Optional[str], context: Dict) -> Optional[float]:
        if field in (None, "", "price"):
            return context.get("price")

        # OHLC first
        ohlc_val = _resolve_ohlc(field, context.get("ohlc"))
        if ohlc_val is not None:
            return ohlc_val

        # VWAP bands/VWAP
        vwap_val = _resolve_vwap(field, context.get("vwap"))
        if vwap_val is not None:
            return vwap_val

        # EMA values
        ema_val = _resolve_ema(field, context.get("ema"))
        if ema_val is not None:
            return ema_val

        # Indicator values (Volume, RSI, Stochastic, etc.)
        indicators = context.get("indicators", {})
        indicator_val = _resolve_indicators(field, indicators)
        if indicator_val is not None:
            return indicator_val

        # Fallback to explicit value (useful for constants)
        if self.value is not None:
            return self.value

        return None

    def evaluate(self, context: Dict, previous_price: Optional[float] = None) -> bool:
        """
        Evaluate the condition.

        context keys expected (optional):
            price: float
            ohlc: {open, high, low, close}
            vwap: {vwap, bands:{std:{upper,lower}}}
            ema: {ema_1, ema_2, ...}
            indicators: {Volume, RSI, Stochastic, ...} - dict of indicator objects or values
        """
        try:
            left_val = self._resolve_operand(self.left_field, context)
            right_val = self._resolve_operand(self.right_field, context)
        except Exception as e:
            logger.error(f"MixedCondition: error resolving operands: {e}", exc_info=True)
            return False

        if left_val is None or right_val is None:
            return False

        # Band checks
        if self.operator == "Within Band":
            # right_field must be a band
            if self.right_field and "band" in self.right_field:
                lower = _resolve_vwap(f"lower_band_{self.right_field.split('_')[-1]}", context.get("vwap"))
                upper = _resolve_vwap(f"upper_band_{self.right_field.split('_')[-1]}", context.get("vwap"))
                if lower is not None and upper is not None:
                    return lower <= left_val <= upper
            return False

        if self.operator == "Outside Band":
            if self.right_field and "band" in self.right_field:
                lower = _resolve_vwap(f"lower_band_{self.right_field.split('_')[-1]}", context.get("vwap"))
                upper = _resolve_vwap(f"upper_band_{self.right_field.split('_')[-1]}", context.get("vwap"))
                if lower is not None and upper is not None:
                    return left_val < lower or left_val > upper
            return False

        # Cross detection
        if self.operator == "Crosses Above":
            if previous_price is not None:
                was_below = previous_price < right_val
                is_above = left_val >= right_val
                if was_below and is_above:
                    self.previous_state = True
                    return True
            self.previous_state = left_val >= right_val
            return False

        if self.operator == "Crosses Under":
            if previous_price is not None:
                was_above = previous_price > right_val
                is_below = left_val <= right_val
                if was_above and is_below:
                    self.previous_state = False
                    return True
            self.previous_state = left_val > right_val
            return False

        if self.operator == "Any_Cross":
            if previous_price is not None:
                crossed_up = previous_price < right_val <= left_val
                crossed_down = previous_price > right_val >= left_val
                if crossed_up or crossed_down:
                    self.previous_state = left_val >= right_val
                    return True
            self.previous_state = left_val >= right_val
            return False

        # Simple comparisons
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

        logger.warning(f"MixedCondition: unsupported operator '{self.operator}'")
        return False

    def to_dict(self) -> Dict:
        return {
            "price_reference": self.price_reference,
            "operator": self.operator,
            "left_field": self.left_field,
            "right_field": self.right_field,
            "connector": self.connector,
            "value": self.value,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MixedCondition":
        return cls(
            operator=data.get("operator", ">"),
            left_field=data.get("left_field", "price"),
            right_field=data.get("right_field"),
            connector=data.get("connector", data.get("logical_connector", "OR")),
            price_reference=data.get("price_reference", "Current Price"),
            value=data.get("value"),
        )


