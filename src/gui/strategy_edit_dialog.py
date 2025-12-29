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
from ..strategy.ema_strategy import EMAStrategy
from ..indicators import SMA, EMA, RSI, MACD
from ..indicators.vwap import VWAP
from ..indicators.volume import Volume


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
        
        # Indicators Section
        indicators_group = QGroupBox("Indicators")
        indicators_layout = QVBoxLayout()
        
        self.indicators_list = QListWidget()
        self.indicators_list.setMaximumHeight(150)
        indicators_layout.addWidget(self.indicators_list)
        
        # Indicator buttons
        indicator_btn_layout = QHBoxLayout()
        self.add_indicator_btn = QPushButton("Add Indicator")
        self.add_indicator_btn.clicked.connect(self.add_indicator)
        indicator_btn_layout.addWidget(self.add_indicator_btn)
        
        self.edit_indicator_btn = QPushButton("Edit Selected")
        self.edit_indicator_btn.clicked.connect(self.edit_indicator)
        indicator_btn_layout.addWidget(self.edit_indicator_btn)
        
        self.remove_indicator_btn = QPushButton("Remove Selected")
        self.remove_indicator_btn.clicked.connect(self.remove_indicator)
        indicator_btn_layout.addWidget(self.remove_indicator_btn)
        
        indicators_layout.addLayout(indicator_btn_layout)
        indicators_group.setLayout(indicators_layout)
        content_layout.addWidget(indicators_group)
        
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
        
        # Enable/Disable Stop Loss
        self.enable_sl_check = QComboBox()
        self.enable_sl_check.addItem("Enabled", True)
        self.enable_sl_check.addItem("Disabled", False)
        self.enable_sl_check.setCurrentIndex(0)  # Default: Enabled
        self.enable_sl_check.currentIndexChanged.connect(self._on_sl_enabled_changed)
        sl_tp_layout.addRow("Enable Stop Loss:", self.enable_sl_check)
        
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
        
        # Enable/Disable Take Profit
        self.enable_tp_check = QComboBox()
        self.enable_tp_check.addItem("Enabled", True)
        self.enable_tp_check.addItem("Disabled", False)
        self.enable_tp_check.setCurrentIndex(0)  # Default: Enabled
        self.enable_tp_check.currentIndexChanged.connect(self._on_tp_enabled_changed)
        sl_tp_layout.addRow("Enable Take Profit:", self.enable_tp_check)
        
        self.use_ratio_check = QCheckBox("Use 1:2 Ratio")
        sl_tp_layout.addRow("", self.use_ratio_check)
        
        self.tp_value_spin = QDoubleSpinBox()
        self.tp_value_spin.setMinimum(0.0)
        self.tp_value_spin.setMaximum(100000.0)
        self.tp_value_spin.setDecimals(2)
        sl_tp_layout.addRow("TP Value:", self.tp_value_spin)
        
        sl_tp_group.setLayout(sl_tp_layout)
        content_layout.addWidget(sl_tp_group)
        
        # Lot Size Configuration
        lot_size_group = QGroupBox("Lot Size")
        lot_size_layout = QFormLayout()
        
        self.lot_size_spin = QDoubleSpinBox()
        self.lot_size_spin.setMinimum(0.01)
        self.lot_size_spin.setMaximum(100.0)
        self.lot_size_spin.setSingleStep(0.01)
        self.lot_size_spin.setDecimals(2)
        self.lot_size_spin.setValue(0.01)
        self.lot_size_spin.setToolTip("Lot size for this strategy. Leave as default to use global default lot size.")
        lot_size_layout.addRow("Lot Size:", self.lot_size_spin)
        
        lot_size_group.setLayout(lot_size_layout)
        content_layout.addWidget(lot_size_group)
        
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
        
        # Store indicator configurations temporarily
        self.indicators_config = {}  # {name: {type, config}}
    
    def load_strategy(self):
        """Load strategy data into form"""
        # Load indicators
        self.load_indicators()
        
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
        
        # Load Lot Size
        if hasattr(self.strategy, 'lot_size') and self.strategy.lot_size is not None:
            self.lot_size_spin.setValue(self.strategy.lot_size)
        else:
            # Use default from config if strategy doesn't have lot_size set
            from ..config import Config
            config = Config()
            default_lot = config.get('trading.default_lot_size', 0.01)
            self.lot_size_spin.setValue(default_lot)
        
        # Load SL/TP
        sl_enabled = getattr(self.strategy, 'sl_enabled', True)
        tp_enabled = getattr(self.strategy, 'tp_enabled', True)
        self.enable_sl_check.setCurrentIndex(0 if sl_enabled else 1)
        self.enable_tp_check.setCurrentIndex(0 if tp_enabled else 1)
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
    
    def _on_sl_enabled_changed(self, index: int):
        """Handle SL enable/disable toggle"""
        enabled = self.enable_sl_check.currentData()
        self.sl_type_combo.setEnabled(enabled)
        self.sl_value_spin.setEnabled(enabled)

    def _on_tp_enabled_changed(self, index: int):
        """Handle TP enable/disable toggle"""
        enabled = self.enable_tp_check.currentData()
        self.tp_value_spin.setEnabled(enabled)
        self.use_ratio_check.setEnabled(enabled)

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
            # Update indicators
            self.save_indicators()
            
            # Update buy conditions
            if hasattr(self.strategy, 'buy_conditions'):
                self.strategy.buy_conditions.clear()
                self.strategy.buy_conditions.extend(self.buy_conditions_data)
            
            # Update sell conditions
            if hasattr(self.strategy, 'sell_conditions'):
                self.strategy.sell_conditions.clear()
                self.strategy.sell_conditions.extend(self.sell_conditions_data)
            
            # Update Lot Size
            self.strategy.lot_size = self.lot_size_spin.value()
            
            # Update SL/TP
            sl_enabled = self.enable_sl_check.currentData()
            tp_enabled = self.enable_tp_check.currentData()
            
            if sl_enabled:
                self.strategy.sl_type = self.sl_type_combo.currentData()
                self.strategy.sl_value = self.sl_value_spin.value()
            else:
                self.strategy.sl_type = None
                self.strategy.sl_value = 0.0
            
            self.strategy.sl_enabled = sl_enabled
            
            if tp_enabled:
                self.strategy.use_ratio = self.use_ratio_check.isChecked()
                self.strategy.tp_value = self.tp_value_spin.value()
            else:
                self.strategy.tp_value = 0.0
            
            self.strategy.tp_enabled = tp_enabled
            
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
    
    def load_indicators(self):
        """Load current indicators from strategy"""
        self.indicators_config.clear()
        self.indicators_list.clear()
        
        if not hasattr(self.strategy, 'indicators') or not self.strategy.indicators:
            return
        
        # Extract indicator configurations
        for name, indicator in self.strategy.indicators.items():
            ind_type = type(indicator).__name__
            config = {}
            
            if hasattr(indicator, 'period'):
                config['period'] = indicator.period
            elif hasattr(indicator, 'fast_period'):  # MACD
                config['fast_period'] = indicator.fast_period
                config['slow_period'] = indicator.slow_period
                config['signal_period'] = indicator.signal_period
            elif hasattr(indicator, 'session_type'):  # VWAP
                config['session_type'] = indicator.session_type
                config['use_typical_price'] = getattr(indicator, 'use_typical_price', True)
            
            self.indicators_config[name] = {
                'type': ind_type,
                'config': config
            }
        
        # Update list widget
        self.update_indicator_list()
    
    def update_indicator_list(self):
        """Update the indicators list widget"""
        self.indicators_list.clear()
        for name, ind_data in self.indicators_config.items():
            ind_type = ind_data['type']
            config = ind_data['config']
            
            # Format display text
            if ind_type in ['SMA', 'EMA', 'RSI', 'Volume']:
                period = config.get('period', '?')
                display_text = f"{name} ({ind_type}, period: {period})"
            elif ind_type == 'MACD':
                fast = config.get('fast_period', '?')
                slow = config.get('slow_period', '?')
                signal = config.get('signal_period', '?')
                display_text = f"{name} ({ind_type}, {fast}, {slow}, {signal})"
            elif ind_type == 'VWAP':
                session = config.get('session_type', '?')
                display_text = f"{name} ({ind_type}, session: {session})"
            else:
                display_text = f"{name} ({ind_type})"
            
            self.indicators_list.addItem(display_text)
    
    def add_indicator(self):
        """Add a new indicator"""
        from .strategy_indicator_config_dialog import StrategyIndicatorConfigDialog
        
        dialog = StrategyIndicatorConfigDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            config = dialog.get_config()
            name = config['name']
            
            # Check if name already exists
            if name in self.indicators_config:
                QMessageBox.warning(
                    self, "Duplicate Name",
                    f"An indicator with name '{name}' already exists. Please choose a different name."
                )
                return
            
            # Store configuration
            self.indicators_config[name] = {
                'type': config['type'],
                'config': {k: v for k, v in config.items() if k not in ['name', 'type']}
            }
            
            self.update_indicator_list()
    
    def edit_indicator(self):
        """Edit selected indicator"""
        current_row = self.indicators_list.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "No Selection", "Please select an indicator to edit.")
            return
        
        # Get indicator name from list item
        item = self.indicators_list.item(current_row)
        display_text = item.text()
        # Extract name (everything before the first '(')
        name = display_text.split('(')[0].strip()
        
        if name not in self.indicators_config:
            QMessageBox.warning(self, "Error", f"Indicator '{name}' not found in configuration.")
            return
        
        ind_data = self.indicators_config[name]
        ind_type = ind_data['type']
        config = ind_data['config']
        
        from .strategy_indicator_config_dialog import StrategyIndicatorConfigDialog
        
        dialog = StrategyIndicatorConfigDialog(self, name, ind_type, config)
        if dialog.exec() == dialog.DialogCode.Accepted:
            new_config = dialog.get_config()
            new_name = new_config['name']
            
            # If name changed, check for duplicates
            if new_name != name and new_name in self.indicators_config:
                QMessageBox.warning(
                    self, "Duplicate Name",
                    f"An indicator with name '{new_name}' already exists. Please choose a different name."
                )
                return
            
            # Update configuration
            if new_name != name:
                # Remove old entry and add new one
                del self.indicators_config[name]
            
            self.indicators_config[new_name] = {
                'type': new_config['type'],
                'config': {k: v for k, v in new_config.items() if k not in ['name', 'type']}
            }
            
            self.update_indicator_list()
    
    def remove_indicator(self):
        """Remove selected indicator"""
        current_row = self.indicators_list.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "No Selection", "Please select an indicator to remove.")
            return
        
        # Get indicator name from list item
        item = self.indicators_list.item(current_row)
        display_text = item.text()
        name = display_text.split('(')[0].strip()
        
        reply = QMessageBox.question(
            self, "Confirm Removal",
            f"Are you sure you want to remove indicator '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if name in self.indicators_config:
                del self.indicators_config[name]
                self.update_indicator_list()
    
    def save_indicators(self):
        """Save indicator configurations to strategy"""
        # Clear existing indicators
        self.strategy.indicators.clear()
        
        # Handle EMA Strategy special case
        if isinstance(self.strategy, EMAStrategy):
            # EMA Strategy uses ema_periods dict
            ema_periods = {}
            for name, ind_data in self.indicators_config.items():
                if ind_data['type'] == 'EMA':
                    # Extract ema number from name (e.g., "EMA_1" -> "ema_1")
                    if name.startswith('EMA_') or name.startswith('ema_'):
                        ema_key = name.lower()
                        period = ind_data['config'].get('period', 20)
                        ema_periods[ema_key] = period
            
            if ema_periods:
                self.strategy.ema_periods = ema_periods
                self.strategy._rebuild_indicators()
        
        # Handle VWAP Strategy special case
        elif isinstance(self.strategy, VWAPStrategy):
            # VWAP Strategy has built-in VWAP and Volume indicators
            for name, ind_data in self.indicators_config.items():
                if ind_data['type'] == 'VWAP':
                    config = ind_data['config']
                    session_type = config.get('session_type', 'NY')
                    use_typical_price = config.get('use_typical_price', True)
                    vwap_ind = VWAP(session_type=session_type, use_typical_price=use_typical_price)
                    self.strategy.vwap_indicator = vwap_ind
                    self.strategy.add_indicator(name, vwap_ind)
                elif ind_data['type'] == 'Volume':
                    period = ind_data['config'].get('period', 20)
                    volume_ind = Volume(period=period)
                    self.strategy.volume_indicator = volume_ind
                    self.strategy.add_indicator(name, volume_ind)
        
        # Handle other indicators (SMA, RSI, MACD, etc.)
        else:
            for name, ind_data in self.indicators_config.items():
                ind_type = ind_data['type']
                config = ind_data['config']
                
                if ind_type == 'SMA':
                    period = config.get('period', 20)
                    self.strategy.add_indicator(name, SMA(period))
                elif ind_type == 'EMA':
                    period = config.get('period', 20)
                    self.strategy.add_indicator(name, EMA(period))
                elif ind_type == 'RSI':
                    period = config.get('period', 14)
                    self.strategy.add_indicator(name, RSI(period))
                elif ind_type == 'MACD':
                    fast = config.get('fast_period', 12)
                    slow = config.get('slow_period', 26)
                    signal = config.get('signal_period', 9)
                    self.strategy.add_indicator(name, MACD(fast, slow, signal))
                elif ind_type == 'VWAP':
                    session_type = config.get('session_type', 'NY')
                    use_typical_price = config.get('use_typical_price', True)
                    self.strategy.add_indicator(name, VWAP(session_type=session_type, use_typical_price=use_typical_price))
                elif ind_type == 'Volume':
                    period = config.get('period', 20)
                    self.strategy.add_indicator(name, Volume(period=period))

