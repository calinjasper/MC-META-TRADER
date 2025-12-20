"""
MT5 Built-in Indicators Wrapper
Provides real-time indicator values using MT5's native indicator calculations
"""

import logging
import MetaTrader5 as mt5
from typing import Optional, Dict, List, Tuple

logger = logging.getLogger(__name__)


class MT5IndicatorManager:
    """Manages MT5 indicator handles for real-time calculations"""
    
    def __init__(self, mt5_connector):
        self.mt5_connector = mt5_connector
        self.indicator_handles = {}  # Cache indicator handles
    
    def get_rsi(self, symbol: str, timeframe: int, period: int = 14) -> Optional[float]:
        """Get RSI value using MT5's built-in calculation"""
        if not self.mt5_connector.is_connected():
            return None
        
        try:
            rsi_handle = mt5.iRSI(symbol, timeframe, period)
            if rsi_handle == mt5.INVALID_HANDLE:
                logger.warning(f"Failed to create RSI indicator handle: {mt5.last_error()}")
                return None
            
            rsi_values = mt5.copy_indicator_buffer(rsi_handle, 0, 0, 1)
            mt5.IndicatorRelease(rsi_handle)
            
            if rsi_values is None or len(rsi_values) == 0:
                return None
            
            return float(rsi_values[0])
        except Exception as e:
            logger.error(f"Error getting RSI: {e}")
            return None
    
    def get_macd(self, symbol: str, timeframe: int, 
                 fast_ema: int = 12, slow_ema: int = 26, signal_sma: int = 9) -> Optional[Dict[str, float]]:
        """Get MACD values (MACD line, Signal line, Histogram)"""
        if not self.mt5_connector.is_connected():
            return None
        
        try:
            macd_handle = mt5.iMACD(symbol, timeframe, fast_ema, slow_ema, signal_sma, 0)  # 0 = MODE_CLOSE
            if macd_handle == mt5.INVALID_HANDLE:
                logger.warning(f"Failed to create MACD indicator handle: {mt5.last_error()}")
                return None
            
            # Get MACD line (buffer 0), Signal line (buffer 1), Histogram (buffer 2)
            macd_line = mt5.copy_indicator_buffer(macd_handle, 0, 0, 1)
            signal_line = mt5.copy_indicator_buffer(macd_handle, 1, 0, 1)
            histogram = mt5.copy_indicator_buffer(macd_handle, 2, 0, 1)
            mt5.IndicatorRelease(macd_handle)
            
            if macd_line is None or len(macd_line) == 0:
                return None
            
            return {
                'macd': float(macd_line[0]),
                'signal': float(signal_line[0]) if signal_line and len(signal_line) > 0 else None,
                'histogram': float(histogram[0]) if histogram and len(histogram) > 0 else None
            }
        except Exception as e:
            logger.error(f"Error getting MACD: {e}")
            return None
    
    def get_bollinger_bands(self, symbol: str, timeframe: int, 
                           period: int = 20, deviation: float = 2.0) -> Optional[Dict[str, float]]:
        """Get Bollinger Bands (Upper, Middle, Lower)"""
        if not self.mt5_connector.is_connected():
            return None
        
        try:
            bb_handle = mt5.iBands(symbol, timeframe, period, 0, deviation, 0)  # 0 = MODE_CLOSE
            if bb_handle == mt5.INVALID_HANDLE:
                logger.warning(f"Failed to create Bollinger Bands indicator handle: {mt5.last_error()}")
                return None
            
            # Get Upper (buffer 0), Middle (buffer 1), Lower (buffer 2)
            upper = mt5.copy_indicator_buffer(bb_handle, 0, 0, 1)
            middle = mt5.copy_indicator_buffer(bb_handle, 1, 0, 1)
            lower = mt5.copy_indicator_buffer(bb_handle, 2, 0, 1)
            mt5.IndicatorRelease(bb_handle)
            
            if upper is None or len(upper) == 0:
                return None
            
            return {
                'upper': float(upper[0]),
                'middle': float(middle[0]) if middle and len(middle) > 0 else None,
                'lower': float(lower[0]) if lower and len(lower) > 0 else None
            }
        except Exception as e:
            logger.error(f"Error getting Bollinger Bands: {e}")
            return None
    
    def get_stochastic(self, symbol: str, timeframe: int,
                      k_period: int = 5, d_period: int = 3, slowing: int = 3) -> Optional[Dict[str, float]]:
        """Get Stochastic values (%K and %D)"""
        if not self.mt5_connector.is_connected():
            return None
        
        try:
            # MT5 iStochastic: symbol, timeframe, %K period, %D period, slowing, method, price
            # method: 0=MODE_SMA, 1=MODE_EMA, 2=MODE_SMMA, 3=MODE_LWMA
            # price: 0=MODE_LOW, 1=MODE_HIGH, 2=MODE_CLOSE
            stoch_handle = mt5.iStochastic(symbol, timeframe, k_period, d_period, slowing, 0, 0)  # 0=MODE_SMA, 0=MODE_LOW
            if stoch_handle == mt5.INVALID_HANDLE:
                logger.warning(f"Failed to create Stochastic indicator handle: {mt5.last_error()}")
                return None
            
            # Get %K (buffer 0), %D (buffer 1)
            k_line = mt5.copy_indicator_buffer(stoch_handle, 0, 0, 1)
            d_line = mt5.copy_indicator_buffer(stoch_handle, 1, 0, 1)
            mt5.IndicatorRelease(stoch_handle)
            
            if k_line is None or len(k_line) == 0:
                return None
            
            return {
                'k': float(k_line[0]),
                'd': float(d_line[0]) if d_line and len(d_line) > 0 else None
            }
        except Exception as e:
            logger.error(f"Error getting Stochastic: {e}")
            return None
    
    def get_moving_average(self, symbol: str, timeframe: int, period: int, 
                          ma_method: int = 0, applied_price: int = 0) -> Optional[float]:
        """Get Moving Average value (SMA, EMA, etc.)"""
        if not self.mt5_connector.is_connected():
            return None
        
        try:
            ma_handle = mt5.iMA(symbol, timeframe, period, 0, ma_method, applied_price)
            if ma_handle == mt5.INVALID_HANDLE:
                logger.warning(f"Failed to create MA indicator handle: {mt5.last_error()}")
                return None
            
            ma_values = mt5.copy_indicator_buffer(ma_handle, 0, 0, 1)
            mt5.IndicatorRelease(ma_handle)
            
            if ma_values is None or len(ma_values) == 0:
                return None
            
            return float(ma_values[0])
        except Exception as e:
            logger.error(f"Error getting Moving Average: {e}")
            return None
    
    def get_all_indicators(self, symbol: str, timeframe: int, 
                          indicator_config: Dict) -> Dict[str, any]:
        """
        Get all requested indicators at once for efficiency
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe
            indicator_config: Dict with indicator names and their parameters
                Example: {
                    'RSI': {'period': 14},
                    'MACD': {'fast': 12, 'slow': 26, 'signal': 9},
                    'BB': {'period': 20, 'deviation': 2.0},
                    'Stochastic': {'k': 5, 'd': 3, 'slowing': 3},
                    'SMA': {'period': 20}
                }
        
        Returns:
            Dict with indicator values
        """
        results = {}
        
        for ind_name, params in indicator_config.items():
            try:
                if ind_name.upper() == 'RSI':
                    period = params.get('period', 14)
                    value = self.get_rsi(symbol, timeframe, period)
                    if value is not None:
                        results['RSI'] = value
                
                elif ind_name.upper() == 'MACD':
                    fast = params.get('fast', 12)
                    slow = params.get('slow', 26)
                    signal = params.get('signal', 9)
                    value = self.get_macd(symbol, timeframe, fast, slow, signal)
                    if value:
                        results['MACD'] = value
                
                elif ind_name.upper() in ['BB', 'BOLLINGER', 'BOLLINGERBANDS']:
                    period = params.get('period', 20)
                    deviation = params.get('deviation', 2.0)
                    value = self.get_bollinger_bands(symbol, timeframe, period, deviation)
                    if value:
                        results['BollingerBands'] = value
                
                elif ind_name.upper() in ['STOCH', 'STOCHASTIC']:
                    k = params.get('k', 5)
                    d = params.get('d', 3)
                    slowing = params.get('slowing', 3)
                    value = self.get_stochastic(symbol, timeframe, k, d, slowing)
                    if value:
                        results['Stochastic'] = value
                
                elif ind_name.upper() in ['SMA', 'EMA']:
                    period = params.get('period', 20)
                    # MT5 iMA method: 0=MODE_SMA, 1=MODE_EMA, 2=MODE_SMMA, 3=MODE_LWMA
                    ma_method = 1 if ind_name.upper() == 'EMA' else 0  # 1=MODE_EMA, 0=MODE_SMA
                    value = self.get_moving_average(symbol, timeframe, period, ma_method)
                    if value is not None:
                        results[ind_name.upper()] = value
                
            except Exception as e:
                logger.error(f"Error getting indicator {ind_name}: {e}")
                continue
        
        return results

