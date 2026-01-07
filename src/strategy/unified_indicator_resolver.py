"""
Unified Indicator Resolver
Provides a single point of resolution for all indicator types across all strategy types.
Allows mixing any indicator type (SMC, OHLC, VWAP, EMA, etc.) in any strategy.
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def resolve_operand(field: str, context: Dict) -> Optional[float]:
    """
    Resolve an operand field to a numeric value.
    
    Supports:
    - Price fields: 'price'
    - OHLC fields: 'open', 'high', 'low', 'close', 'hl2', 'hlc3', 'ohlc4'
    - SMC fields: 'smc_pivot_high', 'smc_pivot_low'
    - VWAP fields: 'vwap', 'upper_band_X', 'lower_band_X'
    - EMA fields: 'ema_1', 'ema_2', etc.
    - Any indicator from context['indicators']
    
    Args:
        field: Field name to resolve
        context: Dictionary containing:
            - 'price': Current price (float)
            - 'ohlc': OHLC data dict with 'open', 'high', 'low', 'close'
            - 'smc_pivots': Dict with 'pivot_high', 'pivot_low'
            - 'vwap': VWAP data dict
            - 'ema': EMA values dict
            - 'indicators': General indicators dict
    
    Returns:
        Resolved numeric value or None if field cannot be resolved
    """
    if not field:
        return None
    
    # Price field
    if field == "price":
        price = context.get("price")
        if price is not None:
            return float(price)
        return None
    
    # OHLC fields
    ohlc = context.get("ohlc")
    if ohlc:
        if field == "open":
            val = ohlc.get("open")
            return float(val) if val is not None else None
        if field == "high":
            val = ohlc.get("high")
            return float(val) if val is not None else None
        if field == "low":
            val = ohlc.get("low")
            return float(val) if val is not None else None
        if field == "close":
            val = ohlc.get("close")
            return float(val) if val is not None else None
        if field == "hl2":
            h = ohlc.get("high")
            l = ohlc.get("low")
            if h is not None and l is not None:
                return (float(h) + float(l)) / 2.0
        if field == "hlc3":
            h = ohlc.get("high")
            l = ohlc.get("low")
            c = ohlc.get("close")
            if h is not None and l is not None and c is not None:
                return (float(h) + float(l) + float(c)) / 3.0
        if field == "ohlc4":
            o = ohlc.get("open")
            h = ohlc.get("high")
            l = ohlc.get("low")
            c = ohlc.get("close")
            if o is not None and h is not None and l is not None and c is not None:
                return (float(o) + float(h) + float(l) + float(c)) / 4.0
    
    # SMC pivot fields
    smc_pivots = context.get("smc_pivots")
    if smc_pivots:
        if field == "smc_pivot_high":
            val = smc_pivots.get("pivot_high")
            return float(val) if val is not None else None
        if field == "smc_pivot_low":
            val = smc_pivots.get("pivot_low")
            return float(val) if val is not None else None
    
    # VWAP fields
    vwap_data = context.get("vwap")
    # Check if vwap_data exists and is a dict (check isinstance first to avoid errors)
    if vwap_data is not None and isinstance(vwap_data, dict):
        if field == "vwap":
            val = vwap_data.get("vwap")
            return float(val) if val is not None else None
        # Support both "upper_band_X" and "vwap_upper_X" formats
        if field.startswith("upper_band_") or field.startswith("vwap_upper_"):
            logger.debug(f"Attempting to resolve VWAP upper band field '{field}' from vwap_data with keys: {list(vwap_data.keys())}")
            try:
                # Extract std dev from either format
                std_str = field.replace("upper_band_", "").replace("vwap_upper_", "")
                std = float(std_str)
                bands = vwap_data.get("bands", {})
                if not bands:
                    logger.debug(f"VWAP bands dict is empty for field '{field}'. vwap_data keys: {list(vwap_data.keys())}")
                    return None
                # Try to get band data - handle both float and string keys
                band_data = bands.get(std, {})
                if not band_data:
                    # Try with string key as fallback
                    band_data = bands.get(str(std), {})
                val = band_data.get("upper") if band_data else None
                if val is not None:
                    return float(val)
                logger.debug(f"Could not find upper band for std={std} in bands. Available std keys: {list(bands.keys())}")
                return None
            except (ValueError, TypeError) as e:
                logger.debug(f"Error parsing VWAP upper band field '{field}': {e}")
                return None
        # Support both "lower_band_X" and "vwap_lower_X" formats
        if field.startswith("lower_band_") or field.startswith("vwap_lower_"):
            logger.debug(f"Attempting to resolve VWAP lower band field '{field}' from vwap_data with keys: {list(vwap_data.keys())}")
            try:
                # Extract std dev from either format
                std_str = field.replace("lower_band_", "").replace("vwap_lower_", "")
                std = float(std_str)
                bands = vwap_data.get("bands", {})
                if not bands:
                    logger.debug(f"VWAP bands dict is empty for field '{field}'. vwap_data keys: {list(vwap_data.keys())}")
                    return None
                # Try to get band data - handle both float and string keys
                band_data = bands.get(std, {})
                if not band_data:
                    # Try with string key as fallback
                    band_data = bands.get(str(std), {})
                val = band_data.get("lower") if band_data else None
                if val is not None:
                    return float(val)
                logger.debug(f"Could not find lower band for std={std} in bands. Available std keys: {list(bands.keys())}")
                return None
            except (ValueError, TypeError) as e:
                logger.debug(f"Error parsing VWAP lower band field '{field}': {e}")
                return None
    
    # EMA fields
    ema_data = context.get("ema")
    if ema_data:
        if field.startswith("ema_"):
            # First try direct lookup (position-based like "ema_1")
            val = ema_data.get(field)
            if val is not None:
                # #region agent log
                import json
                try:
                    with open(r'c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log', 'a') as f:
                        f.write(json.dumps({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "E",
                            "location": "unified_indicator_resolver.py:resolve_operand",
                            "message": "Direct EMA lookup success",
                            "data": {
                                "field": field,
                                "value": float(val)
                            },
                            "timestamp": __import__("time").time() * 1000
                        }) + "\n")
                except: pass
                # #endregion
                return float(val)
            
            # If not found, try period-based lookup (e.g., "ema_20" -> find which ema_X has period 20)
            ema_periods = context.get("ema_periods")
            # #region agent log
            try:
                with open(r'c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log', 'a') as f:
                    f.write(json.dumps({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "E",
                        "location": "unified_indicator_resolver.py:resolve_operand",
                        "message": "Attempting period-based EMA lookup",
                        "data": {
                            "field": field,
                            "has_ema_periods": ema_periods is not None,
                            "ema_periods": ema_periods,
                            "ema_data_keys": list(ema_data.keys())
                        },
                        "timestamp": __import__("time").time() * 1000
                    }) + "\n")
            except: pass
            # #endregion
            if ema_periods:
                try:
                    period_str = field.replace("ema_", "")
                    period = int(period_str)
                    # Find which ema_X has this period
                    for ema_key, ema_period in ema_periods.items():
                        if ema_period == period:
                            # Found the matching ema_X, return its value
                            val = ema_data.get(ema_key)
                            if val is not None:
                                # #region agent log
                                try:
                                    with open(r'c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log', 'a') as f:
                                        f.write(json.dumps({
                                            "sessionId": "debug-session",
                                            "runId": "run1",
                                            "hypothesisId": "E",
                                            "location": "unified_indicator_resolver.py:resolve_operand",
                                            "message": "Period-based EMA mapping success",
                                            "data": {
                                                "field": field,
                                                "period": period,
                                                "mapped_to": ema_key,
                                                "value": float(val)
                                            },
                                            "timestamp": __import__("time").time() * 1000
                                        }) + "\n")
                                except: pass
                                # #endregion
                                return float(val)
                except ValueError:
                    # Not a valid period number, return None
                    pass
            return None
    
    # General indicators from market_data['indicators']
    indicators = context.get("indicators", {})
    if field in indicators:
        val = indicators[field]
        return float(val) if val is not None else None
    
    # Try case-insensitive match for indicators
    for key, val in indicators.items():
        if key.upper() == field.upper():
            return float(val) if val is not None else None
    
    # If field looks like a numeric value, try to parse it
    try:
        return float(field)
    except (ValueError, TypeError):
        pass
    
    logger.debug(f"Could not resolve field '{field}' from context. Available keys: {list(context.keys())}")
    return None

