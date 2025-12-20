"""
Real-Time Indicator Feed
Updates indicators automatically when new price data arrives
"""

import logging
from typing import Dict, List, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime
import MetaTrader5 as mt5

from ..mt5_connector import MT5Connector
from .mt5_indicators import MT5IndicatorManager

logger = logging.getLogger(__name__)


class RealTimeIndicatorFeed(QObject):
    """Real-time indicator feed that updates with price ticks"""
    
    # Signal emitted when indicators are updated
    indicators_updated = pyqtSignal(str, dict)  # symbol, indicators_dict
    
    def __init__(self, mt5_connector: MT5Connector):
        super().__init__()
        self.mt5 = mt5_connector
        self.indicator_manager = MT5IndicatorManager(mt5_connector)
        
        # Track symbols and their indicator configurations
        self.symbol_configs: Dict[str, Dict] = {}  # symbol -> {timeframe, indicators}
        
        # Cache latest indicator values
        self.indicator_cache: Dict[str, Dict] = {}  # symbol -> indicators_dict
    
    def subscribe(self, symbol: str, timeframe: int, indicators: List[str], 
                  indicator_params: Optional[Dict] = None):
        """
        Subscribe to real-time indicator updates for a symbol
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe
            indicators: List of indicator names (e.g., ['RSI', 'MACD', 'BB'])
            indicator_params: Optional dict with indicator parameters
                Example: {
                    'RSI': {'period': 14},
                    'MACD': {'fast': 12, 'slow': 26, 'signal': 9}
                }
        """
        if indicator_params is None:
            indicator_params = {}
        
        # Default parameters for common indicators
        default_params = {
            'RSI': {'period': 14},
            'MACD': {'fast': 12, 'slow': 26, 'signal': 9},
            'BB': {'period': 20, 'deviation': 2.0},
            'BollingerBands': {'period': 20, 'deviation': 2.0},
            'Stochastic': {'k': 5, 'd': 3, 'slowing': 3},
            'SMA': {'period': 20},
            'EMA': {'period': 20}
        }
        
        # Merge default and custom parameters
        config = {}
        for ind in indicators:
            config[ind] = indicator_params.get(ind, default_params.get(ind, {}))
        
        self.symbol_configs[symbol] = {
            'timeframe': timeframe,
            'indicators': config
        }
        
        logger.info(f"Subscribed to indicators for {symbol}: {indicators}")
    
    def unsubscribe(self, symbol: str):
        """Unsubscribe from indicator updates for a symbol"""
        if symbol in self.symbol_configs:
            del self.symbol_configs[symbol]
        if symbol in self.indicator_cache:
            del self.indicator_cache[symbol]
        logger.info(f"Unsubscribed from indicators for {symbol}")
    
    def update_indicators(self, symbol: str):
        """
        Update indicators for a symbol (called when new tick arrives)
        
        Args:
            symbol: Trading symbol to update indicators for
        """
        if symbol not in self.symbol_configs:
            return
        
        if not self.mt5.is_connected():
            return
        
        config = self.symbol_configs[symbol]
        timeframe = config['timeframe']
        indicators_config = config['indicators']
        
        try:
            # Get all indicators at once
            indicator_values = self.indicator_manager.get_all_indicators(
                symbol, timeframe, indicators_config
            )
            
            if indicator_values:
                # Update cache
                self.indicator_cache[symbol] = indicator_values
                
                # Emit signal for real-time updates
                self.indicators_updated.emit(symbol, indicator_values)
                
                logger.debug(f"Updated indicators for {symbol}: {indicator_values}")
        
        except Exception as e:
            logger.error(f"Error updating indicators for {symbol}: {e}", exc_info=True)
    
    def get_latest_indicators(self, symbol: str) -> Optional[Dict]:
        """Get latest cached indicator values for a symbol"""
        return self.indicator_cache.get(symbol)
    
    def get_indicator_value(self, symbol: str, indicator_name: str) -> Optional[any]:
        """
        Get latest value for a specific indicator
        
        Args:
            symbol: Trading symbol
            indicator_name: Name of indicator (e.g., 'RSI', 'MACD')
        
        Returns:
            Indicator value or None
        """
        indicators = self.indicator_cache.get(symbol)
        if indicators:
            return indicators.get(indicator_name)
        return None

