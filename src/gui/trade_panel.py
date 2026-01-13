"""
Trade Panel - STOXXO QTP Style
Compact, efficient trading interface
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QComboBox, QDoubleSpinBox, QPushButton, QLabel,
                             QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QDialog, QLineEdit, QSpinBox, QFrame,
                             QScrollArea, QSplitter, QButtonGroup, QRadioButton)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette
import MetaTrader5 as mt5
from typing import Optional, Dict

from ..mt5_connector import MT5Connector
from ..trading.order_manager import OrderManager
from ..trading.risk_manager import RiskManager
from .quick_trade_widget import QuickTradeWidget
from ..config import Config


class RiskCalculatorWidget(QWidget):
    """Risk Calculator Widget"""
    
    order_type_changed = pyqtSignal(str)  # Emitted when order type changes
    
    def __init__(self, risk_manager: RiskManager, mt5: MT5Connector):
        super().__init__()
        self.risk_manager = risk_manager
        self.mt5 = mt5
        self.selected_order_type = "BUY"  # Default to BUY
        self.setup_ui()
    
    def setup_ui(self):
        """Setup risk calculator UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        group = QGroupBox("Risk Calculator")
        form_layout = QFormLayout()
        
        # Order Type Selection (BUY/SELL)
        order_type_layout = QHBoxLayout()
        order_type_layout.addWidget(QLabel("Order Type:"))
        
        self.order_type_group = QButtonGroup(self)
        self.buy_radio = QRadioButton("BUY")
        self.buy_radio.setChecked(True)
        self.buy_radio.setStyleSheet("color: #4CAF50; font-weight: bold;")
        self.buy_radio.toggled.connect(lambda checked: self.on_order_type_changed("BUY") if checked else None)
        self.order_type_group.addButton(self.buy_radio, 0)
        order_type_layout.addWidget(self.buy_radio)
        
        self.sell_radio = QRadioButton("SELL")
        self.sell_radio.setStyleSheet("color: #f44336; font-weight: bold;")
        self.sell_radio.toggled.connect(lambda checked: self.on_order_type_changed("SELL") if checked else None)
        self.order_type_group.addButton(self.sell_radio, 1)
        order_type_layout.addWidget(self.sell_radio)
        
        order_type_layout.addStretch()
        form_layout.addRow("Order Type:", order_type_layout)
        
        self.risk_percentage_spin = QDoubleSpinBox()
        self.risk_percentage_spin.setMinimum(0.1)
        self.risk_percentage_spin.setMaximum(10.0)
        self.risk_percentage_spin.setValue(2.0)
        self.risk_percentage_spin.setSuffix("%")
        self.risk_percentage_spin.setDecimals(1)
        form_layout.addRow("Risk Per Trade:", self.risk_percentage_spin)
        
        self.risk_amount_label = QLabel("--")
        self.risk_amount_label.setStyleSheet("font-weight: bold; color: #ff9800;")
        form_layout.addRow("Risk Amount:", self.risk_amount_label)
        
        self.potential_profit_label = QLabel("--")
        self.potential_profit_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        form_layout.addRow("Potential Profit:", self.potential_profit_label)
        
        self.potential_loss_label = QLabel("--")
        self.potential_loss_label.setStyleSheet("font-weight: bold; color: #f44336;")
        form_layout.addRow("Potential Loss:", self.potential_loss_label)
        
        group.setLayout(form_layout)
        layout.addWidget(group)
    
    def on_order_type_changed(self, order_type: str):
        """Handle order type change"""
        self.selected_order_type = order_type
        self.order_type_changed.emit(order_type)
    
    def get_order_type(self) -> str:
        """Get selected order type"""
        return self.selected_order_type
    
    def calculate_risk(self, symbol: str, entry_price: float, stop_loss: float,
                       volume: float, order_type: str, take_profit: float = 0.0):
        """Calculate and display risk"""
        if not symbol or entry_price == 0 or stop_loss == 0:
            self.risk_amount_label.setText("--")
            self.potential_profit_label.setText("--")
            self.potential_loss_label.setText("--")
            return
        
        result = self.risk_manager.calculate_risk_amount(
            symbol, entry_price, stop_loss, volume, order_type
        )
        
        account_info = self.mt5.get_account_info()
        currency = account_info.get('currency', 'USD') if account_info else 'USD'
        
        # Calculate potential profit/loss
        symbol_info = self.mt5.get_symbol_info(symbol)
        if not symbol_info:
        self.risk_amount_label.setText(f"{result['risk_amount']:.2f} {currency}")
            self.potential_profit_label.setText("--")
            self.potential_loss_label.setText(f"{result['risk_amount']:.2f} {currency}")
            return
        
        contract_size = symbol_info.get('contract_size', 100000)
        point = symbol_info.get('point', 0.0001)
        
        # Calculate potential loss (risk amount)
        potential_loss = result.get('risk_amount', 0.0)
        
        # Calculate potential profit if TP is set
        potential_profit = 0.0
        if take_profit > 0:
            if order_type.upper() == "BUY":
                price_diff = take_profit - entry_price
            else:  # SELL
                price_diff = entry_price - take_profit
            
            # Calculate profit: price_diff * contract_size * volume
            # For forex, this gives profit in quote currency
            potential_profit = price_diff * contract_size * volume
            
            # Convert to account currency if needed
            # For now, assume quote currency matches account currency (simplified)
            # In a full implementation, you'd need to convert using exchange rates
        
        self.risk_amount_label.setText(f"{result['risk_amount']:.2f} {currency}")
        self.potential_profit_label.setText(f"{potential_profit:.2f} {currency}" if potential_profit > 0 else "--")
        self.potential_loss_label.setText(f"{potential_loss:.2f} {currency}")


class ModifyPositionDialog(QDialog):
    """Dialog for modifying position SL/TP"""
    
    def __init__(self, position: Dict, parent=None):
        super().__init__(parent)
        self.position = position
        self.setWindowTitle(f"Modify Position {position.get('ticket', '')}")
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Current values
        current_sl = self.position.get('sl', 0.0)
        current_tp = self.position.get('tp', 0.0)
        
        self.sl_spin = QDoubleSpinBox()
        self.sl_spin.setMinimum(0.0)
        self.sl_spin.setMaximum(100000.0)
        self.sl_spin.setDecimals(5)
        self.sl_spin.setValue(current_sl if current_sl > 0 else 0.0)
        form_layout.addRow("Stop Loss:", self.sl_spin)
        
        self.tp_spin = QDoubleSpinBox()
        self.tp_spin.setMinimum(0.0)
        self.tp_spin.setMaximum(100000.0)
        self.tp_spin.setDecimals(5)
        self.tp_spin.setValue(current_tp if current_tp > 0 else 0.0)
        form_layout.addRow("Take Profit:", self.tp_spin)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("Modify")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def get_values(self):
        """Get SL/TP values"""
        return self.sl_spin.value(), self.tp_spin.value()


