"""
Headless Mode Entry Point
Runs trading platform without GUI - ideal for 24/7 data collection and trading
"""

import sys
import os
import logging
import time
import signal
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Initialize minimal QApplication for Qt-based components (DataFeed uses QObject)
# This is required even in headless mode, but we won't show any windows
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from src.mt5_connector import MT5Connector
from src.data_feed import DataFeed
from src.data.mysql_manager import MySQLManager
from src.config import Config
from src.utils.device_utils import get_local_ip_address
from src.trading.order_manager import OrderManager
from src.strategy.strategy_manager import StrategyManager
from src.strategy.strategy_persistence import StrategyPersistence
from src.trading.risk_manager import RiskManager
from src.trading.trade_monitor import TradeMonitor
from src.indicators.real_time_feed import RealTimeIndicatorFeed
import MetaTrader5 as mt5

# Configure logging to both console and file
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "trading_platform_headless.log"

# Use RotatingFileHandler to prevent log files from growing too large
from logging.handlers import RotatingFileHandler

# Create rotating file handler (max 10MB per file, keep 5 backup files)
file_handler = RotatingFileHandler(
    log_file, 
    mode='a', 
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5,  # Keep 5 backup files
    encoding='utf-8'
)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)  # Less verbose in headless mode
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logging.info("=" * 70)
logging.info("Headless Trading Platform Starting")
logging.info("=" * 70)
logging.info(f"Log file: {log_file}")


