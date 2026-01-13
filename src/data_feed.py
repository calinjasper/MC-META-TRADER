"""
Data Feed Manager
Handles live price streaming and historical data retrieval with caching
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal
import MetaTrader5 as mt5

from .mt5_connector import MT5Connector, UTC

logger = logging.getLogger(__name__)

class DataFeed(QObject):
    """Manages live data feeds and historical data with caching"""
    
    # Signals for Qt integration
    tick_received = pyqtSignal(str, dict)  # symbol, tick_data
    data_updated = pyqtSignal(str, list)   # symbol, rates
    indicators_updated = pyqtSignal(str, dict)  # symbol, indicators_dict
    
    def __init__(self, mt5_connector: MT5Connector, update_interval: float = 0.1, mysql_manager=None):
        super().__init__()
        self.mt5 = mt5_connector
        self.mysql_manager = mysql_manager  # MySQL manager for data storage
        self.symbols: List[str] = []
        self.tick_cache: Dict[str, deque] = {}  # symbol -> deque of recent ticks
        self.rates_cache: Dict[str, Dict[int, List[Dict]]] = {}  # symbol -> {timeframe -> rates}
        self.cache_size = 1000
        self.running = False
        self.update_thread: Optional[threading.Thread] = None
        self.update_interval = update_interval  # seconds - configurable update interval for real-time data
        self.callbacks: Dict[str, List[Callable]] = {}  # symbol -> list of callbacks
        # Allowed symbols for MySQL storage
        # Allowed symbols for MySQL storage (normalized - without 'm' suffix)
        # These will be normalized in mysql_manager.store_tick()
        self.allowed_symbols = ['XAUUSD', 'EURUSD', 'EURJPY', 'USDJPY', 'BTCUSD']
    
    def add_symbol(self, symbol: str) -> bool:
        """Add a symbol to monitor (case-insensitive) - only allowed symbols for MySQL storage"""
        if not self.mt5.is_connected():
            logger.error("MT5 not connected")
            return False
        
        symbol_info = self.mt5.get_symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Symbol {symbol} not available")
            return False
        
        # Use the correct symbol name as returned by MT5 (correct case)
        correct_symbol = symbol_info['name']
        symbol_upper = correct_symbol.upper()
        
        # Check if symbol is in allowed list for MySQL storage
        if symbol_upper not in [s.upper() for s in self.allowed_symbols]:
            logger.warning(f"Symbol {correct_symbol} is not in allowed list for MySQL storage: {self.allowed_symbols}")
            logger.warning(f"Symbol will be monitored but data will not be stored in MySQL")
        
        # Check if already added (case-insensitive)
        for existing_symbol in self.symbols:
            if existing_symbol.upper() == symbol_upper:
                logger.info(f"Symbol {correct_symbol} already added")
                return True
        
        self.symbols.append(correct_symbol)
        self.tick_cache[correct_symbol] = deque(maxlen=self.cache_size)
        self.rates_cache[correct_symbol] = {}
        if correct_symbol not in self.callbacks:
            self.callbacks[correct_symbol] = []
        logger.info(f"Added symbol: {correct_symbol}")
        
        return True
    
    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from monitoring"""
        if symbol in self.symbols:
            self.symbols.remove(symbol)
            if symbol in self.tick_cache:
                del self.tick_cache[symbol]
            if symbol in self.rates_cache:
                del self.rates_cache[symbol]
            if symbol in self.callbacks:
                del self.callbacks[symbol]
            # Symbol removed - any cleanup needed can go here
            logger.info(f"Removed symbol: {symbol}")
    
    def get_latest_tick(self, symbol: str) -> Optional[Dict]:
        """Get latest tick for symbol - always gets fresh data from MT5"""
        # Always get fresh data from MT5 to avoid stale cache
        tick = self.mt5.get_tick(symbol)
        if tick:
            # Update cache with fresh data
            if symbol not in self.tick_cache:
                self.tick_cache[symbol] = deque(maxlen=self.cache_size)
            self.tick_cache[symbol].append(tick)
        return tick
    
    def get_rates(self, symbol: str, timeframe: int, count: int = 1000) -> Optional[List[Dict]]:
        """
        Get historical rates with caching
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe constant
            count: Number of bars
            
        Returns:
            List of rate dictionaries
        """
        # Check cache first
        if symbol in self.rates_cache and timeframe in self.rates_cache[symbol]:
            cached = self.rates_cache[symbol][timeframe]
            if len(cached) >= count:
                return cached[-count:]
        
        # Fetch from MT5
        rates = self.mt5.get_rates(symbol, timeframe, count)
        if rates:
            # Update cache
            if symbol not in self.rates_cache:
                self.rates_cache[symbol] = {}
            self.rates_cache[symbol][timeframe] = rates
            return rates
        
        return None
    
    def register_callback(self, symbol: str, callback: Callable) -> None:
        """Register a callback function for tick updates"""
        if symbol not in self.callbacks:
            self.callbacks[symbol] = []
        if callback not in self.callbacks[symbol]:
            self.callbacks[symbol].append(callback)
    
    def unregister_callback(self, symbol: str, callback: Callable) -> None:
        """Unregister a callback function"""
        if symbol in self.callbacks and callback in self.callbacks[symbol]:
            self.callbacks[symbol].remove(callback)
    
    def start(self) -> None:
        """Start live data feed"""
        if self.running:
            return
        
        if not self.mt5.is_connected():
            logger.error("Cannot start data feed: MT5 not connected")
            return
        
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        logger.info("Data feed started")
    
    def stop(self) -> None:
        """Stop live data feed"""
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
        logger.info("Data feed stopped")
    
    def _update_loop(self) -> None:
        """Main update loop running in separate thread - real-time price updates"""
        while self.running:
            try:
                for symbol in self.symbols:
                    try:
                        # Always get fresh tick data (no caching in get_tick)
                        tick = self.mt5.get_tick(symbol)
                        if tick:
                            # Get last tick from cache for comparison
                            last_tick = None
                            if symbol in self.tick_cache and len(self.tick_cache[symbol]) > 0:
                                last_tick = self.tick_cache[symbol][-1]
                            
                            # Use epsilon for floating point comparison (1 pip = 0.00001 for 5-digit)
                            epsilon = 0.00001
                            
                            # Update if:
                            # 1. No previous tick exists
                            # 2. Time has changed (new tick)
                            # 3. Price has changed (bid or ask) - using epsilon for comparison
                            should_update = False
                            if last_tick is None:
                                should_update = True
                            elif tick['time'] != last_tick['time']:
                                should_update = True
                            elif (abs(tick['bid'] - last_tick['bid']) > epsilon or 
                                  abs(tick['ask'] - last_tick['ask']) > epsilon):
                                # Price changed - update immediately
                                should_update = True
                            
                            if should_update:
                                # New tick or price change detected
                                self.tick_cache[symbol].append(tick)
                                
                                # Store raw tick in MySQL (only for allowed symbols)
                                # Note: mysql_manager.store_tick() will normalize the symbol (remove 'm' suffix)
                                if self.mysql_manager:
                                    try:
                                        self.mysql_manager.store_tick(symbol, tick)
                                    except Exception as e:
                                        logger.debug(f"Error storing tick in MySQL: {e}")
                                
                                # Emit Qt signal for real-time update (if Qt is available)
                                try:
                                    self.tick_received.emit(symbol, tick)
                                except (RuntimeError, AttributeError):
                                    # Qt not available (headless mode) - signals will fail silently
                                    pass
                                
                                # Call registered callbacks (works in both GUI and headless mode)
                                for callback in self.callbacks.get(symbol, []):
                                    try:
                                        callback(symbol, tick)
                                    except Exception as e:
                                        logger.error(f"Error in callback for {symbol}: {e}")
                                
                    except Exception as e:
                        # Log error for specific symbol but continue with other symbols
                        logger.error(f"Error getting tick for {symbol}: {e}")
                        continue
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in data feed update loop: {e}")
                time.sleep(self.update_interval)
    
    def refresh_rates(self, symbol: str, timeframe: int) -> None:
        """Manually refresh rates for a symbol and timeframe"""
        rates = self.get_rates(symbol, timeframe, 1000)
        if rates:
            self.data_updated.emit(symbol, rates)
    