class PartialCloseDialog(QDialog):
    """Dialog for partial close"""
    
    def __init__(self, position: Dict, parent=None):
        super().__init__(parent)
        self.position = position
        self.setWindowTitle(f"Partial Close Position {position.get('ticket', '')}")
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        max_volume = self.position.get('volume', 0.0)
        
        self.volume_spin = QDoubleSpinBox()
        self.volume_spin.setMinimum(0.01)
        self.volume_spin.setMaximum(max_volume - 0.01)
        self.volume_spin.setSingleStep(0.01)
        self.volume_spin.setDecimals(2)
        self.volume_spin.setValue(max_volume / 2.0)  # Default to half
        form_layout.addRow(f"Close Volume (Max: {max_volume:.2f}):", self.volume_spin)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("Close Partial")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def get_volume(self):
        """Get volume to close"""
        return self.volume_spin.value()


class TradePanel(QWidget):
    """Trade execution panel - STOXXO QTP Style"""
    
    def __init__(self, mt5: MT5Connector, order_manager: OrderManager,
                 risk_manager: RiskManager, config: Config = None, data_feed=None):
        super().__init__()
        self.mt5 = mt5
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.config = config or Config()
        self.data_feed = data_feed
        self.setup_ui()
        self.setup_timers()
        self.update_positions()
    
    def setup_ui(self):
        """Setup the UI - STOXXO QTP Style"""
        # Apply dark theme styling
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
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
            QGroupBox {
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #252525;
                color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #ffffff;
            }
            QRadioButton {
                color: #ffffff;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Compact Account Info Bar (horizontal)
        account_bar = self.create_account_bar()
        main_layout.addWidget(account_bar)
        
        # Splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Quick Trade + Risk Calculator
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Quick Trade Widget
        self.quick_trade = QuickTradeWidget(self.mt5)
        self.quick_trade.buy_clicked.connect(self.on_quick_buy)
        self.quick_trade.sell_clicked.connect(self.on_quick_sell)
        # Connect symbol change to ensure symbol is in data feed and update risk calculator
        self.quick_trade.symbol_combo.currentTextChanged.connect(self.on_trade_symbol_changed)
        self.quick_trade.symbol_combo.currentTextChanged.connect(self.update_risk_calculator)
        # Connect lot size changes to update risk calculator
        if hasattr(self.quick_trade, 'custom_lot_spin'):
            self.quick_trade.custom_lot_spin.valueChanged.connect(self.update_risk_calculator)
        self.quick_trade.setToolTip("Quick Trade Panel - One-click trading with preset lot sizes")
        left_layout.addWidget(self.quick_trade)
        
        # Enhanced Order Entry Panel
        order_panel = self.create_order_entry_panel()
        order_panel.setToolTip("Order Entry - Set stop loss and take profit levels")
        left_layout.addWidget(order_panel)
        
        # Risk Calculator
        self.risk_calculator = RiskCalculatorWidget(self.risk_manager, self.mt5)
        self.risk_calculator.order_type_changed.connect(self.on_risk_calculator_order_type_changed)
        self.risk_calculator.setToolTip("Risk Calculator - View risk amount and potential profit/loss before placing order")
        # Connect to update risk when SL/TP or volume changes
        self.sl_spin.valueChanged.connect(self.update_risk_calculator)
        self.tp_spin.valueChanged.connect(self.update_risk_calculator)
        self.quick_trade.custom_lot_spin.valueChanged.connect(self.update_risk_calculator)
        self.quick_trade.symbol_combo.currentTextChanged.connect(self.update_risk_calculator)
        left_layout.addWidget(self.risk_calculator)
        
        # Execute Trade Button
        execute_layout = QHBoxLayout()
        execute_layout.addStretch()
        self.execute_trade_btn = QPushButton("Execute Trade")
        self.execute_trade_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.execute_trade_btn.clicked.connect(self.on_execute_trade)
        execute_layout.addWidget(self.execute_trade_btn)
        execute_layout.addStretch()
        left_layout.addLayout(execute_layout)
        
        left_layout.addStretch()
        
        # Right side: Positions
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Position Summary
        position_summary = self.create_position_summary()
        right_layout.addWidget(position_summary)
        
        # Positions Table
        positions_label = QLabel("Open Positions")
        positions_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(positions_label)
        
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(12)
        self.positions_table.setHorizontalHeaderLabels([
            "Ticket", "Name", "Symbol", "Type", "Volume", "Price Open", 
            "Price Current", "SL", "TP", "Profit", "P&L %", "Actions"
        ])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.positions_table.setAlternatingRowColors(True)
        # Enhanced table styling
        self.positions_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #2b2b2b;
                color: white;
                gridline-color: #555;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #3d5afe;
                color: white;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: white;
                padding: 5px;
                border: 1px solid #555;
                font-weight: bold;
            }
        """)
        right_layout.addWidget(self.positions_table)
        
        # Action buttons
        action_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.update_positions)
        action_layout.addWidget(refresh_btn)
        
        close_all_btn = QPushButton("Close All")
        close_all_btn.clicked.connect(self.close_all_positions)
        action_layout.addWidget(close_all_btn)
        
        action_layout.addStretch()
        right_layout.addLayout(action_layout)
        
        # Add to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
    
    def create_account_bar(self) -> QWidget:
        """Create compact account information bar"""
        bar = QFrame()
        bar.setFrameStyle(QFrame.Shape.Box)
        bar.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555; padding: 5px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.balance_label = QLabel("Balance: --")
        self.balance_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(self.balance_label)
        
        layout.addWidget(self.create_separator())
        
        self.equity_label = QLabel("Equity: --")
        self.equity_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(self.equity_label)
        
        layout.addWidget(self.create_separator())
        
        self.margin_label = QLabel("Margin: --")
        self.margin_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(self.margin_label)
        
        layout.addWidget(self.create_separator())
        
        self.free_margin_label = QLabel("Free Margin: --")
        self.free_margin_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(self.free_margin_label)
        
        layout.addWidget(self.create_separator())
        
        self.margin_level_label = QLabel("Margin Level: --")
        self.margin_level_label.setStyleSheet("color: white; font-weight: bold;")
        self.margin_level_label.setToolTip("Margin Level: >200% = Safe, 100-200% = Warning, <100% = Danger")
        layout.addWidget(self.margin_level_label)
        
        # Connection status indicator
        self.connection_status = QLabel("●")
        self.connection_status.setStyleSheet("color: #888; font-size: 16px;")
        self.connection_status.setToolTip("Connection Status")
        layout.addWidget(self.connection_status)
        
        layout.addStretch()
        
        return bar
    
    def create_separator(self) -> QLabel:
        """Create visual separator"""
        sep = QLabel("|")
        sep.setStyleSheet("color: #888; margin: 0 5px;")
        return sep
    
    def create_order_entry_panel(self) -> QGroupBox:
        """Create enhanced order entry panel"""
        group = QGroupBox("Order Entry")
        layout = QVBoxLayout()
        
        # SL/TP quick buttons
        sl_tp_layout = QHBoxLayout()
        sl_tp_layout.addWidget(QLabel("Quick SL:"))
        
        sl_buttons = [10, 20, 50, 100]
        for sl_value in sl_buttons:
            btn = QPushButton(f"{sl_value} pips")
            btn.setMinimumWidth(70)
            btn.clicked.connect(lambda checked, v=sl_value: self.set_quick_sl(v))
            sl_tp_layout.addWidget(btn)
        
        sl_tp_layout.addStretch()
        sl_tp_layout.addWidget(QLabel("Quick TP:"))
        
        tp_buttons = [20, 40, 100, 200]
        for tp_value in tp_buttons:
            btn = QPushButton(f"{tp_value} pips")
            btn.setMinimumWidth(70)
            btn.clicked.connect(lambda checked, v=tp_value: self.set_quick_tp(v))
            sl_tp_layout.addWidget(btn)
        
        layout.addLayout(sl_tp_layout)
        
        # Manual SL/TP entry
        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel("SL:"))
        self.sl_spin = QDoubleSpinBox()
        self.sl_spin.setMinimum(0.0)
        self.sl_spin.setMaximum(10000.0)
        self.sl_spin.setDecimals(5)
        self.sl_spin.setValue(0.0)
        self.sl_spin.valueChanged.connect(self.on_sl_tp_changed)
        manual_layout.addWidget(self.sl_spin)
        
        manual_layout.addWidget(QLabel("TP:"))
        self.tp_spin = QDoubleSpinBox()
        self.tp_spin.setMinimum(0.0)
        self.tp_spin.setMaximum(10000.0)
        self.tp_spin.setDecimals(5)
        self.tp_spin.setValue(0.0)
        self.tp_spin.valueChanged.connect(self.on_sl_tp_changed)
        manual_layout.addWidget(self.tp_spin)
        
        auto_btn = QPushButton("Auto SL/TP")
        auto_btn.clicked.connect(self.calculate_sl_tp)
        manual_layout.addWidget(auto_btn)
        
        layout.addLayout(manual_layout)
        group.setLayout(layout)
        
        return group
    
    def create_position_summary(self) -> QFrame:
        """Create position summary widget"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.Shape.Box)
        frame.setStyleSheet("background-color: #1e1e1e; border: 1px solid #555; padding: 5px;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)
        
        self.total_positions_label = QLabel("Positions: 0")
        self.total_positions_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(self.total_positions_label)
        
        layout.addWidget(self.create_separator())
        
        self.total_profit_label = QLabel("Total P&L: --")
        self.total_profit_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(self.total_profit_label)
        
        layout.addWidget(self.create_separator())
        
        self.margin_used_label = QLabel("Margin Used: --")
        self.margin_used_label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(self.margin_used_label)
        
        layout.addStretch()
        
        return frame
    
    def setup_timers(self):
        """Setup update timers"""
        # Timer for price updates
        self.price_timer = QTimer()
        self.price_timer.timeout.connect(self.update_prices)
        self.price_timer.start(500)  # Update every 0.5 seconds
        
        # Timer for account info
        self.account_timer = QTimer()
        self.account_timer.timeout.connect(self.update_account_info)
        self.account_timer.start(2000)  # Update every 2 seconds
    
    def set_quick_sl(self, pips: int):
        """Set quick SL in pips based on selected order type"""
        symbol = self.quick_trade.current_symbol
        if not symbol:
            return
        
        tick = self.mt5.get_tick(symbol)
        if not tick:
            return
        
        symbol_info = self.mt5.get_symbol_info(symbol)
        if not symbol_info:
            return
        
        point = symbol_info.get('point', 0.0001)
        digits = symbol_info.get('digits', 5)
        pip_size = point * (10 if digits == 5 else 1)
        
        # Get order type from risk calculator
        order_type = self.risk_calculator.get_order_type()
        
        if order_type == "BUY":
            entry_price = tick['ask']
            # SL for BUY: below entry
            sl_price = entry_price - (pips * pip_size)
        else:  # SELL
            entry_price = tick['bid']
            # SL for SELL: above entry
            sl_price = entry_price + (pips * pip_size)
        
        self.sl_spin.setValue(sl_price)
        # Risk calculator will update via valueChanged signal
    
    def set_quick_tp(self, pips: int):
        """Set quick TP in pips based on selected order type"""
        symbol = self.quick_trade.current_symbol
        if not symbol:
            return
        
        tick = self.mt5.get_tick(symbol)
        if not tick:
            return
        
        symbol_info = self.mt5.get_symbol_info(symbol)
        if not symbol_info:
            return
        
        point = symbol_info.get('point', 0.0001)
        digits = symbol_info.get('digits', 5)
        pip_size = point * (10 if digits == 5 else 1)
        
        # Get order type from risk calculator
        order_type = self.risk_calculator.get_order_type()
        
        if order_type == "BUY":
            entry_price = tick['ask']
            # TP for BUY: above entry
            tp_price = entry_price + (pips * pip_size)
        else:  # SELL
            entry_price = tick['bid']
            # TP for SELL: below entry
            tp_price = entry_price - (pips * pip_size)
        
        self.tp_spin.setValue(tp_price)
        # Risk calculator will update via valueChanged signal
    
    def update_prices(self):
        """Update real-time prices"""
        # Prices are updated by the timer in QuickTradeWidget
        # This method can be used for additional price updates if needed
        pass
    
    def update_account_info(self):
        """Update account information"""
        if not self.mt5.is_connected():
            # Update connection status
            self.connection_status.setText("●")
            self.connection_status.setStyleSheet("color: #f44336; font-size: 16px;")
            self.connection_status.setToolTip("Disconnected")
            return
        
        # Update connection status
        self.connection_status.setText("●")
        self.connection_status.setStyleSheet("color: #4CAF50; font-size: 16px;")
        self.connection_status.setToolTip("Connected")
        
        account_info = self.mt5.get_account_info()
        if account_info:
            currency = account_info.get('currency', 'USD')
            self.balance_label.setText(f"Balance: {account_info['balance']:.2f} {currency}")
            self.balance_label.setToolTip(f"Account Balance: {account_info['balance']:.2f} {currency}")
            
            self.equity_label.setText(f"Equity: {account_info['equity']:.2f} {currency}")
            self.equity_label.setToolTip(f"Account Equity (Balance + Floating P&L): {account_info['equity']:.2f} {currency}")
            
            self.margin_label.setText(f"Margin: {account_info['margin']:.2f} {currency}")
            self.margin_label.setToolTip(f"Margin Used: {account_info['margin']:.2f} {currency}")
            
            self.free_margin_label.setText(f"Free Margin: {account_info['free_margin']:.2f} {currency}")
            self.free_margin_label.setToolTip(f"Free Margin Available: {account_info['free_margin']:.2f} {currency}")
            
            # Margin level with status indicator
            margin_level = account_info.get('margin_level', 0)
            margin_level_text = f"{margin_level:.2f}%"
            if margin_level > 200:
                color = "#4CAF50"  # Green - safe
                status = "Safe"
            elif margin_level > 100:
                color = "#ff9800"  # Orange - warning
                status = "Warning"
            else:
                color = "#f44336"  # Red - danger
                status = "Danger"
            
            self.margin_level_label.setText(f"Margin Level: {margin_level_text}")
            self.margin_level_label.setStyleSheet(f"color: {color}; font-weight: bold;")
            self.margin_level_label.setToolTip(f"Margin Level: {margin_level_text} ({status})")
    
    def calculate_sl_tp(self):
        """Calculate stop loss and take profit automatically"""
        symbol = self.quick_trade.current_symbol
        if not symbol:
            QMessageBox.warning(self, "Error", "Please select a symbol")
            return
        
        tick = self.mt5.get_tick(symbol)
        if not tick:
            QMessageBox.warning(self, "Error", "Could not get current price")
            return
        
        entry_price = tick['ask']  # Default to ask for BUY
        order_type = "BUY"  # Default
        
        sl = self.risk_manager.calculate_stop_loss(symbol, entry_price, order_type)
        tp = self.risk_manager.calculate_take_profit(symbol, entry_price, order_type, stop_loss=sl)
        
        # Temporarily block signals to avoid multiple updates
        self.sl_spin.blockSignals(True)
        self.tp_spin.blockSignals(True)
        self.sl_spin.setValue(sl)
        self.tp_spin.setValue(tp)
        self.sl_spin.blockSignals(False)
        self.tp_spin.blockSignals(False)
        
        # Update risk calculator
        self.update_risk_calculator()
    
    def on_sl_tp_changed(self):
        """Handle SL/TP value change - update risk calculator"""
        self.update_risk_calculator()
    
    def on_risk_calculator_order_type_changed(self, order_type: str):
        """Handle order type change in risk calculator"""
        # Update SL/TP based on new order type
        self.update_sl_tp_for_order_type(order_type)
        # Update risk calculator
        self.update_risk_calculator()
    
    def update_sl_tp_for_order_type(self, order_type: str):
        """Update SL/TP values to be valid for the selected order type"""
        symbol = self.quick_trade.current_symbol
        if not symbol:
            return
        
        tick = self.mt5.get_tick(symbol)
        if not tick:
            return
        
        symbol_info = self.mt5.get_symbol_info(symbol)
        if not symbol_info:
            return
        
        point = symbol_info.get('point', 0.0001)
        digits = symbol_info.get('digits', 5)
        pip_size = point * (10 if digits == 5 else 1)
        
        # Get current prices
        ask_price = tick['ask']
        bid_price = tick['bid']
        
        # Get current SL/TP
        current_sl = self.sl_spin.value()
        current_tp = self.tp_spin.value()
        
        # Block signals to avoid triggering updates
        self.sl_spin.blockSignals(True)
        self.tp_spin.blockSignals(True)
        
        if order_type == "BUY":
            entry_price = ask_price
            # If SL is set but invalid for BUY (above or equal to entry), adjust it
            if current_sl > 0 and current_sl >= entry_price:
                # Set SL 20 pips below entry
                self.sl_spin.setValue(entry_price - (20 * pip_size))
            # If TP is set but invalid for BUY (below or equal to entry), adjust it
            if current_tp > 0 and current_tp <= entry_price:
                # Set TP 40 pips above entry
                self.tp_spin.setValue(entry_price + (40 * pip_size))
        else:  # SELL
            entry_price = bid_price
            # If SL is set but invalid for SELL (below or equal to entry), adjust it
            if current_sl > 0 and current_sl <= entry_price:
                # Set SL 20 pips above entry
                self.sl_spin.setValue(entry_price + (20 * pip_size))
            # If TP is set but invalid for SELL (above or equal to entry), adjust it
            if current_tp > 0 and current_tp >= entry_price:
                # Set TP 40 pips below entry
                self.tp_spin.setValue(entry_price - (40 * pip_size))
        
        self.sl_spin.blockSignals(False)
        self.tp_spin.blockSignals(False)
    
    def on_execute_trade(self):
        """Execute trade based on selected order type in risk calculator"""
        order_type = self.risk_calculator.get_order_type()
        symbol = self.quick_trade.current_symbol
        volume = self.quick_trade.get_lot_size()
        
        if not symbol:
            QMessageBox.warning(self, "Error", "Please select a symbol")
            return
        
        self.place_order(order_type, symbol, volume)
    
    def update_risk_calculator(self):
        """Update risk calculator with current values"""
        symbol = self.quick_trade.current_symbol
        if not symbol:
            self.risk_calculator.risk_amount_label.setText("--")
            self.risk_calculator.potential_profit_label.setText("--")
            self.risk_calculator.potential_loss_label.setText("--")
            return
        
        if not self.mt5.is_connected():
            return
        
        tick = self.mt5.get_tick(symbol)
        if not tick or 'ask' not in tick or 'bid' not in tick:
            return
        
        sl = self.sl_spin.value()
        tp = self.tp_spin.value()
        volume = self.quick_trade.get_lot_size()
        
        # Get order type from risk calculator selection
        order_type = self.risk_calculator.get_order_type()
        
        if sl > 0:
            # Use appropriate entry price based on order type
            if order_type == "BUY":
                entry_price = tick['ask']
            else:  # SELL
                entry_price = tick['bid']
            
            self.risk_calculator.calculate_risk(symbol, entry_price, sl, volume, order_type, tp)
        else:
            # Clear if no SL set
            self.risk_calculator.risk_amount_label.setText("--")
            self.risk_calculator.potential_profit_label.setText("--")
            self.risk_calculator.potential_loss_label.setText("--")
    
    def on_quick_buy(self, symbol: str, volume: float):
        """Handle quick buy"""
        self.place_order("BUY", symbol, volume)
    
    def on_quick_sell(self, symbol: str, volume: float):
        """Handle quick sell"""
        self.place_order("SELL", symbol, volume)
    
    def place_order(self, order_type: str, symbol: str = None, volume: float = None):
        """Place a manual order"""
        if symbol is None:
            symbol = self.quick_trade.current_symbol
        
        if not symbol:
            QMessageBox.warning(self, "Error", "Please select a symbol")
            return
        
        if volume is None:
            volume = self.quick_trade.get_lot_size()
        
        # Get FRESH current price for execution (always use latest)
        tick = self.mt5.get_tick(symbol)
        if not tick or 'ask' not in tick or 'bid' not in tick:
            QMessageBox.warning(self, "Error", "Could not get current live price. Please check connection.")
            return
        
        # Use fresh live price for entry
        entry_price = tick['ask'] if order_type == "BUY" else tick['bid']
        
        # Get symbol info for pip calculations
        symbol_info = self.mt5.get_symbol_info(symbol)
        if not symbol_info:
            QMessageBox.warning(self, "Error", "Could not get symbol information")
            return
        
        point = symbol_info.get('point', 0.0001)
        digits = symbol_info.get('digits', 5)
        pip_size = point * (10 if digits == 5 else 1)
        
        # Get SL/TP values from spin boxes
        sl_value = self.sl_spin.value()
        tp_value = self.tp_spin.value()
        
        # Calculate SL/TP preserving pip distance from current live entry price
        # This ensures SL/TP are always valid relative to current market price
        sl = 0.0
        tp = 0.0
        
        if sl_value > 0:
            # Calculate pip distance from the set SL to determine the intended distance
            # Then apply that distance to current live entry price
            if order_type == "BUY":
                # For BUY: Calculate how many pips below entry the SL was intended to be
                # We need to estimate the original entry price when SL was set
                # If SL is valid (below current ask), preserve the distance
                if sl_value < entry_price:
                    # SL is still valid, use it
                    sl = sl_value
                else:
                    # SL became invalid due to price movement
                    # Recalculate based on current price - use a default distance
                    # Try to preserve approximate distance if possible
                    sl = entry_price - (20 * pip_size)  # Default 20 pips
            else:  # SELL
                # For SELL: SL should be above entry
                if sl_value > entry_price:
                    # SL is still valid, use it
                    sl = sl_value
                else:
                    # SL became invalid, recalculate
                    sl = entry_price + (20 * pip_size)  # Default 20 pips
        
        if tp_value > 0:
            if order_type == "BUY":
                # For BUY: TP should be above entry
                if tp_value > entry_price:
                    tp = tp_value
                else:
                    # TP became invalid, recalculate
                    tp = entry_price + (40 * pip_size)  # Default 40 pips
            else:  # SELL
                # For SELL: TP should be below entry
                if tp_value < entry_price:
                    tp = tp_value
                else:
                    # TP became invalid, recalculate
                    tp = entry_price - (40 * pip_size)  # Default 40 pips
        
        # Final validation with current live prices
        # Note: sl and tp have been adjusted above if they became invalid due to price movement
        if sl > 0:
            if order_type == "BUY" and sl >= entry_price:
                QMessageBox.warning(
                    self, 
                    "Invalid Stop Loss", 
                    f"Stop loss ({sl:.5f}) must be below current live entry price ({entry_price:.5f}) for BUY orders.\n\n"
                    f"Price has moved. SL has been recalculated. Please review and adjust if needed, or use 'Auto SL/TP' button."
                )
                # Update the spin box with the recalculated value
                self.sl_spin.blockSignals(True)
                self.sl_spin.setValue(sl)
                self.sl_spin.blockSignals(False)
                # Don't return - continue with the recalculated value
            elif order_type == "SELL" and sl <= entry_price:
                QMessageBox.warning(
                    self, 
                    "Invalid Stop Loss", 
                    f"Stop loss ({sl:.5f}) must be above current live entry price ({entry_price:.5f}) for SELL orders.\n\n"
                    f"Price has moved. SL has been recalculated. Please review and adjust if needed, or use 'Auto SL/TP' button."
                )
                # Update the spin box with the recalculated value
                self.sl_spin.blockSignals(True)
                self.sl_spin.setValue(sl)
                self.sl_spin.blockSignals(False)
                # Don't return - continue with the recalculated value
        
        if tp > 0:
            if order_type == "BUY" and tp <= entry_price:
                QMessageBox.warning(
                    self, 
                    "Invalid Take Profit", 
                    f"Take profit ({tp:.5f}) must be above entry price ({entry_price:.5f}) for BUY orders."
                )
                return
            elif order_type == "SELL" and tp >= entry_price:
                QMessageBox.warning(
                    self, 
                    "Invalid Take Profit", 
                    f"Take profit ({tp:.5f}) must be below entry price ({entry_price:.5f}) for SELL orders."
                )
                return
        
        # Update risk calculator
        if sl > 0:
            self.risk_calculator.calculate_risk(symbol, entry_price, sl, volume, order_type, tp)
        else:
            # Update risk calculator even if no SL (will show --)
            self.update_risk_calculator()
        
        # Validate order (including TP distance)
        validation = self.risk_manager.validate_order(symbol, volume, entry_price, sl, tp)
        if not validation['valid']:
            QMessageBox.warning(self, "Validation Error", validation['message'])
            return
        
        # Confirm order
        reply = QMessageBox.question(
            self,
            "Confirm Order",
            f"Place {order_type} order for {volume} lots of {symbol}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Log order details before placing
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Placing {order_type} order: symbol={symbol}, volume={volume}, sl={sl}, tp={tp}, entry_price={entry_price}")
            
            result = self.order_manager.place_market_order(
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                sl=sl,
                tp=tp,
                comment="Manual Trade"
            )
            
            logger.info(f"Order result: {result}")
            
            if result:
                retcode = result.get('retcode', 0)
                success = result.get('success', False)
                
                # Check if order was actually successful
                # TRADE_RETCODE_DONE (10009) = fully executed
                # TRADE_RETCODE_DONE_PARTIAL (10010) = partially executed (still a position)
                # TRADE_RETCODE_PLACED (10008) = order placed but pending execution
                if (success and retcode == 10009) or retcode == 10010:  # Fully or partially executed
                    order_ticket = result.get('order', 0)
                    QMessageBox.information(
                        self, 
                        "Success", 
                        f"Order placed successfully\nTicket: {order_ticket}\nReturn Code: {retcode}"
                    )
                    
                    # Wait a moment for position to appear, then update
                    import time
                    time.sleep(0.5)  # Small delay to allow MT5 to process
                    
                    # Update positions and verify the position exists
                self.update_positions()
                    
                    # Verify position was actually opened
                    positions = self.order_manager.get_positions()
                    position_found = any(p.get('ticket') == order_ticket for p in positions)
                    
                    if not position_found and order_ticket > 0:
                        # Position might be delayed, try again after a bit more time
                        import threading
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.warning(f"Position with ticket {order_ticket} not found immediately. Retrying...")
                        
                        def delayed_check():
                            time.sleep(1.5)
                            self.update_positions()
                            # Check again
                            positions_after = self.order_manager.get_positions()
                            found_after = any(p.get('ticket') == order_ticket for p in positions_after)
                            if not found_after:
                                logger.warning(f"Position {order_ticket} still not found after delay. Available positions: {[p.get('ticket') for p in positions_after]}")
                        threading.Thread(target=delayed_check, daemon=True).start()
            else:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"Position {order_ticket} found successfully. Total positions: {len(positions)}")
                        
                elif retcode == 10008:  # TRADE_RETCODE_PLACED - order placed but pending
                    QMessageBox.information(
                        self,
                        "Order Placed",
                        f"Order placed but pending execution\nTicket: {result.get('order', 'N/A')}\nReturn Code: {retcode}\n\nThis is a pending order, not an open position yet."
                    )
                    self.update_positions()
                else:
                    # Order was rejected or failed
                    retcode = result.get('retcode', 0)
                    comment = result.get('comment', 'Unknown error')
                    
                    # Get human-readable error message
                    import MetaTrader5 as mt5
                    error_msg = f"Failed to place order"
                    
                    if retcode > 0:
                        error_msg += f"\n\nReturn Code: {retcode}"
                        error_msg += f"\nMessage: {comment}"
                        
                        # Add common retcode meanings
                        if retcode == 10004:  # TRADE_RETCODE_REQUOTE
                            error_msg += "\n(Requote - price changed, please retry)"
                        elif retcode == 10006:  # TRADE_RETCODE_REJECT
                            error_msg += "\n(Order rejected by broker)"
                        elif retcode == 10007:  # TRADE_RETCODE_CANCEL
                            error_msg += "\n(Order cancelled)"
                        elif retcode == 10008:  # TRADE_RETCODE_PLACED
                            error_msg += "\n(Order placed but not executed yet)"
                        elif retcode == 10009:  # TRADE_RETCODE_DONE
                            error_msg += "\n(Order executed successfully)"
                        elif retcode == 10010:  # TRADE_RETCODE_DONE_PARTIAL
                            error_msg += "\n(Order partially executed)"
                        elif retcode == 10011:  # TRADE_RETCODE_ERROR
                            error_msg += "\n(General error)"
                        elif retcode == 10012:  # TRADE_RETCODE_TIMEOUT
                            error_msg += "\n(Timeout)"
                        elif retcode == 10013:  # TRADE_RETCODE_INVALID
                            error_msg += "\n(Invalid request)"
                        elif retcode == 10014:  # TRADE_RETCODE_INVALID_VOLUME
                            error_msg += "\n(Invalid volume)"
                        elif retcode == 10015:  # TRADE_RETCODE_INVALID_PRICE
                            error_msg += "\n(Invalid price)"
                        elif retcode == 10016:  # TRADE_RETCODE_INVALID_STOPS
                            error_msg += "\n(Invalid stop loss or take profit)"
                        elif retcode == 10017:  # TRADE_RETCODE_TRADE_DISABLED
                            error_msg += "\n(Trading is disabled)"
                        elif retcode == 10018:  # TRADE_RETCODE_MARKET_CLOSED
                            error_msg += "\n(Market is closed)"
                        elif retcode == 10019:  # TRADE_RETCODE_NO_MONEY
                            error_msg += "\n(Insufficient funds)"
                        elif retcode == 10020:  # TRADE_RETCODE_PRICE_CHANGED
                            error_msg += "\n(Price changed, please retry)"
                        elif retcode == 10021:  # TRADE_RETCODE_PRICE_OFF
                            error_msg += "\n(Price is off)"
                        elif retcode == 10022:  # TRADE_RETCODE_INVALID_EXPIRATION
                            error_msg += "\n(Invalid expiration)"
                        elif retcode == 10023:  # TRADE_RETCODE_ORDER_CHANGED
                            error_msg += "\n(Order changed)"
                        elif retcode == 10024:  # TRADE_RETCODE_TOO_MANY_REQUESTS
                            error_msg += "\n(Too many requests)"
                        elif retcode == 10025:  # TRADE_RETCODE_NO_CHANGES
                            error_msg += "\n(No changes)"
                        elif retcode == 10026:  # TRADE_RETCODE_SERVER_DISABLES_AT
                            error_msg += "\n(Server disables AT)"
                        elif retcode == 10027:  # TRADE_RETCODE_CLIENT_DISABLES_AT
                            error_msg += "\n(Client disables AT)"
                        elif retcode == 10028:  # TRADE_RETCODE_LOCKED
                            error_msg += "\n(Order locked)"
                        elif retcode == 10029:  # TRADE_RETCODE_FROZEN
                            error_msg += "\n(Order frozen)"
                        elif retcode == 10030:  # TRADE_RETCODE_INVALID_FILL
                            error_msg += "\n(Invalid fill)"
                        elif retcode == 10031:  # TRADE_RETCODE_CONNECTION
                            error_msg += "\n(Connection error)"
                        elif retcode == 10032:  # TRADE_RETCODE_ONLY_REAL
                            error_msg += "\n(Only real accounts allowed)"
                        elif retcode == 10033:  # TRADE_RETCODE_LIMIT_ORDERS
                            error_msg += "\n(Limit orders reached)"
                        elif retcode == 10034:  # TRADE_RETCODE_LIMIT_VOLUME
                            error_msg += "\n(Volume limit reached)"
                        elif retcode == 10035:  # TRADE_RETCODE_INVALID_ORDER
                            error_msg += "\n(Invalid order)"
                        elif retcode == 10036:  # TRADE_RETCODE_POSITION_CLOSED
                            error_msg += "\n(Position already closed)"
                    
                    QMessageBox.critical(self, "Error", error_msg)
            else:
                # No result returned (None) - this means order_send returned None
                # This usually means a connection issue or MT5 error
                import MetaTrader5 as mt5
                error_code = mt5.last_error()
                error_msg = f"Failed to place order"
                
                # Only show last_error if it's actually an error (code != 0 and != 1)
                # Error code 1 with "Success" is misleading - ignore it
                if error_code[0] != 0 and error_code[0] != 1:
                    error_msg += f"\n\nError Code: {error_code[0]}\nError: {error_code[1]}"
                elif error_code[0] == 1 and "success" not in str(error_code[1]).lower():
                    # Only show if it's not the misleading "Success" message
                    error_msg += f"\n\nError Code: {error_code[0]}\nError: {error_code[1]}"
                else:
                    error_msg += "\n\nNo result returned from MT5. Possible causes:"
                    error_msg += "\n- Connection issue with MT5"
                    error_msg += "\n- Trading disabled on account"
                    error_msg += "\n- Invalid order parameters"
                    error_msg += "\n- Market closed"
                    error_msg += "\n\nPlease check your MT5 connection and account status."
                
                QMessageBox.critical(self, "Error", error_msg)
    
    def update_positions(self):
        """Update positions table"""
        positions = self.order_manager.get_positions()
        
        self.positions_table.setRowCount(len(positions))
        
        total_profit = 0.0
        total_margin = 0.0
        
        for row, pos in enumerate(positions):
            # Ticket
            self.positions_table.setItem(row, 0, QTableWidgetItem(str(pos['ticket'])))
            
            # Name (extract from comment if it's a strategy trade)
            strategy_name = "--"
            comment = pos.get('comment', '')
            if comment and 'Strategy:' in comment:
                strategy_name = comment.replace('Strategy:', '').strip()
            elif comment:
                strategy_name = comment
            self.positions_table.setItem(row, 1, QTableWidgetItem(strategy_name))
            
            # Symbol
            self.positions_table.setItem(row, 2, QTableWidgetItem(pos['symbol']))
            
            # Type with enhanced styling
            pos_type = "BUY" if pos['type'] == 0 else "SELL"
            type_item = QTableWidgetItem(pos_type)
            if pos['type'] == 0:  # BUY
                type_item.setForeground(QColor("#4CAF50"))
                type_item.setBackground(QColor("#1B5E20"))
            else:  # SELL
                type_item.setForeground(QColor("#F44336"))
                type_item.setBackground(QColor("#B71C1C"))
            type_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            self.positions_table.setItem(row, 3, type_item)
            
            # Volume
            self.positions_table.setItem(row, 4, QTableWidgetItem(f"{pos['volume']:.2f}"))
            
            # Price Open
            self.positions_table.setItem(row, 5, QTableWidgetItem(f"{pos['price_open']:.5f}"))
            
            # Price Current
            self.positions_table.setItem(row, 6, QTableWidgetItem(f"{pos['price_current']:.5f}"))
            
            # Stop Loss
            sl = pos.get('sl', 0.0)
            sl_text = f"{sl:.5f}" if sl > 0 else "--"
            self.positions_table.setItem(row, 7, QTableWidgetItem(sl_text))
            
            # Take Profit
            tp = pos.get('tp', 0.0)
            tp_text = f"{tp:.5f}" if tp > 0 else "--"
            self.positions_table.setItem(row, 8, QTableWidgetItem(tp_text))
            
            # Profit with enhanced color coding
            profit = pos.get('profit', 0.0)
            total_profit += profit
            profit_item = QTableWidgetItem(f"{profit:.2f}")
            if profit >= 0:
                profit_item.setForeground(QColor("#4CAF50"))  # Bright green
                profit_item.setBackground(QColor("#1B5E20"))  # Dark green background
            else:
                profit_item.setForeground(QColor("#F44336"))  # Bright red
                profit_item.setBackground(QColor("#B71C1C"))  # Dark red background
            profit_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            self.positions_table.setItem(row, 9, profit_item)
            
            # P&L %
            price_open = pos.get('price_open', 0.0)
            price_current = pos.get('price_current', 0.0)
            if price_open > 0:
                if pos['type'] == 0:  # BUY
                    pnl_pct = ((price_current - price_open) / price_open) * 100
                else:  # SELL
                    pnl_pct = ((price_open - price_current) / price_open) * 100
                
                pnl_item = QTableWidgetItem(f"{pnl_pct:.2f}%")
                if pnl_pct >= 0:
                    pnl_item.setForeground(QColor("#4CAF50"))
                    pnl_item.setBackground(QColor("#1B5E20"))
                else:
                    pnl_item.setForeground(QColor("#F44336"))
                    pnl_item.setBackground(QColor("#B71C1C"))
                pnl_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
                self.positions_table.setItem(row, 10, pnl_item)
            else:
                self.positions_table.setItem(row, 10, QTableWidgetItem("--"))
            
            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            
            modify_btn = QPushButton("Modify")
            modify_btn.setMaximumWidth(60)
            modify_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 3px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            modify_btn.clicked.connect(lambda checked, p=pos: self.modify_position(p))
            action_layout.addWidget(modify_btn)
            
            partial_btn = QPushButton("Partial")
            partial_btn.setMaximumWidth(60)
            partial_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    border: none;
                    padding: 3px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
            partial_btn.clicked.connect(lambda checked, p=pos: self.partial_close_position(p))
            action_layout.addWidget(partial_btn)
            
            close_btn = QPushButton("Close")
            close_btn.setMaximumWidth(60)
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F44336;
                    color: white;
                    border: none;
                    padding: 3px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #D32F2F;
                }
            """)
            close_btn.clicked.connect(lambda checked, t=pos['ticket']: self.close_position(t))
            action_layout.addWidget(close_btn)
            
            self.positions_table.setCellWidget(row, 11, action_widget)
            
            # Calculate margin (simplified)
            total_margin += pos.get('volume', 0.0) * 1000  # Simplified calculation
        
        # Update summary
        account_info = self.mt5.get_account_info()
        currency = account_info.get('currency', 'USD') if account_info else 'USD'
        
        self.total_positions_label.setText(f"Positions: {len(positions)}")
        
        total_profit_text = f"Total P&L: {total_profit:.2f} {currency}"
        if total_profit >= 0:
            color = "#4CAF50"
        else:
            color = "#f44336"
        self.total_profit_label.setText(total_profit_text)
        self.total_profit_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
        self.margin_used_label.setText(f"Margin Used: {total_margin:.2f} {currency}")
        
        self.update_account_info()
    
    def modify_position(self, position: Dict):
        """Modify position SL/TP"""
        dialog = ModifyPositionDialog(position, self)
        if dialog.exec():
            sl, tp = dialog.get_values()
            ticket = position.get('ticket')
            if self.order_manager.modify_position(ticket, sl, tp):
                QMessageBox.information(self, "Success", "Position modified successfully")
                self.update_positions()
            else:
                QMessageBox.critical(self, "Error", "Failed to modify position")
    
    def partial_close_position(self, position: Dict):
        """Partially close a position"""
        dialog = PartialCloseDialog(position, self)
        if dialog.exec():
            volume = dialog.get_volume()
            ticket = position.get('ticket')
            if self.order_manager.close_position_partial(ticket, volume):
                QMessageBox.information(self, "Success", f"Partially closed {volume} lots")
                self.update_positions()
            else:
                QMessageBox.critical(self, "Error", "Failed to partially close position")
    
    def close_position(self, ticket: int):
        """Close a position"""
        reply = QMessageBox.question(
            self,
            "Confirm Close",
            f"Close position {ticket}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.order_manager.close_position(ticket):
                QMessageBox.information(self, "Success", "Position closed")
                self.update_positions()
            else:
                QMessageBox.critical(self, "Error", "Failed to close position")
    
    def close_all_positions(self):
        """Close all positions"""
        reply = QMessageBox.question(
            self,
            "Confirm Close All",
            "Close all open positions?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            count = self.order_manager.close_all_positions()
            QMessageBox.information(self, "Success", f"Closed {count} positions")
            self.update_positions()
    
    def update_symbol_list(self, symbols: list):
        """Update symbol list in quick trade widget"""
        self.quick_trade.update_symbol_list(symbols)
    
    def update_risk_calculator(self):
        """Update risk calculator when SL/TP or volume changes"""
        symbol = self.quick_trade.current_symbol
        if not symbol:
            return
        
        # Get current prices
        tick = self.mt5.get_tick(symbol)
        if not tick:
            return
        
        # Get entry price (use ask for BUY, bid for SELL - default to ask)
        entry_price = tick.get('ask', 0.0)
        if not entry_price:
            entry_price = tick.get('bid', 0.0)
        
        if entry_price == 0:
            return
        
        # Get SL and TP values
        sl = self.sl_spin.value()
        tp = self.tp_spin.value()
        
        # Use SL if set, otherwise use TP to calculate risk
        if sl > 0:
            stop_loss = sl
            order_type = "BUY"  # Default, will adjust based on SL position
            # Determine order type based on SL position
            if sl < entry_price:
                order_type = "BUY"
            else:
                order_type = "SELL"
        elif tp > 0:
            # If no SL, estimate from TP (assuming 1:2 ratio)
            stop_loss = entry_price - (tp - entry_price) / 2.0 if tp > entry_price else entry_price + (entry_price - tp) / 2.0
            order_type = "BUY" if tp > entry_price else "SELL"
        else:
            # No SL or TP set, can't calculate
            return
        
        # Get volume
        volume = self.quick_trade.get_lot_size()
        
        # Calculate and display risk
        self.risk_calculator.calculate_risk(symbol, entry_price, stop_loss, volume, order_type)
    
    def update_risk_calculator(self):
        """Update risk calculator when SL/TP or symbol/volume changes"""
        symbol = self.quick_trade.current_symbol
        if not symbol:
            self.risk_calculator.risk_amount_label.setText("--")
            self.risk_calculator.potential_profit_label.setText("--")
            self.risk_calculator.potential_loss_label.setText("--")
            return
        
        # Get current prices
        tick = self.mt5.get_tick(symbol)
        if not tick or 'ask' not in tick or 'bid' not in tick:
            self.risk_calculator.risk_amount_label.setText("--")
            self.risk_calculator.potential_profit_label.setText("--")
            self.risk_calculator.potential_loss_label.setText("--")
            return
        
        # Determine order type (default to BUY for calculation)
        entry_price = tick['ask']  # Use ask for BUY
        sl = self.sl_spin.value()
        tp = self.tp_spin.value()
        volume = self.quick_trade.get_lot_size()
        
        # Only calculate if we have SL
        if sl > 0:
            # Use SL to calculate risk
            self.risk_calculator.calculate_risk(symbol, entry_price, sl, volume, "BUY", tp)
        else:
            # Clear if no SL
            self.risk_calculator.risk_amount_label.setText("--")
            self.risk_calculator.potential_profit_label.setText("--")
            self.risk_calculator.potential_loss_label.setText("--")
    
    def on_settings_changed(self, settings: Dict):
        """Handle settings change"""
        # Update quick trade widget with new lot size
        lot_size = settings.get('lot_size', 0.01)
        self.quick_trade.custom_lot_spin.setValue(lot_size)
        
        # Update risk manager
        risk_per_trade = settings.get('risk_per_trade', 2.0) / 100.0  # Convert to decimal
        self.risk_manager.max_risk_per_trade = risk_per_trade
    
    def on_trade_symbol_changed(self, symbol: str):
        """Handle symbol change in trade panel - ensure symbol is in data feed"""
        symbol = symbol.strip()
        if symbol and self.data_feed:
            # Check if symbol is in data feed (case-insensitive)
            symbol_upper = symbol.upper()
            symbol_in_feed = False
            for feed_symbol in self.data_feed.symbols:
                if feed_symbol.upper() == symbol_upper:
                    symbol_in_feed = True
                    break
            
            # Add to data feed if not present
            if not symbol_in_feed:
                self.data_feed.add_symbol(symbol)
