"""
MetaTrader 5 Connector
Handles connection, data retrieval, and order execution with MT5
"""

import MetaTrader5 as mt5
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import time

# UTC timezone support for MT5 timestamps (MT5 returns UTC timestamps)
try:
    from zoneinfo import ZoneInfo
    UTC = ZoneInfo("UTC")
except ImportError:
    # Fallback for Python < 3.9
    try:
        import pytz
        UTC = pytz.UTC
    except ImportError:
        # If neither available, use UTC offset manually
        from datetime import timezone
        UTC = timezone.utc


logger = logging.getLogger(__name__)

# Log that enhanced diagnostic code is active
logger.info("MT5Connector: Enhanced diagnostic logging is ACTIVE")


class MT5Connector:
    """MetaTrader 5 API wrapper"""
    
    def __init__(self):
        self.connected = False
        self.account_info = None
        self.last_error: Optional[str] = None
        # Cache for M1 bars per symbol to optimize volume retrieval
        # Format: {symbol: {'bar_time': datetime, 'tick_volume': int}}
        self._m1_bar_cache: Dict[str, Dict] = {}
    
    def initialize(self, path: str = "", login: int = 0, password: str = "", 
                   server: str = "", timeout: int = 10000) -> bool:
        """
        Initialize and connect to MT5 terminal
        
        Args:
            path: Path to MT5 terminal executable (empty for auto-detect)
            login: Account login number
            password: Account password
            server: Trading server name
            timeout: Connection timeout in milliseconds
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Initialize MT5
            if path:
                if not mt5.initialize(path=path):
                    logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                    return False
            else:
                if not mt5.initialize():
                    logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                    return False
            
            # Login if credentials provided
            if login and password and server:
                authorized = mt5.login(login, password=password, server=server, timeout=timeout)
                if not authorized:
                    logger.error(f"MT5 login failed: {mt5.last_error()}")
                    mt5.shutdown()
                    return False
                logger.info(f"Connected to MT5 account {login}")
            
            # Get account info
            self.account_info = mt5.account_info()
            if self.account_info is None:
                logger.warning("Could not retrieve account info")
            else:
                logger.info(f"Account balance: {self.account_info.balance}")
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Error initializing MT5: {e}")
            self.connected = False
            return False
    
    def shutdown(self) -> None:
        """Close MT5 connection"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("MT5 connection closed")

        # Reset last error on shutdown
        self.last_error = None
    
    def is_connected(self) -> bool:
        """Check if connected to MT5"""
        return self.connected and mt5.terminal_info() is not None

    def get_last_error(self) -> Optional[str]:
        """Return the last MT5 error message captured by this connector"""
        return self.last_error
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account information"""
        if not self.is_connected():
            return None
        
        account = mt5.account_info()
        if account is None:
            return None
        
        return {
            'login': account.login,
            'balance': account.balance,
            'equity': account.equity,
            'margin': account.margin,
            'free_margin': account.margin_free,
            'margin_level': account.margin_level,
            'profit': account.profit,
            'currency': account.currency,
            'server': account.server,
            'leverage': account.leverage,
        }
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol information (case-insensitive)"""
        if not self.is_connected():
            return None
        
        # Try exact match first
        symbol_info = mt5.symbol_info(symbol)
        
        # If not found, try case-insensitive match
        if symbol_info is None:
            available_symbols = self.get_available_symbols()
            symbol_upper = symbol.upper()
            for available_symbol in available_symbols:
                if available_symbol.upper() == symbol_upper:
                    symbol_info = mt5.symbol_info(available_symbol)
                    if symbol_info:
                        logger.info(f"Found symbol '{available_symbol}' for input '{symbol}'")
                        break
        
        if symbol_info is None:
            logger.warning(f"Symbol {symbol} not found")
            return None
        
        return {
            'name': symbol_info.name,
            'bid': symbol_info.bid,
            'ask': symbol_info.ask,
            'spread': symbol_info.spread,
            'digits': symbol_info.digits,
            'point': symbol_info.point,
            'volume_min': symbol_info.volume_min,
            'volume_max': symbol_info.volume_max,
            'volume_step': symbol_info.volume_step,
            'trade_mode': symbol_info.trade_mode,
            'trade_stops_level': symbol_info.trade_stops_level,
        }
    
    def get_available_symbols(self, group: str = "*") -> List[str]:
        """
        Get list of available symbols from MT5
        
        Args:
            group: Symbol group filter (e.g., "*" for all, "EUR*" for EUR pairs)
            
        Returns:
            List of symbol names
        """
        if not self.is_connected():
            return []
        
        symbols = mt5.symbols_get(group)
        if symbols is None:
            logger.warning("Could not retrieve symbols list")
            return []
        
        # Filter only symbols that are visible and tradeable
        # Also include symbols that might not be visible but are tradeable
        available = []
        for symbol in symbols:
            # Include if visible and tradeable, or if tradeable (some brokers hide symbols but they're still tradeable)
            if symbol.trade_mode > 0:  # 0 = disabled, >0 means enabled
                if symbol.visible or symbol.trade_mode == 4:  # 4 = full trading allowed
                    available.append(symbol.name)
        
        # If we still have very few symbols, try including all tradeable symbols regardless of visibility
        if len(available) < 10:
            available = []
            for symbol in symbols:
                if symbol.trade_mode > 0:
                    available.append(symbol.name)
        
        # If still very few, include all symbols (some brokers have different trade_mode values)
        if len(available) < 5:
            available = [symbol.name for symbol in symbols]
        
        return sorted(available)
    
    def get_tick(self, symbol: str) -> Optional[Dict]:
        """
        Get latest tick data for symbol - always gets the absolute latest from MT5
        
        Note: Some MetaTrader5 Python builds do not expose `copy_ticks_from_pos`.
        We therefore use `symbol_info_tick()` as the primary method to avoid
        repeated AttributeError spam and ensure stable real-time updates.
        
        Volume is retrieved from the most recent M1 (1-minute) OHLC bar's tick_volume
        as a proxy, since individual tick volume from symbol_info_tick() is often 0.
        """
        if not self.is_connected():
            return None

        # Ensure symbol is selected (some brokers require this for ticks/rates)
        try:
            mt5.symbol_select(symbol, True)
        except Exception:
            pass

        # Primary: symbol_info_tick (stable across MetaTrader5 package versions)
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            
            # Use last price if available, otherwise calculate mid price (bid + ask) / 2
            last_price = tick.last if tick.last > 0 else (tick.bid + tick.ask) / 2.0
            
            # MT5 timestamps are in UTC, create UTC-aware datetime
            tick_time = datetime.fromtimestamp(tick.time, tz=UTC)
            
            # Get volume from most recent M1 bar (proxy for tick volume)
            # tick.volume is often 0 for individual ticks, so we use M1 bar's tick_volume
            volume = self._get_m1_bar_volume(symbol, tick_time)
            if volume == 0:
                # Fallback to tick.volume if M1 bar fetch fails
                volume = tick.volume
            
            return {
                'symbol': symbol,
                'time': tick_time,
                'bid': tick.bid,
                'ask': tick.ask,
                'last': last_price,
                'volume': volume,
                'spread': tick.ask - tick.bid,
            }
        except Exception as e:
            logger.error(f"Error getting tick for {symbol}: {e}")
            return None
    
    def _get_m1_bar_volume(self, symbol: str, tick_time: datetime) -> int:
        """
        Get tick volume from the most recent M1 bar for the given symbol.
        Uses caching to avoid fetching on every tick - only refreshes when a new bar starts.
        
        Args:
            symbol: Trading symbol
            tick_time: Current tick time (used to determine if we need to refresh cache)
            
        Returns:
            Tick volume from most recent M1 bar, or 0 if fetch fails
        """
        try:
            # Calculate the current M1 bar's start time (rounded down to minute)
            current_bar_time = tick_time.replace(second=0, microsecond=0)
            
            # Check cache - refresh if:
            # 1. No cache entry exists for this symbol
            # 2. Cached bar time is different (new bar started)
            cache_entry = self._m1_bar_cache.get(symbol)
            if cache_entry is None or cache_entry.get('bar_time') != current_bar_time:
                # Fetch most recent M1 bar
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 1)
                
                if rates is not None and len(rates) > 0:
                    # Get the most recent bar
                    rate = rates[0]
                    bar_time = datetime.fromtimestamp(rate[0], tz=UTC).replace(second=0, microsecond=0)
                    tick_volume = int(rate[5])  # tick_volume is at index 5
                    
                    # Update cache
                    self._m1_bar_cache[symbol] = {
                        'bar_time': bar_time,
                        'tick_volume': tick_volume
                    }
                    
                    logger.debug(f"M1 bar volume cached for {symbol}: {tick_volume} (bar time: {bar_time})")
                    return tick_volume
                else:
                    # If fetch fails, try to use cached value if available
                    if cache_entry:
                        logger.debug(f"Failed to fetch M1 bar for {symbol}, using cached volume: {cache_entry.get('tick_volume', 0)}")
                        return cache_entry.get('tick_volume', 0)
                    return 0
            else:
                # Use cached value
                return cache_entry.get('tick_volume', 0)
                
        except Exception as e:
            logger.debug(f"Error getting M1 bar volume for {symbol}: {e}")
            # Return cached value if available, otherwise 0
            cache_entry = self._m1_bar_cache.get(symbol)
            if cache_entry:
                return cache_entry.get('tick_volume', 0)
            return 0
    
    def get_rates(self, symbol: str, timeframe: int, count: int = 1000, 
                  start_pos: int = 0) -> Optional[List[Dict]]:
        """
        Get historical rates (OHLCV data) with symbol selection and fallback
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (mt5.TIMEFRAME_M1, M5, M15, H1, H4, D1, etc.)
            count: Number of bars to retrieve
            start_pos: Starting position (0 for most recent)
            
        Returns:
            List of rate dictionaries
        """
        if not self.is_connected():
            return None
        
        # Resolve symbol case (MT5 is case-sensitive)
        symbol_info = self.get_symbol_info(symbol)
        if symbol_info:
            symbol = symbol_info['name']  # Use the correct case from MT5
        else:
            # If symbol_info fails, try case-insensitive match manually
            available_symbols = self.get_available_symbols()
            symbol_upper = symbol.upper()
            for available_symbol in available_symbols:
                if available_symbol.upper() == symbol_upper:
                    symbol = available_symbol
                    break
        
        # Ensure symbol is selected in MT5
        mt5.symbol_select(symbol, True)
        
        # Try copy_rates_from_pos first (most efficient)
        rates = mt5.copy_rates_from_pos(symbol, timeframe, start_pos, count)
        
        # Fallback: try copy_rates_from with date range
        if rates is None or len(rates) == 0:
            # Calculate days needed based on timeframe
            timeframe_days = {
                mt5.TIMEFRAME_M1: 1,
                mt5.TIMEFRAME_M5: 2,
                mt5.TIMEFRAME_M15: 5,
                mt5.TIMEFRAME_M30: 10,
                mt5.TIMEFRAME_H1: 20,
                mt5.TIMEFRAME_H4: 80,
                mt5.TIMEFRAME_D1: 200,
            }
            days = timeframe_days.get(timeframe, 20)
            start_date = datetime.now() - timedelta(days=days)
            rates = mt5.copy_rates_from(symbol, timeframe, start_date, count)
        
        if rates is None or len(rates) == 0:
            logger.warning(f"Could not retrieve rates for {symbol} (timeframe: {timeframe})")
            return None
        
        # Convert to list of dicts
        result = []
        for rate in rates:
            # MT5 timestamps are in UTC, create UTC-aware datetime
            result.append({
                'time': datetime.fromtimestamp(rate[0], tz=UTC),
                'open': rate[1],
                'high': rate[2],
                'low': rate[3],
                'close': rate[4],
                'tick_volume': rate[5],
                'spread': rate[6],
                'real_volume': rate[7] if len(rate) > 7 else 0,
            })
        
        return result
    
    def get_rsi(self, symbol: str, timeframe: int, period: int = 14, 
                count: int = 300) -> Optional[float]:
        """
        Get RSI value calculated from MT5's rate data (exact MT5 method)
        Note: MetaTrader5 Python package doesn't have iRSI(), so we calculate it ourselves
        using MT5's rate data to ensure exact match with MT5 charts
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (mt5.TIMEFRAME_M1, M5, etc.)
            period: RSI period (default 14)
            count: Number of bars to use for calculation
            
        Returns:
            Current RSI value or None if calculation fails
        """
        if not self.is_connected():
            return None
        
        try:
            # Get historical rates from MT5 (closed bars)
            # Use start_pos=0 to get all bars including the most recent closed bar
            rates = self.get_rates(symbol, timeframe, count, 0)
            if not rates or len(rates) < period + 1:
                logger.warning(f"Insufficient rate data for RSI calculation: {len(rates) if rates else 0} bars (need {period + 1})")
                return None
            
            # Get current tick to use as current bar's close price for real-time updates
            tick = self.get_tick(symbol)
            if not tick:
                logger.warning(f"Could not get current tick for {symbol}")
                # Still calculate RSI with closed bars only
                tick = None
            
            # Use the most recent closed bar as base, or current tick if available
            if tick:
                # Add current bar with latest close price (for real-time RSI)
                # This matches MT5's behavior of including the current forming bar
                last_close = rates[-1]['close'] if rates else tick['last']
                current_bar = {
                    'time': datetime.now(),
                    'open': last_close,
                    'high': max(last_close, tick['ask']),
                    'low': min(last_close, tick['bid']),
                    'close': tick['last'],  # Use current last price as close
                    'tick_volume': 0,
                    'spread': tick['spread'],
                    'real_volume': 0
                }
                # Combine closed bars + current forming bar
                all_bars = rates + [current_bar]
            else:
                # Use only closed bars if no tick available
                all_bars = rates
            
            # Calculate RSI using MT5's exact method (Wilder's smoothing)
            # Import RSI indicator - use the same import style as other modules
            try:
                from src.indicators import RSI
            except ImportError:
                # Fallback: try importing directly from rsi module
                import sys
                import os
                # Add project root to path if not already there
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                if project_root not in sys.path:
                    sys.path.insert(0, project_root)
                from src.indicators import RSI
            
            rsi_indicator = RSI(period)
            rsi_indicator.update(all_bars)
            rsi_value = rsi_indicator.get_value()
            
            if rsi_value is not None:
                logger.info(f"RSI for {symbol} (MT5 method): {rsi_value:.2f} (bars: {len(all_bars)})")
                return float(rsi_value)
            else:
                logger.warning(f"RSI calculation returned None for {symbol} (had {len(all_bars)} bars)")
                return None
            
        except Exception as e:
            logger.error(f"Error calculating RSI for {symbol}: {e}", exc_info=True)
            return None
    
    def get_last_bar_time(self, symbol: str, timeframe: int) -> Optional[datetime]:
        """
        Get the time of the last closed bar for a symbol and timeframe
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe
            
        Returns:
            Datetime of last closed bar or None if failed
        """
        if not self.is_connected():
            return None
        
        try:
            # Get the most recent bar (position 0)
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 1)
            if rates is None or len(rates) == 0:
                return None
            
            # Return the time of the bar (first element is time)
            # MT5 timestamps are in UTC, create UTC-aware datetime
            return datetime.fromtimestamp(rates[0][0], tz=UTC)
        except Exception as e:
            logger.error(f"Error getting last bar time: {e}")
            return None
    
    def place_order(self, symbol: str, order_type: int, volume: float, 
                   price: float = 0.0, sl: float = 0.0, tp: float = 0.0,
                   deviation: int = 20, comment: str = "Python Script") -> Optional[Dict]:
        """
        Place a trading order
        
        Args:
            symbol: Trading symbol
            order_type: Order type (mt5.ORDER_TYPE_BUY, ORDER_TYPE_SELL, etc.)
            volume: Lot size
            price: Price for pending orders (0 for market orders)
            sl: Stop loss price
            tp: Take profit price
            deviation: Maximum price deviation in points
            comment: Order comment
            
        Returns:
            Order result dictionary or None if failed
        """
        # Log connection status check
        logger.info(f"place_order: Checking MT5 connection for {symbol}")
        if not self.is_connected():
            error_msg = "Not connected to MT5"
            logger.info(f"place_order validation failed: {error_msg}")
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")  # Console output for user
            return None
        
        # Get symbol information
        logger.info(f"place_order: Retrieving symbol info for {symbol}")
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            error_msg = f"Symbol {symbol} not found in MT5"
            logger.info(f"place_order validation failed: {error_msg}")
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return None
        
        # Check if symbol is tradeable
        logger.info(f"place_order: Checking tradeability for {symbol} (trade_mode={symbol_info.trade_mode})")
        if symbol_info.trade_mode == 0:
            error_msg = f"Symbol {symbol} is not tradeable (trade_mode=0)"
            logger.info(f"place_order validation failed: {error_msg}")
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return None
        
        # Normalize volume to symbol's lot step
        lot_step = symbol_info.volume_step
        min_volume = symbol_info.volume_min
        max_volume = symbol_info.volume_max
        volume = round(volume / lot_step) * lot_step
        volume = max(min_volume, min(max_volume, volume))
        
        # Get current price
        logger.info(f"place_order: Getting current price (tick) for {symbol}")
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            error_msg = f"Could not get current price (tick) for {symbol}"
            logger.info(f"place_order validation failed: {error_msg}")
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return None
        logger.info(f"place_order: Current price for {symbol} - bid={tick.bid}, ask={tick.ask}")
        
        # Normalize price
        # For market orders (price=0.0), use appropriate price based on order type
        # For BUY: use ASK (we buy at ask price)
        # For SELL: use BID (we sell at bid price)
        if price == 0.0:
            if order_type == mt5.ORDER_TYPE_BUY:
                price = tick.ask
                logger.info(f"place_order: Market BUY order - using ASK price: {price} (bid={tick.bid}, ask={tick.ask})")
                # Defensive check: ensure we're using ASK, not BID
                if price == tick.bid:
                    logger.error(f"CRITICAL: Price was set to BID instead of ASK for BUY order! Fixing...")
                    price = tick.ask
                    logger.info(f"place_order: Corrected price to ASK: {price}")
            elif order_type == mt5.ORDER_TYPE_SELL:
                price = tick.bid
                logger.info(f"place_order: Market SELL order - using BID price: {price} (bid={tick.bid}, ask={tick.ask})")
                # Defensive check: ensure we're using BID, not ASK
                if price == tick.ask:
                    logger.error(f"CRITICAL: Price was set to ASK instead of BID for SELL order! Fixing...")
                    price = tick.bid
                    logger.info(f"place_order: Corrected price to BID: {price}")
        else:
            # Price was provided (pending order), log which price is being used
            logger.info(f"place_order: Pending order - using provided price: {price}")
        
        # Normalize prices to symbol's digits
        digits = symbol_info.digits
        price = round(price, digits)
        
        # Final validation: ensure price is correct for order type
        if order_type == mt5.ORDER_TYPE_BUY and price <= tick.bid:
            logger.error(f"CRITICAL: BUY order price ({price}) is <= BID ({tick.bid}). This is invalid! Using ASK instead.")
            price = round(tick.ask, digits)
        elif order_type == mt5.ORDER_TYPE_SELL and price >= tick.ask:
            logger.error(f"CRITICAL: SELL order price ({price}) is >= ASK ({tick.ask}). This is invalid! Using BID instead.")
            price = round(tick.bid, digits)
        
        # Validate and adjust SL/TP relative to current entry price
        # This ensures SL/TP are valid even if price changed slightly since calculation
        trade_stops_level = symbol_info.trade_stops_level
        point = symbol_info.point
        min_distance = trade_stops_level * point if trade_stops_level > 0 else 0
        
        logger.info(f"place_order: Validating and adjusting SL/TP for {symbol} - price={price}, sl={sl}, tp={tp}, order_type={order_type}, min_distance={min_distance}")
        logger.info(f"place_order: Price source - bid={tick.bid}, ask={tick.ask}, using={'ASK' if order_type == mt5.ORDER_TYPE_BUY else 'BID'}")
        
        # Validate and adjust SL
        if sl > 0:
            sl = round(sl, digits)
            
            # Check if SL is on correct side
            if order_type == mt5.ORDER_TYPE_BUY:
                if sl >= price:
                    # SL is invalid (above/equal to entry) - adjust it
                    if min_distance > 0:
                        sl = price - min_distance
                        sl = round(sl, digits)
                        logger.warning(f"SL was above entry price for BUY order. Adjusted SL to {sl} (min distance: {min_distance})")
                    else:
                        # No minimum distance requirement, use a reasonable default
                        # For gold (XAUUSDm), use at least 0.5 (50 points) to ensure broker acceptance
                        # For other symbols, use 10 points or 0.1% of price, whichever is larger
                        default_distance = max(point * 50, price * 0.001)  # At least 50 points or 0.1% of price
                        sl = price - default_distance
                        sl = round(sl, digits)
                        logger.warning(f"SL was above entry price for BUY order. Adjusted SL to {sl} (default distance: {default_distance:.5f})")
                else:
                    # SL is below entry (correct), check minimum distance
                    sl_distance = abs(price - sl)
                    if min_distance > 0 and sl_distance < min_distance:
                        sl = price - min_distance
                        sl = round(sl, digits)
                        logger.warning(f"SL too close to entry price. Adjusted SL to {sl} (min distance: {min_distance})")
            else:  # SELL
                if sl <= price:
                    # SL is invalid (below/equal to entry) - adjust it
                    if min_distance > 0:
                        sl = price + min_distance
                        sl = round(sl, digits)
                        logger.warning(f"SL was below entry price for SELL order. Adjusted SL to {sl} (min distance: {min_distance})")
                    else:
                        # No minimum distance requirement, use a reasonable default
                        # For gold (XAUUSDm), use at least 0.5 (50 points) to ensure broker acceptance
                        # For other symbols, use 10 points or 0.1% of price, whichever is larger
                        default_distance = max(point * 50, price * 0.001)  # At least 50 points or 0.1% of price
                        sl = price + default_distance
                        sl = round(sl, digits)
                        logger.warning(f"SL was below entry price for SELL order. Adjusted SL to {sl} (default distance: {default_distance:.5f})")
                else:
                    # SL is above entry (correct), check minimum distance
                    sl_distance = abs(sl - price)
                    if min_distance > 0 and sl_distance < min_distance:
                        sl = price + min_distance
                        sl = round(sl, digits)
                        logger.warning(f"SL too close to entry price. Adjusted SL to {sl} (min distance: {min_distance})")
        
        # Validate and adjust TP
        if tp > 0:
            tp = round(tp, digits)
            
            # Check if TP is on correct side
            if order_type == mt5.ORDER_TYPE_BUY:
                if tp <= price:
                    # TP is invalid (below/equal to entry) - adjust it
                    if min_distance > 0:
                        tp = price + min_distance
                        tp = round(tp, digits)
                        logger.warning(f"TP was below entry price for BUY order. Adjusted TP to {tp} (min distance: {min_distance})")
                    else:
                        # No minimum distance requirement, use a reasonable default
                        # For gold (XAUUSDm), use at least 0.5 (50 points) to ensure broker acceptance
                        # For other symbols, use 10 points or 0.1% of price, whichever is larger
                        default_distance = max(point * 50, price * 0.001)  # At least 50 points or 0.1% of price
                        tp = price + default_distance
                        tp = round(tp, digits)
                        logger.warning(f"TP was below entry price for BUY order. Adjusted TP to {tp} (default distance: {default_distance:.5f})")
                else:
                    # TP is above entry (correct), check minimum distance
                    tp_distance = abs(tp - price)
                    if min_distance > 0 and tp_distance < min_distance:
                        tp = price + min_distance
                        tp = round(tp, digits)
                        logger.warning(f"TP too close to entry price. Adjusted TP to {tp} (min distance: {min_distance})")
            else:  # SELL
                if tp >= price:
                    # TP is invalid (above/equal to entry) - adjust it
                    if min_distance > 0:
                        tp = price - min_distance
                        tp = round(tp, digits)
                        logger.warning(f"TP was above entry price for SELL order. Adjusted TP to {tp} (min distance: {min_distance})")
                    else:
                        # No minimum distance requirement, use a reasonable default
                        # For gold (XAUUSDm), use at least 0.5 (50 points) to ensure broker acceptance
                        # For other symbols, use 10 points or 0.1% of price, whichever is larger
                        default_distance = max(point * 50, price * 0.001)  # At least 50 points or 0.1% of price
                        tp = price - default_distance
                        tp = round(tp, digits)
                        logger.warning(f"TP was above entry price for SELL order. Adjusted TP to {tp} (default distance: {default_distance:.5f})")
                else:
                    # TP is below entry (correct), check minimum distance
                    tp_distance = abs(price - tp)
                    if min_distance > 0 and tp_distance < min_distance:
                        tp = price - min_distance
                        tp = round(tp, digits)
                        logger.warning(f"TP too close to entry price. Adjusted TP to {tp} (min distance: {min_distance})")
        
        # Final validation - ensure SL/TP are still valid after adjustments
        if sl > 0:
            if order_type == mt5.ORDER_TYPE_BUY and sl >= price:
                error_msg = f"Stop loss ({sl}) is invalid for BUY order at price {price}. Cannot adjust automatically."
                logger.error(error_msg)
                print(f"ERROR: {error_msg}")
                return {
                    'success': False,
                    'retcode': 10016,
                    'error': error_msg,
                    'comment': 'Invalid stops - SL adjustment failed'
                }
            elif order_type == mt5.ORDER_TYPE_SELL and sl <= price:
                error_msg = f"Stop loss ({sl}) is invalid for SELL order at price {price}. Cannot adjust automatically."
                logger.error(error_msg)
                print(f"ERROR: {error_msg}")
                return {
                    'success': False,
                    'retcode': 10016,
                    'error': error_msg,
                    'comment': 'Invalid stops - SL adjustment failed'
                }
        
        if tp > 0:
            if order_type == mt5.ORDER_TYPE_BUY and tp <= price:
                error_msg = f"Take profit ({tp}) is invalid for BUY order at price {price}. Cannot adjust automatically."
                logger.error(error_msg)
                print(f"ERROR: {error_msg}")
                return {
                    'success': False,
                    'retcode': 10016,
                    'error': error_msg,
                    'comment': 'Invalid stops - TP adjustment failed'
                }
            elif order_type == mt5.ORDER_TYPE_SELL and tp >= price:
                error_msg = f"Take profit ({tp}) is invalid for SELL order at price {price}. Cannot adjust automatically."
                logger.error(error_msg)
                print(f"ERROR: {error_msg}")
                return {
                    'success': False,
                    'retcode': 10016,
                    'error': error_msg,
                    'comment': 'Invalid stops - TP adjustment failed'
                }
        
        logger.info(f"place_order: Final SL/TP values - price={price}, sl={sl}, tp={tp}")
        
        # Determine order filling type
        # filling_mode is a bitmask where:
        # Bit 0 (1) = FOK (Fill or Kill)
        # Bit 1 (2) = IOC (Immediate or Cancel)
        # Bit 2 (4) = RETURN (Return)
        filling_mode = symbol_info.filling_mode
        type_filling = mt5.ORDER_FILLING_FOK   # Default
        
        # Check which filling modes are available using bitwise operations
        # Priority: FOK > IOC > RETURN
        if filling_mode & 1:  # FOK bit (bit 0)
            type_filling = mt5.ORDER_FILLING_FOK
            logger.info(f"Using ORDER_FILLING_FOK for {symbol} (filling_mode={filling_mode})")
        elif filling_mode & 2:  # IOC bit (bit 1)
            type_filling = mt5.ORDER_FILLING_IOC
            logger.info(f"Using ORDER_FILLING_IOC for {symbol} (filling_mode={filling_mode})")
        elif filling_mode & 4:  # RETURN bit (bit 2)
            type_filling = mt5.ORDER_FILLING_RETURN
            logger.info(f"Using ORDER_FILLING_RETURN for {symbol} (filling_mode={filling_mode})")
        else:
            # No filling mode available - this is a problem
            error_msg = f"Symbol {symbol} has no valid filling mode (filling_mode={filling_mode})"
            logger.info(f"place_order validation failed: {error_msg}")
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return None
        
        # Check account info and trading permissions before sending
        logger.info(f"place_order: Checking account info and trading permissions for {symbol}")
        account_info = mt5.account_info()
        if account_info is None:
            error_msg = "Could not get account info - MT5 connection issue"
            logger.info(f"place_order validation failed: {error_msg}")
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return None
        
        # Check if AutoTrading is enabled (PRIMARY CHECK - reflects AutoTrading button state)
        # This is the critical check for programmatic trading
        logger.info(f"place_order: Checking terminal info and AutoTrading status")
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            error_msg = "Could not get terminal info - MT5 connection issue"
            logger.info(f"place_order validation failed: {error_msg}")
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return None
            
        logger.info(f"place_order: Terminal trade_allowed={terminal_info.trade_allowed} (True=AutoTrading enabled, False=disabled)")
        
        # Check account trade_mode (SECONDARY CHECK - account-level permission)
        # account_info.trade_mode values:
        # 0 = May indicate restrictions, but not always blocking if AutoTrading is enabled
        # 1 = Trading allowed (demo account)
        # 2 = Trading allowed (real account)
        # 4 = Trading allowed (cent account)
        logger.info(f"place_order: Account trade_mode={account_info.trade_mode} (0=may have restrictions, >0=enabled)")
        
        # Log both values for transparency
        logger.info(f"place_order: Trading permissions - Terminal trade_allowed={terminal_info.trade_allowed}, Account trade_mode={account_info.trade_mode}")
        
        # PRIMARY CHECK: Block if AutoTrading is disabled (this is the critical check)
        if not terminal_info.trade_allowed:
            error_msg = "AutoTrading is disabled in MT5 terminal. Please enable it in Tools > Options > Expert Advisors > Allow automated trading"
            logger.info(f"place_order validation failed: {error_msg}")
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return {
                'success': False,
                'retcode': 0,
                'error': 'AutoTrading disabled in MT5 terminal. Enable in Tools > Options > Expert Advisors',
                'comment': 'AutoTrading disabled - enable in MT5 terminal settings',
                'terminal_trade_allowed': False,
                'account_trade_mode': account_info.trade_mode
            }
        
        # SECONDARY CHECK: Warn if account trade_mode=0, but don't block if AutoTrading is enabled
        # Some brokers/accounts may have trade_mode=0 but still allow trading when AutoTrading is enabled
        if account_info.trade_mode == 0:
            account_type = "Demo" if "demo" in str(account_info.server).lower() or account_info.balance < 1000 else "Real"
            warning_msg = (
                f"Account trade_mode=0 detected (Account: {account_info.login}, Server: {account_info.server}, Type: {account_type}). "
                f"However, AutoTrading is enabled (trade_allowed=True), so proceeding with order. "
                f"If orders fail, verify account permissions with your broker."
            )
            logger.warning(warning_msg)
            print(f"WARNING: {warning_msg}")
            # Continue with order placement since AutoTrading is enabled
        
        # Log account status for debugging
        logger.info(f"Account: {account_info.login}, Balance: {account_info.balance}, Trade Mode: {account_info.trade_mode}, Trade Allowed: {terminal_info.trade_allowed}")
        
        # Prepare request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "deviation": deviation,
            "magic": 234000,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": type_filling,
        }
        
        # Add stop loss and take profit
        if sl > 0:
            request["sl"] = sl
        if tp > 0:
            request["tp"] = tp
        
        # Log the request for debugging
        logger.info(f"place_order: Prepared order request: symbol={symbol}, type={order_type}, volume={volume}, price={price}, sl={sl}, tp={tp}, filling={type_filling}")
        
        # Verify MT5 is still connected before sending
        logger.info(f"place_order: Final connection check before order_send for {symbol}")
        terminal_check = mt5.terminal_info()
        if terminal_check is None:
            error_msg = "MT5 terminal info is None - connection lost before order_send"
            logger.info(f"place_order validation failed: {error_msg}")
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return None
        
        if not terminal_check.trade_allowed:
            error_msg = "AutoTrading is disabled in MT5 terminal. Enable it in Tools > Options > Expert Advisors"
            logger.info(f"place_order validation failed: {error_msg}")
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            return None
        
        # Log before sending
        print(f"INFO: Sending order - Symbol: {symbol}, Type: {order_type}, Volume: {volume}, Price: {price}, SL: {sl}, TP: {tp}")
        logger.info(f"place_order: Calling mt5.order_send() for {symbol} with request: {request}")
        
        # Send order
        result = mt5.order_send(request)
        
        # Log immediately after order_send returns
        if result is None:
            logger.info(f"place_order: mt5.order_send() returned None for {symbol}")
        else:
            logger.info(f"place_order: mt5.order_send() returned result with retcode={result.retcode if hasattr(result, 'retcode') else 'N/A'}")
        
        if result is None:
            error = mt5.last_error()
            # Log detailed error information
            error_msg = f"order_send() returned None - CRITICAL FAILURE"
            logger.error(error_msg)
            logger.error(f"MT5 last_error: {error}")
            logger.error(f"Request details: {request}")
            logger.error(f"Account trade_mode: {account_info.trade_mode} (0=disabled, >0=enabled)")
            logger.error(f"Terminal trade_allowed: {terminal_check.trade_allowed}")
            logger.error(f"Symbol trade_mode: {symbol_info.trade_mode} (0=disabled, >0=enabled)")
            logger.error(f"Symbol visible: {symbol_info.visible}")
            logger.error(f"Connection status: terminal_info={terminal_check is not None}, account_info={mt5.account_info() is not None}")
            
            # Print to console for user visibility
            print(f"ERROR: {error_msg}")
            print(f"ERROR: MT5 last_error: {error}")
            print(f"ERROR: Check the logs above for detailed diagnostics")
            
            # Additional checks
            account_check = mt5.account_info()
            if account_check is None:
                logger.error("CRITICAL: Cannot retrieve account info - MT5 connection is broken")
                print("ERROR: Cannot retrieve account info - MT5 connection is broken")
                return {
                    'success': False,
                    'retcode': 0,
                    'error': 'MT5 connection broken - cannot retrieve account info',
                    'comment': 'MT5 connection broken'
                }
            else:
                logger.error(f"Account balance: {account_check.balance}, margin: {account_check.margin}, free_margin: {account_check.free_margin}")
                print(f"INFO: Account balance: {account_check.balance}, free_margin: {account_check.free_margin}")
            
            # Build detailed error message
            error_details = []
            if error:
                error_code = error[0] if isinstance(error, tuple) else 0
                error_desc = error[1] if isinstance(error, tuple) and len(error) > 1 else str(error)
                error_details.append(f"MT5 Error {error_code}: {error_desc}")
            
            if account_info.trade_mode == 0:
                error_details.append("Trading disabled on account")
            if symbol_info.trade_mode == 0:
                error_details.append(f"Symbol {symbol} trading disabled")
            if not symbol_info.visible:
                error_details.append(f"Symbol {symbol} not visible in Market Watch")
            if account_check.free_margin < 0:
                error_details.append("Insufficient margin")
            
            # Build error message - ensure symbol is preserved correctly
            if error_details:
                # Join with " - " for single line display in UI
                error_message = " - ".join(error_details)
            else:
                # Check if this is a connection/server issue
                if account_check is None:
                    error_message = f"Order placement failed for {symbol} - MT5 connection lost (no response from server)"
                elif error and isinstance(error, tuple) and error[0] == 10031:
                    error_message = f"Order placement failed for {symbol} - Connection error (no response from server)"
                else:
                    error_message = f"Order placement failed for {symbol} - no response from server (check MT5 connection and AutoTrading settings)"
            
            # Return error dictionary instead of None
            return {
                'success': False,
                'retcode': error[0] if isinstance(error, tuple) else 0,
                'error': error_message,
                'comment': error_message
            }
        
        # Check if order was successful
        # TRADE_RETCODE_DONE (10009) = fully executed (position opened)
        # TRADE_RETCODE_DONE_PARTIAL (10010) = partially executed (partial position opened)
        # TRADE_RETCODE_PLACED (10008) = order placed but pending (not a position yet)
        retcode = result.retcode
        
        if retcode == mt5.TRADE_RETCODE_DONE:
            # Order fully executed - position should be open
            logger.info(f"Order placed successfully: ticket={result.order}, retcode={retcode}")
            print(f"SUCCESS: Order executed! Ticket: {result.order}, Volume: {result.volume}, Price: {result.price}")
            return {
                'order': result.order,
                'volume': result.volume,
                'price': result.price,
                'bid': result.bid,
                'ask': result.ask,
                'comment': result.comment,
                'request_id': result.request_id,
                'retcode': retcode,
                'success': True,
            }
        elif retcode == mt5.TRADE_RETCODE_DONE_PARTIAL:
            # Order partially executed - partial position opened
            logger.info(f"Order partially executed: ticket={result.order}, retcode={retcode}, volume={result.volume}")
            return {
                'order': result.order,
                'volume': result.volume,
                'price': result.price,
                'bid': result.bid,
                'ask': result.ask,
                'comment': result.comment,
                'request_id': result.request_id,
                'retcode': retcode,
                'success': True,  # Still a success, just partial
            }
        elif retcode == mt5.TRADE_RETCODE_PLACED:
            # Order placed but pending - not a position yet
            logger.info(f"Order placed but pending: ticket={result.order}, retcode={retcode}")
            return {
                'order': result.order,
                'volume': result.volume,
                'price': result.price,
                'bid': result.bid,
                'ask': result.ask,
                'comment': result.comment,
                'request_id': result.request_id,
                'retcode': retcode,
                'success': False,  # Not executed yet, so not a position
            }
        else:
            # Order was not executed successfully
            logger.error(f"Order failed: retcode={retcode}, comment={result.comment}")
            
            # Get human-readable error message based on retcode
            retcode_meanings = {
                10004: "Requote - price changed, please retry",
                10006: "Order rejected by broker",
                10007: "Order cancelled",
                10011: "General error",
                10012: "Timeout",
                10013: "Invalid request",
                10014: "Invalid volume",
                10015: "Invalid price",
                10016: "Invalid stop loss or take profit",
                10017: "Trading disabled",
                10018: "Market closed",
                10019: "Insufficient funds",
                10020: "Price changed",
                10031: "Connection error",
            }
            
            # Build comprehensive error message
            comment = result.comment if hasattr(result, 'comment') else ''
            retcode_msg = retcode_meanings.get(retcode, f"Unknown error (code: {retcode})")
            
            # Combine MT5 comment with retcode meaning for clarity
            if comment:
                error_message = f"{comment} - {retcode_msg}"
            else:
                error_message = retcode_msg
            
            # Return the result anyway so caller can see the retcode and comment
            return {
                'order': result.order if hasattr(result, 'order') else 0,
                'volume': result.volume if hasattr(result, 'volume') else 0,
                'price': result.price if hasattr(result, 'price') else 0.0,
                'bid': result.bid if hasattr(result, 'bid') else 0.0,
                'ask': result.ask if hasattr(result, 'ask') else 0.0,
                'comment': comment,
                'error': error_message,  # Add error field with comprehensive message
                'request_id': result.request_id if hasattr(result, 'request_id') else 0,
                'retcode': retcode,
                'success': False,
            }
    
    def get_positions(self, symbol: str = None) -> List[Dict]:
        """Get open positions"""
        if not self.is_connected():
            return []
        
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        if positions is None:
            return []
        
        result = []
        for pos in positions:
            result.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': pos.type,
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'profit': pos.profit,
                'swap': pos.swap,
                'comment': pos.comment,
                'time': datetime.fromtimestamp(pos.time, tz=UTC),  # MT5 timestamps are in UTC
                'sl': pos.sl,  # Stop loss price
                'tp': pos.tp,  # Take profit price
            })
        
        return result
    
    def get_historical_deals(self, date_from: datetime, date_to: datetime = None, 
                            symbol: str = None) -> List[Dict]:
        """
        Get historical closed deals from MT5
        
        Args:
            date_from: Start date for history
            date_to: End date (None = now)
            symbol: Filter by symbol (None = all)
        
        Returns:
            List of deal dictionaries
        """
        if not self.is_connected():
            logger.error("MT5 not connected")
            return []
        
        try:
            if date_to is None:
                date_to = datetime.now()
            
            # Get history deals
            if symbol:
                deals = mt5.history_deals_get(date_from, date_to, group=f"*{symbol}*")
            else:
                deals = mt5.history_deals_get(date_from, date_to)
            
            if deals is None:
                logger.warning("No historical deals found")
                return []
            
            result = []
            for deal in deals:
                # Only include OUT deals (position closures)
                if deal.entry == mt5.DEAL_ENTRY_OUT:
                    result.append({
                        'ticket': deal.position_id,
                        'deal_ticket': deal.ticket,
                        'symbol': deal.symbol,
                        'type': 'BUY' if deal.type == mt5.DEAL_TYPE_BUY else 'SELL',
                        'volume': deal.volume,
                        'price': deal.price,
                        'time': datetime.fromtimestamp(deal.time, tz=UTC),  # MT5 timestamps are in UTC
                        'profit': deal.profit,
                        'comment': deal.comment
                    })
            
            logger.info(f"Retrieved {len(result)} closed deals from MT5 history")
            return result
            
        except Exception as e:
            logger.error(f"Error getting historical deals: {e}", exc_info=True)
            return []
    
    def close_position(self, ticket: int) -> bool:
        """Close a position by ticket"""
        if not self.is_connected():
            return False
        
        position = mt5.positions_get(ticket=ticket)
        if position is None or len(position) == 0:
            logger.error(f"Position {ticket} not found")
            return False
        
        pos = position[0]
        
        # Determine order type for closing
        if pos.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(pos.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(pos.symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Close position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Failed to close position {ticket}")
            return False
        
        logger.info(f"Position {ticket} closed")
        return True
    
    def modify_position(self, ticket: int, sl: float = 0.0, tp: float = 0.0) -> bool:
        """
        Modify stop loss and take profit of an open position
        
        Args:
            ticket: Position ticket
            sl: New stop loss price (0 to remove)
            tp: New take profit price (0 to remove)
            
        Returns:
            True if successful, False otherwise
        """
        # Reset previous error before attempting
        self.last_error = None

        if not self.is_connected():
            self.last_error = "MT5 not connected"
            logger.error(f"Failed to modify position {ticket}: {self.last_error}")
            return False
        
        position = mt5.positions_get(ticket=ticket)
        if position is None or len(position) == 0:
            self.last_error = "Position not found"
            logger.error(f"Position {ticket} not found")
            return False
        
        pos = position[0]

        symbol_info = mt5.symbol_info(pos.symbol)
        tick = mt5.symbol_info_tick(pos.symbol)

        if symbol_info is None or tick is None:
            self.last_error = "Symbol info/tick unavailable"
            logger.error(f"Failed to modify position {ticket}: {self.last_error}")
            return False

        point = getattr(symbol_info, "point", 0.0) or 0.0
        digits = getattr(symbol_info, "digits", 5)
        # MT5 returns stop_level/freeze_level in points; use the stricter of the two
        min_gap_points = max(getattr(symbol_info, "stop_level", 0), getattr(symbol_info, "freeze_level", 0))
        min_gap_price = min_gap_points * point

        bid = tick.bid
        ask = tick.ask
        validation_errors = []

        # Get current SL/TP values from position
        current_sl = pos.sl if hasattr(pos, 'sl') else 0.0
        current_tp = pos.tp if hasattr(pos, 'tp') else 0.0

        if sl > 0:
            sl = round(sl, digits)
            if pos.type == mt5.ORDER_TYPE_BUY:
                if sl >= bid - min_gap_price:
                    validation_errors.append(
                        f"SL must be at least {min_gap_price:.{digits}f} below bid {bid:.{digits}f}"
                    )
            else:  # SELL position
                if sl <= ask + min_gap_price:
                    validation_errors.append(
                        f"SL must be at least {min_gap_price:.{digits}f} above ask {ask:.{digits}f}"
                    )
        else:
            sl = 0.0

        if tp > 0:
            tp = round(tp, digits)
            if pos.type == mt5.ORDER_TYPE_BUY:
                if tp <= ask + min_gap_price:
                    validation_errors.append(
                        f"TP must be at least {min_gap_price:.{digits}f} above ask {ask:.{digits}f}"
                    )
            else:  # SELL position
                if tp >= bid - min_gap_price:
                    validation_errors.append(
                        f"TP must be at least {min_gap_price:.{digits}f} below bid {bid:.{digits}f}"
                    )
        else:
            tp = 0.0

        if validation_errors:
            self.last_error = "; ".join(validation_errors)
            logger.error(f"Failed to modify position {ticket}: {self.last_error}")
            return False
        
        # Check if values are effectively the same (within tolerance)
        # Use tolerance based on symbol point size (minimum 0.00001 for 5-digit symbols)
        tolerance = max(point * 0.1, 0.00001)
        sl_changed = abs(sl - current_sl) >= tolerance
        tp_changed = abs(tp - current_tp) >= tolerance
        
        if not sl_changed and not tp_changed:
            # No changes needed - values are effectively the same
            logger.debug(f"Position {ticket} modification skipped: SL and TP values unchanged (SL={sl:.{digits}f}, TP={tp:.{digits}f})")
            return True
        
        # Log the modification attempt with current vs new values
        changes = []
        if sl_changed:
            changes.append(f"SL: {current_sl:.{digits}f} → {sl:.{digits}f}")
        if tp_changed:
            changes.append(f"TP: {current_tp:.{digits}f} → {tp:.{digits}f}")
        logger.info(f"Modifying position {ticket}: {', '.join(changes)}")
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": pos.symbol,
            "position": ticket,
            "sl": sl,
            "tp": tp,
        }
        
        result = mt5.order_send(request)
        
        if result is None:
            self.last_error = "Unknown error (no result returned)"
            logger.error(f"Failed to modify position {ticket}: {self.last_error}")
            return False

        # Handle retcode 10025 (TRADE_RETCODE_NO_CHANGES) as a warning, not an error
        if result.retcode == 10025:  # TRADE_RETCODE_NO_CHANGES
            logger.warning(f"Position {ticket} modification: No changes (retcode 10025) - values may have been set by another process")
            return True  # Return True since this is not a real failure
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            comment = result.comment if hasattr(result, "comment") else "Unknown error"
            self.last_error = f"{comment} (retcode {result.retcode})"
            logger.error(f"Failed to modify position {ticket}: {self.last_error}")
            return False
        
        logger.info(f"Position {ticket} modified: SL={sl}, TP={tp}")
        return True
    
    def get_deal_history(self, date_from=None, date_to=None, symbol=None) -> List[Dict]:
        """
        Get deal history from MT5
        
        Args:
            date_from: Start date (datetime, defaults to 30 days ago)
            date_to: End date (datetime, defaults to now)
            symbol: Filter by symbol (optional)
            
        Returns:
            List of deal dictionaries
        """
        if not self.is_connected():
            return []
        
        import MetaTrader5 as mt5
        from datetime import datetime, timedelta
        
        # Set default date range if not provided
        if date_to is None:
            date_to = datetime.now()
        if date_from is None:
            date_from = date_to - timedelta(days=30)
        
        # Convert to timestamp
        date_from_ts = int(date_from.timestamp())
        date_to_ts = int(date_to.timestamp())
        
        # Get deals
        if symbol:
            # Filter by symbol after getting all deals
            all_deals = mt5.history_deals_get(date_from_ts, date_to_ts)
            if all_deals:
                deals = [d for d in all_deals if d.symbol == symbol]
            else:
                deals = None
        else:
            deals = mt5.history_deals_get(date_from_ts, date_to_ts)
        
        if deals is None:
            return []
        
        result = []
        for deal in deals:
            # Get deal reason (exit condition)
            deal_reason = getattr(deal, 'reason', None)
            exit_condition = self._get_exit_condition_from_reason(deal_reason)
            
            result.append({
                'ticket': deal.ticket,
                'order': deal.order,
                'time': datetime.fromtimestamp(deal.time, tz=UTC),  # MT5 timestamps are in UTC
                'type': deal.type,
                'entry': deal.entry,  # DEAL_ENTRY_IN or DEAL_ENTRY_OUT
                'position_id': deal.position_id,
                'price': deal.price,
                'volume': deal.volume,
                'profit': deal.profit,
                'swap': deal.swap,
                'commission': deal.commission,
                'symbol': deal.symbol,
                'comment': deal.comment,
                'reason': deal_reason,  # MT5 deal reason code
                'exit_condition': exit_condition,  # Human-readable exit condition
            })
        
        return result
    
    def _get_exit_condition_from_reason(self, reason_code: int, fallback: str = "Manual") -> str:
        """
        Convert MT5 DEAL_REASON code to human-readable exit condition
        
        Args:
            reason_code: MT5 deal reason code
            fallback: Fallback value if reason code is not recognized
            
        Returns:
            Human-readable exit condition string (SL, TP, Client, Expert, etc.)
        """
        if reason_code is None:
            return fallback
        
        # MT5 DEAL_REASON constants
        # These are the standard MT5 deal reason codes
        reason_map = {
            0: "Client",           # DEAL_REASON_CLIENT
            1: "Mobile",            # DEAL_REASON_MOBILE
            2: "Web",               # DEAL_REASON_WEB
            3: "Expert",            # DEAL_REASON_EXPERT
            4: "SL",                # DEAL_REASON_SL
            5: "TP",                # DEAL_REASON_TP
            6: "SO",                # DEAL_REASON_SO (Stop Out)
            7: "Rollover",          # DEAL_REASON_ROLLOVER
            8: "VMargin Call",      # DEAL_REASON_VMARGIN
            9: "Split",             # DEAL_REASON_SPLIT
            10: "Expert",           # DEAL_REASON_EXPERT (alternative)
            11: "Deposit",          # DEAL_REASON_DEPOSIT
            12: "Credit",           # DEAL_REASON_CREDIT
            16: "Balance",          # DEAL_REASON_BALANCE
            17: "Commission",       # DEAL_REASON_COMMISSION
            18: "Commission Daily", # DEAL_REASON_COMMISSION_DAILY
            19: "Commission Monthly", # DEAL_REASON_COMMISSION_MONTHLY
            20: "Commission Agent", # DEAL_REASON_COMMISSION_AGENT
            21: "Interest",         # DEAL_REASON_INTEREST
            22: "Buy",              # DEAL_REASON_BUY
            23: "Sell",             # DEAL_REASON_SELL
            24: "Dividend",         # DEAL_REASON_DIVIDEND
            25: "Dividend Franked", # DEAL_REASON_DIVIDEND_FRANKED
            26: "Tax",              # DEAL_REASON_TAX
            27: "Tax Franked",      # DEAL_REASON_TAX_FRANKED
            28: "Tax Withholding",  # DEAL_REASON_TAX_WITHHOLDING
            29: "Rebate",            # DEAL_REASON_REBATE
            30: "Commission Daily", # DEAL_REASON_COMMISSION_DAILY (alternative)
            31: "Commission Monthly", # DEAL_REASON_COMMISSION_MONTHLY (alternative)
            32: "Commission Agent Daily", # DEAL_REASON_COMMISSION_AGENT_DAILY
            33: "Commission Agent Monthly", # DEAL_REASON_COMMISSION_AGENT_MONTHLY
            34: "Interest Rate",    # DEAL_REASON_INTEREST_RATE
            35: "Buy Cancelled",    # DEAL_REASON_BUY_CANCELLED
            36: "Sell Cancelled",   # DEAL_REASON_SELL_CANCELLED
            37: "Dividend Cancelled", # DEAL_REASON_DIVIDEND_CANCELLED
            38: "Dividend Franked Cancelled", # DEAL_REASON_DIVIDEND_FRANKED_CANCELLED
            39: "Tax Cancelled",     # DEAL_REASON_TAX_CANCELLED
            40: "Tax Franked Cancelled", # DEAL_REASON_TAX_FRANKED_CANCELLED
            41: "Tax Withholding Cancelled", # DEAL_REASON_TAX_WITHHOLDING_CANCELLED
            42: "Rebate Cancelled", # DEAL_REASON_REBATE_CANCELLED
            43: "Commission Cancelled", # DEAL_REASON_COMMISSION_CANCELLED
            44: "Commission Daily Cancelled", # DEAL_REASON_COMMISSION_DAILY_CANCELLED
            45: "Commission Monthly Cancelled", # DEAL_REASON_COMMISSION_MONTHLY_CANCELLED
            46: "Commission Agent Cancelled", # DEAL_REASON_COMMISSION_AGENT_CANCELLED
            47: "Commission Agent Daily Cancelled", # DEAL_REASON_COMMISSION_AGENT_DAILY_CANCELLED
            48: "Commission Agent Monthly Cancelled", # DEAL_REASON_COMMISSION_AGENT_MONTHLY_CANCELLED
            49: "Interest Rate Cancelled", # DEAL_REASON_INTEREST_RATE_CANCELLED
            64: "Dealer",           # DEAL_REASON_DEALER
            65: "Dealer",           # DEAL_REASON_DEALER (alternative)
            100: "Dealer",          # DEAL_REASON_DEALER (alternative)
        }
        
        # Most common exit reasons for trading
        if reason_code in reason_map:
            return reason_map[reason_code]
        
        # Try to use MT5 constants if available
        try:
            import MetaTrader5 as mt5
            if reason_code == mt5.DEAL_REASON_SL:
                return "SL"
            elif reason_code == mt5.DEAL_REASON_TP:
                return "TP"
            elif reason_code == mt5.DEAL_REASON_CLIENT:
                return "Client"
            elif reason_code == mt5.DEAL_REASON_EXPERT:
                return "Expert"
            elif reason_code == mt5.DEAL_REASON_DEALER:
                return "Dealer"
            elif reason_code == mt5.DEAL_REASON_SO:
                return "SO"
        except (AttributeError, ImportError):
            pass
        
        return fallback
    
    def close_position_partial(self, ticket: int, volume: float) -> bool:
        """
        Partially close a position
        
        Args:
            ticket: Position ticket
            volume: Volume to close (must be less than position volume)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        position = mt5.positions_get(ticket=ticket)
        if position is None or len(position) == 0:
            logger.error(f"Position {ticket} not found")
            return False
        
        pos = position[0]
        
        if volume >= pos.volume:
            logger.error(f"Cannot close {volume} lots, position has {pos.volume} lots")
            return False
        
        # Determine order type for closing
        if pos.type == mt5.ORDER_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(pos.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(pos.symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Partial close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Failed to partially close position {ticket}")
            return False
        
        logger.info(f"Partially closed position {ticket}: {volume} lots")
        return True
    
    def get_order_history_by_ticket(self, order_ticket: int) -> Optional[Dict]:
        """
        Get order history by order ticket from MT5
        
        Args:
            order_ticket: Order ticket number
            
        Returns:
            Order dictionary with SL/TP values, or None if not found
        """
        if not self.is_connected():
            return None
        
        import MetaTrader5 as mt5
        from datetime import datetime, timedelta
        
        # Get orders from last 30 days
        date_from = datetime.now() - timedelta(days=30)
        date_to = datetime.now()
        
        date_from_ts = int(date_from.timestamp())
        date_to_ts = int(date_to.timestamp())
        
        orders = mt5.history_orders_get(date_from_ts, date_to_ts, group="*")
        
        if orders is None:
            return None
        
        for order in orders:
            if order.ticket == order_ticket:
                return {
                    'ticket': order.ticket,
                    'order': order.order,
                    'time_setup': datetime.fromtimestamp(order.time_setup, tz=UTC),  # MT5 timestamps are in UTC
                    'time_done': datetime.fromtimestamp(order.time_done, tz=UTC) if order.time_done > 0 else None,  # MT5 timestamps are in UTC
                    'type': order.type,
                    'volume': order.volume_initial,
                    'price_open': order.price_open,
                    'price_current': order.price_current,
                    'sl': order.sl,
                    'tp': order.tp,
                    'symbol': order.symbol,
                    'comment': order.comment
                }
        
        return None