class HeadlessTradingPlatform:
    """Headless trading platform without GUI"""
    
    def __init__(self):
        self.running = False
        self.config = Config()
        self.mt5 = None
        self.data_feed = None
        self.indicator_feed = None
        self.pb_manager = None
        self.mysql_manager = None
        self.order_manager = None
        self.strategy_manager = None
        self.risk_manager = None
        self.trade_monitor = None
        
        # Update intervals
        self.strategy_update_interval = 1.0  # seconds
        self.position_update_interval = 0.5  # seconds
        self.trade_monitor_interval = 0.5  # seconds
        
        # Timers
        self.last_strategy_update = 0
        self.last_position_update = 0
        self.last_trade_monitor = 0
    
    def initialize(self):
        """Initialize all components"""
        logging.info("Initializing components...")
        
        # Initialize MT5 with credentials from config
        self.mt5 = MT5Connector()
        mt5_config = self.config.get('mt5', {})
        
        path = mt5_config.get('path', '')
        login = mt5_config.get('login', 0)
        password = mt5_config.get('password', '')
        server = mt5_config.get('server', '')
        timeout = mt5_config.get('timeout', 10000)
        
        # Ensure login is an integer (MT5 requires int)
        try:
            login = int(login) if login else 0
        except (ValueError, TypeError):
            logging.error(f"Invalid login value: {login}. Must be a number.")
            return False
        
        # Auto-detect path if not set
        if not path:
            try:
                from src.mt5_utils import find_mt5_path
                path = find_mt5_path() or ""
                if path:
                    self.config.set('mt5.path', path)
                    self.config.save()
                    logging.info(f"Auto-detected MT5 path: {path}")
            except ImportError:
                logging.warning("mt5_utils not available, using default path")
        
        # Validate credentials before attempting connection
        if not login or login == 0:
            logging.error("MT5 login not configured. Please set mt5.login in config.json")
            return False
        
        if not password:
            logging.error("MT5 password not configured. Please set mt5.password in config.json")
            return False
        
        if not server:
            logging.error("MT5 server not configured. Please set mt5.server in config.json")
            return False
        
        logging.info(f"Connecting to MT5 (login: {login}, server: {server})...")
        logging.debug(f"MT5 connection parameters: path={path}, timeout={timeout}")
        
        # Initialize MT5 with credentials
        if not self.mt5.initialize(path=path, login=login, password=password, server=server, timeout=timeout):
            error = self.mt5.get_last_error() or "Unknown error"
            logging.error(f"Failed to connect to MT5: {error}")
            # Try to get more detailed error from MT5
            try:
                import MetaTrader5 as mt5
                mt5_error = mt5.last_error()
                if mt5_error:
                    logging.error(f"MT5 last_error: {mt5_error}")
            except Exception:
                pass
            return False
        
        logging.info("MT5 connected successfully")
        
        # Verify connection by getting account info
        account_info = self.mt5.get_account_info()
        if account_info:
            logging.info(f"Account verified - Login: {account_info.get('login')}, Balance: {account_info.get('balance')}, Server: {account_info.get('server')}")
        else:
            logging.warning("Could not retrieve account info after connection")
        
        # Get or detect device ID
        device_id = self.config.get('data_storage.device_id')
        if not device_id:
            device_id = get_local_ip_address()
            if device_id:
                self.config.set('data_storage.device_id', device_id)
                self.config.save()
                logging.info(f"Auto-detected and saved device_id: {device_id}")
            else:
                logging.warning("Could not detect device ID")
                device_id = 'unknown'
        else:
            logging.info(f"Using configured device_id: {device_id}")
        
        # Initialize MySQL Manager for tick data storage
        mysql_enabled = self.config.get('mysql.enabled', True)
        
        self.mysql_manager = None
        if mysql_enabled:
            try:
                mysql_config = {
                    'host': self.config.get('mysql.host', '127.0.0.1'),
                    'port': self.config.get('mysql.port', 3306),
                    'username': self.config.get('mysql.username', 'root'),
                    'password': self.config.get('mysql.password', 'lokesh'),
                    'database': self.config.get('mysql.database', 'forex')
                }
                
                self.mysql_manager = MySQLManager(**mysql_config)
                
                if self.mysql_manager.initialize():
                    logging.info("MySQL connection successful - tick data will be stored in MySQL")
                else:
                    logging.warning("MySQL initialization failed - tick data storage disabled")
                    self.mysql_manager = None
            except Exception as e:
                logging.warning(f"MySQL initialization failed: {e} - continuing without MySQL storage")
                self.mysql_manager = None
        else:
            logging.info("MySQL storage disabled in configuration")
        
        # Initialize PocketBase Manager (still used for trades/signals)
        data_storage_enabled = self.config.get('data_storage.enabled', True)
        pocketbase_url = self.config.get('data_storage.pocketbase_url', 'http://192.168.173.112:8090')
        
        if data_storage_enabled:
            try:
                admin_email = self.config.get('data_storage.admin_email', '')
                admin_password = self.config.get('data_storage.admin_password', '')
                
                self.pb_manager = PocketBaseManager(
                    base_url=pocketbase_url,
                    device_id=device_id,
                    telegram_bot=None,  # No Telegram in headless mode (can be added later)
                    admin_email=admin_email if admin_email else None,
                    admin_password=admin_password if admin_password else None
                )
                
                if self.pb_manager.health_check():
                    logging.info("PocketBase connection successful - trades/signals will be stored in PocketBase")
                else:
                    logging.warning("PocketBase server not reachable - trade/signal storage disabled")
                    self.pb_manager = None
            except Exception as e:
                logging.warning(f"PocketBase initialization failed: {e} - continuing without PocketBase storage")
                self.pb_manager = None
        else:
            logging.info("PocketBase storage disabled in configuration")
        
        # Initialize DataFeed with MySQL manager (for tick data)
        update_interval = self.config.get('data_feed.update_interval_seconds', 0.1)
        self.data_feed = DataFeed(self.mt5, update_interval=update_interval, mysql_manager=self.mysql_manager)
        
        # Add symbols from config - only allowed symbols will be stored in MySQL
        # Allowed symbols: XAUSD, EURUSD, EURJPY, USDJPY, BTCUSD
        symbols = self.config.get('data_feed.symbols', [])
        for symbol in symbols:
            self.data_feed.add_symbol(symbol)
        
        # Start data feed
        self.data_feed.start()
        logging.info(f"DataFeed started with {len(self.data_feed.symbols)} symbols")
        
        # Initialize Indicator Feed
        self.indicator_feed = RealTimeIndicatorFeed(self.mt5, pb_manager=self.pb_manager)
        
        # Initialize OrderManager
        project_root = Path(__file__).resolve().parent.parent
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)
        persistence_file = str(data_dir / "trade_history.json")
        self.order_manager = OrderManager(self.mt5, persistence_file=persistence_file)
        
        # Attach PocketBase to trade history
        if self.pb_manager and hasattr(self.order_manager, 'trade_history'):
            self.order_manager.trade_history.pb_manager = self.pb_manager
            logging.info("PocketBase manager attached to TradeHistory")
        
        # Initialize StrategyManager with signal storage callback
        self.strategy_manager = StrategyManager(
            position_tracker=self.order_manager.position_tracker,
            signal_callback=self.on_strategy_signal,
            pb_manager=self.pb_manager
        )
        
        # Load saved strategies
        strategy_persistence = StrategyPersistence()
        saved_strategies = strategy_persistence.load_all_strategies()
        for strategy in saved_strategies:
            try:
                # Set MT5 connector reference if needed (for VWAP, SMC, EMA, SuperTrend strategies)
                if hasattr(strategy, 'set_mt5_connector'):
                    strategy.set_mt5_connector(self.mt5)
                
                # Set market data panel reference if needed (for OHLC strategies)
                # In headless mode, we don't have market data panel, but strategies should work without it
                
                # Add strategy to manager
                self.strategy_manager.add_strategy(strategy)
                
                # Subscribe to indicators for this symbol if needed
                if hasattr(strategy, 'timeframe') and hasattr(strategy, 'indicators'):
                    timeframe = getattr(strategy, 'timeframe', mt5.TIMEFRAME_M1)
                    indicator_names = list(strategy.indicators.keys()) if strategy.indicators else []
                    if indicator_names:
                        self.indicator_feed.subscribe(strategy.symbol, timeframe, indicator_names)
                
                logging.info(f"Loaded strategy: {strategy.name} (enabled={strategy.enabled})")
            except Exception as e:
                logging.error(f"Error loading strategy: {e}", exc_info=True)
        
        # Initialize RiskManager and TradeMonitor
        self.risk_manager = RiskManager(self.mt5)
        self.trade_monitor = TradeMonitor(self.mt5)
        
        logging.info("All components initialized successfully")
        return True
    
    def on_strategy_signal(self, strategy_name: str, signal: str, symbol: str, price: float, timestamp: datetime):
        """
        Handle strategy signal (callback from StrategyManager)
        Stores signal in PocketBase and executes trade
        """
        logging.info(f"Strategy {strategy_name} generated {signal} signal for {symbol} at {price}")
        
        # Store signal in PocketBase (already done by StrategyManager, but ensure it's stored)
        if self.pb_manager:
            try:
                signal_data = {
                    'symbol': symbol,
                    'timestamp': timestamp.isoformat(),
                    'signal_type': signal,
                    'strategy_name': strategy_name,
                    'price': price
                }
                self.pb_manager.store_signal(signal_data)
            except Exception as e:
                logging.error(f"Error storing signal: {e}")
        
        # Execute the trade
        strategy = self.strategy_manager.get_strategy(strategy_name)
        if strategy:
            self.execute_strategy_signal(strategy, signal)
    
    def execute_strategy_signal(self, strategy, signal: str):
        """Execute a strategy signal (trade)"""
        symbol = strategy.symbol
        
        # Find correct symbol case from data feed
        actual_symbol = symbol
        for feed_symbol in self.data_feed.symbols:
            if feed_symbol.upper() == symbol.upper():
                actual_symbol = feed_symbol
                break
        
        # Get current price
        tick = self.data_feed.get_latest_tick(actual_symbol)
        if not tick:
            logging.warning(f"No tick data for {actual_symbol}")
            return
        
        entry_price = tick['ask'] if signal == 'BUY' else tick['bid']
        default_lot = self.config.get('trading.default_lot_size', 0.01)
        
        # Check if strategy already has position in same direction
        if self.order_manager.position_tracker.has_position(strategy.name, actual_symbol, signal):
            logging.debug(f"Strategy {strategy.name} already has {signal} position for {actual_symbol}, skipping")
            return
        
        # Calculate SL/TP
        sl, tp = self.calculate_sl_tp(strategy, actual_symbol, entry_price, signal)
        
        # Validate order with risk manager
        validation = self.risk_manager.validate_order(actual_symbol, default_lot, entry_price, sl)
        if not validation.get('valid', True):
            logging.warning(f"Order validation failed for {strategy.name}: {validation.get('message', 'Unknown error')}")
            return
        
        # Place order via OrderManager
        try:
            result = self.order_manager.place_market_order(
                symbol=actual_symbol,
                order_type=signal,
                volume=default_lot,
                sl=sl,
                tp=tp,
                comment=f"Strategy: {strategy.name}"
            )
        except Exception as e:
            logging.error(f"Error placing order: {e}", exc_info=True)
            result = None
        
        if result:
            retcode = result.get('retcode', 0)
            success = result.get('success', False)
            
            if success or retcode == 10009:  # TRADE_RETCODE_DONE
                ticket = result.get('order') or result.get('ticket')
                logging.info(f"Trade executed: {signal} {actual_symbol} @ {entry_price}, Ticket: {ticket}")
                
                # Add to trade history
                if hasattr(self.order_manager, 'trade_history') and ticket:
                    self.order_manager.trade_history.add_trade(
                        ticket=ticket,
                        strategy_name=strategy.name,
                        symbol=actual_symbol,
                        entry_price=entry_price,
                        entry_time=datetime.now(),
                        entry_condition=f"{strategy.name} {signal} signal",
                        sl=sl,
                        tp=tp,
                        volume=default_lot,
                        direction=signal
                    )
            else:
                error = result.get('error', f"Retcode: {retcode}")
                logging.error(f"Failed to execute trade: {error}")
        else:
            logging.error("Failed to execute trade: No result from order manager")
    
    def calculate_sl_tp(self, strategy, symbol: str, entry_price: float, signal: str):
        """Calculate stop loss and take profit from strategy settings"""
        # Get symbol info for point/pip calculations
        symbol_info = self.mt5.get_symbol_info(symbol)
        if not symbol_info:
            # Fallback to risk manager
            sl = self.risk_manager.calculate_stop_loss(symbol, entry_price, signal)
            tp = self.risk_manager.calculate_take_profit(symbol, entry_price, signal, stop_loss=sl)
            return sl, tp
        
        point = symbol_info.get('point', 0.0001)
        digits = symbol_info.get('digits', 5)
        
        # Check if strategy has SL/TP configuration
        if not hasattr(strategy, 'sl_type') or strategy.sl_type is None:
            # Use default risk manager calculation
            sl = self.risk_manager.calculate_stop_loss(symbol, entry_price, signal)
            tp = self.risk_manager.calculate_take_profit(symbol, entry_price, signal, stop_loss=sl)
            return sl, tp
        
        # Calculate SL based on type
        sl_value = getattr(strategy, 'sl_value', 20.0)
        sl_type = strategy.sl_type
        
        if "Pips" in sl_type:
            # Convert pips to price points (1 pip = 10 points for 5-digit, 1 point for 4-digit)
            pip_size = point * (10 if digits == 5 else 1)
            sl_distance = sl_value * pip_size
        elif "Points" in sl_type:
            # Direct points
            sl_distance = sl_value * point
        else:  # Percentage
            # Percentage-based
            sl_distance = entry_price * (sl_value / 100.0)
        
        # Calculate SL price
        if signal == 'BUY':
            sl = entry_price - sl_distance
        else:  # SELL
            sl = entry_price + sl_distance
        
        # Calculate TP
        use_ratio = getattr(strategy, 'use_ratio', True)
        if use_ratio:
            # Use 1:2 ratio (TP = 2x SL distance)
            tp_distance = sl_distance * 2.0
        else:
            # Use manual TP value
            tp_value = getattr(strategy, 'tp_value', sl_value * 2.0)
            if "Pips" in sl_type:
                pip_size = point * (10 if digits == 5 else 1)
                tp_distance = tp_value * pip_size
            elif "Points" in sl_type:
                tp_distance = tp_value * point
            else:  # Percentage
                tp_distance = entry_price * (tp_value / 100.0)
        
        # Calculate TP price
        if signal == 'BUY':
            tp = entry_price + tp_distance
        else:  # SELL
            tp = entry_price - tp_distance
        
        return sl, tp
    
    def update_strategies(self):
        """Update all strategies and handle signals"""
        if not self.mt5.is_connected() or not self.data_feed.running:
            return
        
        enabled_strategies = self.strategy_manager.get_enabled_strategies()
        if not enabled_strategies:
            return
        
        # Collect market data for all symbols
        strategy_symbols = set(s.symbol for s in enabled_strategies)
        market_data = {}
        
        for symbol in strategy_symbols:
            # Find correct case
            actual_symbol = symbol
            for feed_symbol in self.data_feed.symbols:
                if feed_symbol.upper() == symbol.upper():
                    actual_symbol = feed_symbol
                    break
            
            tick = self.data_feed.get_latest_tick(actual_symbol)
            if not tick:
                continue
            
            # Get rates for indicators
            rates = self.data_feed.get_rates(actual_symbol, mt5.TIMEFRAME_M1, 300)
            if not rates:
                rates = self.mt5.get_rates(actual_symbol, mt5.TIMEFRAME_M1, 300)
            
            if not rates:
                continue
            
            market_data[actual_symbol] = {
                'tick': tick,
                'rates': rates,
                'indicators': {}
            }
        
        # Calculate indicators for each strategy
        for strategy in enabled_strategies:
            symbol = strategy.symbol
            matching_symbol = None
            for market_symbol in market_data.keys():
                if market_symbol.upper() == symbol.upper():
                    matching_symbol = market_symbol
                    break
            
            if matching_symbol:
                data = market_data[matching_symbol]
                rates = data['rates']
                timeframe = getattr(strategy, 'timeframe', mt5.TIMEFRAME_M1)
                
                # Calculate indicators
                indicators = {}
                for ind_name, indicator in getattr(strategy, 'indicators', {}).items():
                    try:
                        if ind_name.upper() == "RSI" or "RSI" in ind_name.upper():
                            rsi_period = getattr(indicator, 'period', 14)
                            mt5_rsi = self.mt5.get_rsi(matching_symbol, timeframe, rsi_period, 300)
                            if mt5_rsi is not None:
                                indicators[ind_name] = mt5_rsi
                        else:
                            indicator.update(rates)
                            latest_value = indicator.get_value()
                            if latest_value is not None:
                                indicators[ind_name] = latest_value
                    except Exception as e:
                        logging.error(f"Error calculating indicator {ind_name}: {e}")
                
                data['indicators'] = indicators
        
        # Update strategies (this will call on_strategy_signal callback if signal generated)
        signals = self.strategy_manager.update_strategies(market_data)
        
        # Handle signals that weren't processed by callback
        for strategy_name, signal in signals.items():
            if signal:
                strategy = self.strategy_manager.get_strategy(strategy_name)
                if strategy:
                    # Check if already has position
                    if self.order_manager.position_tracker.has_position(strategy.name, strategy.symbol, signal):
                        continue
                    
                    # Execute trade (callback should have handled this, but ensure it's done)
                    self.execute_strategy_signal(strategy, signal)
    
    def update_positions(self):
        """Update position tracking and sync external trades"""
        if hasattr(self.order_manager, 'update_positions'):
            self.order_manager.update_positions()
        
        # Sync external trades (trades made from development code or other systems)
        self.sync_external_trades()
    
    def sync_external_trades(self):
        """
        Sync trade history with MT5 positions to detect external trades
        This ensures trades made from development code or other systems are captured
        """
        if not self.mt5.is_connected() or not hasattr(self.order_manager, 'trade_history'):
            return
        
        try:
            # Get all open positions from MT5
            open_positions = {}
            open_tickets = set()
            try:
                positions = self.order_manager.get_positions()
                for pos in positions:
                    ticket = pos.get('ticket', 0)
                    if ticket:
                        open_positions[ticket] = pos
                        open_tickets.add(ticket)
            except Exception as e:
                logging.error(f"Error getting open positions for sync: {e}", exc_info=True)
                return
            
            # Get all trades from trade history
            all_trades = self.order_manager.trade_history.get_all_trades()
            
            # Sync closed trades: If trade shows "Open" but position doesn't exist in MT5, it was closed
            for trade in all_trades:
                ticket = trade.get('ticket', 0)
                if not ticket:
                    continue
                
                # If trade is marked "Open" but position doesn't exist in MT5, it was closed
                if trade.get('status') == 'Open' and ticket not in open_tickets:
                    logging.info(f"Trade {ticket} marked as Open but not in MT5 positions - syncing as closed")
                    
                    # Get exit details from MT5 deal history
                    exit_price, exit_time, profit = self._get_exit_details_from_mt5(ticket)
                    exit_condition = self._get_exit_condition_from_mt5(ticket, 'Manual')
                    
                    # Update trade in history (this will also store to PocketBase)
                    try:
                        self.order_manager.trade_history.close_trade(
                            ticket=ticket,
                            exit_price=exit_price,
                            exit_time=exit_time or datetime.now(),
                            exit_condition=exit_condition,
                            profit=profit
                        )
                        logging.info(f"Synced closed trade {ticket} in history: {exit_condition}")
                    except Exception as e:
                        logging.error(f"Error syncing closed trade {ticket}: {e}", exc_info=True)
            
            # Add any MT5 positions not in trade history (positions opened outside system)
            for ticket, pos in open_positions.items():
                if not self.order_manager.trade_history.get_trade(ticket):
                    # Position exists in MT5 but not in trade history - add it
                    strategy_name = self._extract_strategy_name(pos.get('comment', ''))
                    entry_condition = self._get_entry_condition(pos.get('comment', ''))
                    
                    self.order_manager.trade_history.add_trade(
                        ticket=ticket,
                        strategy_name=strategy_name,
                        symbol=pos.get('symbol', ''),
                        entry_price=pos.get('price_open', 0.0),
                        entry_time=pos.get('time', datetime.now()),
                        entry_condition=entry_condition,
                        sl=pos.get('sl', 0.0),
                        tp=pos.get('tp', 0.0),
                        volume=pos.get('volume', 0.01),
                        direction='BUY' if pos.get('type', 0) == 0 else 'SELL'
                    )
                    logging.info(f"Added external trade {ticket} to history from MT5: {strategy_name} - {pos.get('symbol', '')} - {'BUY' if pos.get('type', 0) == 0 else 'SELL'}")
        
        except Exception as e:
            logging.error(f"Error syncing external trades: {e}", exc_info=True)
    
    def _extract_strategy_name(self, comment: str) -> str:
        """Extract strategy name from order comment"""
        if not comment:
            return "External Trade"
        
        if 'Strategy:' in comment:
            return comment.split('Strategy:')[1].strip()
        
        # If comment is too long, truncate it
        if len(comment) > 50:
            return comment[:50]
        
        return comment if comment else "External Trade"
    
    def _get_entry_condition(self, comment: str) -> str:
        """Extract entry condition from comment or return default"""
        if not comment:
            return "External Trade"
        
        if 'Condition:' in comment:
            return comment.split('Condition:')[1].strip()
        
        return "External Trade"
    
    def _get_exit_condition_from_mt5(self, ticket: int, fallback: str = "Manual") -> str:
        """
        Get exit condition from MT5 deal history
        
        Args:
            ticket: Position ticket
            fallback: Fallback value if not found
            
        Returns:
            Exit condition string
        """
        try:
            if not self.mt5.is_connected():
                return fallback
            
            # Get deal history from MT5
            date_from = datetime.now() - timedelta(days=1)
            deals = self.mt5.get_deal_history(date_from=date_from)
            
            for deal in deals:
                # Find exit deal for this position (entry == 1 means exit/out deal)
                if (deal.get('position_id') == ticket or deal.get('order') == ticket) and deal.get('entry') == 1:
                    exit_condition = deal.get('exit_condition', fallback)
                    if exit_condition and exit_condition != fallback:
                        return exit_condition
            
            return fallback
        except Exception as e:
            logging.error(f"Error getting exit condition from MT5 for ticket {ticket}: {e}", exc_info=True)
            return fallback
    
    def _get_exit_details_from_mt5(self, ticket: int) -> tuple:
        """
        Get exit price, time, and profit from MT5 deal history
        
        Args:
            ticket: Position ticket
            
        Returns:
            Tuple of (exit_price, exit_time, profit) or (0.0, None, 0.0) if not found
        """
        try:
            if not self.mt5.is_connected():
                return (0.0, None, 0.0)
            
            # Get deal history from MT5
            date_from = datetime.now() - timedelta(days=1)
            deals = self.mt5.get_deal_history(date_from=date_from)
            
            for deal in deals:
                # Find exit deal for this position (entry == 1 means exit/out deal)
                if (deal.get('position_id') == ticket or deal.get('order') == ticket) and deal.get('entry') == 1:
                    exit_price = deal.get('price', 0.0)
                    profit = deal.get('profit', 0.0)
                    exit_time = deal.get('time')
                    
                    if isinstance(exit_time, datetime):
                        pass  # Already datetime
                    elif isinstance(exit_time, (int, float)):
                        exit_time = datetime.fromtimestamp(exit_time)
                    else:
                        exit_time = None
                    
                    return (exit_price, exit_time, profit)
            
            return (0.0, None, 0.0)
        except Exception as e:
            logging.error(f"Error getting exit details from MT5 for ticket {ticket}: {e}", exc_info=True)
            return (0.0, None, 0.0)
    
    def monitor_trades(self):
        """Monitor trades for SL/TP"""
        if not self.mt5.is_connected() or not self.trade_monitor:
            return
        
        # Get all open positions
        positions = self.order_manager.get_positions()
        if not positions:
            return
        
        # Helper function to get current price for a symbol and position type
        def get_current_price(symbol, pos_type):
            """Get current price for monitoring (ask for BUY, bid for SELL)"""
            tick = self.data_feed.get_latest_tick(symbol)
            if not tick:
                return None
            # pos_type: 0 = BUY, 1 = SELL
            return tick['ask'] if pos_type == 0 else tick['bid']
        
        # Monitor positions and check SL/TP conditions
        positions_to_close = self.trade_monitor.monitor_positions(positions, get_current_price)
        
        # Close positions that hit SL/TP
        for pos_to_close in positions_to_close:
            ticket = pos_to_close.get('ticket')
            action = pos_to_close.get('action')  # 'SL' or 'TP'
            trigger_price = pos_to_close.get('trigger_price')
            
            logging.info(f"Closing position {ticket} due to {action} at {trigger_price}")
            
            # Try to close position
            close_success = self.order_manager.close_position(ticket)
            
            if close_success:
                logging.info(f"Position {ticket} closed successfully")
            else:
                # Check if position still exists (might have been auto-closed by MT5)
                remaining_positions = self.mt5.get_positions()
                position_still_exists = any(p.get('ticket') == ticket for p in remaining_positions)
                
                if not position_still_exists:
                    logging.info(f"Position {ticket} was already closed by MT5 (auto-close)")
                else:
                    logging.warning(f"Failed to close position {ticket}, position still exists")
    
    def update_indicators(self):
        """Update indicators for subscribed symbols"""
        if self.indicator_feed:
            for symbol in self.data_feed.symbols:
                self.indicator_feed.update_indicators(symbol)
    
    def run(self):
        """Main loop"""
        self.running = True
        logging.info("=" * 70)
        logging.info("Headless Trading Platform Running")
        logging.info("=" * 70)
        logging.info("Press Ctrl+C to stop")
        
        try:
            while self.running:
                current_time = time.time()
                
                # Update strategies
                if current_time - self.last_strategy_update >= self.strategy_update_interval:
                    self.update_strategies()
                    self.last_strategy_update = current_time
                
                # Update positions
                if current_time - self.last_position_update >= self.position_update_interval:
                    self.update_positions()
                    self.last_position_update = current_time
                
                # Monitor trades
                if current_time - self.last_trade_monitor >= self.trade_monitor_interval:
                    self.monitor_trades()
                    self.last_trade_monitor = current_time
                
                # Update indicators (less frequently)
                if int(current_time) % 5 == 0:  # Every 5 seconds
                    self.update_indicators()
                
                time.sleep(0.1)  # Small sleep to prevent CPU spinning
                
        except KeyboardInterrupt:
            logging.info("Shutdown requested by user")
        except Exception as e:
            logging.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Shutdown gracefully"""
        logging.info("Shutting down...")
        self.running = False
        
        if self.data_feed:
            self.data_feed.stop()
        
        if self.mt5:
            self.mt5.shutdown()
        
        logging.info("Shutdown complete")


def main():
    """Main entry point"""
    # Initialize minimal QApplication (required for Qt-based components)
    app = QApplication(sys.argv)
    app.setApplicationName("MT5 Trading Platform (Headless)")
    
    # Create and initialize platform
    platform = HeadlessTradingPlatform()
    if not platform.initialize():
        logging.error("Initialization failed")
        sys.exit(1)
    
    # Setup signal handler for graceful shutdown
    def signal_handler(sig, frame):
        logging.info("Received shutdown signal")
        platform.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run platform (this will block)
    platform.run()
    
    # Cleanup
    app.quit()


if __name__ == "__main__":
    main()

