"""
Market Data Panel
Displays live market data and account information
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QLabel, QPushButton, QLineEdit,
                             QHeaderView, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from typing import Dict, Optional, List

from ..data_feed import DataFeed
from ..mt5_connector import MT5Connector
from .custom_indicator_panel import PreviousSessionOHLCCalculator
from ..indicators.session_first_candle import SessionFirstCandle
from datetime import datetime
import MetaTrader5 as mt5_lib
import logging

logger = logging.getLogger(__name__)


class MarketDataPanel(QWidget):
    """Market data display panel"""
    
    def __init__(self, data_feed: DataFeed, mt5: MT5Connector):
        super().__init__()
        self.data_feed = data_feed
        self.mt5 = mt5
        self.ohlc_data = {}  # Store OHLC data: symbol -> {'open': float, 'high': float, 'low': float, 'close': float}
        self.ohlc_calculator = PreviousSessionOHLCCalculator(session_type='daily')
        self.session_type = 'daily'
        
        # Session First Candle calculators per symbol
        # We'll create them on-demand, but store the session config
        self.session_first_candle_config = {
            'session1_start_hour': 0,
            'session1_end_hour': 9,
            'session2_start_hour': 8,
            'session2_end_hour': 17,
            'session3_start_hour': 13,
            'session3_end_hour': 22
        }
        self.session_data = {}  # symbol -> {'high': float, 'low': float}
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_connections(self):
        """Setup signal connections for automatic OHLC loading"""
        # Connect to tick_received signal to fetch OHLC when new symbols get ticks
        if hasattr(self.data_feed, 'tick_received'):
            self.data_feed.tick_received.connect(self._on_tick_received)
    
    def _on_tick_received(self, symbol: str, tick_data: dict):
        """Handle tick received - fetch OHLC if not already loaded for this symbol"""
        # Only fetch OHLC if we haven't loaded it yet for this symbol
        if symbol not in self.ohlc_data and self.mt5.is_connected():
            self.fetch_ohlc_for_symbols([symbol])
    
    def setup_ui(self):
        """Setup the UI"""
        # Apply dark theme styling
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit, QComboBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #2196F3;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #2b2b2b;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2b2b;
                color: #ffffff;
                selection-background-color: #2196F3;
                border: 1px solid #444;
            }
            QPushButton {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #555;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #444;
                border: 1px solid #444;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #2196F3;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #444;
                font-weight: bold;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Account info section
        account_label = QLabel("Account Information")
        account_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        layout.addWidget(account_label)
        
        self.account_info_layout = QHBoxLayout()
        self.balance_label = QLabel("Balance: --")
        self.equity_label = QLabel("Equity: --")
        self.margin_label = QLabel("Margin: --")
        self.free_margin_label = QLabel("Free Margin: --")
        
        self.account_info_layout.addWidget(self.balance_label)
        self.account_info_layout.addWidget(self.equity_label)
        self.account_info_layout.addWidget(self.margin_label)
        self.account_info_layout.addWidget(self.free_margin_label)
        self.account_info_layout.addStretch()
        
        layout.addLayout(self.account_info_layout)
        
        # Symbol management
        symbol_layout = QHBoxLayout()
        symbol_label = QLabel("Add Symbol:")
        
        # Symbol combo box with available symbols
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.setPlaceholderText("Select or type symbol")
        self.symbol_combo.lineEdit().setPlaceholderText("e.g., EURUSD")
        
        # Manual input (alternative)
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Or type symbol name")
        
        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_symbol)
        
        browse_button = QPushButton("Browse Symbols")
        browse_button.clicked.connect(self.show_available_symbols)
        
        symbol_layout.addWidget(symbol_label)
        symbol_layout.addWidget(self.symbol_combo)
        symbol_layout.addWidget(self.symbol_input)
        symbol_layout.addWidget(add_button)
        symbol_layout.addWidget(browse_button)
        symbol_layout.addStretch()
        
        layout.addLayout(symbol_layout)
        
        # Load available symbols
        self.load_available_symbols()
        
        # Market data table
        table_label = QLabel("Live Market Data")
        table_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        layout.addWidget(table_label)
        
        self.data_table = QTableWidget()
        self._setup_table_columns()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.data_table.setAlternatingRowColors(True)
        # Context menu removed since SMC settings are removed
        # Can be re-enabled if needed: self.data_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        layout.addWidget(self.data_table)
        
        # Session type selector and refresh button
        session_layout = QHBoxLayout()
        session_label = QLabel("Session Type:")
        self.session_combo = QComboBox()
        self.session_combo.addItems(["Daily", "Asian Session", "European Session", "US Session"])
        self.session_combo.setCurrentText("Daily")
        self.session_combo.currentTextChanged.connect(self.on_session_changed)
        session_layout.addWidget(session_label)
        session_layout.addWidget(self.session_combo)
        
        # Refresh button (more prominent)
        refresh_button = QPushButton("🔄 Refresh OHLC Data")
        refresh_button.setStyleSheet("""
            font-weight: bold; 
            padding: 5px;
            background-color: #2196F3;
            color: #ffffff;
            border: none;
        """)
        refresh_button.clicked.connect(self.refresh_data)
        session_layout.addWidget(refresh_button)
        session_layout.addStretch()
        layout.addLayout(session_layout)
    
    def _setup_table_columns(self):
        """Setup table columns - always 12 columns with Session First Candle High/Low"""
        self.data_table.setColumnCount(12)
        self.data_table.setHorizontalHeaderLabels([
            "Symbol", "Bid", "Ask", "Spread", "Last", "Time", 
            "Prev Open", "Prev High", "Prev Low", "Prev Close",
            "High", "Low"
        ])
    
    def _show_table_context_menu(self, position):
        """Show context menu for table (empty for now, can add other actions later)"""
        # Context menu disabled since we removed SMC settings
        # Can be re-enabled if we add other context menu actions later
        pass
    
    def load_available_symbols(self):
        """Load available symbols from MT5"""
        if not self.mt5.is_connected():
            return
        
        try:
            symbols = self.mt5.get_available_symbols()
            self.symbol_combo.clear()
            self.symbol_combo.addItems(symbols)
            
            # Set common symbols at top
            common_symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
            for common in common_symbols:
                if common in symbols:
                    index = self.symbol_combo.findText(common)
                    if index >= 0:
                        self.symbol_combo.removeItem(index)
                        self.symbol_combo.insertItem(0, common)
        except Exception as e:
            logger.error(f"Error loading symbols: {e}")
    
    def add_symbol(self):
        """Add a symbol to monitor"""
        # Try combo box first, then input field
        symbol = self.symbol_combo.currentText().strip()
        if not symbol:
            symbol = self.symbol_input.text().strip()
        
        if not symbol:
            QMessageBox.warning(self, "Error", "Please enter or select a symbol")
            return
        
        # Store original input for error message
        original_symbol = symbol
        
        if self.data_feed.add_symbol(symbol):
            # Get the correct symbol name (with proper case) from data feed
            # Find the symbol in the data feed (case-insensitive)
            symbol_upper = original_symbol.upper()
            correct_symbol = None
            for feed_symbol in self.data_feed.symbols:
                if feed_symbol.upper() == symbol_upper:
                    correct_symbol = feed_symbol
                    break
            
            self.symbol_input.clear()
            self.symbol_combo.setCurrentText("")
            
            # Show success message with correct symbol name if different
            if correct_symbol and correct_symbol != original_symbol:
                QMessageBox.information(
                    self,
                    "Symbol Added",
                    f"Symbol added successfully!\n\n"
                    f"Note: The symbol '{original_symbol}' was found as '{correct_symbol}' "
                    f"(case-insensitive match)."
                )
            
            # Save symbols to config for persistence
            self._save_symbols_to_config()
            
            # Fetch OHLC immediately when symbol is added
            if correct_symbol and self.mt5.is_connected():
                self.fetch_ohlc_for_symbols([correct_symbol])
                # Calculate session first candle for new symbol
                self._calculate_session_first_candle(correct_symbol)
            
            self.refresh_data()
        else:
            # Show available symbols in error message
            available = self.mt5.get_available_symbols()
            if available:
                # Show first 20 symbols as examples
                examples = ", ".join(available[:20])
                if len(available) > 20:
                    examples += f" ... and {len(available) - 20} more"
                QMessageBox.warning(
                    self,
                    "Symbol Not Found",
                    f"Symbol '{symbol}' not found or not available.\n\n"
                    f"Available symbols include:\n{examples}\n\n"
                    f"Click 'Browse Symbols' to see all available symbols."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Symbol Not Found",
                    f"Symbol '{symbol}' not found or not available.\n\n"
                    f"Make sure the symbol is enabled in your MT5 terminal."
                )
    
    def _save_symbols_to_config(self):
        """Save symbols to config"""
        try:
            from ..config import Config
            config = Config()
            symbols = list(self.data_feed.symbols)
            config.set('data_feed.symbols', symbols)
            config.save()
        except Exception as e:
            logger.error(f"Error saving symbols: {e}")
    
    def show_available_symbols(self):
        """Show dialog with all available symbols"""
        if not self.mt5.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to MT5 first")
            return
        
        try:
            symbols = self.mt5.get_available_symbols()
            if not symbols:
                QMessageBox.information(self, "No Symbols", "No symbols available")
                return
            
            # Create message with symbols list
            symbols_text = "\n".join(symbols)
            msg = QMessageBox(self)
            msg.setWindowTitle("Available Symbols")
            msg.setText(f"Found {len(symbols)} available symbols:")
            msg.setDetailedText(symbols_text)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading symbols: {e}")
    
    def update_account_info(self):
        """Update account information display"""
        if not self.mt5.is_connected():
            return
        
        account_info = self.mt5.get_account_info()
        if account_info:
            self.balance_label.setText(f"Balance: {account_info['balance']:.2f} {account_info['currency']}")
            self.equity_label.setText(f"Equity: {account_info['equity']:.2f} {account_info['currency']}")
            self.margin_label.setText(f"Margin: {account_info['margin']:.2f} {account_info['currency']}")
            self.free_margin_label.setText(f"Free Margin: {account_info['free_margin']:.2f} {account_info['currency']}")
    
    def update_tick(self, symbol: str, tick_data: Dict):
        """Update tick data in table"""
        # Find row for symbol
        row = -1
        for i in range(self.data_table.rowCount()):
            if self.data_table.item(i, 0) and self.data_table.item(i, 0).text() == symbol:
                row = i
                break
        
        # Add new row if symbol not found
        if row == -1:
            row = self.data_table.rowCount()
            self.data_table.insertRow(row)
            self.data_table.setItem(row, 0, QTableWidgetItem(symbol))
        
        # Update data
        digits = 5  # Default, should get from symbol info
        symbol_info = self.mt5.get_symbol_info(symbol)
        if symbol_info:
            digits = symbol_info.get('digits', 5)
        
        self.data_table.setItem(row, 1, QTableWidgetItem(f"{tick_data['bid']:.{digits}f}"))
        self.data_table.setItem(row, 2, QTableWidgetItem(f"{tick_data['ask']:.{digits}f}"))
        self.data_table.setItem(row, 3, QTableWidgetItem(f"{tick_data['spread']:.{digits}f}"))
        self.data_table.setItem(row, 4, QTableWidgetItem(f"{tick_data.get('last', 0):.{digits}f}"))
        self.data_table.setItem(row, 5, QTableWidgetItem(str(tick_data['time'])))
        
        # Add OHLC data (columns 6-9)
        ohlc = self.ohlc_data.get(symbol, {})
        prev_open = ohlc.get('open')
        prev_high = ohlc.get('high')
        prev_low = ohlc.get('low')
        prev_close = ohlc.get('close')
        
        # Format OHLC values
        if prev_open is not None:
            self.data_table.setItem(row, 6, QTableWidgetItem(f"{prev_open:.{digits}f}"))
        else:
            self.data_table.setItem(row, 6, QTableWidgetItem("--"))
        
        if prev_high is not None:
            self.data_table.setItem(row, 7, QTableWidgetItem(f"{prev_high:.{digits}f}"))
        else:
            self.data_table.setItem(row, 7, QTableWidgetItem("--"))
        
        if prev_low is not None:
            self.data_table.setItem(row, 8, QTableWidgetItem(f"{prev_low:.{digits}f}"))
        else:
            self.data_table.setItem(row, 8, QTableWidgetItem("--"))
        
        if prev_close is not None:
            self.data_table.setItem(row, 9, QTableWidgetItem(f"{prev_close:.{digits}f}"))
        else:
            self.data_table.setItem(row, 9, QTableWidgetItem("--"))
        
        # Add Session First Candle High/Low data (columns 10-11)
        session_data = self.session_data.get(symbol, {})
        self._update_session_cell(row, 10, session_data.get('high'), digits, QColor(30, 60, 30))  # Light green bg for High
        self._update_session_cell(row, 11, session_data.get('low'), digits, QColor(60, 30, 30))   # Light red bg for Low
    
    def _update_session_cell(self, row: int, col: int, value: Optional[float], digits: int, bg_color: QColor):
        """Update session first candle cell with value and background color"""
        if value is not None:
            item = QTableWidgetItem(f"{value:.{digits}f}")
            item.setBackground(QBrush(bg_color))
            self.data_table.setItem(row, col, item)
        else:
            item = QTableWidgetItem("--")
            item.setForeground(QBrush(QColor(128, 128, 128)))  # Gray text for empty
            self.data_table.setItem(row, col, item)
    
    def _calculate_session_first_candle(self, symbol: str) -> Dict[str, Optional[float]]:
        """
        Calculate session first candle high/low for a symbol using M1 timeframe
        
        Args:
            symbol: Trading symbol to calculate for
            
        Returns:
            Dict with 'high' and 'low' keys, or empty dict if calculation fails
        """
        if not self.mt5.is_connected():
            return {}
        
        try:
            # Fetch M1 rates - request enough bars to cover 3 full days (4320 bars = 3 days * 24 hours * 60 minutes)
            # MT5 indicator processes all available bars from history, so we need enough to capture all session starts
            # get_rates returns list of dicts with newest first, need to reverse for chronological order
            rates = self.mt5.get_rates(symbol, mt5_lib.TIMEFRAME_M1, 4320)  # 3 days worth of M1 bars
            
            if not rates or len(rates) == 0:
                logger.debug(f"No M1 rates available for {symbol}")
                self.session_data[symbol] = {'high': None, 'low': None}
                return {'high': None, 'low': None}
            
            # MT5 get_rates returns newest first (reverse chronological)
            # SessionFirstCandle expects oldest to newest (chronological)
            # Reverse the list to get chronological order
            rates_list = list(reversed(rates))
            
            # Create a fresh calculator instance for clean calculation
            calculator = SessionFirstCandle(
                session1_start_hour=self.session_first_candle_config['session1_start_hour'],
                session1_end_hour=self.session_first_candle_config['session1_end_hour'],
                session2_start_hour=self.session_first_candle_config['session2_start_hour'],
                session2_end_hour=self.session_first_candle_config['session2_end_hour'],
                session3_start_hour=self.session_first_candle_config['session3_start_hour'],
                session3_end_hour=self.session_first_candle_config['session3_end_hour']
            )
            
            # Update the calculator with rates (will calculate chronologically)
            calculator.update(rates_list)
            
            # Get session high/low values
            session_high = calculator.get_session_high()
            session_low = calculator.get_session_low()
            
            # Store in session_data
            self.session_data[symbol] = {
                'high': session_high,
                'low': session_low
            }
            
            logger.debug(f"Calculated Session First Candle for {symbol}: High={session_high}, Low={session_low}")
            
            return {'high': session_high, 'low': session_low}
            
        except Exception as e:
            logger.error(f"Error calculating session first candle for {symbol}: {e}", exc_info=True)
            self.session_data[symbol] = {'high': None, 'low': None}
            return {'high': None, 'low': None}
    
    def on_session_changed(self, session_text: str):
        """Handle session type change"""
        session_map = {
            "Daily": "daily",
            "Asian Session": "asian",
            "European Session": "european",
            "US Session": "us"
        }
        self.session_type = session_map.get(session_text, "daily")
        self.ohlc_calculator = PreviousSessionOHLCCalculator(session_type=self.session_type)
        # Clear existing OHLC data and refetch
        self.ohlc_data = {}
        self.refresh_data()
    
    def fetch_ohlc_for_symbols(self, symbols: List[str]):
        """Fetch OHLC data for all symbols"""
        if not self.mt5.is_connected():
            return
        
        for symbol in symbols:
            try:
                if self.ohlc_calculator.calculate_ohlc(symbol):
                    ohlc = self.ohlc_calculator.get_ohlc()
                    self.ohlc_data[symbol] = ohlc
                    logger.debug(f"Fetched OHLC for {symbol}: O={ohlc['open']:.5f}, H={ohlc['high']:.5f}, L={ohlc['low']:.5f}, C={ohlc['close']:.5f}")
                else:
                    logger.warning(f"Failed to calculate OHLC for {symbol}")
                    # Set default values if calculation fails
                    self.ohlc_data[symbol] = {'open': None, 'high': None, 'low': None, 'close': None}
            except Exception as e:
                logger.error(f"Error fetching OHLC for {symbol}: {e}")
                self.ohlc_data[symbol] = {'open': None, 'high': None, 'low': None, 'close': None}
    
    def refresh_data(self):
        """Refresh market data"""
        # Fetch OHLC for all symbols first
        if self.data_feed.symbols:
            self.fetch_ohlc_for_symbols(list(self.data_feed.symbols))
            
            # Calculate session first candle for all symbols
            for symbol in self.data_feed.symbols:
                self._calculate_session_first_candle(symbol)
        
        self.data_table.setRowCount(0)
        
        for symbol in self.data_feed.symbols:
            tick = self.data_feed.get_latest_tick(symbol)
            if tick:
                self.update_tick(symbol, tick)
        
        self.update_account_info()

