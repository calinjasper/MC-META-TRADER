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
    
    def __init__(self, mt5_connector: MT5Connector, pb_manager=None):
        """
        Initialize RealTimeIndicatorFeed
        
        Args:
            mt5_connector: MT5 connector instance
            pb_manager: Optional PocketBase manager for indicator storage
        """
        super().__init__()
        self.mt5 = mt5_connector
        self.indicator_manager = MT5IndicatorManager(mt5_connector)
        self.pb_manager = pb_manager  # PocketBase manager for indicator storage
        
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
                
                # Emit signal for real-time updates (if Qt is available)
                try:
                    self.indicators_updated.emit(symbol, indicator_values)
                except (RuntimeError, AttributeError):
                    # Qt not available (headless mode) - signals will fail silently
                    pass
                
                # Store indicators in PocketBase if manager is available
                if self.pb_manager:
                    try:
                        import MetaTrader5 as mt5
                        # Convert MT5 timeframe constant to string
                        timeframe_map = {
                            mt5.TIMEFRAME_M1: "M1",
                            mt5.TIMEFRAME_M5: "M5",
                            mt5.TIMEFRAME_M15: "M15",
                            mt5.TIMEFRAME_M30: "M30",
                            mt5.TIMEFRAME_H1: "H1",
                            mt5.TIMEFRAME_H4: "H4",
                            mt5.TIMEFRAME_D1: "D1",
                        }
                        timeframe_str = timeframe_map.get(timeframe, f"TF{timeframe}")
                        current_time = datetime.now()
                        
                        for indicator_name, indicator_value in indicator_values.items():
                            # Handle complex indicator values (e.g., MACD returns dict)
                            if isinstance(indicator_value, dict):
                                # Store each component separately
                                for component_name, component_value in indicator_value.items():
                                    if isinstance(component_value, (int, float)):
                                        self.pb_manager.store_indicator(
                                            symbol=symbol,
                                            timeframe=timeframe_str,
                                            timestamp=current_time,
                                            indicator_name=f"{indicator_name}_{component_name}",
                                            value=component_value,
                                            metadata={'full_name': indicator_name, 'component': component_name}
                                        )
                            elif isinstance(indicator_value, (int, float)):
                                # Simple numeric value
                                self.pb_manager.store_indicator(
                                    symbol=symbol,
                                    timeframe=timeframe_str,
                                    timestamp=current_time,
                                    indicator_name=indicator_name,
                                    value=indicator_value
                                )
                    except Exception as e:
                        logger.debug(f"Error storing indicators in PocketBase: {e}")
                
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

