"""
MT5 Indicator Exporter Service
Exports Python-calculated indicator values to MT5-readable JSON files
"""

import logging
import json
import os
import tempfile
from typing import Dict, Optional, Set
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

from .indicator_calculator import IndicatorCalculator
from ..mt5_connector import MT5Connector
from ..mt5_utils import find_mt5_data_folder
from ..data_feed import DataFeed

logger = logging.getLogger(__name__)


class MT5IndicatorExporter(QObject):
    """Exports indicator values to MT5 data folder for real-time chart display"""
    
    # Signal emitted when indicators are exported
    indicators_exported = pyqtSignal(str, int, dict)  # symbol, timeframe, indicators_dict
    
    def __init__(self, mt5_connector: MT5Connector, data_feed: DataFeed):
        """
        Initialize MT5 indicator exporter
        
        Args:
            mt5_connector: MT5 connector instance
            data_feed: Data feed instance for receiving tick updates
        """
        super().__init__()
        self.mt5 = mt5_connector
        self.data_feed = data_feed
        self.calculator = IndicatorCalculator(mt5_connector)
        
        # Find MT5 data folder
        self.mt5_data_folder = find_mt5_data_folder()
        if self.mt5_data_folder:
            self.export_folder = os.path.join(self.mt5_data_folder, "PythonIndicators")
            # Create export folder if it doesn't exist
            os.makedirs(self.export_folder, exist_ok=True)
            logger.info(f"MT5 Indicator Exporter initialized. Export folder: {self.export_folder}")
        else:
            logger.warning("MT5 data folder not found. Indicator export will be disabled.")
            self.export_folder = None
        
        # Track symbols and timeframes being exported
        self.exported_symbols: Set[str] = set()
        self.timeframes: Dict[str, int] = {}  # symbol -> timeframe
        
        # Track last exported values to avoid unnecessary writes
        self.last_exported: Dict[str, Dict] = {}  # {f"{symbol}_{timeframe}": indicators_dict}
        
        # Connect to data feed signals
        if data_feed:
            data_feed.tick_received.connect(self._on_tick_received)
    
    def _on_tick_received(self, symbol: str, tick_data: Dict):
        """
        Handle tick received signal
        
        Args:
            symbol: Trading symbol
            tick_data: Tick data dictionary
        """
        if not self.export_folder:
            return
        
        # Get timeframe for this symbol (default to M1 if not set)
        timeframe = self.timeframes.get(symbol, None)
        if timeframe is None:
            # Default to M1 for real-time updates
            import MetaTrader5 as mt5
            timeframe = mt5.TIMEFRAME_M1
            self.timeframes[symbol] = timeframe
        
        # Export indicators for this symbol/timeframe
        self.export_indicators(symbol, timeframe)
    
    def add_symbol(self, symbol: str, timeframe: Optional[int] = None):
        """
        Add symbol to export list
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe constant (default: M1)
        """
        if timeframe is None:
            import MetaTrader5 as mt5
            timeframe = mt5.TIMEFRAME_M1
        
        self.exported_symbols.add(symbol)
        self.timeframes[symbol] = timeframe
        logger.info(f"Added {symbol} (timeframe: {timeframe}) to indicator export")
    
    def remove_symbol(self, symbol: str):
        """Remove symbol from export list"""
        if symbol in self.exported_symbols:
            self.exported_symbols.remove(symbol)
        if symbol in self.timeframes:
            del self.timeframes[symbol]
        logger.info(f"Removed {symbol} from indicator export")
    
    def export_indicators(self, symbol: str, timeframe: int) -> bool:
        """
        Calculate and export indicators for symbol/timeframe
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe constant
            
        Returns:
            True if export successful, False otherwise
        """
        if not self.export_folder:
            return False
        
        try:
            # Calculate all indicators
            indicators = self.calculator.calculate_all_indicators(symbol, timeframe)
            
            if not indicators:
                logger.debug(f"No indicators calculated for {symbol} {timeframe}")
                return False
            
            # Check if values have changed (avoid unnecessary writes)
            cache_key = f"{symbol}_{timeframe}"
            if cache_key in self.last_exported:
                if self._indicators_equal(indicators, self.last_exported[cache_key]):
                    # Values haven't changed, skip write
                    return True
            
            # Convert timeframe to string representation
            timeframe_str = self._timeframe_to_string(timeframe)
            
            # Prepare export data
            export_data = {
                "symbol": symbol,
                "timeframe": timeframe_str,
                "timestamp": int(datetime.now().timestamp()),
                "indicators": indicators
            }
            
            # Write to file (atomic write)
            filename = f"{symbol}_{timeframe_str}_indicators.json"
            filepath = os.path.join(self.export_folder, filename)
            
            # Atomic write: write to temp file first, then rename
            try:
                with tempfile.NamedTemporaryFile(mode='w', dir=self.export_folder, 
                                                 delete=False, suffix='.tmp') as tmp_file:
                    json.dump(export_data, tmp_file, indent=2)
                    tmp_path = tmp_file.name
                
                # Rename temp file to final file (atomic on Windows)
                if os.path.exists(filepath):
                    os.remove(filepath)
                os.rename(tmp_path, filepath)
                
                # Update cache
                self.last_exported[cache_key] = indicators.copy()
                
                # Emit signal
                self.indicators_exported.emit(symbol, timeframe, indicators)
                
                logger.debug(f"Exported indicators for {symbol} {timeframe_str}: {len(indicators)} indicators")
                return True
                
            except Exception as e:
                logger.error(f"Error writing indicator file for {symbol} {timeframe_str}: {e}", exc_info=True)
                # Clean up temp file if it exists
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
                return False
        
        except Exception as e:
            logger.error(f"Error exporting indicators for {symbol} {timeframe}: {e}", exc_info=True)
            return False
    
    def _indicators_equal(self, indicators1: Dict, indicators2: Dict) -> bool:
        """Check if two indicator dictionaries are equal (within tolerance)"""
        if set(indicators1.keys()) != set(indicators2.keys()):
            return False
        
        tolerance = 0.0001  # Small tolerance for floating point comparison
        
        for key in indicators1.keys():
            val1 = indicators1[key]
            val2 = indicators2[key]
            
            # Handle nested dictionaries (like MACD)
            if isinstance(val1, dict) and isinstance(val2, dict):
                if not self._indicators_equal(val1, val2):
                    return False
            elif isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                if abs(val1 - val2) > tolerance:
                    return False
            elif val1 != val2:
                return False
        
        return True
    
    def _timeframe_to_string(self, timeframe: int) -> str:
        """Convert MT5 timeframe constant to string"""
        import MetaTrader5 as mt5
        
        timeframe_map = {
            mt5.TIMEFRAME_M1: "M1",
            mt5.TIMEFRAME_M5: "M5",
            mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_M30: "M30",
            mt5.TIMEFRAME_H1: "H1",
            mt5.TIMEFRAME_H4: "H4",
            mt5.TIMEFRAME_D1: "D1",
            mt5.TIMEFRAME_W1: "W1",
            mt5.TIMEFRAME_MN1: "MN1",
        }
        
        return timeframe_map.get(timeframe, f"TF{timeframe}")
    
    def export_all_symbols(self):
        """Export indicators for all tracked symbols"""
        for symbol in self.exported_symbols:
            timeframe = self.timeframes.get(symbol)
            if timeframe:
                self.export_indicators(symbol, timeframe)
    
    def get_export_folder(self) -> Optional[str]:
        """Get the export folder path"""
        return self.export_folder

