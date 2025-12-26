"""
Market Data Panel
Displays live market data and account information
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QLabel, QPushButton, QLineEdit,
                             QHeaderView, QComboBox, QMessageBox)
from PyQt6.QtCore import Qt
from typing import Dict, Optional, List

from ..data_feed import DataFeed
from ..mt5_connector import MT5Connector
from .custom_indicator_panel import PreviousSessionOHLCCalculator
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
        layout = QVBoxLayout(self)
        
        # Account info section
        account_label = QLabel("Account Information")
        account_label.setStyleSheet("font-weight: bold; font-size: 14px;")
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
        table_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(table_label)
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(10)
        self.data_table.setHorizontalHeaderLabels([
            "Symbol", "Bid", "Ask", "Spread", "Last", "Time", 
            "Prev Open", "Prev High", "Prev Low", "Prev Close"
        ])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.data_table.setAlternatingRowColors(True)
        
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
        refresh_button.setStyleSheet("font-weight: bold; padding: 5px;")
        refresh_button.clicked.connect(self.refresh_data)
        session_layout.addWidget(refresh_button)
        session_layout.addStretch()
        layout.addLayout(session_layout)
    
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
        
        self.data_table.setRowCount(0)
        
        for symbol in self.data_feed.symbols:
            tick = self.data_feed.get_latest_tick(symbol)
            if tick:
                self.update_tick(symbol, tick)
        
        self.update_account_info()

