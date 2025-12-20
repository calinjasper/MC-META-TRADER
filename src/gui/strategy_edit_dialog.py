"""
Strategy Edit Dialog
Allows editing of strategy conditions and settings
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QPushButton, QGroupBox, QListWidget, QListWidgetItem,
                             QMessageBox, QLabel, QScrollArea, QWidget, QComboBox,
                             QDoubleSpinBox, QLineEdit, QCheckBox)
from PyQt6.QtCore import Qt
from typing import Optional
import MetaTrader5 as mt5

from ..strategy.base_strategy import BaseStrategy
from ..strategy.ohlc_price_strategy import OHLCPriceStrategy, OHLCPriceCondition
from ..strategy.vwap_strategy import VWAPStrategy, VWAPCondition
from ..strategy.strategy_persistence import StrategyPersistence


class StrategyEditDialog(QDialog):
    """Dialog for editing strategy configuration"""
    
    def __init__(self, strategy: BaseStrategy, strategy_manager, parent=None):
        super().__init__(parent)
        self.strategy = strategy
        self.strategy_manager = strategy_manager
        self.original_strategy = strategy
        self.setWindowTitle(f"Edit Strategy: {strategy.name}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self.setup_ui()
        self.load_strategy()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)
        
        self.content_layout = content_layout
        
        # Basic Information (read-only)
        basic_group = QGroupBox("Basic Information (Read-Only)")
        basic_layout = QFormLayout()
        
        self.name_label = QLabel(self.strategy.name)
        basic_layout.addRow("Name:", self.name_label)
        
        self.symbol_label = QLabel(self.strategy.symbol)
        basic_layout.addRow("Symbol:", self.symbol_label)
        
        basic_group.setLayout(basic_layout)
        content_layout.addWidget(basic_group)
        
        # Buy Conditions
        buy_group = QGroupBox("Buy Conditions")
        buy_layout = QVBoxLayout()
        
        self.buy_conditions_list = QListWidget()
        buy_layout.addWidget(self.buy_conditions_list)
        
        # Add/Remove buttons for buy conditions
        buy_btn_layout = QHBoxLayout()
        self.add_buy_btn = QPushButton("Add Buy Condition")
        self.add_buy_btn.clicked.connect(self.add_buy_condition_dialog)
        buy_btn_layout.addWidget(self.add_buy_btn)
        
        self.remove_buy_btn = QPushButton("Remove Selected")
        self.remove_buy_btn.clicked.connect(lambda: self.remove_condition(self.buy_conditions_list))
        buy_btn_layout.addWidget(self.remove_buy_btn)
        
        buy_layout.addLayout(buy_btn_layout)
        buy_group.setLayout(buy_layout)
        content_layout.addWidget(buy_group)
        
        # Sell Conditions
        sell_group = QGroupBox("Sell Conditions")
        sell_layout = QVBoxLayout()
        
        self.sell_conditions_list = QListWidget()
        sell_layout.addWidget(self.sell_conditions_list)
        
        # Add/Remove buttons for sell conditions
        sell_btn_layout = QHBoxLayout()
        self.add_sell_btn = QPushButton("Add Sell Condition")
        self.add_sell_btn.clicked.connect(self.add_sell_condition_dialog)
        sell_btn_layout.addWidget(self.add_sell_btn)
        
        self.remove_sell_btn = QPushButton("Remove Selected")
        self.remove_sell_btn.clicked.connect(lambda: self.remove_condition(self.sell_conditions_list))
        sell_btn_layout.addWidget(self.remove_sell_btn)
        
        sell_layout.addLayout(sell_btn_layout)
        sell_group.setLayout(sell_layout)
        content_layout.addWidget(sell_group)
        
        # SL/TP Configuration
        sl_tp_group = QGroupBox("Stop Loss / Take Profit")
        sl_tp_layout = QFormLayout()
        
        self.sl_type_combo = QComboBox()
        self.sl_type_combo.addItem("Price (Pips)", "Price (Pips)")
        self.sl_type_combo.addItem("Price (Points)", "Price (Points)")
        self.sl_type_combo.addItem("Percentage", "Percentage")
        sl_tp_layout.addRow("SL Type:", self.sl_type_combo)
        
        self.sl_value_spin = QDoubleSpinBox()
        self.sl_value_spin.setMinimum(0.0)
        self.sl_value_spin.setMaximum(100000.0)
        self.sl_value_spin.setDecimals(2)
        sl_tp_layout.addRow("SL Value:", self.sl_value_spin)
        
        self.use_ratio_check = QCheckBox("Use 1:2 Ratio")
        sl_tp_layout.addRow("", self.use_ratio_check)
        
        self.tp_value_spin = QDoubleSpinBox()
        self.tp_value_spin.setMinimum(0.0)
        self.tp_value_spin.setMaximum(100000.0)
        self.tp_value_spin.setDecimals(2)
        sl_tp_layout.addRow("TP Value:", self.tp_value_spin)
        
        sl_tp_group.setLayout(sl_tp_layout)
        content_layout.addWidget(sl_tp_group)
        
        # Re-Entry Settings
        reentry_group = QGroupBox("Re-Entry Settings")
        reentry_layout = QFormLayout()
        
        self.reentry_sl_enabled = QCheckBox("Enable Re-Entry on SL")
        reentry_layout.addRow("", self.reentry_sl_enabled)
        
        self.reentry_sl_mode_combo = QComboBox()
        self.reentry_sl_mode_combo.addItem("RE-ASAP", "RE_ASAP")
        self.reentry_sl_mode_combo.addItem("RE-ASAP Reverse", "RE_ASAP_REVERSE")
        self.reentry_sl_mode_combo.addItem("RE-COST", "RE_COST")
        self.reentry_sl_mode_combo.addItem("RE-COST Reverse", "RE_COST_REVERSE")
        reentry_layout.addRow("Re-Entry on SL Mode:", self.reentry_sl_mode_combo)
        
        self.reentry_sl_count_spin = QDoubleSpinBox()
        self.reentry_sl_count_spin.setMinimum(0)
        self.reentry_sl_count_spin.setMaximum(20)
        self.reentry_sl_count_spin.setDecimals(0)
        reentry_layout.addRow("Re-Entry on SL Count:", self.reentry_sl_count_spin)
        
        self.reentry_tp_enabled = QCheckBox("Enable Re-Entry on TP")
        reentry_layout.addRow("", self.reentry_tp_enabled)
        
        self.reentry_tp_mode_combo = QComboBox()
        self.reentry_tp_mode_combo.addItem("RE-ASAP", "RE_ASAP")
        self.reentry_tp_mode_combo.addItem("RE-ASAP Reverse", "RE_ASAP_REVERSE")
        self.reentry_tp_mode_combo.addItem("RE-COST", "RE_COST")
        self.reentry_tp_mode_combo.addItem("RE-COST Reverse", "RE_COST_REVERSE")
        reentry_layout.addRow("Re-Entry on TP Mode:", self.reentry_tp_mode_combo)
        
        self.reentry_tp_count_spin = QDoubleSpinBox()
        self.reentry_tp_count_spin.setMinimum(0)
        self.reentry_tp_count_spin.setMaximum(20)
        self.reentry_tp_count_spin.setDecimals(0)
        reentry_layout.addRow("Re-Entry on TP Count:", self.reentry_tp_count_spin)
        
        reentry_group.setLayout(reentry_layout)
        content_layout.addWidget(reentry_group)
        
        # Advanced Risk Management
        risk_group = QGroupBox("Advanced Risk Management")
        risk_layout = QFormLayout()
        
        self.trailing_sl_enabled = QCheckBox("Enable Trailing Stop-Loss")
        risk_layout.addRow("", self.trailing_sl_enabled)
        
        self.trailing_sl_gap_spin = QDoubleSpinBox()
        self.trailing_sl_gap_spin.setMinimum(0.1)
        self.trailing_sl_gap_spin.setMaximum(10000.0)
        self.trailing_sl_gap_spin.setDecimals(5)
        risk_layout.addRow("Trailing SL Gap:", self.trailing_sl_gap_spin)
        
        self.profit_lock_enabled = QCheckBox("Enable Profit Lock")
        risk_layout.addRow("", self.profit_lock_enabled)
        
        self.profit_lock_trigger_spin = QDoubleSpinBox()
        self.profit_lock_trigger_spin.setMinimum(0.01)
        self.profit_lock_trigger_spin.setMaximum(1000000.0)
        self.profit_lock_trigger_spin.setDecimals(2)
        risk_layout.addRow("Profit Lock Trigger:", self.profit_lock_trigger_spin)
        
        self.profit_lock_value_spin = QDoubleSpinBox()
        self.profit_lock_value_spin.setMinimum(0.01)
        self.profit_lock_value_spin.setMaximum(1000000.0)
        self.profit_lock_value_spin.setDecimals(2)
        risk_layout.addRow("Profit Lock Value:", self.profit_lock_value_spin)
        
        self.profit_trail_step_spin = QDoubleSpinBox()
        self.profit_trail_step_spin.setMinimum(0.0)
        self.profit_trail_step_spin.setMaximum(1000000.0)
        self.profit_trail_step_spin.setDecimals(2)
        risk_layout.addRow("Profit Trail Step:", self.profit_trail_step_spin)
        
        self.profit_trail_amount_spin = QDoubleSpinBox()
        self.profit_trail_amount_spin.setMinimum(0.0)
        self.profit_trail_amount_spin.setMaximum(1000000.0)
        self.profit_trail_amount_spin.setDecimals(2)
        risk_layout.addRow("Profit Trail Amount:", self.profit_trail_amount_spin)
        
        risk_group.setLayout(risk_layout)
        content_layout.addWidget(risk_group)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_strategy)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Store conditions temporarily
        self.buy_conditions_data = []
        self.sell_conditions_data = []
    
    def load_strategy(self):
        """Load strategy data into form"""
        # Load buy conditions
        if hasattr(self.strategy, 'buy_conditions'):
            self.buy_conditions_data = list(self.strategy.buy_conditions)
            for condition in self.buy_conditions_data:
                condition_text = self._format_condition(condition, "BUY")
                self.buy_conditions_list.addItem(condition_text)
        
        # Load sell conditions
        if hasattr(self.strategy, 'sell_conditions'):
            self.sell_conditions_data = list(self.strategy.sell_conditions)
            for condition in self.sell_conditions_data:
                condition_text = self._format_condition(condition, "SELL")
                self.sell_conditions_list.addItem(condition_text)
        
        # Load SL/TP
        self.sl_type_combo.setCurrentText(getattr(self.strategy, 'sl_type', 'Price (Pips)'))
        self.sl_value_spin.setValue(getattr(self.strategy, 'sl_value', 20.0))
        self.use_ratio_check.setChecked(getattr(self.strategy, 'use_ratio', True))
        self.tp_value_spin.setValue(getattr(self.strategy, 'tp_value', 40.0))
        
        # Load Re-Entry
        self.reentry_sl_enabled.setChecked(getattr(self.strategy, 'reentry_on_sl_enabled', False))
        mode = getattr(self.strategy, 'reentry_on_sl_mode', 'RE_ASAP')
        index = self.reentry_sl_mode_combo.findData(mode)
        if index >= 0:
            self.reentry_sl_mode_combo.setCurrentIndex(index)
        self.reentry_sl_count_spin.setValue(getattr(self.strategy, 'reentry_on_sl_count', 0))
        
        self.reentry_tp_enabled.setChecked(getattr(self.strategy, 'reentry_on_tp_enabled', False))
        mode = getattr(self.strategy, 'reentry_on_tp_mode', 'RE_ASAP')
        index = self.reentry_tp_mode_combo.findData(mode)
        if index >= 0:
            self.reentry_tp_mode_combo.setCurrentIndex(index)
        self.reentry_tp_count_spin.setValue(getattr(self.strategy, 'reentry_on_tp_count', 0))
        
        # Load Risk Management
        self.trailing_sl_enabled.setChecked(getattr(self.strategy, 'enable_trailing_sl', False))
        self.trailing_sl_gap_spin.setValue(getattr(self.strategy, 'trailing_sl_gap', 0.0))
        
        self.profit_lock_enabled.setChecked(getattr(self.strategy, 'enable_profit_lock', False))
        self.profit_lock_trigger_spin.setValue(getattr(self.strategy, 'profit_lock_trigger', 0.0))
        self.profit_lock_value_spin.setValue(getattr(self.strategy, 'profit_lock_value', 0.0))
        self.profit_trail_step_spin.setValue(getattr(self.strategy, 'profit_trail_step', 0.0))
        self.profit_trail_amount_spin.setValue(getattr(self.strategy, 'profit_trail_amount', 0.0))
    
    def add_buy_condition_dialog(self):
        """Open dialog to add buy condition"""
        # Validation: Warn if sell conditions already exist (for separate buy/sell legs)
        if len(self.sell_conditions_data) > 0:
            reply = QMessageBox.warning(
                self, "Separate Buy/Sell Legs",
                f"This strategy already has {len(self.sell_conditions_data)} sell condition(s).\n\n"
                "For separate buy/sell legs, strategies should have only buy OR only sell conditions.\n\n"
                "Do you want to continue adding a buy condition?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        condition = self._create_condition_dialog("BUY")
        if condition:
            self.buy_conditions_data.append(condition)
            condition_text = self._format_condition(condition, "BUY")
            self.buy_conditions_list.addItem(condition_text)
    
    def add_sell_condition_dialog(self):
        """Open dialog to add sell condition"""
        # Validation: Warn if buy conditions already exist (for separate buy/sell legs)
        if len(self.buy_conditions_data) > 0:
            reply = QMessageBox.warning(
                self, "Separate Buy/Sell Legs",
                f"This strategy already has {len(self.buy_conditions_data)} buy condition(s).\n\n"
                "For separate buy/sell legs, strategies should have only buy OR only sell conditions.\n\n"
                "Do you want to continue adding a sell condition?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        condition = self._create_condition_dialog("SELL")
        if condition:
            self.sell_conditions_data.append(condition)
            condition_text = self._format_condition(condition, "SELL")
            self.sell_conditions_list.addItem(condition_text)
    
    def _create_condition_dialog(self, signal_type: str):
        """Create a condition using a simple dialog"""
        from PyQt6.QtWidgets import QInputDialog
        
        is_ohlc = isinstance(self.strategy, OHLCPriceStrategy)
        is_vwap = isinstance(self.strategy, VWAPStrategy)
        
        if is_ohlc:
            # For OHLC, create condition with price reference and operator
            price_ref, ok1 = QInputDialog.getItem(
                self, "Price Reference", "Select price reference:",
                ["Current Price", "Previous OHLC"], 0, False
            )
            if not ok1:
                return None
            
            operators = [">", "<", ">=", "<=", "==", "Crosses Above", "Crosses Under"]
            operator, ok2 = QInputDialog.getItem(
                self, "Operator", "Select operator:", operators, 0, False
            )
            if not ok2:
                return None
            
            if price_ref == "Previous OHLC":
                ohlc_fields = ["open", "high", "low", "close"]
                ohlc_field, ok3 = QInputDialog.getItem(
                    self, "OHLC Field", "Select OHLC field:", ohlc_fields, 0, False
                )
                if not ok3:
                    return None
                return OHLCPriceCondition(price_ref, operator, ohlc_field=ohlc_field)
            else:
                return OHLCPriceCondition(price_ref, operator, value=0.0)
        
        elif is_vwap:
            # For VWAP, create condition with VWAP reference
            price_ref, ok1 = QInputDialog.getItem(
                self, "Price Reference", "Select price reference:",
                ["Current Price", "VWAP", "Upper Band", "Lower Band"], 0, False
            )
            if not ok1:
                return None
            
            operators = [">", "<", ">=", "<=", "==", "Crosses Above", "Crosses Under", "Within Band", "Outside Band"]
            operator, ok2 = QInputDialog.getItem(
                self, "Operator", "Select operator:", operators, 0, False
            )
            if not ok2:
                return None
            
            if price_ref in ["Upper Band", "Lower Band"] or operator in ["Within Band", "Outside Band"]:
                std_options = ["1", "1.5", "2"]
                std_val, ok3 = QInputDialog.getItem(
                    self, "Standard Deviation", "Select STD:", std_options, 0, False
                )
                if not ok3:
                    return None
                
                vwap_field = f"{price_ref.lower().replace(' ', '_')}_{std_val}"
                if price_ref == "Upper Band":
                    vwap_field = f"upper_band_{std_val}"
                elif price_ref == "Lower Band":
                    vwap_field = f"lower_band_{std_val}"
                
                return VWAPCondition(price_ref, operator, vwap_field=vwap_field)
            elif price_ref == "VWAP":
                return VWAPCondition(price_ref, operator, vwap_field="vwap")
            else:
                return VWAPCondition(price_ref, operator, value=0.0)
        
        return None
    
    def remove_condition(self, list_widget: QListWidget):
        """Remove selected condition from list"""
        current_row = list_widget.currentRow()
        if current_row >= 0:
            list_widget.takeItem(current_row)
            if list_widget == self.buy_conditions_list:
                self.buy_conditions_data.pop(current_row)
            else:
                self.sell_conditions_data.pop(current_row)
    
    def save_strategy(self):
        """Save strategy changes"""
        try:
            # Update buy conditions
            if hasattr(self.strategy, 'buy_conditions'):
                self.strategy.buy_conditions.clear()
                self.strategy.buy_conditions.extend(self.buy_conditions_data)
            
            # Update sell conditions
            if hasattr(self.strategy, 'sell_conditions'):
                self.strategy.sell_conditions.clear()
                self.strategy.sell_conditions.extend(self.sell_conditions_data)
            
            # Update SL/TP
            self.strategy.sl_type = self.sl_type_combo.currentData()
            self.strategy.sl_value = self.sl_value_spin.value()
            self.strategy.use_ratio = self.use_ratio_check.isChecked()
            self.strategy.tp_value = self.tp_value_spin.value()
            
            # Update Re-Entry
            self.strategy.reentry_on_sl_enabled = self.reentry_sl_enabled.isChecked()
            self.strategy.reentry_on_sl_mode = self.reentry_sl_mode_combo.currentData()
            self.strategy.reentry_on_sl_count = int(self.reentry_sl_count_spin.value())
            
            self.strategy.reentry_on_tp_enabled = self.reentry_tp_enabled.isChecked()
            self.strategy.reentry_on_tp_mode = self.reentry_tp_mode_combo.currentData()
            self.strategy.reentry_on_tp_count = int(self.reentry_tp_count_spin.value())
            
            # Update Risk Management
            self.strategy.enable_trailing_sl = self.trailing_sl_enabled.isChecked()
            self.strategy.trailing_sl_gap = self.trailing_sl_gap_spin.value()
            
            self.strategy.enable_profit_lock = self.profit_lock_enabled.isChecked()
            self.strategy.profit_lock_trigger = self.profit_lock_trigger_spin.value()
            self.strategy.profit_lock_value = self.profit_lock_value_spin.value()
            self.strategy.profit_trail_step = self.profit_trail_step_spin.value()
            self.strategy.profit_trail_amount = self.profit_trail_amount_spin.value()
            
            # Save to disk
            persistence = StrategyPersistence()
            persistence.save_strategy(self.strategy)
            
            QMessageBox.information(self, "Success", "Strategy saved successfully!")
            self.accept()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save strategy: {str(e)}")
    
    def _format_condition(self, condition, signal_type: str) -> str:
        """Format a condition object to human-readable text"""
        if hasattr(condition, 'price_reference'):
            price_ref = condition.price_reference
            operator = condition.operator
            ohlc_field = getattr(condition, 'ohlc_field', None)
            vwap_field = getattr(condition, 'vwap_field', None)
            value = getattr(condition, 'value', None)
            
            if ohlc_field:
                return f"{price_ref} {operator} Previous {ohlc_field.upper()}"
            elif vwap_field:
                field_name = vwap_field.replace('_', ' ').title()
                return f"{price_ref} {operator} {field_name}"
            elif value is not None:
                return f"{price_ref} {operator} {value}"
            else:
                return f"{price_ref} {operator}"
        
        return str(condition)

