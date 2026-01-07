"""
Indicator Calculator Service
Centralized service to calculate all indicators for given symbol/timeframe
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import MetaTrader5 as mt5

from .ema import EMA
from .rsi import RSI
from .macd import MACD
from .bollinger_bands import BollingerBands
from .stochastic import Stochastic
from .vwap import VWAP
from ..mt5_connector import MT5Connector

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """Centralized service to calculate all indicators"""
    
    def __init__(self, mt5_connector: MT5Connector):
        """
        Initialize indicator calculator
        
        Args:
            mt5_connector: MT5 connector instance
        """
        self.mt5 = mt5_connector
        # Cache indicator instances per symbol/timeframe
        self.indicator_cache: Dict[str, Dict] = {}  # {f"{symbol}_{timeframe}": {indicator_name: instance}}
    
    def _get_cache_key(self, symbol: str, timeframe: int) -> str:
        """Generate cache key for symbol and timeframe"""
        return f"{symbol}_{timeframe}"
    
    def _get_candles(self, symbol: str, timeframe: int, count: int = 500) -> Optional[List[Dict]]:
        """
        Get candle data for symbol and timeframe
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe constant
            count: Number of candles to retrieve
            
        Returns:
            List of candle dictionaries or None
        """
        if not self.mt5.is_connected():
            return None
        
        try:
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
            if rates is None or len(rates) == 0:
                return None
            
            # Convert to list of dictionaries
            candles = []
            for rate in rates:
                candles.append({
                    'time': datetime.fromtimestamp(rate[0], tz=mt5.UTC),
                    'open': float(rate[1]),
                    'high': float(rate[2]),
                    'low': float(rate[3]),
                    'close': float(rate[4]),
                    'tick_volume': int(rate[5]),
                    'spread': int(rate[6]),
                    'real_volume': int(rate[7]) if len(rate) > 7 else 0
                })
            
            return candles
        except Exception as e:
            logger.error(f"Error getting candles for {symbol} {timeframe}: {e}", exc_info=True)
            return None
    
    def _get_or_create_indicator(self, cache_key: str, indicator_name: str, indicator_class, *args, **kwargs):
        """Get cached indicator instance or create new one"""
        if cache_key not in self.indicator_cache:
            self.indicator_cache[cache_key] = {}
        
        if indicator_name not in self.indicator_cache[cache_key]:
            self.indicator_cache[cache_key][indicator_name] = indicator_class(*args, **kwargs)
        
        return self.indicator_cache[cache_key][indicator_name]
    
    def calculate_all_indicators(self, symbol: str, timeframe: int, 
                                 ema_periods: List[int] = None,
                                 vwap_session: str = 'NY',
                                 rsi_period: int = 14,
                                 macd_fast: int = 12, macd_slow: int = 26, macd_signal: int = 9,
                                 bb_period: int = 20, bb_std: float = 2.0,
                                 stoch_k: int = 14, stoch_d: int = 3, stoch_slowing: int = 3) -> Dict:
        """
        Calculate all indicators for given symbol and timeframe
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe constant
            ema_periods: List of EMA periods to calculate (default: [50, 200])
            vwap_session: VWAP session type (default: 'NY')
            rsi_period: RSI period (default: 14)
            macd_fast: MACD fast period (default: 12)
            macd_slow: MACD slow period (default: 26)
            macd_signal: MACD signal period (default: 9)
            bb_period: Bollinger Bands period (default: 20)
            bb_std: Bollinger Bands standard deviation (default: 2.0)
            stoch_k: Stochastic %K period (default: 14)
            stoch_d: Stochastic %D period (default: 3)
            stoch_slowing: Stochastic slowing (default: 3)
            
        Returns:
            Dictionary with all indicator values
        """
        if ema_periods is None:
            ema_periods = [50, 200]
        
        # Get candle data
        candles = self._get_candles(symbol, timeframe, count=500)
        if not candles or len(candles) == 0:
            logger.warning(f"No candles available for {symbol} {timeframe}")
            return {}
        
        cache_key = self._get_cache_key(symbol, timeframe)
        results = {}
        
        try:
            # Calculate EMAs
            for period in ema_periods:
                ema = self._get_or_create_indicator(cache_key, f"EMA_{period}", EMA, period)
                ema_values = ema.calculate(candles)
                if ema_values and len(ema_values) > 0:
                    latest_value = ema_values[-1]
                    if latest_value is not None:
                        results[f"EMA_{period}"] = float(latest_value)
            
            # Calculate VWAP
            vwap = self._get_or_create_indicator(cache_key, f"VWAP_{vwap_session}", VWAP, vwap_session)
            vwap.calculate(candles)
            vwap_value = vwap.get_vwap()
            if vwap_value is not None:
                results["VWAP"] = float(vwap_value)
            
            # Calculate RSI
            rsi = self._get_or_create_indicator(cache_key, f"RSI_{rsi_period}", RSI, rsi_period)
            rsi_values = rsi.calculate(candles)
            if rsi_values and len(rsi_values) > 0:
                latest_rsi = rsi_values[-1]
                if latest_rsi is not None:
                    results["RSI"] = float(latest_rsi)
            
            # Calculate MACD
            macd = self._get_or_create_indicator(cache_key, f"MACD_{macd_fast}_{macd_slow}_{macd_signal}", 
                                                 MACD, macd_fast, macd_slow, macd_signal)
            macd_values = macd.calculate(candles)
            if macd_values and len(macd_values) > 0:
                latest_macd = macd_values[-1]
                signal_line = macd.get_signal_line()
                histogram = macd.get_histogram()
                
                if latest_macd is not None:
                    macd_dict = {"macd": float(latest_macd)}
                    if signal_line and len(signal_line) > 0 and signal_line[-1] is not None:
                        macd_dict["signal"] = float(signal_line[-1])
                    if histogram and len(histogram) > 0 and histogram[-1] is not None:
                        macd_dict["histogram"] = float(histogram[-1])
                    results["MACD"] = macd_dict
            
            # Calculate Bollinger Bands
            bb = self._get_or_create_indicator(cache_key, f"BB_{bb_period}_{bb_std}", 
                                              BollingerBands, bb_period, bb_std)
            bb_values = bb.calculate(candles)
            if bb_values and len(bb_values) > 0:
                upper_band = bb.get_upper_band()
                lower_band = bb.get_lower_band()
                middle_band = bb.get_middle_band()
                
                if upper_band and len(upper_band) > 0 and upper_band[-1] is not None:
                    results["BB_Upper"] = float(upper_band[-1])
                if middle_band and len(middle_band) > 0 and middle_band[-1] is not None:
                    results["BB_Middle"] = float(middle_band[-1])
                if lower_band and len(lower_band) > 0 and lower_band[-1] is not None:
                    results["BB_Lower"] = float(lower_band[-1])
            
            # Calculate Stochastic
            stoch = self._get_or_create_indicator(cache_key, f"Stoch_{stoch_k}_{stoch_d}_{stoch_slowing}",
                                                 Stochastic, stoch_k, stoch_d, stoch_slowing)
            stoch_values = stoch.calculate(candles)
            if stoch_values and len(stoch_values) > 0:
                latest_k = stoch_values[-1]
                percent_d = stoch.get_percent_d()
                
                if latest_k is not None:
                    results["Stochastic_K"] = float(latest_k)
                if percent_d and len(percent_d) > 0 and percent_d[-1] is not None:
                    results["Stochastic_D"] = float(percent_d[-1])
            
            # Calculate SuperTrend (from strategy module)
            try:
                from ..strategy.supertrend_strategy import compute_supertrend
                
                # Default SuperTrend parameters
                atr_period = 10
                atr_multiplier = 3.0
                use_wilder = True
                
                trend, atr, up_final, dn_final = compute_supertrend(
                    candles, atr_period, atr_multiplier, use_wilder
                )
                
                if trend and len(trend) > 0 and up_final and len(up_final) > 0 and dn_final and len(dn_final) > 0:
                    # Get latest values
                    latest_trend = trend[-1]
                    latest_up = up_final[-1]
                    latest_dn = dn_final[-1]
                    
                    if latest_up is not None and latest_dn is not None:
                        results["SuperTrend"] = float(latest_up if latest_trend == 1 else latest_dn)
                        results["SuperTrend_Upper"] = float(latest_up)
                        results["SuperTrend_Lower"] = float(latest_dn)
            except Exception as e:
                logger.debug(f"Error calculating SuperTrend: {e}")
        
        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol} {timeframe}: {e}", exc_info=True)
        
        return results
    
    def clear_cache(self, symbol: Optional[str] = None, timeframe: Optional[int] = None):
        """
        Clear indicator cache
        
        Args:
            symbol: If provided, clear only for this symbol
            timeframe: If provided, clear only for this timeframe
        """
        if symbol and timeframe:
            cache_key = self._get_cache_key(symbol, timeframe)
            if cache_key in self.indicator_cache:
                del self.indicator_cache[cache_key]
        elif symbol:
            # Clear all timeframes for symbol
            keys_to_remove = [k for k in self.indicator_cache.keys() if k.startswith(f"{symbol}_")]
            for key in keys_to_remove:
                del self.indicator_cache[key]
        else:
            # Clear all
            self.indicator_cache.clear()

