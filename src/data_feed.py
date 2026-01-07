import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
from collections import deque
import threading
import time
import queue
from PyQt6.QtCore import QObject, pyqtSignal
import MetaTrader5 as mt5

from .mt5_connector import MT5Connector

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
        
        # Database write queue to prevent blocking the data feed loop
        self.db_queue = queue.Queue()
        self.db_worker_thread: Optional[threading.Thread] = None
    
    def add_symbol(self, symbol: str) -> bool:
        """Add a symbol to monitor (case-insensitive)"""
        # #region agent log
        import json
        import time
        log_path = r"c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log"
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"id":f"log_{int(time.time()*1000)}_feed_add_symbol_entry","timestamp":int(time.time()*1000),"location":"data_feed.py:45","message":"add_symbol entry","data":{"symbol":symbol,"mt5_connected":self.mt5.is_connected()},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + "\n")
        except: pass
        # #endregion
        
        if not self.mt5.is_connected():
            logger.error("MT5 not connected")
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"id":f"log_{int(time.time()*1000)}_feed_add_symbol_no_mt5","timestamp":int(time.time()*1000),"location":"data_feed.py:47","message":"add_symbol: MT5 not connected","data":{"symbol":symbol},"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + "\n")
            except: pass
            # #endregion
            return False
        
        symbol_info = self.mt5.get_symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Symbol {symbol} not available")
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"id":f"log_{int(time.time()*1000)}_feed_add_symbol_not_available","timestamp":int(time.time()*1000),"location":"data_feed.py:52","message":"add_symbol: Symbol not available","data":{"symbol":symbol},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + "\n")
            except: pass
            # #endregion
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
        
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"id":f"log_{int(time.time()*1000)}_feed_add_symbol_success","timestamp":int(time.time()*1000),"location":"data_feed.py:70","message":"add_symbol success","data":{"symbol":symbol,"correct_symbol":correct_symbol,"symbols_count":len(self.symbols)},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + "\n")
        except: pass
        # #endregion
        
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
        # #region agent log
        import json
        import time
        log_path = r"c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log"
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"id":f"log_{int(time.time()*1000)}_feed_start_entry","timestamp":int(time.time()*1000),"location":"data_feed.py:140","message":"DataFeed start entry","data":{"running":self.running,"mt5_connected":self.mt5.is_connected(),"symbols_count":len(self.symbols)},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + "\n")
        except: pass
        # #endregion
        
        if self.running:
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"id":f"log_{int(time.time()*1000)}_feed_already_running","timestamp":int(time.time()*1000),"location":"data_feed.py:142","message":"DataFeed already running","data":{},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + "\n")
            except: pass
            # #endregion
            return
        
        if not self.mt5.is_connected():
            logger.error("Cannot start data feed: MT5 not connected")
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"id":f"log_{int(time.time()*1000)}_feed_no_mt5","timestamp":int(time.time()*1000),"location":"data_feed.py:145","message":"DataFeed cannot start: MT5 not connected","data":{},"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + "\n")
            except: pass
            # #endregion
            return
        
        self.running = True
        
        # Start data update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        
        # Start DB worker thread if manager is present
        if self.pb_manager:
            self.db_worker_thread = threading.Thread(target=self._db_worker, daemon=True)
            self.db_worker_thread.start()
            
        logger.info("Data feed started")
        
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"id":f"log_{int(time.time()*1000)}_feed_started","timestamp":int(time.time()*1000),"location":"data_feed.py:160","message":"DataFeed started successfully","data":{"running":self.running,"has_update_thread":self.update_thread is not None,"has_db_thread":self.db_worker_thread is not None},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + "\n")
        except: pass
        # #endregion
    
    def stop(self) -> None:
        """Stop live data feed"""
        self.running = False
        
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
            
        # Signal DB worker to stop (by pushing None)
        if self.db_worker_thread:
            self.db_queue.put(None)
            self.db_worker_thread.join(timeout=2.0)
            
        logger.info("Data feed stopped")
    
    def _db_worker(self) -> None:
        """Worker thread for handling database writes asynchronously"""
        while True:
            try:
                # Get task from queue (blocking)
                task = self.db_queue.get()
                
                # Check for stop signal
                if task is None:
                    break
                
                # Process task
                task_type = task.get('type')
                
                if task_type == 'tick':
                    symbol = task.get('symbol')
                    tick = task.get('data')
                    try:
                        self.pb_manager.store_tick(symbol, tick)
                    except Exception as e:
                        logger.debug(f"Error storing tick for {symbol}: {e}")
                        
                elif task_type == 'ohlc':
                    symbol = task.get('symbol')
                    timeframe = task.get('timeframe')
                    data = task.get('data')
                    try:
                        self.pb_manager.store_ohlc(symbol, timeframe, data)
                        # Log success occasionally or on debug
                        # logger.debug(f"Stored {timeframe} bar for {symbol}")
                    except Exception as e:
                        logger.error(f"Error storing {timeframe} bar for {symbol}: {e}")
                
                # Mark task as done
                self.db_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in DB worker thread: {e}")
    
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
                                
                                # Queue tick for storage (non-blocking)
                                if self.pb_manager:
                                    self.db_queue.put({
                                        'type': 'tick',
                                        'symbol': symbol,
                                        'data': tick
                                    })
                                
                                # Emit Qt signal for real-time update (always emit for latest data)
                                self.tick_received.emit(symbol, tick)
                                
                                # Call registered callbacks
                                for callback in self.callbacks.get(symbol, []):
                                    try:
                                        callback(tick)
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
            # Use get_rates directly to avoid caching logic here, we want fresh data
            rates = self.mt5.get_rates(symbol, mt5.TIMEFRAME_M1, 1, 0)
            
            if not rates or len(rates) == 0:
                return
            
            # Get the most recent closed bar
            bar = rates[0]
            bar_time = bar['time']
            
            # Check if self.mt5.get_rates returns dicts with datetime objects
            # Based on MT5Connector.get_rates, it returns dicts with 'time' as datetime
            
            # Normalize bar time to minute precision (remove seconds/microseconds)
            if isinstance(bar_time, datetime):
                bar_time_normalized = bar_time.replace(second=0, microsecond=0)
            else:
                # Should be datetime, but just in case
                logger.warning(f"Unexpected bar time type: {type(bar_time)}")
                return
            
            # Check if we've already stored this bar
            last_stored_time = self._m1_bar_cache.get(symbol)
            
            if last_stored_time is None or last_stored_time != bar_time_normalized:
                # New bar detected - prepare data
                candle_data = {
                    'time': bar_time,
                    'open': bar['open'],
                    'high': bar['high'],
                    'low': bar['low'],
                    'close': bar['close'],
                    'tick_volume': bar.get('tick_volume', 0),
                    'real_volume': bar.get('real_volume', 0)
                }
                
                # Queue for storage (non-blocking)
                self.db_queue.put({
                    'type': 'ohlc',
                    'symbol': symbol,
                    'timeframe': 'M1',
                    'data': candle_data
                })
                
                # Update cache immediately so we don't queue duplicates
                self._m1_bar_cache[symbol] = bar_time_normalized
                logger.debug(f"Queued storage of M1 bar for {symbol} at {bar_time_normalized}")
            
        except Exception as e:
            logger.debug(f"Error checking M1 bar for {symbol}: {e}")

