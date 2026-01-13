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
            - 'smc_pivots': Dict with 'pivot_high', 'pivot_low', 'choch_price', 'bos_price'
            - 'vwap': VWAP data dict
            - 'ema': EMA values dict
            - 'indicators': General indicators dict
    
    Returns:
        Resolved numeric value or None if field cannot be resolved
    """
    if not field:
        return None
    
    # Price fields (support multiple names)
    if field in ("price", "current_price"):
        price = context.get("price")
        if price is not None:
            return float(price)
        # Fallback: try to get from ohlc close
        ohlc = context.get("ohlc")
        if ohlc and ohlc.get("close") is not None:
            return float(ohlc.get("close"))
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
    
    # SMC pivot and event fields
    smc_pivots = context.get("smc_pivots")
    if smc_pivots:
        if field == "smc_pivot_high":
            val = smc_pivots.get("pivot_high")
            return float(val) if val is not None else None
        if field == "smc_pivot_low":
            val = smc_pivots.get("pivot_low")
            return float(val) if val is not None else None
        if field == "smc_choch_price":
            val = smc_pivots.get("choch_price")
            return float(val) if val is not None else None
        if field == "smc_bos_price":
            val = smc_pivots.get("bos_price")
            return float(val) if val is not None else None
    
    # VWAP fields
    vwap_data = context.get("vwap")
    if vwap_data:
        if field == "vwap":
            val = vwap_data.get("vwap")
            return float(val) if val is not None else None
        if field.startswith("upper_band_"):
            try:
                std = float(field.replace("upper_band_", ""))
                bands = vwap_data.get("bands", {})
                band_data = bands.get(std, {})
                val = band_data.get("upper")
                return float(val) if val is not None else None
            except (ValueError, TypeError):
                return None
        if field.startswith("lower_band_"):
            try:
                std = float(field.replace("lower_band_", ""))
                bands = vwap_data.get("bands", {})
                band_data = bands.get(std, {})
                val = band_data.get("lower")
                return float(val) if val is not None else None
            except (ValueError, TypeError):
                return None
    
    # EMA fields
    ema_data = context.get("ema")
    if ema_data:
        if field.startswith("ema_"):
            val = ema_data.get(field)
            return float(val) if val is not None else None
    
    # Session First Candle fields
    session_first_candle = context.get("session_first_candle")
    if session_first_candle:
        if field in ("session_high_line", "session_high", "high_line"):
            val = session_first_candle.get("session_high")
            return float(val) if val is not None else None
        if field in ("session_low_line", "session_low", "low_line"):
            val = session_first_candle.get("session_low")
            return float(val) if val is not None else None
    
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

