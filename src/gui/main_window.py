"""
Main Window
PyQt6 main application window
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Tuple
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QTabWidget, QStatusBar, QMenuBar, QMessageBox, QLabel, QPushButton)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QColor

from .market_data_panel import MarketDataPanel
from .chart_widget import ChartWidget
from .strategy_builder import StrategyBuilder
from .strategy_panel import StrategyPanel
from .settings_dialog import SettingsDialog
from .trading_bot_panel import TradingBotPanel
from ..mt5_connector import MT5Connector
from ..data_feed import DataFeed
from ..indicators.real_time_feed import RealTimeIndicatorFeed
from ..strategy.strategy_manager import StrategyManager
from ..trading.order_manager import OrderManager
from ..trading.risk_manager import RiskManager
from ..trading.trade_monitor import TradeMonitor, TradeMonitoringMode
from ..trading.reentry_manager import ReEntryManager
from ..config import Config
from ..signal_routing.signal_router import SignalRouter

logger = logging.getLogger(__name__)

# Log that enhanced diagnostic code is active
logger.info("MainWindow: Enhanced diagnostic logging is ACTIVE")


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        logger.info("MainWindow: Initializing with enhanced diagnostic capabilities")
        self.config = Config()
        self.mt5 = MT5Connector()
        # Get update interval from config (default 0.1 seconds for real-time)
        update_interval = self.config.get('data_feed.update_interval_seconds', 0.1)
        self.data_feed = DataFeed(self.mt5, update_interval=update_interval)
        self.indicator_feed = RealTimeIndicatorFeed(self.mt5)
        
        # Create data directory for trade history persistence
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"
        data_dir.mkdir(exist_ok=True)
        persistence_file = str(data_dir / "trade_history.json")
        
        self.order_manager = OrderManager(self.mt5, persistence_file=persistence_file)
        self.strategy_manager = StrategyManager(position_tracker=self.order_manager.position_tracker)
        self.risk_manager = RiskManager(self.mt5)
        self.trade_monitor = TradeMonitor(self.mt5)
        self.reentry_manager = ReEntryManager()
        
        # Initialize Telegram bot if enabled
        self.telegram_bot = None
        self._initialize_telegram_bot()
        
        logger.info(f"MainWindow: Initialized - MT5 connected={self.mt5.is_connected()}")
        
        # Initialize signal routing (kept for potential strategy use)
        self.signal_router = SignalRouter(self.order_manager, self.risk_manager)
        # Signal server removed - no longer needed without Signals tab
        
        self.setup_ui()
        self.setup_timers()
        self.setup_connections()
        
        # Load saved strategies from disk (before connecting to MT5)
        self.load_saved_strategies()
        
        # Update strategy panel after loading
        if hasattr(self, 'strategy_panel'):
            self.strategy_panel.update_strategies()
        
        # Signal server setup removed - no longer needed without Signals tab
        
        # Try to connect to MT5 on startup
        self.connect_to_mt5()
        
        # Load saved strategies from disk (before connecting to MT5)
        self.load_saved_strategies()
        
        # Update strategy panel after loading
        if hasattr(self, 'strategy_panel'):
            self.strategy_panel.update_strategies()
        
        # Try to connect to MT5 on startup
        self.connect_to_mt5()
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("MetaTrader 5 Trading Platform")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_tabs()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add Telegram bot status indicator
        self.telegram_status_label = QLabel("Telegram: Not Configured")
        self.telegram_status_label.setStyleSheet("padding: 2px 8px; border-radius: 3px; background-color: #666; color: white;")
        self.status_bar.addPermanentWidget(self.telegram_status_label)
        
        # Add test message button
        self.telegram_test_btn = QPushButton("Test Telegram")
        self.telegram_test_btn.setMaximumWidth(100)
        self.telegram_test_btn.clicked.connect(self.test_telegram_message)
        self.telegram_test_btn.setEnabled(False)
        self.status_bar.addPermanentWidget(self.telegram_test_btn)
        
        self.status_bar.showMessage("Ready")
        
        # Update telegram status after initialization
        self.update_telegram_status()
    
    def create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        connect_action = QAction("Connect to MT5", self)
        connect_action.triggered.connect(self.connect_to_mt5)
        file_menu.addAction(connect_action)
        
        disconnect_action = QAction("Disconnect from MT5", self)
        disconnect_action.triggered.connect(self.disconnect_from_mt5)
        file_menu.addAction(disconnect_action)
        
        file_menu.addSeparator()
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        refresh_action = QAction("Refresh Data", self)
        refresh_action.triggered.connect(self.refresh_data)
        view_menu.addAction(refresh_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_tabs(self):
        """Create application tabs"""
        # Market Data tab
        self.market_data_panel = MarketDataPanel(self.data_feed, self.mt5)
        self.tab_widget.addTab(self.market_data_panel, "Market Data")
        
        # Chart tab (pass market_data_panel for OHLC data access and order_manager for trade levels)
        self.chart_widget = ChartWidget(self.data_feed, self.mt5, self.strategy_manager, self.market_data_panel, self.order_manager)
        self.tab_widget.addTab(self.chart_widget, "Charts")
        
        # Strategy Builder tab
        self.strategy_builder = StrategyBuilder(
            self.data_feed, 
            self.strategy_manager,
            self.mt5
        )
        self.tab_widget.addTab(self.strategy_builder, "Strategy Builder")
        
        # Trading Bot tab
        self.trading_bot_panel = TradingBotPanel(
            self.data_feed,
            self.strategy_manager,
            self.mt5,
            self.market_data_panel
        )
        self.tab_widget.addTab(self.trading_bot_panel, "Trading Bot")
        
        # Strategy Manager tab
        self.strategy_panel = StrategyPanel(
            self.strategy_manager,
            self.order_manager,
            self.data_feed,
            self.mt5,
            manual_close_handler=self._handle_manual_close,
            execute_signal_handler=self.execute_strategy_signal
        )
        self.tab_widget.addTab(self.strategy_panel, "Strategies")
    
    def setup_timers(self):
        """Setup update timers"""
        # Timer for strategy updates
        self.strategy_timer = QTimer()
        self.strategy_timer.timeout.connect(self.update_strategies)
        self.strategy_timer.start(1000)  # Update every second
        
        # Timer for position updates and trade monitoring
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self.update_positions)
        self.position_timer.start(500)  # Update every 0.5 seconds (faster for ARM)
        
        # Timer for trade monitoring (SL/TP checking)
        self.trade_monitor_timer = QTimer()
        self.trade_monitor_timer.timeout.connect(self.monitor_trades)
        self.trade_monitor_timer.start(500)  # Check every 0.5 seconds for LTP mode
    
    def setup_connections(self):
        """Setup signal connections"""
        # Connect data feed signals
        self.data_feed.tick_received.connect(self.on_tick_received)
        
        # Connect real-time indicator feed
        # Update indicators when new ticks arrive
        self.data_feed.tick_received.connect(self._on_tick_for_indicators)
        self.indicator_feed.indicators_updated.connect(self._on_indicators_updated)
        
        # Update trade panel symbols when data feed symbols change
        # We'll update on tick received (indicates symbol was added)
        self.data_feed.tick_received.connect(self._on_tick_for_symbol_update)
        
        # Connect strategy panel signals
        if hasattr(self.strategy_panel, 'strategy_enabled'):
            self.strategy_panel.strategy_enabled.connect(self.on_strategy_enabled)
        if hasattr(self.strategy_panel, 'strategy_edit_requested'):
            self.strategy_panel.strategy_edit_requested.connect(self.on_strategy_edit_requested)
    
    def connect_to_mt5(self):
        """Connect to MetaTrader 5"""
        mt5_config = self.config.get('mt5', {})
        
        path = mt5_config.get('path', '')
        login = mt5_config.get('login', 0)
        password = mt5_config.get('password', '')
        server = mt5_config.get('server', '')
        timeout = mt5_config.get('timeout', 10000)
        
        # Auto-detect path if not set
        if not path:
            from ..mt5_utils import find_mt5_path
            path = find_mt5_path() or ""
            if path:
                self.config.set('mt5.path', path)
                self.config.save()
        
        if not login or not password or not server:
            QMessageBox.warning(
                self,
                "Configuration Required",
                "Please configure MT5 connection settings in Settings menu."
            )
            self.show_settings()
            return
        
        self.status_bar.showMessage("Connecting to MT5...")
        
        if self.mt5.initialize(path, login, password, server, timeout):
            self.status_bar.showMessage("Connected to MT5", 5000)
            
            # Load available symbols in market data panel
            self.market_data_panel.load_available_symbols()
            
            # Update chart widget symbol list
            self.chart_widget.update_symbol_list()
            
            # Update strategy builder symbol list
            self.strategy_builder.update_symbol_list()
            
            # Symbols are available in data feed for other panels
            
            # Load saved symbols from config
            saved_symbols = self.config.get('data_feed.symbols', [])
            for symbol in saved_symbols:
                self.data_feed.add_symbol(symbol)
            
            # Add symbols from loaded strategies
            for strategy in self.strategy_manager.get_all_strategies():
                if strategy.symbol not in self.data_feed.symbols:
                    self.data_feed.add_symbol(strategy.symbol)
            
            # Start data feed
            if not self.data_feed.symbols:
                # If no saved symbols, try default
                default_symbol = self.config.get('trading.default_symbol', 'EURUSD')
                if not self.data_feed.add_symbol(default_symbol):
                    # Try common alternatives
                    alternatives = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD']
                    for alt in alternatives:
                        if self.data_feed.add_symbol(alt):
                            break
            
            self.data_feed.start()
            
            # Save symbols to config
            self.save_symbols_to_config()
            
            # Update UI
            self.market_data_panel.update_account_info()
        else:
            self.status_bar.showMessage("Failed to connect to MT5", 5000)
            QMessageBox.critical(
                self,
                "Connection Failed",
                "Failed to connect to MetaTrader 5. Please check your settings."
            )
    
    def disconnect_from_mt5(self):
        """Disconnect from MetaTrader 5"""
        self.data_feed.stop()
        self.mt5.shutdown()
        self.status_bar.showMessage("Disconnected from MT5", 5000)
    
    def setup_signal_server(self):
        """Setup and start signal server"""
        signal_config = self.config.get('signal_server', {})
        
        if not signal_config.get('enabled', True):
            logger.info("Signal server is disabled in config")
            return
        
        port = signal_config.get('port', 8080)
        host = signal_config.get('host', '0.0.0.0')
        
        # Configure signal rules
        if hasattr(self.signal_router, 'signal_rules'):
            self.signal_router.signal_rules.cancel_previous_enabled = signal_config.get('cancel_previous', True)
            self.signal_router.signal_rules.stop_reverse_enabled = signal_config.get('stop_reverse', False)
        
        # Signal server removed - no longer needed without Signals tab
        # Signal router is still available for strategy use if needed
    
    def stop_signal_server(self):
        """Stop signal server - DISABLED: Signal server removed"""
        # Signal server has been removed
        pass
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            # Reload config
            self.config.load()
            # Reinitialize Telegram bot if settings changed
            self._initialize_telegram_bot()
            self.update_telegram_status()
            self.status_bar.showMessage("Settings saved", 3000)
    
    def refresh_data(self):
        """Refresh market data"""
        if self.mt5.is_connected():
            self.market_data_panel.refresh_data()
            self.chart_widget.refresh_chart()
    
    def on_tick_received(self, symbol: str, tick_data: dict):
        """Handle tick data received"""
        # Update market data panel
        self.market_data_panel.update_tick(symbol, tick_data)
        
        # Update chart
        self.chart_widget.update_tick(symbol, tick_data)
    
    def update_strategies(self):
        """Update all strategies"""
        # Reduced logging frequency - only log important events to file (INFO level)
        
        if not self.mt5.is_connected():
            return
        
        if not self.data_feed.running:
            return
        
        enabled_strategies = self.strategy_manager.get_enabled_strategies()
        
        if not enabled_strategies:
            return
        
        # Collect market data for all symbols used by strategies
        strategy_symbols = set(s.symbol for s in enabled_strategies)
        market_data = {}
        
        for symbol in strategy_symbols:
            # Ensure symbol is in data feed (case-insensitive match)
            symbol_in_feed = None
            for feed_symbol in self.data_feed.symbols:
                if feed_symbol.upper() == symbol.upper():
                    symbol_in_feed = feed_symbol
                    break
            
            if not symbol_in_feed:
                if self.mt5.is_connected():
                    logger.debug(f"update_strategies: Adding symbol {symbol} to data feed")
                    self.data_feed.add_symbol(symbol)
                    # Try to find the correct case after adding
                    for feed_symbol in self.data_feed.symbols:
                        if feed_symbol.upper() == symbol.upper():
                            symbol_in_feed = feed_symbol
                            break
            
            # Use the correct case symbol from data feed
            actual_symbol = symbol_in_feed if symbol_in_feed else symbol
            
            tick = self.data_feed.get_latest_tick(actual_symbol)
            if not tick:
                continue
            
            # Get rates for indicators (use strategy's timeframe)
            import MetaTrader5 as mt5
            # Note: We'll get the timeframe from the strategy when we process it
            # For now, collect data for all strategies using their individual timeframes
            # We'll handle this per-strategy below
            # Use more bars (300) for better indicator accuracy, especially for RSI
            rates = self.data_feed.get_rates(actual_symbol, mt5.TIMEFRAME_M1, 300)
            
            # If data feed doesn't have rates, get directly from MT5
            if not rates and self.mt5.is_connected():
                rates = self.mt5.get_rates(actual_symbol, mt5.TIMEFRAME_M1, 300)
            
            if not rates:
                continue
            
            # Prepare market data with indicators (use actual_symbol for consistency)
            market_data[actual_symbol] = {
                'tick': tick,
                'rates': rates,
                'indicators': {}
            }
        
        # Calculate indicators for each strategy
        for strategy in enabled_strategies:
            symbol = strategy.symbol
            # Find matching symbol in market_data (case-insensitive)
            matching_symbol = None
            for market_symbol in market_data.keys():
                if market_symbol.upper() == symbol.upper():
                    matching_symbol = market_symbol
                    break
            
            if matching_symbol:
                data = market_data[matching_symbol]
                rates = data['rates']
                
                # Get strategy's timeframe
                import MetaTrader5 as mt5
                timeframe = getattr(strategy, 'timeframe', mt5.TIMEFRAME_M1)
                timeframe_name = {mt5.TIMEFRAME_M1: "M1", mt5.TIMEFRAME_M5: "M5", mt5.TIMEFRAME_M15: "M15", 
                                 mt5.TIMEFRAME_M30: "M30", mt5.TIMEFRAME_H1: "H1", mt5.TIMEFRAME_H4: "H4", 
                                 mt5.TIMEFRAME_D1: "D1"}.get(timeframe, f"TF{timeframe}")
                
                logger.debug(f"Strategy {strategy.name}: Calculating indicators for {matching_symbol} with {len(rates)} rates (timeframe: {timeframe_name})")
                
                # Calculate indicators for this strategy
                indicators = {}
                for ind_name, indicator in strategy.indicators.items():
                    try:
                        # For RSI, fetch directly from MT5's built-in indicator
                        if ind_name.upper() == "RSI" or "RSI" in ind_name.upper():
                            # Get RSI period from indicator
                            rsi_period = getattr(indicator, 'period', 14)
                            
                            # Fetch RSI directly from MT5 (primary method)
                            mt5_rsi = self.mt5.get_rsi(matching_symbol, timeframe, rsi_period, 300)
                            if mt5_rsi is not None:
                                indicators[ind_name] = mt5_rsi
                                logger.debug(f"Strategy {strategy.name}: {ind_name} (MT5) = {mt5_rsi:.5f}")
                            else:
                                # Fallback to our calculation only if MT5 fails
                                logger.warning(f"Strategy {strategy.name}: MT5 RSI calculation failed, using fallback")
                                indicator.update(rates)
                                latest_value = indicator.get_value()
                                if latest_value is not None:
                                    indicators[ind_name] = latest_value
                                    logger.debug(f"Strategy {strategy.name}: {ind_name} (Fallback) = {latest_value:.5f}")
                                else:
                                    logger.debug(f"Strategy {strategy.name}: {ind_name} returned None")
                        else:
                            # For other indicators, use our calculation
                            indicator.update(rates)
                            latest_value = indicator.get_value()
                            if latest_value is not None:
                                indicators[ind_name] = latest_value
                                logger.debug(f"Strategy {strategy.name}: {ind_name} = {latest_value:.5f}")
                            else:
                                logger.debug(f"Strategy {strategy.name}: {ind_name} returned None")
                    except Exception as e:
                        logger.error(f"Error calculating indicator {ind_name} for {strategy.name}: {e}", exc_info=True)
                
                data['indicators'] = indicators
                logger.debug(f"Strategy {strategy.name} indicators: {indicators}")
            else:
                logger.warning(f"Strategy {strategy.name}: Symbol {symbol} not found in market_data. Available: {list(market_data.keys())}")
        
        # Update strategies
        signals = self.strategy_manager.update_strategies(market_data)
        
        # Handle signals (execute trades)
        for strategy_name, signal in signals.items():
            if signal:
                strategy = self.strategy_manager.get_strategy(strategy_name)
                if strategy:
                    # Check if strategy already has position in same direction - skip condition check entirely
                    if self.order_manager.position_tracker.has_position(strategy.name, strategy.symbol, signal):
                        logger.debug(f"Strategy {strategy_name} has {signal} position for {strategy.symbol}, skipping condition check")
                        continue
                    
                    logger.info(f"Strategy {strategy_name} generated {signal} signal")
                    
                    # Notify chart widget about the signal
                    if hasattr(self, 'chart_widget'):
                        current_price = market_data.get(strategy.symbol, {}).get('close', 0.0)
                        from datetime import datetime
                        self.chart_widget.add_strategy_signal(
                            symbol=strategy.symbol,
                            signal_type=signal,
                            price=current_price,
                            timestamp=datetime.now(),
                            strategy_name=strategy_name
                        )
                    
                    self.execute_strategy_signal(strategy, signal)
            else:
                # Log when no signal is generated (for debugging)
                strategy = self.strategy_manager.get_strategy(strategy_name)
                if strategy:
                    symbol = strategy.symbol
                    if symbol in market_data:
                        indicators = market_data[symbol].get('indicators', {})
                        logger.debug(f"Strategy {strategy_name}: No signal. Indicators: {indicators}")
    
    def _get_entry_condition_text(self, strategy, signal: str = None) -> str:
        """Get entry condition text from strategy"""
        # Check for entry_conditions_text (used by CustomStrategy)
        if hasattr(strategy, 'entry_conditions_text') and strategy.entry_conditions_text:
            return strategy.entry_conditions_text[0] if len(strategy.entry_conditions_text) > 0 else "--"
        
        # Check for buy_conditions and sell_conditions (used by OHLC and VWAP strategies)
        if signal:
            from ..strategy.ohlc_price_strategy import OHLCPriceStrategy
            from ..strategy.vwap_strategy import VWAPStrategy
            from ..strategy.ema_strategy import EMAStrategy
            
            if isinstance(strategy, OHLCPriceStrategy):
                conditions = strategy.buy_conditions if signal == 'BUY' else strategy.sell_conditions
                if conditions:
                    condition = conditions[0]  # Get first condition
                    return self._format_condition_text(condition, signal, 'ohlc')
            
            elif isinstance(strategy, VWAPStrategy):
                conditions = strategy.buy_conditions if signal == 'BUY' else strategy.sell_conditions
                if conditions:
                    condition = conditions[0]  # Get first condition
                    return self._format_condition_text(condition, signal, 'vwap')

            elif isinstance(strategy, EMAStrategy):
                conditions = strategy.buy_conditions if signal == 'BUY' else strategy.sell_conditions
                if conditions:
                    condition = conditions[0]
                    return self._format_condition_text(condition, signal, 'ema')
        
        return "--"
    
    def _format_condition_text(self, condition, signal: str, strategy_type: str) -> str:
        """Format condition object to human-readable text"""
        if not condition:
            return "--"
        
        price_ref = getattr(condition, 'price_reference', 'Current Price')
        operator = getattr(condition, 'operator', '>')
        
        if strategy_type == 'ohlc':
            ohlc_field = getattr(condition, 'ohlc_field', None)
            value = getattr(condition, 'value', None)
            
            if ohlc_field:
                return f"{price_ref} {operator} Previous {ohlc_field.upper()}"
            elif value is not None:
                return f"{price_ref} {operator} {value}"
            else:
                return f"{price_ref} {operator}"
        
        elif strategy_type == 'vwap':
            vwap_field = getattr(condition, 'vwap_field', None)
            value = getattr(condition, 'value', None)
            
            if vwap_field:
                # Format VWAP field names nicely
                if vwap_field == 'vwap':
                    field_name = 'VWAP'
                elif vwap_field.startswith('upper_band_'):
                    std = vwap_field.replace('upper_band_', '')
                    field_name = f"Upper Band ({std} STD)"
                elif vwap_field.startswith('lower_band_'):
                    std = vwap_field.replace('lower_band_', '')
                    field_name = f"Lower Band ({std} STD)"
                else:
                    field_name = vwap_field.replace('_', ' ').title()
                
                return f"{price_ref} {operator} {field_name}"
            elif value is not None:
                return f"{price_ref} {operator} {value}"
            else:
                return f"{price_ref} {operator}"

        elif strategy_type == 'ema':
            ema_field = getattr(condition, 'ema_field', None)
            value = getattr(condition, 'value', None)

            if ema_field:
                field_name = ema_field.replace('_', ' ').upper()  # EMA_1 -> EMA 1
                return f"{price_ref} {operator} {field_name}"
            elif value is not None:
                return f"{price_ref} {operator} {value}"
            else:
                return f"{price_ref} {operator}"
        
        return str(condition)
    
    def execute_strategy_signal(self, strategy, signal: str):
        """Execute a strategy signal"""
        logger.info(f"execute_strategy_signal: Executing {signal} signal for strategy {strategy.name}")
        symbol = strategy.symbol
        default_lot = self.config.get('trading.default_lot_size', 0.01)
        
        # Find the correct symbol case from data feed (case-insensitive)
        actual_symbol = symbol
        for feed_symbol in self.data_feed.symbols:
            if feed_symbol.upper() == symbol.upper():
                actual_symbol = feed_symbol
                break
        
        logger.debug(f"execute_strategy_signal: Using symbol {actual_symbol} (requested {symbol})")
        
        # Get current price
        tick = self.data_feed.get_latest_tick(actual_symbol)
        if not tick:
            logger.warning(f"execute_strategy_signal: No tick data for {actual_symbol}. Available symbols: {list(self.data_feed.symbols)}")
            return
        
        # Use actual_symbol for order placement
        symbol = actual_symbol
        
        entry_price = tick['ask'] if signal == 'BUY' else tick['bid']
        logger.debug(f"execute_strategy_signal: Entry price for {signal} = {entry_price}")
        
        # Calculate stop loss and take profit from strategy settings
        sl, tp = self.calculate_strategy_sl_tp(strategy, symbol, entry_price, signal)
        logger.debug(f"execute_strategy_signal: SL={sl}, TP={tp}")
        
        # Always check for existing positions to prevent duplicate entries (strict)
        # If strategy already has a position in the same direction, skip
        if self.order_manager.position_tracker.has_position(strategy.name, symbol, signal):
            logger.info(f"Strategy {strategy.name} already has {signal} position for {symbol}, skipping duplicate entry (strict)")
            return
        
        # Additional check: Verify position exists in MT5 (backup check in case tracker is out of sync)
        mt5_position_exists, mt5_position = self._check_mt5_position_exists(strategy.name, symbol, signal)
        if mt5_position_exists:
            logger.warning(f"Strategy {strategy.name} has {signal} position in MT5 (ticket: {mt5_position.get('ticket')}) but tracker was out of sync. Syncing tracker and skipping duplicate entry.")
            # Sync the position tracker with the MT5 position
            self.order_manager.position_tracker.add_position(
                strategy_name=strategy.name,
                symbol=symbol,
                direction=signal,
                ticket=mt5_position.get('ticket'),
                entry_price=mt5_position.get('price_open'),
                entry_time=mt5_position.get('time'),
                volume=mt5_position.get('volume'),
                sl=mt5_position.get('sl'),
                tp=mt5_position.get('tp')
            )
            return
        
        # Cross-strategy position management: Check for opposite-direction positions
        opposite_direction = 'SELL' if signal == 'BUY' else 'BUY'
        opposite_positions = self.order_manager.position_tracker.get_positions_by_direction(symbol, opposite_direction)
        
        if opposite_positions:
            logger.info(f"Found {len(opposite_positions)} opposite-direction ({opposite_direction}) position(s) for {symbol}. Closing before opening {signal} position.")
            
            # Close all opposite-direction positions from any strategy
            for opp_pos in opposite_positions:
                opp_strategy_name = opp_pos.get('strategy_name')
                opp_ticket = opp_pos.get('ticket')
                
                if opp_ticket:
                    logger.info(f"Closing {opposite_direction} position (Ticket: {opp_ticket}) from strategy {opp_strategy_name} before opening {signal} position")
                    close_success = self.order_manager.close_position(opp_ticket)
                    
                    if close_success:
                        # Get exit details from MT5 deal history
                        import time
                        time.sleep(0.2)  # Small delay to allow MT5 to process the close
                        deals = self.mt5.get_deal_history(date_from=None, date_to=None, symbol=symbol)
                        closed_deal = None
                        for deal in deals:
                            if deal.get('ticket') == opp_ticket or deal.get('position_id') == opp_ticket:
                                if deal.get('type') in [2, 3]:  # DEAL_TYPE_BALANCE or DEAL_TYPE_CREDIT
                                    continue
                                if deal.get('entry') == 1:  # Entry deal
                                    continue
                                closed_deal = deal
                                break
                        
                        # Get exit price and time
                        # Always set exit_condition to 'Opposite Strategy' when closing opposite positions
                        exit_condition = 'Opposite Strategy'
                        
                        if closed_deal:
                            exit_price = closed_deal.get('price', entry_price)
                            deal_time = closed_deal.get('time')
                            if isinstance(deal_time, datetime):
                                exit_time = deal_time
                            elif isinstance(deal_time, (int, float)):
                                exit_time = datetime.fromtimestamp(deal_time)
                            else:
                                exit_time = datetime.now()
                            profit = closed_deal.get('profit', 0.0)
                        else:
                            # Fallback: use current price
                            exit_price = entry_price
                            exit_time = datetime.now()
                            profit = 0.0
                        
                        # Get trade details for Telegram notification
                        trade = self.order_manager.trade_history.get_trade(opp_ticket)
                        entry_price_for_exit = opp_pos.get('entry_price')
                        entry_time_for_exit = opp_pos.get('entry_time', datetime.now())
                        entry_condition_for_exit = opp_pos.get('entry_condition', '--')
                        
                        if trade and not entry_price_for_exit:
                            entry_price_for_exit = trade.get('entry_price', entry_price)
                            entry_time_for_exit = trade.get('entry_time', datetime.now())
                            entry_condition_for_exit = trade.get('entry_condition', '--')
                        
                        # Update trade history with exit details
                        try:
                            self.order_manager.trade_history.close_trade(
                                ticket=opp_ticket,
                                exit_price=exit_price,
                                exit_time=exit_time,
                                exit_condition=exit_condition,
                                profit=profit
                            )
                            logger.info(f"Closed trade {opp_ticket} in history (opposite strategy): {exit_condition} at {exit_price}")
                        except Exception as e:
                            logger.error(f"Error closing trade {opp_ticket} in history: {e}", exc_info=True)
                        
                        # Send Telegram notification
                        if hasattr(self, 'telegram_bot') and self.telegram_bot and self.telegram_bot._initialized:
                            try:
                                self.telegram_bot.send_trade_exit(
                                    ticker=symbol,
                                    volume=opp_pos.get('volume', default_lot),
                                    strategy_name=opp_strategy_name,
                                    entry_price=entry_price_for_exit or entry_price,
                                    entry_time=entry_time_for_exit,
                                    entry_condition=entry_condition_for_exit,
                                    exit_price=exit_price,
                                    exit_time=exit_time,
                                    exit_condition=exit_condition,
                                    profit=profit,
                                    entry_type=opposite_direction,
                                    exit_type=("SELL" if opposite_direction == "BUY" else "BUY")
                                )
                                logger.info(f"Sent Telegram exit notification for trade {opp_ticket} (opposite strategy): {exit_condition}, P&L: {profit:.2f}")
                            except Exception as e:
                                logger.error(f"Error sending Telegram exit notification: {e}", exc_info=True)
                        
                        # Remove from position tracker
                        self.order_manager.position_tracker.remove_position(
                            opp_strategy_name, symbol, opposite_direction, opp_ticket
                        )
                        logger.info(f"Successfully closed {opposite_direction} position {opp_ticket} from {opp_strategy_name}")
                    else:
                        logger.warning(f"Failed to close {opposite_direction} position {opp_ticket} from {opp_strategy_name}")
        
        # Validate order
        validation = self.risk_manager.validate_order(symbol, default_lot, entry_price, sl)
        if not validation['valid']:
            logger.warning(f"Order validation failed for {strategy.name}: {validation['message']}")
            return
        
        logger.info(f"execute_strategy_signal: Placing {signal} order for {symbol}, lot={default_lot}, SL={sl}, TP={tp}")
        
        # Log diagnostic information before placing order
        logger.info(f"execute_strategy_signal: MT5 connected={self.mt5.is_connected()}, symbol={symbol}, strategy={strategy.name}")
        
        # Place order
        try:
            result = self.order_manager.place_market_order(
                symbol=symbol,
                order_type=signal,
                volume=default_lot,
                sl=sl,
                tp=tp,
                comment=f"Strategy: {strategy.name}"
            )
        except Exception as e:
            logger.error(f"execute_strategy_signal: Exception calling place_market_order for {strategy.name}: {e}", exc_info=True)
            result = None
        
        # Always set cooldown regardless of result to prevent spam
        strategy.last_trade_time = datetime.now()
        
        if result:
            # Check if order was actually successful
            retcode = result.get('retcode', 0)
            success = result.get('success', False)
            
            if success or retcode == 10009:  # TRADE_RETCODE_DONE
                logger.info(f"execute_strategy_signal: Order placed successfully! Strategy: {strategy.name}, Symbol: {symbol}, Result: {result}")
                
                # Record original entry for RE-COST mode
                self.reentry_manager.record_original_entry(strategy, entry_price, signal, symbol)
                
                # Register position for advanced risk management if enabled
                ticket = result.get('order')
                if ticket:
                    # Get the position from MT5
                    positions = self.mt5.get_positions(symbol)
                    position = None
                    for pos in positions:
                        if pos.get('ticket') == ticket:
                            position = pos
                            break
                    
                    if position:
                        # Check if strategy has advanced risk management enabled
                        config = {
                            'enable_trailing_sl': getattr(strategy, 'enable_trailing_sl', False),
                            'trailing_sl_gap': getattr(strategy, 'trailing_sl_gap', 0.0),
                            'enable_profit_lock': getattr(strategy, 'enable_profit_lock', False),
                            'profit_lock_trigger': getattr(strategy, 'profit_lock_trigger', 0.0),
                            'profit_lock_value': getattr(strategy, 'profit_lock_value', 0.0),
                            'profit_trail_step': getattr(strategy, 'profit_trail_step', 0.0),
                            'profit_trail_amount': getattr(strategy, 'profit_trail_amount', 0.0),
                            'enable_wt': getattr(strategy, 'enable_wt', False),
                            'wt_value': getattr(strategy, 'wt_value', 0.0),
                            'wt_is_percentage': getattr(strategy, 'wt_is_percentage', False),
                        }
                        
                        if config['enable_trailing_sl'] or config['enable_profit_lock'] or config['enable_wt']:
                            self.trade_monitor.register_position_for_advanced_risk(position, config)
                            logger.info(
                                "Registered position %s for advanced risk management: trailing_sl=%s, profit_lock=%s, wt=%s",
                                ticket,
                                config['enable_trailing_sl'],
                                config['enable_profit_lock'],
                                config['enable_wt'],
                            )
                        
                        # Track position for preservation and get entry condition
                        entry_condition_text = self._get_entry_condition_text(strategy, signal)
                        entry_time = datetime.now()
                        
                        # Add to position tracker
                        self.order_manager.position_tracker.add_position(
                            strategy.name, symbol, signal, ticket,
                            entry_price=entry_price,
                            entry_time=entry_time,
                            volume=default_lot,
                            entry_condition=entry_condition_text,
                            sl=sl,
                            tp=tp
                        )
                        
                        # Add to trade history
                        self.order_manager.trade_history.add_trade(
                            ticket=ticket,
                            strategy_name=strategy.name,
                            symbol=symbol,
                            entry_price=entry_price,
                            entry_time=entry_time,
                            entry_condition=entry_condition_text,
                            sl=sl,
                            tp=tp,
                            volume=default_lot,
                            direction=signal
                        )
                        
                        # Send Telegram notification
                        if hasattr(self, 'telegram_bot') and self.telegram_bot and self.telegram_bot._initialized:
                            self.telegram_bot.send_trade_entry(
                                ticker=symbol,
                                volume=default_lot,
                                strategy_name=strategy.name,
                                entry_price=entry_price,
                                entry_time=datetime.now(),
                                entry_condition=entry_condition_text,
                                entry_type=signal
                            )
                
                self.status_bar.showMessage(
                    f"Strategy {strategy.name} executed {signal} order for {symbol}",
                    5000
                )
            else:
                # Order failed - log error with details
                error_msg = result.get('error') or result.get('comment', 'Unknown error')
                logger.warning(f"execute_strategy_signal: Order placement failed for {strategy.name}. Retcode: {retcode}, Error: {error_msg}, Result: {result}")
                
                # Check if trading is disabled and show user-friendly message
                if 'Trading disabled' in error_msg or 'trade_mode=0' in error_msg or result.get('trade_mode') == 0:
                    QMessageBox.warning(
                        self,
                        "Trading Disabled",
                        f"Trading is disabled on your MT5 account.\n\n"
                        f"To enable trading:\n"
                        f"1. Open MT5 Terminal\n"
                        f"2. Go to Tools > Options > Expert Advisors\n"
                        f"3. Check 'Allow automated trading'\n"
                        f"4. Click OK and restart the application\n\n"
                        f"If the issue persists, contact your broker to enable trading permissions."
                    )
                    self.status_bar.showMessage(
                        f"Trading disabled on account - Enable in MT5: Tools > Options > Expert Advisors",
                        10000
                    )
                else:
                    # Truncate error message for status bar if too long
                    display_msg = error_msg[:100] + "..." if len(error_msg) > 100 else error_msg
                    self.status_bar.showMessage(
                        f"Strategy {strategy.name} order failed: {display_msg}",
                        5000
                    )
        else:
            # Result is None - this means order_manager returned None
            logger.error(f"execute_strategy_signal: Order placement returned None for {strategy.name}. Symbol: {symbol}, Signal: {signal}")
            logger.error(f"execute_strategy_signal: Diagnostics - MT5 connected={self.mt5.is_connected()}, symbol={symbol}")
            
            self.status_bar.showMessage(
                f"Strategy {strategy.name} order failed: No result from MT5 (check logs)",
                5000
            )
    
    def update_positions(self):
        """Update position displays and advanced risk management"""
        # Update advanced risk management for all registered positions
        if self.mt5.is_connected():
            try:
                # Get all open positions
                all_positions = self.mt5.get_positions()
                
                for position in all_positions:
                    ticket = position.get('ticket')
                    if not ticket:
                        continue
                    
                    # Check if position is registered for advanced risk management
                    if ticket in self.trade_monitor.active_trailing_sl or ticket in self.trade_monitor.active_profit_locks or ticket in getattr(self.trade_monitor, 'active_wt', {}):
                        symbol = position.get('symbol')
                        pos_type = position.get('type', 0)  # 0 = BUY, 1 = SELL
                        
                        # Get current price
                        tick = self.data_feed.get_latest_tick(symbol)
                        if not tick:
                            continue
                        
                        current_price = tick['ask'] if pos_type == 0 else tick['bid']
                        
                        # Calculate current profit
                        entry_price = position.get('price_open', 0.0)
                        volume = position.get('volume', 0.0)
                        current_profit = position.get('profit', 0.0)  # MT5 provides profit directly
                        
                        # Update advanced risk management
                        updates = self.trade_monitor.update_advanced_risk_management(
                            position, current_price, current_profit, self.order_manager
                        )
                        
                        # Check if position should be closed (trailing SL triggered)
                        if updates.get('should_close'):
                            reason = updates.get('reason', 'AdvancedRisk')
                            logger.info(f"Advanced risk trigger for position {ticket} (reason={reason}), closing position")
                            self.order_manager.close_position(ticket)
                            self.trade_monitor.unregister_position(ticket)
                            continue
                        
                        # Update SL if changed
                        if updates.get('new_sl') is not None:
                            new_sl = updates['new_sl']
                            current_tp = position.get('tp', 0.0)
                            if self.order_manager.modify_position(ticket, new_sl, current_tp):
                                logger.info(f"Updated trailing SL for position {ticket}: {new_sl:.5f}")
                        
                        # Update TP if changed
                        if updates.get('new_tp') is not None:
                            new_tp = updates['new_tp']
                            current_sl = position.get('sl', 0.0)
                            if self.order_manager.modify_position(ticket, current_sl, new_tp):
                                logger.info(f"Updated profit lock TP for position {ticket}: {new_tp:.5f}")
                
                # Clean up closed positions from tracking
                tracked_tickets = (
                    set(self.trade_monitor.active_trailing_sl.keys())
                    | set(self.trade_monitor.active_profit_locks.keys())
                    | set(getattr(self.trade_monitor, 'active_wt', {}).keys())
                )
                open_tickets = {pos.get('ticket') for pos in all_positions if pos.get('ticket')}
                closed_tickets = tracked_tickets - open_tickets
                for ticket in closed_tickets:
                    self.trade_monitor.unregister_position(ticket)
                    logger.debug(f"Unregistered closed position {ticket} from advanced risk management")
                
                # Check for manually closed positions (not closed by SL/TP in monitor_trades)
                # Get all tracked positions from position_tracker
                for strategy_name in list(self.order_manager.position_tracker.positions.keys()):
                    for symbol in list(self.order_manager.position_tracker.positions[strategy_name].keys()):
                        for direction, pos_data in list(self.order_manager.position_tracker.positions[strategy_name][symbol].items()):
                            tracked_ticket = pos_data.get('ticket')
                            # If tracked position is not in open positions, it was closed
                            if tracked_ticket and tracked_ticket not in open_tickets:
                                # Check if it was already handled by monitor_trades (SL/TP)
                                # If not, it was manually closed
                                self._handle_manual_close(tracked_ticket, strategy_name, symbol, direction, pos_data)
            except Exception as e:
                logger.error(f"Error updating advanced risk management: {e}", exc_info=True)
        
        # Update position displays (existing code)
        if self.mt5.is_connected():
            self.strategy_panel.update_positions()
        if self.mt5.is_connected():
            self.strategy_panel.update_positions()
    
    def monitor_trades(self):
        """Monitor open positions and check SL/TP based on monitoring mode"""
        if not self.mt5.is_connected():
            return
        
        # Get all open positions
        positions = self.order_manager.get_positions()
        if not positions:
            return
        
        # Group positions by strategy (based on comment)
        strategy_positions = {}
        other_positions = []
        
        for pos in positions:
            comment = pos.get('comment', '')
            if comment and 'Strategy:' in comment:
                strategy_name = comment.replace('Strategy:', '').strip()
                if strategy_name not in strategy_positions:
                    strategy_positions[strategy_name] = []
                strategy_positions[strategy_name].append(pos)
            else:
                other_positions.append(pos)
        
        # Monitor strategy positions with their specific monitoring mode
        for strategy_name, strategy_pos_list in strategy_positions.items():
            strategy = self.strategy_manager.get_strategy(strategy_name)
            if strategy:
                # Set monitoring mode for this strategy
                monitoring_mode = getattr(strategy, 'trade_monitoring_mode', 'LTP')
                if monitoring_mode == 'CANDLE_CLOSE':
                    self.trade_monitor.set_monitoring_mode(TradeMonitoringMode.CANDLE_CLOSE)
                else:
                    self.trade_monitor.set_monitoring_mode(TradeMonitoringMode.LTP)
                
                # Monitor positions for this strategy
                def get_price(symbol, pos_type):
                    tick = self.data_feed.get_latest_tick(symbol)
                    if not tick:
                        return None
                    return tick['ask'] if pos_type == 0 else tick['bid']
                
                positions_to_close = self.trade_monitor.monitor_positions(
                    strategy_pos_list, get_price
                )
                
                # Close positions that hit SL/TP and handle re-entry
                for pos_to_close in positions_to_close:
                    ticket = pos_to_close.get('ticket')
                    action = pos_to_close.get('action')  # 'SL' or 'TP'
                    trigger_price = pos_to_close.get('trigger_price')
                    
                    logger.info(f"Closing position {ticket} due to {action} at {trigger_price}")
                    
                    # Record closed position for RE-COST tracking
                    original_entry_price = getattr(strategy, 'original_entry_price', pos_to_close.get('price_open', 0))
                    original_entry_type = getattr(strategy, 'original_entry_type', 'BUY' if pos_to_close.get('type', 0) == 0 else 'SELL')
                    original_entry_symbol = pos_to_close.get('symbol', strategy.symbol)
                    self.reentry_manager.record_closed_position(
                        pos_to_close, original_entry_price, original_entry_type, original_entry_symbol
                    )
                    
                    # Try to close position
                    close_success = self.order_manager.close_position(ticket)
                    
                    # If close failed, check if MT5 already closed it (auto-close)
                    if not close_success:
                        # Check if position still exists
                        positions = self.mt5.get_positions(symbol=original_entry_symbol)
                        position_still_exists = any(p.get('ticket') == ticket for p in positions)
                        
                        if not position_still_exists:
                            # Position was already closed by MT5 (auto-close)
                            logger.info(f"Position {ticket} was already closed by MT5 (auto-close), fetching exit condition")
                            # Continue to process as closed
                        else:
                            # Position still exists, close failed for another reason
                            logger.error(f"Failed to close position {ticket}, position still exists")
                            continue
                    
                    # Remove from position tracker and get stored data
                    direction = 'BUY' if pos_to_close.get('type', 0) == 0 else 'SELL'
                    
                    # Get entry condition from position tracker before removing
                    tracked_pos = self.order_manager.position_tracker.get_positions_for_strategy(
                        strategy.name, original_entry_symbol
                    )
                    entry_condition_text = "--"
                    for tp in tracked_pos:
                        if tp.get('ticket') == ticket:
                            entry_condition_text = tp.get('entry_condition', '--')
                            break
                    
                    # If not found in tracker, try to get from strategy
                    if entry_condition_text == "--":
                        entry_condition_text = self._get_entry_condition_text(strategy, direction)
                    
                    # Update trade history - get exit condition from MT5 (with retry, passing action)
                    import time
                    exit_condition = self._get_exit_condition_from_mt5(ticket, action, action)
                    # If MT5 hasn't processed yet, wait and retry once
                    if exit_condition not in ["SL", "TP"] and action in ["SL", "TP"]:
                        time.sleep(0.5)  # Wait for MT5 to process
                        exit_condition = self._get_exit_condition_from_mt5(ticket, action, action)
                        
                        profit = pos_to_close.get('profit', 0.0)
                        try:
                            self.order_manager.trade_history.close_trade(
                                ticket=ticket,
                                exit_price=trigger_price,
                                exit_time=datetime.now(),
                                exit_condition=exit_condition,
                                profit=profit
                            )
                            logger.info(f"Closed trade {ticket} in history: {exit_condition} at {trigger_price}")
                        except Exception as e:
                            logger.error(f"Error closing trade {ticket} in history: {e}", exc_info=True)
                        
                        self.order_manager.position_tracker.remove_position(
                            strategy.name, original_entry_symbol, direction, ticket
                        )
                        
                        # Send Telegram notification
                        if hasattr(self, 'telegram_bot') and self.telegram_bot and self.telegram_bot._initialized:
                            try:
                                # Get profit from position data
                                trade_profit = pos_to_close.get('profit', 0.0)
                                self.telegram_bot.send_trade_exit(
                                    ticker=original_entry_symbol,
                                    volume=pos_to_close.get('volume', 0.01),
                                    strategy_name=strategy.name,
                                    entry_price=original_entry_price,
                                    entry_time=pos_to_close.get('time', datetime.now()),
                                    entry_condition=entry_condition_text,
                                    exit_price=trigger_price,
                                    exit_time=datetime.now(),
                                    exit_condition=exit_condition,
                                    profit=trade_profit,
                                    entry_type=direction,
                                    exit_type=("SELL" if direction == "BUY" else "BUY")
                                )
                                logger.info(f"Sent Telegram exit notification for trade {ticket}: {exit_condition}, P&L: {trade_profit:.2f}")
                            except Exception as e:
                                logger.error(f"Error sending Telegram exit notification: {e}", exc_info=True)
                        
                        # Log viewer updates automatically via log handler
                        
                        self.status_bar.showMessage(
                            f"Position {ticket} closed: {action} triggered",
                            5000
                        )
                        
                        # Check if re-entry is needed
                        self.handle_reentry(strategy, action, original_entry_symbol)
                
        # Check for RE-COST re-entry opportunities for all strategies (continuous monitoring)
        for strategy_name, strategy_pos_list in strategy_positions.items():
            strategy = self.strategy_manager.get_strategy(strategy_name)
            if strategy:
                self.check_reentry_cost(strategy)
        
        # Monitor other positions with default LTP mode
        if other_positions:
            self.trade_monitor.set_monitoring_mode(TradeMonitoringMode.LTP)
            
            def get_price(symbol, pos_type):
                tick = self.data_feed.get_latest_tick(symbol)
                if not tick:
                    return None
                return tick['ask'] if pos_type == 0 else tick['bid']
            
            positions_to_close = self.trade_monitor.monitor_positions(
                other_positions, get_price
            )
            
            for pos_to_close in positions_to_close:
                ticket = pos_to_close.get('ticket')
                action = pos_to_close.get('action')
                trigger_price = pos_to_close.get('trigger_price')
                
                logger.info(f"Closing position {ticket} due to {action} at {trigger_price}")
                
                # Try to close position
                close_success = self.order_manager.close_position(ticket)
                position_still_exists = True  # Default assumption
                
                # If close failed, check if MT5 already closed it (auto-close)
                if not close_success:
                    # Check if position still exists
                    positions = self.mt5.get_positions(symbol=pos_to_close.get('symbol'))
                    position_still_exists = any(p.get('ticket') == ticket for p in positions)
                    
                    if not position_still_exists:
                        # Position was already closed by MT5 (auto-close)
                        logger.info(f"Position {ticket} was already closed by MT5 (auto-close), fetching exit condition")
                        # Continue to process as closed
                    else:
                        # Position still exists, close failed for another reason
                        logger.error(f"Failed to close position {ticket}, position still exists")
                        continue
                
                if close_success or not position_still_exists:
                    # Update trade history for other positions (non-strategy)
                    if hasattr(self.order_manager, 'trade_history'):
                        trade = self.order_manager.trade_history.get_trade(ticket)
                        if trade:
                            try:
                                # Get exit condition from MT5 (with retry, passing action)
                                import time
                                exit_condition = self._get_exit_condition_from_mt5(ticket, action, action)
                                # If MT5 hasn't processed yet, wait and retry once
                                if exit_condition not in ["SL", "TP"] and action in ["SL", "TP"]:
                                    time.sleep(0.5)
                                    exit_condition = self._get_exit_condition_from_mt5(ticket, action, action)
                                
                                self.order_manager.trade_history.close_trade(
                                    ticket=ticket,
                                    exit_price=trigger_price,
                                    exit_time=datetime.now(),
                                    exit_condition=exit_condition,
                                    profit=pos_to_close.get('profit', 0.0)
                                )
                                logger.info(f"Closed trade {ticket} in history (other): {exit_condition}")
                                
                                # Log viewer updates automatically via log handler
                            except Exception as e:
                                logger.error(f"Error closing trade {ticket} in history: {e}", exc_info=True)
                        else:
                            logger.warning(f"Trade {ticket} not found in history when trying to close")
                    
                    self.status_bar.showMessage(
                        f"Position {ticket} closed: {action} triggered",
                        5000
                    )
    
    def handle_reentry(self, strategy, action: str, symbol: str):
        """
        Handle re-entry logic after SL/TP is hit
        
        Args:
            strategy: Strategy object
            action: 'SL' or 'TP'
            symbol: Trading symbol
        """
        # Get current price
        tick = self.data_feed.get_latest_tick(symbol)
        if not tick:
            logger.warning(f"Cannot handle re-entry for {strategy.name}: No tick data for {symbol}")
            return
        
        # Get re-entry signal based on mode
        current_price = tick['ask']  # Use ask for BUY, will adjust if needed
        reentry_signal = self.reentry_manager.get_reentry_signal(strategy, action, current_price)
        
        if not reentry_signal:
            # For RE-COST modes, we need to wait for price to reach entry price
            # This will be checked continuously in monitor_trades
            return
        
        # Check if we should re-enter immediately (RE-ASAP modes)
        should_reenter, mode = self.reentry_manager.should_reenter(strategy, action)
        if not should_reenter:
            return
        
        if mode in ["RE_ASAP", "RE_ASAP_REVERSE"]:
            # Immediate re-entry
            logger.info(f"Strategy {strategy.name}: Re-entering with {reentry_signal} signal (mode: {mode})")
            
            # Get entry price for re-entry
            entry_price = tick['ask'] if reentry_signal == 'BUY' else tick['bid']
            
            # Calculate SL/TP for re-entry (same as original)
            sl, tp = self.calculate_strategy_sl_tp(strategy, symbol, entry_price, reentry_signal)
            
            # Validate order
            default_lot = self.config.get('trading.default_lot_size', 0.01)
            validation = self.risk_manager.validate_order(symbol, default_lot, entry_price, sl)
            if not validation['valid']:
                logger.warning(f"Re-entry order validation failed for {strategy.name}: {validation['message']}")
                return
            
            # Place re-entry order
            result = self.order_manager.place_market_order(
                symbol=symbol,
                order_type=reentry_signal,
                volume=default_lot,
                sl=sl,
                tp=tp,
                comment=f"Strategy: {strategy.name} (Re-Entry {action})"
            )
            
            if result:
                # Increment re-entry count
                self.reentry_manager.increment_reentry_count(strategy, action)
                
                # Record new original entry for RE-COST mode
                self.reentry_manager.record_original_entry(strategy, entry_price, reentry_signal, symbol)
                
                # Update last trade time
                strategy.last_trade_time = datetime.now()
                
                logger.info(f"Strategy {strategy.name}: Re-entry order placed successfully")
                self.status_bar.showMessage(
                    f"Strategy {strategy.name} re-entered: {reentry_signal} @ {entry_price}",
                    5000
                )
            else:
                logger.error(f"Strategy {strategy.name}: Re-entry order placement failed")
    
    def check_reentry_cost(self, strategy):
        """
        Continuously check for RE-COST re-entry opportunities
        
        Args:
            strategy: Strategy object
        """
        # Check if strategy has RE-COST mode enabled
        sl_mode = getattr(strategy, 'reentry_on_sl_mode', None)
        tp_mode = getattr(strategy, 'reentry_on_tp_mode', None)
        
        if sl_mode not in ["RE_COST", "RE_COST_REVERSE"] and tp_mode not in ["RE_COST", "RE_COST_REVERSE"]:
            return  # No RE-COST mode enabled
        
        symbol = strategy.symbol
        tick = self.data_feed.get_latest_tick(symbol)
        if not tick:
            return
        
        current_price = tick['ask']  # Will be adjusted based on signal
        
        # Check SL RE-COST
        if sl_mode in ["RE_COST", "RE_COST_REVERSE"]:
            should_reenter, _ = self.reentry_manager.should_reenter(strategy, 'SL')
            if should_reenter:
                reentry_signal = self.reentry_manager.get_reentry_signal(strategy, 'SL', current_price)
                if reentry_signal:
                    # Price reached original entry, execute re-entry
                    self.execute_reentry(strategy, 'SL', symbol, reentry_signal, tick)
        
        # Check TP RE-COST
        if tp_mode in ["RE_COST", "RE_COST_REVERSE"]:
            should_reenter, _ = self.reentry_manager.should_reenter(strategy, 'TP')
            if should_reenter:
                reentry_signal = self.reentry_manager.get_reentry_signal(strategy, 'TP', current_price)
                if reentry_signal:
                    # Price reached original entry, execute re-entry
                    self.execute_reentry(strategy, 'TP', symbol, reentry_signal, tick)
    
    def execute_reentry(self, strategy, action: str, symbol: str, reentry_signal: str, tick: dict):
        """
        Execute a re-entry order
        
        Args:
            strategy: Strategy object
            action: 'SL' or 'TP'
            symbol: Trading symbol
            reentry_signal: 'BUY' or 'SELL'
            tick: Current tick data
        """
        # Get entry price for re-entry
        entry_price = tick['ask'] if reentry_signal == 'BUY' else tick['bid']
        
        # Calculate SL/TP for re-entry (same as original)
        sl, tp = self.calculate_strategy_sl_tp(strategy, symbol, entry_price, reentry_signal)
        
        # Validate order
        default_lot = self.config.get('trading.default_lot_size', 0.01)
        validation = self.risk_manager.validate_order(symbol, default_lot, entry_price, sl)
        if not validation['valid']:
            logger.warning(f"Re-entry order validation failed for {strategy.name}: {validation['message']}")
            return
        
        # Place re-entry order
        result = self.order_manager.place_market_order(
            symbol=symbol,
            order_type=reentry_signal,
            volume=default_lot,
            sl=sl,
            tp=tp,
            comment=f"Strategy: {strategy.name} (Re-Entry {action})"
        )
        
        if result:
            # Increment re-entry count
            self.reentry_manager.increment_reentry_count(strategy, action)
            
            # Record new original entry for RE-COST mode
            self.reentry_manager.record_original_entry(strategy, entry_price, reentry_signal, symbol)
            
            # Update last trade time
            strategy.last_trade_time = datetime.now()
            
            logger.info(f"Strategy {strategy.name}: Re-entry order placed successfully ({action})")
            self.status_bar.showMessage(
                f"Strategy {strategy.name} re-entered: {reentry_signal} @ {entry_price}",
                5000
            )
        else:
            logger.error(f"Strategy {strategy.name}: Re-entry order placement failed")
    
    def load_saved_strategies(self):
        """Load saved strategies from disk"""
        try:
            from ..strategy.strategy_persistence import StrategyPersistence
            persistence = StrategyPersistence()
            strategies = persistence.load_all_strategies()
            
            for strategy in strategies:
                # Set market data panel reference for OHLC strategies
                if hasattr(strategy, 'set_market_data_panel'):
                    strategy.set_market_data_panel(self.market_data_panel)
                
                # Set MT5 connector reference for VWAP strategies
                if hasattr(strategy, 'set_mt5_connector'):
                    strategy.set_mt5_connector(self.mt5)
                
                # Restore enabled state from saved file
                # Add strategy first
                self.strategy_manager.add_strategy(strategy)
                
                # Log enabled state
                logger.info(f"Strategy '{strategy.name}' loaded with enabled={strategy.enabled}")
                
                # Add symbol to data feed if not already there
                if strategy.symbol not in self.data_feed.symbols:
                    # Will be added when MT5 connects
                    pass
            
            if strategies:
                logger.info(f"Loaded {len(strategies)} saved strategies")
                # Update strategy panel to show loaded strategies
                if hasattr(self, 'strategy_panel'):
                    self.strategy_panel.update_strategies()
        except Exception as e:
            logger.error(f"Error loading saved strategies: {e}")
    
    def on_strategy_enabled(self, strategy_name: str, enabled: bool):
        """Handle strategy enable/disable"""
        if enabled:
            self.strategy_manager.enable_strategy(strategy_name)
        else:
            self.strategy_manager.disable_strategy(strategy_name)
        
        # Save strategy state to disk
        strategy = self.strategy_manager.get_strategy(strategy_name)
        if strategy:
            try:
                from ..strategy.strategy_persistence import StrategyPersistence
                persistence = StrategyPersistence()
                persistence.save_strategy(strategy)
            except Exception as e:
                logger.error(f"Error saving strategy state: {e}")
    
    def on_strategy_edit_requested(self, strategy_name: str):
        """Handle strategy edit request - load strategy into builder"""
        strategy = self.strategy_manager.get_strategy(strategy_name)
        if not strategy:
            logger.warning(f"Strategy '{strategy_name}' not found for editing")
            return
        
        # Load strategy into builder
        self.strategy_builder.load_strategy(strategy)
        
        # Switch to Strategy Builder tab
        for i in range(self.tab_widget.count()):
            if self.tab_widget.tabText(i) == "Strategy Builder":
                self.tab_widget.setCurrentIndex(i)
                break
    
    def on_strategy_edit_requested(self, strategy_name: str):
        """Handle strategy edit request - load strategy into builder"""
        strategy = self.strategy_manager.get_strategy(strategy_name)
        if not strategy:
            QMessageBox.warning(self, "Error", f"Strategy '{strategy_name}' not found")
            return
        
        # Load strategy into builder
        if hasattr(self.strategy_builder, 'load_strategy_for_editing'):
            self.strategy_builder.load_strategy_for_editing(strategy)
            # Switch to strategy builder tab
            for i in range(self.tab_widget.count()):
                if self.tab_widget.widget(i) == self.strategy_builder:
                    self.tab_widget.setCurrentIndex(i)
                    break
        else:
            QMessageBox.warning(self, "Not Implemented", "Strategy editing is not yet fully implemented")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About",
            "MetaTrader 5 GUI Trading Platform\n\n"
            "A professional trading platform with strategy automation."
        )
    
    def save_symbols_to_config(self):
        """Save current symbols to config for persistence"""
        try:
            symbols = list(self.data_feed.symbols)
            self.config.set('data_feed.symbols', symbols)
            self.config.save()
            logger.info(f"Saved {len(symbols)} symbols to config")
        except Exception as e:
            logger.error(f"Error saving symbols to config: {e}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop signal server
        self.stop_signal_server()
        
        # Auto-save trade book and system logs to timestamped CSVs
        try:
            project_root = Path(__file__).parent.parent.parent
            export_root = project_root / "exports"
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = export_root / ts
            export_dir.mkdir(parents=True, exist_ok=True)

            # Trade book
            if hasattr(self, "strategy_panel") and hasattr(self.strategy_panel, "trade_book_panel"):
                trade_path = export_dir / f"trade_book_{ts}.csv"
                rows = self.strategy_panel.trade_book_panel.export_to_csv_path(trade_path)
                logger.info(f"Auto-saved trade book ({rows} rows) to {trade_path}")

            # System logs
            if hasattr(self, "strategy_panel") and hasattr(self.strategy_panel, "system_logs_panel"):
                log_path = export_dir / f"system_logs_{ts}.csv"
                rows = self.strategy_panel.system_logs_panel.export_csv_to_path(log_path, use_filtered=False)
                logger.info(f"Auto-saved system logs ({rows} rows) to {log_path}")
        except Exception as e:
            logger.error(f"Error auto-saving trade book/system logs on close: {e}", exc_info=True)

        # Save all strategies before closing
        try:
            from ..strategy.strategy_persistence import StrategyPersistence
            persistence = StrategyPersistence()
            for strategy in self.strategy_manager.get_all_strategies():
                persistence.save_strategy(strategy)
            logger.info("Saved all strategies before closing")
        except Exception as e:
            logger.error(f"Error saving strategies on close: {e}")
        
        # Save symbols to config
        self.save_symbols_to_config()
        
        # Disconnect from MT5
        self.disconnect_from_mt5()
        
        event.accept()
        
        self.data_feed.stop()
        self.mt5.shutdown()
        event.accept()
    
    def _on_tick_for_indicators(self, symbol: str, tick_data: dict):
        """Handle tick received - update indicators in real-time"""
        # Update indicators for this symbol
        self.indicator_feed.update_indicators(symbol)
    
    def _on_indicators_updated(self, symbol: str, indicators: dict):
        """Handle indicators updated signal"""
        # This can be used to update GUI components with real-time indicator values
        logger.debug(f"Real-time indicators updated for {symbol}: {indicators}")
    
    def _on_tick_for_symbol_update(self, symbol: str, tick_data: dict):
        """Handle tick received - update symbol lists in trade panel"""
        # Update trade panel symbol list when new symbols are added
        # Symbols are automatically available in data feed for other panels
    
    def calculate_strategy_sl_tp(self, strategy, symbol: str, entry_price: float, signal: str) -> tuple:
        """
        Calculate SL and TP based on strategy configuration
        
        Returns:
            Tuple of (sl_price, tp_price)
        """
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
    
    def _initialize_telegram_bot(self):
        """Initialize Telegram bot if enabled in config"""
        if self.config.get('telegram.enabled', False):
            bot_token = self.config.get('telegram.bot_token', '')
            channel_id = self.config.get('telegram.channel_id', '')
            channel_name = self.config.get('telegram.channel_name', 'TradingBot_Alerts')
            if bot_token:
                try:
                    from ..notifications.telegram_bot import TelegramBot
                    self.telegram_bot = TelegramBot(bot_token, channel_id, channel_name)
                    if self.telegram_bot._initialized:
                        logger.info("Telegram bot initialized successfully")
                    else:
                        logger.warning("Telegram bot initialization failed")
                except Exception as e:
                    logger.error(f"Error initializing Telegram bot: {e}")
                    self.telegram_bot = None
        else:
            self.telegram_bot = None
    
    def update_telegram_status(self):
        """Update Telegram bot status indicator in status bar"""
        if hasattr(self, 'telegram_status_label'):
            if self.telegram_bot and self.telegram_bot._initialized:
                self.telegram_status_label.setText("Telegram: ✅ Active")
                self.telegram_status_label.setStyleSheet("padding: 2px 8px; border-radius: 3px; background-color: #4CAF50; color: white;")
                if hasattr(self, 'telegram_test_btn'):
                    self.telegram_test_btn.setEnabled(True)
            elif self.config.get('telegram.enabled', False):
                self.telegram_status_label.setText("Telegram: ❌ Failed")
                self.telegram_status_label.setStyleSheet("padding: 2px 8px; border-radius: 3px; background-color: #F44336; color: white;")
                if hasattr(self, 'telegram_test_btn'):
                    self.telegram_test_btn.setEnabled(False)
            else:
                self.telegram_status_label.setText("Telegram: Not Configured")
                self.telegram_status_label.setStyleSheet("padding: 2px 8px; border-radius: 3px; background-color: #666; color: white;")
                if hasattr(self, 'telegram_test_btn'):
                    self.telegram_test_btn.setEnabled(False)
    
    def test_telegram_message(self):
        """Send a test message to Telegram channel"""
        if not self.telegram_bot or not self.telegram_bot._initialized:
            QMessageBox.warning(self, "Telegram Bot", "Telegram bot is not active. Please configure it in Settings.")
            return
        
        test_message = (
            f"<b>🧪 TEST MESSAGE</b>\n\n"
            f"This is a test message from the Trading Platform.\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Status: Telegram bot is working correctly! ✅"
        )
        
        success = self.telegram_bot.send_message(test_message)
        
        if success:
            QMessageBox.information(self, "Success", "Test message sent successfully to Telegram channel!")
            self.status_bar.showMessage("Test message sent to Telegram", 3000)
        else:
            QMessageBox.warning(self, "Error", "Failed to send test message. Check your Telegram bot configuration.")
            self.status_bar.showMessage("Failed to send test message", 3000)
    
    def _handle_manual_close(self, ticket: int, strategy_name: str, symbol: str, direction: str, pos_data: dict):
        """Handle manually closed position and send Telegram notification"""
        logger.info(f"Starting manual close handling for ticket {ticket}, strategy: {strategy_name}, symbol: {symbol}, direction: {direction}")
        
        # Initialize entry_price early to avoid UnboundLocalError
        entry_price = 0.0
        
        try:
            # Get strategy
            strategy = self.strategy_manager.get_strategy(strategy_name)
            if not strategy:
                logger.warning(f"Strategy {strategy_name} not found for manual close of ticket {ticket}")
                # Continue anyway - we can still update trade history
            
            # Get closed position details from MT5 deal history
            # MT5: entry == 0 (DEAL_ENTRY_IN) = Entry deal, entry == 1 (DEAL_ENTRY_OUT) = Exit deal
            closed_deal = None
            exit_price = pos_data.get('entry_price', 0.0)  # Fallback
            exit_time = datetime.now()
            
            # Try to get exit deal with retry (MT5 may need time to process)
            import time
            for retry in range(3):  # Try up to 3 times
                deals = self.mt5.get_deal_history(date_from=None, date_to=None, symbol=symbol)
                for deal in deals:
                    # Match by position_id (most reliable) or ticket
                    if (deal.get('position_id') == ticket or deal.get('order') == ticket):
                        if deal.get('type') in [2, 3]:  # DEAL_TYPE_BALANCE or DEAL_TYPE_CREDIT
                            continue
                        # Look for exit deal (entry == 1 means DEAL_ENTRY_OUT = exit)
                        if deal.get('entry') == 1:  # Exit deal
                            closed_deal = deal
                            break
                
                if closed_deal:
                    break
                
                # Wait a bit before retry (MT5 needs time to process the close)
                if retry < 2:
                    time.sleep(0.5)
            
            if closed_deal:
                exit_price = closed_deal.get('price', exit_price)
                deal_time = closed_deal.get('time')
                if isinstance(deal_time, datetime):
                    exit_time = deal_time
                elif isinstance(deal_time, (int, float)):
                    exit_time = datetime.fromtimestamp(deal_time)
                else:
                    exit_time = datetime.now()
                
                logger.info(f"Found exit deal for ticket {ticket}: exit_price={exit_price}, exit_time={exit_time}")
            else:
                logger.warning(f"Could not find exit deal for ticket {ticket} after retries. Using fallback: exit_price={exit_price}")
            
            # Get entry_price from pos_data or trade history FIRST (needed for SL/TP detection)
            entry_price = pos_data.get('entry_price')
            if not entry_price:
                trade = self.order_manager.trade_history.get_trade(ticket)
                if trade:
                    entry_price = trade.get('entry_price', 0.0)
                else:
                    # Try to get from closed_deal (entry deal)
                    if closed_deal:
                        # Find entry deal for this position
                        for deal in deals:
                            if (deal.get('position_id') == ticket or deal.get('order') == ticket) and deal.get('entry') == 0:  # Entry deal
                                entry_price = deal.get('price', 0.0)
                                break
                    if not entry_price:
                        entry_price = 0.0  # Fallback
            
            # Get exit condition - default to "Manual" for user-initiated closes
            # Only override with "SL" or "TP" if detected via price comparison
            exit_condition = "Manual"
            
            # Try to determine if exit was SL/TP based on price comparison
            if True:  # Always check for SL/TP detection
                # Get SL and TP from position data or trade history
                sl = pos_data.get('sl', 0.0)
                tp = pos_data.get('tp', 0.0)
                
                # If not in pos_data, try to get from trade history
                if sl == 0.0 or tp == 0.0:
                    trade = self.order_manager.trade_history.get_trade(ticket)
                    if trade:
                        sl = trade.get('sl', 0.0) if sl == 0.0 else sl
                        tp = trade.get('tp', 0.0) if tp == 0.0 else tp
                
                # If we have SL/TP and exit price, determine exit condition
                if (sl > 0 or tp > 0) and entry_price > 0:
                        # Determine if exit was SL or TP based on price comparison
                        # For BUY: SL is below entry, TP is above entry
                        # For SELL: SL is above entry, TP is below entry
                        if direction == 'BUY':
                            # BUY position: exit below entry = likely SL, exit above entry = likely TP
                            if sl > 0 and abs(exit_price - sl) < abs(exit_price - entry_price) * 0.01:  # Within 1% of SL
                                exit_condition = "SL"
                                logger.info(f"Detected SL exit for position {ticket}: exit_price={exit_price}, sl={sl}, entry={entry_price}")
                            elif tp > 0 and abs(exit_price - tp) < abs(exit_price - entry_price) * 0.01:  # Within 1% of TP
                                exit_condition = "TP"
                                logger.info(f"Detected TP exit for position {ticket}: exit_price={exit_price}, tp={tp}, entry={entry_price}")
                            elif exit_price <= sl and sl > 0:
                                exit_condition = "SL"
                                logger.info(f"Detected SL exit for position {ticket}: exit_price={exit_price} <= sl={sl}")
                            elif exit_price >= tp and tp > 0:
                                exit_condition = "TP"
                                logger.info(f"Detected TP exit for position {ticket}: exit_price={exit_price} >= tp={tp}")
                        else:  # SELL
                            # SELL position: exit above entry = likely SL, exit below entry = likely TP
                            if sl > 0 and abs(exit_price - sl) < abs(exit_price - entry_price) * 0.01:  # Within 1% of SL
                                exit_condition = "SL"
                                logger.info(f"Detected SL exit for position {ticket}: exit_price={exit_price}, sl={sl}, entry={entry_price}")
                            elif tp > 0 and abs(exit_price - tp) < abs(exit_price - entry_price) * 0.01:  # Within 1% of TP
                                exit_condition = "TP"
                                logger.info(f"Detected TP exit for position {ticket}: exit_price={exit_price}, tp={tp}, entry={entry_price}")
                            elif exit_price >= sl and sl > 0:
                                exit_condition = "SL"
                                logger.info(f"Detected SL exit for position {ticket}: exit_price={exit_price} >= sl={sl}")
                            elif exit_price <= tp and tp > 0:
                                exit_condition = "TP"
                                logger.info(f"Detected TP exit for position {ticket}: exit_price={exit_price} <= tp={tp}")
            
            # Get entry condition
            entry_condition = pos_data.get('entry_condition', '--')
            if entry_condition == '--' and strategy:
                entry_condition = self._get_entry_condition_text(strategy, direction)
            
            # Check if trade exists in history before closing
            trade = self.order_manager.trade_history.get_trade(ticket)
            if not trade:
                logger.warning(f"Trade {ticket} not found in history. Attempting to add from MT5 data before closing.")
                # Try to reconstruct trade from pos_data and MT5 deal history
                entry_time = pos_data.get('entry_time', datetime.now())
                if isinstance(entry_time, (int, float)):
                    entry_time = datetime.fromtimestamp(entry_time)
                elif not isinstance(entry_time, datetime):
                    entry_time = datetime.now()
                
                # Get entry deal from MT5 if available
                if not entry_price or entry_price == 0.0:
                    deals = self.mt5.get_deal_history(date_from=None, date_to=None, symbol=symbol) if self.mt5.is_connected() else []
                    for deal in deals:
                        if (deal.get('position_id') == ticket or deal.get('order') == ticket) and deal.get('entry') == 0:  # Entry deal
                            entry_price = deal.get('price', 0.0)
                            deal_time = deal.get('time')
                            if isinstance(deal_time, datetime):
                                entry_time = deal_time
                            elif isinstance(deal_time, (int, float)):
                                entry_time = datetime.fromtimestamp(deal_time)
                            break
                
                # Add trade to history if we have minimum required data
                if entry_price > 0:
                    try:
                        self.order_manager.trade_history.add_trade(
                            ticket=ticket,
                            strategy_name=strategy_name,
                            symbol=symbol,
                            entry_price=entry_price,
                            entry_time=entry_time,
                            entry_condition=entry_condition,
                            sl=pos_data.get('sl', 0.0),
                            tp=pos_data.get('tp', 0.0),
                            volume=pos_data.get('volume', 0.01),
                            direction=direction
                        )
                        logger.info(f"Added missing trade {ticket} to history before closing")
                        trade = self.order_manager.trade_history.get_trade(ticket)
                    except Exception as e:
                        logger.error(f"Error adding trade {ticket} to history: {e}", exc_info=True)
                else:
                    logger.error(f"Cannot add trade {ticket} to history: missing entry_price")
            
            # Validate exit_price and exit_time before updating
            if exit_price <= 0:
                logger.warning(f"Invalid exit_price {exit_price} for ticket {ticket}, using entry_price as fallback")
                exit_price = entry_price if entry_price > 0 else pos_data.get('entry_price', 0.0)
            
            if not isinstance(exit_time, datetime):
                logger.warning(f"Invalid exit_time for ticket {ticket}, using current time")
                exit_time = datetime.now()
            
            # Update trade history with exit details
            profit = closed_deal.get('profit', 0.0) if closed_deal else 0.0
            try:
                if trade:
                    # Trade exists, close it
                    self.order_manager.trade_history.close_trade(
                        ticket=ticket,
                        exit_price=exit_price,
                        exit_time=exit_time,
                        exit_condition=exit_condition,
                        profit=profit
                    )
                    # Also update exit_reason field (for backward compatibility)
                    trade['exit_reason'] = exit_condition
                    logger.info(f"Successfully closed trade {ticket} in history: {exit_condition}, Exit Price: {exit_price}, Exit Time: {exit_time}")
                else:
                    logger.error(f"Cannot close trade {ticket}: trade not found in history and could not be added")
                    raise ValueError(f"Trade {ticket} not in history and could not be added")
            except Exception as e:
                logger.error(f"CRITICAL: Error closing trade {ticket} in history: {e}", exc_info=True)
                raise  # Re-raise to prevent silent failure
            
            # Remove from position tracker
            self.order_manager.position_tracker.remove_position(strategy_name, symbol, direction, ticket)
            
            # Send Telegram notification with retry logic
            telegram_sent = False
            if hasattr(self, 'telegram_bot') and self.telegram_bot:
                if not self.telegram_bot._initialized:
                    logger.warning(f"Telegram bot not initialized, skipping notification for trade {ticket}")
                else:
                    # Get profit from closed_deal or trade history
                    trade_profit = profit if profit else 0.0
                    if not trade_profit and closed_deal:
                        trade_profit = closed_deal.get('profit', 0.0)
                    
                    # Retry sending notification up to 2 times
                    for retry in range(2):
                        try:
                            entry_time_for_notification = pos_data.get('entry_time', datetime.now())
                            if isinstance(entry_time_for_notification, (int, float)):
                                entry_time_for_notification = datetime.fromtimestamp(entry_time_for_notification)
                            elif not isinstance(entry_time_for_notification, datetime):
                                entry_time_for_notification = datetime.now()
                            
                            self.telegram_bot.send_trade_exit(
                                ticker=symbol,
                                volume=pos_data.get('volume', 0.01),
                                strategy_name=strategy_name,
                                entry_price=entry_price,
                                entry_time=entry_time_for_notification,
                                entry_condition=entry_condition,
                                exit_price=exit_price,
                                exit_time=exit_time,
                                exit_condition=exit_condition,
                                profit=trade_profit,
                                entry_type=direction,
                                exit_type=("SELL" if direction == "BUY" else "BUY")
                            )
                            logger.info(f"Successfully sent Telegram exit notification for trade {ticket} (manual): {exit_condition}, P&L: {trade_profit:.2f}")
                            telegram_sent = True
                            break
                        except Exception as e:
                            logger.error(f"Error sending Telegram exit notification (attempt {retry + 1}/2): {e}", exc_info=True)
                            if retry < 1:
                                import time
                                time.sleep(0.5)  # Wait before retry
                    if not telegram_sent:
                        logger.error(f"Failed to send Telegram notification for trade {ticket} after 2 attempts")
            else:
                logger.warning(f"Telegram bot not available, skipping notification for trade {ticket}")
            
            # Update trade book panel if it exists (with retry on failure)
            if hasattr(self, 'strategy_panel') and hasattr(self.strategy_panel, 'trade_book_panel'):
                try:
                    self.strategy_panel.trade_book_panel.update_trade_book()
                    logger.info(f"Updated trade book panel after manual close of ticket {ticket}")
                except Exception as e:
                    logger.error(f"Error updating trade book panel: {e}", exc_info=True)
                    # Try to refresh again after a short delay
                    try:
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(500, lambda: self.strategy_panel.trade_book_panel.update_trade_book())
                        logger.info(f"Scheduled retry update for trade book panel after manual close of ticket {ticket}")
                    except Exception as retry_error:
                        logger.error(f"Error scheduling trade book panel retry: {retry_error}", exc_info=True)
            
            # Log viewer updates automatically via log handler
            
            logger.info(f"Successfully handled manual close for position {ticket}: {strategy_name} - {symbol} - {direction} - Exit Condition: {exit_condition}, Exit Price: {exit_price}, Telegram: {'Sent' if telegram_sent else 'Failed/Skipped'}")
        except Exception as e:
            logger.error(f"CRITICAL: Error handling manual close for position {ticket}: {e}", exc_info=True)
            # Try to at least update the trade book panel even if other operations failed
            try:
                if hasattr(self, 'strategy_panel') and hasattr(self.strategy_panel, 'trade_book_panel'):
                    self.strategy_panel.trade_book_panel.update_trade_book()
            except:
                pass
    
    def _get_exit_condition_from_mt5(self, ticket: int, fallback: str = "Manual", action: str = None) -> str:
        """
        Get exit condition directly from MT5 deal history
        
        Args:
            ticket: Position ticket
            fallback: Fallback value if not found in MT5
            action: Known action ("SL" or "TP") from monitoring - if provided, prioritize this
            
        Returns:
            Exit condition string from MT5 (SL/TP/Manual/etc)
        """
        try:
            if not self.mt5.is_connected():
                # If we know the action (SL/TP), use it even if MT5 is not connected
                if action in ["SL", "TP"]:
                    return action
                return fallback
            
            # Get deal history for this position (recent deals only - last 1 hour)
            from datetime import timedelta
            date_from = datetime.now() - timedelta(hours=1)
            deals = self.mt5.get_deal_history(date_from=date_from)
            
            # Find the most recent exit deal for this position
            exit_deal = None
            exit_deal_time = None
            
            for deal in deals:
                # Find exit deal for this position
                # DEAL_ENTRY_IN = 0, DEAL_ENTRY_OUT = 1
                deal_position_id = deal.get('position_id', 0)
                deal_order = deal.get('order', 0)
                deal_entry = deal.get('entry', 0)
                deal_time = deal.get('time')
                
                # Match by position_id or order ticket, and must be exit deal
                if deal_entry == 1:  # DEAL_ENTRY_OUT
                    if deal_position_id == ticket or deal_order == ticket:
                        # Convert deal_time to datetime if needed
                        if isinstance(deal_time, (int, float)):
                            deal_datetime = datetime.fromtimestamp(deal_time)
                        elif isinstance(deal_time, datetime):
                            deal_datetime = deal_time
                        else:
                            continue
                        
                        # Keep the most recent exit deal
                        if exit_deal is None or (exit_deal_time and deal_datetime > exit_deal_time):
                            exit_deal = deal
                            exit_deal_time = deal_datetime
            
            if exit_deal:
                exit_condition = exit_deal.get('exit_condition', fallback)
                
                # If action is provided (SL/TP) and MT5 says something else (like "Expert"),
                # prioritize the action since we detected it from monitoring
                if action in ["SL", "TP"]:
                    # If MT5 confirms SL/TP, use it
                    if exit_condition in ["SL", "TP"]:
                        logger.debug(f"Found exit condition from MT5 for ticket {ticket}: {exit_condition} (confirmed by action)")
                        return exit_condition
                    # If MT5 says something else but we know it's SL/TP, use action
                    logger.debug(f"MT5 says {exit_condition} for ticket {ticket}, but monitoring detected {action}, using {action}")
                    return action
                
                if exit_condition and exit_condition != fallback:
                    logger.debug(f"Found exit condition from MT5 for ticket {ticket}: {exit_condition}")
                    return exit_condition
            
            # If not found in MT5 but we know the action, use it
            if action in ["SL", "TP"]:
                logger.debug(f"Exit condition not found in MT5 for ticket {ticket}, but monitoring detected {action}, using {action}")
                return action
            
            # If not found, return fallback
            logger.debug(f"Exit condition not found in MT5 for ticket {ticket}, using fallback: {fallback}")
            return fallback
        except Exception as e:
            logger.error(f"Error getting exit condition from MT5 for ticket {ticket}: {e}", exc_info=True)
            # If we know the action, use it even on error
            if action in ["SL", "TP"]:
                return action
            return fallback
    
    def _check_mt5_position_exists(self, strategy_name: str, symbol: str, direction: str) -> Tuple[bool, Optional[Dict]]:
        """
        Check if a position exists in MT5 for the given strategy, symbol, and direction.
        This is a backup check to ensure position tracker is in sync with MT5.
        
        Args:
            strategy_name: Name of the strategy
            symbol: Trading symbol
            direction: "BUY" or "SELL"
            
        Returns:
            Tuple of (exists: bool, position_dict: Optional[Dict])
            If position exists, returns (True, position_dict), else (False, None)
        """
        if not self.mt5.is_connected():
            return (False, None)
        
        try:
            # Get all positions for the symbol
            positions = self.order_manager.get_positions(symbol=symbol)
            
            # Convert direction to MT5 type (0 = BUY, 1 = SELL)
            mt5_type = 0 if direction == 'BUY' else 1
            
            # Look for position matching strategy name and direction
            expected_comment = f"Strategy: {strategy_name}"
            
            for pos in positions:
                comment = pos.get('comment', '')
                pos_type = pos.get('type', -1)
                
                # Check if comment matches strategy and type matches direction
                if comment == expected_comment and pos_type == mt5_type:
                    return (True, pos)
            
            return (False, None)
        except Exception as e:
            logger.error(f"Error checking MT5 position for {strategy_name} {symbol} {direction}: {e}", exc_info=True)
            return (False, None)
    
    def _determine_exit_reason(self, direction: str, entry_price: float, exit_price: float, sl: float, tp: float) -> str:
        """Determine exit reason based on prices (DEPRECATED - use _get_exit_condition_from_mt5)"""
        if direction == 'BUY':
            if sl > 0 and exit_price <= sl:
                return "SL"
            elif tp > 0 and exit_price >= tp:
                return "TP"
        else:  # SELL
            if sl > 0 and exit_price >= sl:
                return "SL"
            elif tp > 0 and exit_price <= tp:
                return "TP"
        return "Manual"

