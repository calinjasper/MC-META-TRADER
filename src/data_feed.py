"""
Data Feed Manager
Handles live price streaming and historical data retrieval with caching
"""

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
from collections import deque
import threading
import time
from PyQt6.QtCore import QObject, pyqtSignal
import MetaTrader5 as mt5

from .mt5_connector import MT5Connector
from .indicators.smc_data_tracker import SMCDataTracker

logger = logging.getLogger(__name__)

class DataFeed(QObject):
    """Manages live data feeds and historical data with caching"""
    
    # Signals for Qt integration
    tick_received = pyqtSignal(str, dict)  # symbol, tick_data
    data_updated = pyqtSignal(str, list)   # symbol, rates
    indicators_updated = pyqtSignal(str, dict)  # symbol, indicators_dict
    
    def __init__(self, mt5_connector: MT5Connector, update_interval: float = 0.1, pb_manager=None):
        super().__init__()
        self.mt5 = mt5_connector
        self.pb_manager = pb_manager  # PocketBase manager for data storage
        self.symbols: List[str] = []
        self.tick_cache: Dict[str, deque] = {}  # symbol -> deque of recent ticks
        self.rates_cache: Dict[str, Dict[int, List[Dict]]] = {}  # symbol -> {timeframe -> rates}
        self.cache_size = 1000
        self.running = False
        self.update_thread: Optional[threading.Thread] = None
        self.update_interval = update_interval  # seconds - configurable update interval for real-time data
        self.callbacks: Dict[str, List[Callable]] = {}  # symbol -> list of callbacks
        # Cache for tracking last stored M1 bar timestamp per symbol
        # Format: {symbol: timestamp (datetime)} - tracks the timestamp of the last stored M1 bar
        self._m1_bar_cache: Dict[str, Optional[datetime]] = {}
        # Track last M1 check time to avoid checking too frequently (once per second)
        self._last_m1_check_time: float = 0.0
        
        # SMC Data Tracker for real-time pivot data
        self.smc_tracker = SMCDataTracker(
            pivot_left=2,
            pivot_right=2,
            emit_on="NONE",  # Track pivots by default
            timeframe=5,  # M5 default
            candle_buffer_size=200
        )
        # Track last SMC update time per symbol (update once per second, not every tick)
        self._last_smc_update_time: Dict[str, float] = {}
    
    def add_symbol(self, symbol: str) -> bool:
        """Add a symbol to monitor (case-insensitive)"""
        if not self.mt5.is_connected():
            logger.error("MT5 not connected")
            return False
        
        symbol_info = self.mt5.get_symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Symbol {symbol} not available")
            return False
        
        # Use the correct symbol name as returned by MT5 (correct case)
        correct_symbol = symbol_info['name']
        
        # Check if already added (case-insensitive)
        symbol_upper = correct_symbol.upper()
        for existing_symbol in self.symbols:
            if existing_symbol.upper() == symbol_upper:
                logger.info(f"Symbol {correct_symbol} already added")
                return True
        
        self.symbols.append(correct_symbol)
        self.tick_cache[correct_symbol] = deque(maxlen=self.cache_size)
        self.rates_cache[correct_symbol] = {}
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
            if symbol in self._m1_bar_cache:
                del self._m1_bar_cache[symbol]
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
                current_time = time.time()
                # Check for M1 bars once per second (optimization)
                should_check_m1 = (current_time - self._last_m1_check_time) >= 1.0
                
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
                                
                                # Store tick in PocketBase
                                if self.pb_manager:
                                    try:
                                        self.pb_manager.store_tick(symbol, tick)
                                    except Exception as e:
                                        logger.debug(f"Error storing tick in PocketBase: {e}")
                                
                                # Update SMC data (once per second per symbol for efficiency)
                                smc_data = self._update_smc_data(symbol, current_time)
                                
                                # Add SMC data to tick for emission
                                tick_with_smc = tick.copy()
                                tick_with_smc['smc'] = smc_data
                                
                                # Emit Qt signal for real-time update (always emit for latest data)
                                self.tick_received.emit(symbol, tick_with_smc)
                                
                                # Call registered callbacks
                                for callback in self.callbacks.get(symbol, []):
                                    try:
                                        callback(tick_with_smc)
                                    except Exception as e:
                                        logger.error(f"Error in callback for {symbol}: {e}")
                        
                        # Check and store M1 bar if it's time (once per second)
                        if should_check_m1:
                            try:
                                self._check_and_store_m1_bar(symbol)
                            except Exception as e:
                                logger.debug(f"Error checking M1 bar for {symbol}: {e}")
                                
                    except Exception as e:
                        # Log error for specific symbol but continue with other symbols
                        logger.error(f"Error getting tick for {symbol}: {e}")
                        continue
                
                # Update last M1 check time if we checked
                if should_check_m1:
                    self._last_m1_check_time = current_time
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in data feed update loop: {e}")
                time.sleep(self.update_interval)
    
    def refresh_rates(self, symbol: str, timeframe: int) -> None:
        """Manually refresh rates for a symbol and timeframe"""
        rates = self.get_rates(symbol, timeframe, 1000)
        if rates:
            self.data_updated.emit(symbol, rates)
    
    def _check_and_store_m1_bar(self, symbol: str) -> None:
        """
        Check for new M1 bar and store it in PocketBase if detected.
        Only stores closed bars (most recent closed bar from MT5).
        
        Args:
            symbol: Trading symbol to check
        """
        if not self.pb_manager:
            return
        
        if not self.mt5.is_connected():
            return
        
        try:
            # Get the most recent closed M1 bar (position 0 is the most recent closed bar)
            rates = self.mt5.get_rates(symbol, mt5.TIMEFRAME_M1, 1, 0)
            
            if not rates or len(rates) == 0:
                return
            
            # Get the most recent closed bar
            bar = rates[0]
            bar_time = bar['time']
            
            # Check if this is a datetime object or needs conversion
            if not isinstance(bar_time, datetime):
                # If it's a timestamp, convert it
                if isinstance(bar_time, (int, float)):
                    # Assume it's a Unix timestamp in seconds
                    bar_time = datetime.fromtimestamp(bar_time)
                else:
                    logger.warning(f"Unexpected bar time format for {symbol}: {type(bar_time)}")
                    return
            
            # Normalize bar time to minute precision (remove seconds/microseconds)
            bar_time_normalized = bar_time.replace(second=0, microsecond=0)
            
            # Check if we've already stored this bar
            last_stored_time = self._m1_bar_cache.get(symbol)
            
            if last_stored_time is None or last_stored_time != bar_time_normalized:
                # New bar detected - store it
                candle_data = {
                    'time': bar_time,
                    'open': bar['open'],
                    'high': bar['high'],
                    'low': bar['low'],
                    'close': bar['close'],
                    'tick_volume': bar.get('tick_volume', 0),
                    'real_volume': bar.get('real_volume', 0)
                }
                
                # Store in PocketBase
                try:
                    self.pb_manager.store_ohlc(symbol, 'M1', candle_data)
                    # Update cache with new bar timestamp
                    self._m1_bar_cache[symbol] = bar_time_normalized
                    logger.debug(f"Stored M1 bar for {symbol} at {bar_time_normalized}")
                except Exception as e:
                    logger.error(f"Error storing M1 bar for {symbol} in PocketBase: {e}")
            
        except Exception as e:
            logger.debug(f"Error checking M1 bar for {symbol}: {e}")

    def _update_smc_data(self, symbol: str, current_time: float) -> Dict:
        """
        Update SMC data for a symbol if needed.
        Updates once per second per symbol for efficiency.
        
        Args:
            symbol: Trading symbol
            current_time: Current timestamp
            
        Returns:
            SMC data dictionary
        """
        # Check if we need to update (once per second per symbol)
        last_update = self._last_smc_update_time.get(symbol, 0)
        
        if current_time - last_update >= 1.0:
            # Time to update SMC data
            try:
                # Get candles for SMC calculation
                timeframe = self.smc_tracker.timeframe
                rates = self.get_rates(symbol, timeframe, 200)
                
                if rates:
                    # Convert rates to candle format
                    candles = []
                    for rate in rates:
                        candles.append({
                            'time': rate.get('time'),
                            'open': rate.get('open'),
                            'high': rate.get('high'),
                            'low': rate.get('low'),
                            'close': rate.get('close'),
                            'volume': rate.get('tick_volume', 0)
                        })
                    
                    # Update SMC tracker
                    self.smc_tracker.update_candles(symbol, candles)
                
                self._last_smc_update_time[symbol] = current_time
                
            except Exception as e:
                logger.debug(f"Error updating SMC data for {symbol}: {e}")
        
        # Return current SMC data (even if not updated this tick)
        return self.smc_tracker.get_smc_data(symbol)
    
    def get_smc_data(self, symbol: str) -> Dict:
        """
        Get SMC data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            SMC data dictionary with pivot_high, pivot_low, choch_price, bos_price
        """
        return self.smc_tracker.get_smc_data(symbol)
    
    def set_smc_parameters(self, pivot_left: int = None, pivot_right: int = None,
                           emit_on: str = None, timeframe: int = None) -> None:
        """
        Update SMC tracker parameters.
        
        Args:
            pivot_left: Number of bars to the left for pivot detection
            pivot_right: Number of bars to the right for pivot detection
            emit_on: "NONE" (pivots only), "CHoCH", "BOS", "BOTH"
            timeframe: Timeframe for candle data (5 = M5)
        """
        self.smc_tracker.set_parameters(pivot_left, pivot_right, emit_on, timeframe)
        
        # Clear last update times to force refresh
        self._last_smc_update_time.clear()
        logger.info(f"SMC parameters updated: pivot_left={pivot_left}, pivot_right={pivot_right}, "
                   f"emit_on={emit_on}, timeframe={timeframe}")