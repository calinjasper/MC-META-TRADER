"""
Quick Trade Widget
STOXXO QTP-style quick trading interface
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QDoubleSpinBox, QGroupBox,
                             QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from typing import Optional

from ..mt5_connector import MT5Connector


class QuickTradeWidget(QWidget):
    """Quick Trade Widget - STOXXO QTP style"""
    
    # Signals
    buy_clicked = pyqtSignal(str, float)  # symbol, volume
    sell_clicked = pyqtSignal(str, float)  # symbol, volume
    
    def __init__(self, mt5: MT5Connector):
        super().__init__()
        self.mt5 = mt5
        self.current_symbol = ""
        self.current_bid = 0.0
        self.current_ask = 0.0
        self.setup_ui()
        # Load available symbols on initialization
        self.load_available_symbols()
    
    def setup_ui(self):
        """Setup the quick trade UI"""
        # Apply dark theme styling
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QComboBox, QDoubleSpinBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px;
            }
            QComboBox:focus, QDoubleSpinBox:focus {
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
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Symbol selector
        symbol_layout = QHBoxLayout()
        symbol_label = QLabel("Symbol:")
        symbol_label.setStyleSheet("color: #ffffff;")
        symbol_layout.addWidget(symbol_label)
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.setMinimumWidth(120)
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed)
        # Also handle when user finishes editing (presses Enter or loses focus)
        self.symbol_combo.lineEdit().editingFinished.connect(self.on_symbol_edited)
        symbol_layout.addWidget(self.symbol_combo)
        symbol_layout.addStretch()
        
        # Price display
        price_frame = QFrame()
        price_frame.setFrameStyle(QFrame.Shape.Box)
        price_frame.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555; padding: 5px;")
        price_layout = QHBoxLayout(price_frame)
        price_layout.setContentsMargins(10, 5, 10, 5)
        
        self.bid_label = QLabel("BID: --")
        self.bid_label.setStyleSheet("color: #ff4444; font-weight: bold; font-size: 14px;")
        price_layout.addWidget(self.bid_label)
        
        price_layout.addWidget(QLabel(" | "))
        
        self.ask_label = QLabel("ASK: --")
        self.ask_label.setStyleSheet("color: #44ff44; font-weight: bold; font-size: 14px;")
        price_layout.addWidget(self.ask_label)
        
        price_layout.addStretch()
        
        # Lot size quick buttons
        lot_layout = QHBoxLayout()
        lot_layout.addWidget(QLabel("Quick Lot:"))
        
        self.lot_buttons = {}
        lot_sizes = [0.01, 0.1, 1.0]
        for lot_size in lot_sizes:
            btn = QPushButton(f"{lot_size}")
            btn.setMinimumWidth(60)
            btn.setMaximumWidth(60)
            btn.clicked.connect(lambda checked, ls=lot_size: self.set_lot_size(ls))
            self.lot_buttons[lot_size] = btn
            lot_layout.addWidget(btn)
        
        self.custom_lot_spin = QDoubleSpinBox()
        self.custom_lot_spin.setMinimum(0.01)
        self.custom_lot_spin.setMaximum(100.0)
        self.custom_lot_spin.setSingleStep(0.01)
        self.custom_lot_spin.setValue(0.01)
        self.custom_lot_spin.setDecimals(2)
        self.custom_lot_spin.setMinimumWidth(80)
        lot_layout.addWidget(QLabel("Custom:"))
        lot_layout.addWidget(self.custom_lot_spin)
        lot_layout.addStretch()
        
        # Quick Buy/Sell buttons (large and prominent)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.buy_btn = QPushButton("BUY")
        self.buy_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 18px;
                padding: 15px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.buy_btn.setMinimumHeight(60)
        self.buy_btn.clicked.connect(self.on_buy_clicked)
        button_layout.addWidget(self.buy_btn)
        
        self.sell_btn = QPushButton("SELL")
        self.sell_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                font-size: 18px;
                padding: 15px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c62828;
            }
        """)
        self.sell_btn.setMinimumHeight(60)
        self.sell_btn.clicked.connect(self.on_sell_clicked)
        button_layout.addWidget(self.sell_btn)
        
        # Assemble layout
        layout.addLayout(symbol_layout)
        layout.addWidget(price_frame)
        layout.addLayout(lot_layout)
        layout.addLayout(button_layout)
        layout.addStretch()
        
        # Setup price update timer
        self.price_timer = QTimer()
        self.price_timer.timeout.connect(self.update_prices)
        self.price_timer.start(500)  # Update every 0.5 seconds
        
        # If MT5 is already connected, load symbols now
        if self.mt5.is_connected():
            self.load_available_symbols()
    
    def on_symbol_changed(self, symbol: str):
        """Handle symbol change from dropdown selection"""
        symbol = symbol.strip()
        if symbol:
            self.current_symbol = symbol.upper()
            # Update prices immediately when symbol changes
            self.update_prices()
        else:
            self.current_symbol = ""
            self.bid_label.setText("BID: --")
            self.ask_label.setText("ASK: --")
    
    def on_symbol_edited(self):
        """Handle when user manually types a symbol"""
        symbol = self.symbol_combo.currentText().strip()
        if symbol:
            # Validate symbol exists in MT5
            if self.mt5.is_connected():
                symbol_info = self.mt5.get_symbol_info(symbol)
                if symbol_info:
                    # Use correct symbol name from MT5
                    correct_symbol = symbol_info.get('name', symbol.upper())
                    self.current_symbol = correct_symbol
                    # Update combo box with correct symbol if different
                    if correct_symbol.upper() != symbol.upper():
                        index = self.symbol_combo.findText(correct_symbol)
                        if index >= 0:
                            self.symbol_combo.setCurrentIndex(index)
                        else:
                            self.symbol_combo.setCurrentText(correct_symbol)
                    self.update_prices()
                else:
                    # Symbol not found, but still try to update (might be valid but not loaded)
                    self.current_symbol = symbol.upper()
                    self.update_prices()
            else:
                self.current_symbol = symbol.upper()
                self.bid_label.setText("BID: --")
                self.ask_label.setText("ASK: --")
    
    def set_lot_size(self, lot_size: float):
        """Set lot size from quick button"""
        self.custom_lot_spin.setValue(lot_size)
    
    def get_lot_size(self) -> float:
        """Get current lot size"""
        return self.custom_lot_spin.value()
    
    def update_prices(self):
        """Update bid/ask prices"""
        # Get current symbol from combo box if not set
        if not self.current_symbol:
            symbol_text = self.symbol_combo.currentText().strip()
            if symbol_text:
                self.current_symbol = symbol_text.upper()
            else:
                self.bid_label.setText("BID: --")
                self.ask_label.setText("ASK: --")
                return
        
        if not self.mt5.is_connected():
            self.bid_label.setText("BID: --")
            self.ask_label.setText("ASK: --")
            return
        
        try:
            tick = self.mt5.get_tick(self.current_symbol)
            if tick and 'bid' in tick and 'ask' in tick:
                self.current_bid = tick['bid']
                self.current_ask = tick['ask']
                self.bid_label.setText(f"BID: {self.current_bid:.5f}")
                self.ask_label.setText(f"ASK: {self.current_ask:.5f}")
            else:
                # Try with different case or symbol variations
                # Sometimes MT5 needs exact symbol name
                symbol_info = self.mt5.get_symbol_info(self.current_symbol)
                if symbol_info:
                    correct_symbol = symbol_info.get('name', self.current_symbol)
                    if correct_symbol != self.current_symbol:
                        self.current_symbol = correct_symbol
                        tick = self.mt5.get_tick(correct_symbol)
                        if tick and 'bid' in tick and 'ask' in tick:
                            self.current_bid = tick['bid']
                            self.current_ask = tick['ask']
                            self.bid_label.setText(f"BID: {self.current_bid:.5f}")
                            self.ask_label.setText(f"ASK: {self.current_ask:.5f}")
                            return
                self.bid_label.setText("BID: --")
                self.ask_label.setText("ASK: --")
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Error updating prices for {self.current_symbol}: {e}")
            self.bid_label.setText("BID: --")
            self.ask_label.setText("ASK: --")
    
    def on_buy_clicked(self):
        """Handle buy button click"""
        if not self.current_symbol:
            return
        volume = self.get_lot_size()
        self.buy_clicked.emit(self.current_symbol, volume)
    
    def on_sell_clicked(self):
        """Handle sell button click"""
        if not self.current_symbol:
            return
        volume = self.get_lot_size()
        self.sell_clicked.emit(self.current_symbol, volume)
    
    def load_available_symbols(self):
        """Load all available symbols from MT5"""
        if not self.mt5.is_connected():
            return
        
        try:
            available_symbols = self.mt5.get_available_symbols()
            if not available_symbols:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("No symbols available from MT5")
                return
            
            current_text = self.symbol_combo.currentText()
            self.symbol_combo.clear()
            
            # Convert to list and make case-insensitive comparison
            available_list = list(available_symbols)
            available_upper = [s.upper() for s in available_list]
            
            # Add common symbols first (case-insensitive match)
            common_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'NZDUSD']
            added_common = []
            for common in common_symbols:
                common_upper = common.upper()
                if common_upper in available_upper:
                    idx = available_upper.index(common_upper)
                    actual_symbol = available_list[idx]
                    self.symbol_combo.addItem(actual_symbol)
                    added_common.append(actual_symbol)
            
            # Remove added symbols from available list (case-insensitive)
            remaining_symbols = [s for s in available_list if s.upper() not in [c.upper() for c in added_common]]
            
            # Add separator if there are more symbols
            if remaining_symbols:
                if self.symbol_combo.count() > 0:
                    self.symbol_combo.insertSeparator(self.symbol_combo.count())
                # Add remaining symbols sorted
                for symbol in sorted(remaining_symbols):
                    self.symbol_combo.addItem(symbol)
            
            # Restore selection or set default
            if current_text:
                index = self.symbol_combo.findText(current_text, Qt.MatchFlag.MatchFixedString)
                if index >= 0:
                    self.symbol_combo.setCurrentIndex(index)
                else:
                    # Try case-insensitive match
                    current_upper = current_text.upper()
                    for i in range(self.symbol_combo.count()):
                        if self.symbol_combo.itemText(i).upper() == current_upper:
                            self.symbol_combo.setCurrentIndex(i)
                            break
                    else:
                        # Set first symbol if current not found
                        if self.symbol_combo.count() > 0:
                            self.symbol_combo.setCurrentIndex(0)
                            self.on_symbol_changed(self.symbol_combo.currentText())
            elif self.symbol_combo.count() > 0:
                # Set first symbol if no current selection
                self.symbol_combo.setCurrentIndex(0)
                self.on_symbol_changed(self.symbol_combo.currentText())
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading available symbols: {e}", exc_info=True)
    
    def update_symbol_list(self, symbols: list):
        """Update symbol combo box with symbols from data feed"""
        if not symbols:
            # If no symbols provided, load all available from MT5
            self.load_available_symbols()
            return
        
        current_text = self.symbol_combo.currentText()
        self.symbol_combo.clear()
        for symbol in symbols:
            self.symbol_combo.addItem(symbol)
        # Restore selection if still valid
        index = self.symbol_combo.findText(current_text)
        if index >= 0:
            self.symbol_combo.setCurrentIndex(index)
        elif self.symbol_combo.count() > 0:
            # Set first symbol if current not found
            self.symbol_combo.setCurrentIndex(0)
            self.on_symbol_changed(self.symbol_combo.currentText())
