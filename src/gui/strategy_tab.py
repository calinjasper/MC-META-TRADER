"""
Strategy Tab - Comprehensive Strategy Builder
Based on STRATEGY_TAB_DOCUMENTATION_CORRECTED.md
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
    QPushButton, QGroupBox, QTimeEdit, QMessageBox,
    QLabel, QScrollArea, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QTime, pyqtSignal
from typing import Dict, Optional, List
import logging
import re
import MetaTrader5 as mt5

from ..data_feed import DataFeed
from ..strategy.strategy_manager import StrategyManager
from ..mt5_connector import MT5Connector
from ..strategy.base_strategy import BaseStrategy
from ..strategy.ohlc_price_strategy import OHLCPriceStrategy, OHLCPriceCondition
from ..strategy.vwap_strategy import VWAPStrategy, VWAPCondition
from ..strategy.smc_strategy import SMCStrategy
from ..strategy.ema_strategy import EMAStrategy, EMACondition
from ..strategy.supertrend_strategy import SuperTrendStrategy
from .system_log_service import system_log_service

logger = logging.getLogger(__name__)


class ConditionRowWidget(QWidget):
    """Single condition row widget with enable, operands, operator, and OR checkbox"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        # Enable checkbox
        self.enable_check = QCheckBox()
        self.enable_check.setChecked(True)
        layout.addWidget(self.enable_check)
        
        # Left operand
        self.left_combo = QComboBox()
        self.left_combo.setMinimumWidth(150)
        layout.addWidget(self.left_combo)
        
        # Operator
        self.operator_combo = QComboBox()
        self.operator_combo.setMinimumWidth(120)
        layout.addWidget(self.operator_combo)
        
        # Right operand
        self.right_combo = QComboBox()
        self.right_combo.setMinimumWidth(150)
        layout.addWidget(self.right_combo)
        
        # OR checkbox (connector to next row)
        self.or_check = QCheckBox("OR")
        self.or_check.setToolTip("If checked, this row connects to next row using OR; otherwise AND")
        layout.addWidget(self.or_check)
        
        layout.addStretch()
    
    def set_operands(self, operands: List[tuple]):
        """Set available operands (list of (text, value) tuples)"""
        current_left = self.left_combo.currentData()
        current_right = self.right_combo.currentData()
        
        self.left_combo.clear()
        self.right_combo.clear()
        
        for text, value in operands:
            self.left_combo.addItem(text, value)
            self.right_combo.addItem(text, value)
        
        # Restore previous selection if possible
        if current_left is not None:
            idx = self.left_combo.findData(current_left)
            if idx >= 0:
                self.left_combo.setCurrentIndex(idx)
        
        if current_right is not None:
            idx = self.right_combo.findData(current_right)
            if idx >= 0:
                self.right_combo.setCurrentIndex(idx)
    
    def set_operators(self, operators: List[tuple]):
        """Set available operators (list of (text, value) tuples)"""
        current = self.operator_combo.currentData()
        
        self.operator_combo.clear()
        for text, value in operators:
            self.operator_combo.addItem(text, value)
        
        if current is not None:
            idx = self.operator_combo.findData(current)
            if idx >= 0:
                self.operator_combo.setCurrentIndex(idx)
    
    def get_data(self) -> Dict:
        """Get condition data"""
        return {
            "enabled": self.enable_check.isChecked(),
            "left_operand": self.left_combo.currentData(),
            "operator": self.operator_combo.currentData(),
            "right_operand": self.right_combo.currentData(),
            "connector": "OR" if self.or_check.isChecked() else "AND"
        }
    
    def set_data(self, data: Dict):
        """Set condition data"""
        self.enable_check.setChecked(data.get("enabled", True))
        
        if "left_operand" in data:
            idx = self.left_combo.findData(data["left_operand"])
            if idx >= 0:
                self.left_combo.setCurrentIndex(idx)
        
        if "operator" in data:
            idx = self.operator_combo.findData(data["operator"])
            if idx >= 0:
                self.operator_combo.setCurrentIndex(idx)
        
        if "right_operand" in data:
            idx = self.right_combo.findData(data["right_operand"])
            if idx >= 0:
                self.right_combo.setCurrentIndex(idx)
        
        self.or_check.setChecked(data.get("connector", "AND") == "OR")


class StrategyTab(QWidget):
    """Comprehensive Strategy Tab based on documentation"""
    
    strategy_saved = pyqtSignal(str)  # Emitted when strategy is saved
    
    def __init__(self, data_feed: DataFeed, strategy_manager: StrategyManager,
                 mt5_connector: MT5Connector):
        super().__init__()
        self.data_feed = data_feed
        self.strategy_manager = strategy_manager
        self.mt5 = mt5_connector
        
        # Track condition rows
        self.buy_condition_rows: List[ConditionRowWidget] = []
        self.sell_condition_rows: List[ConditionRowWidget] = []
        
        # Track editing state
        self.editing_strategy_name: Optional[str] = None
        
        self.setup_ui()
        self.update_symbol_list()
        
        # Connect to data feed for symbol updates
        if hasattr(data_feed, 'tick_received'):
            self.data_feed.tick_received.connect(self._on_tick_received)
    
    def setup_ui(self):
        """Setup the comprehensive UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Form widget
        form_widget = QWidget()
        layout = QVBoxLayout(form_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # 1. Strategy Type
        self._create_strategy_type_section(layout)
        
        # 2. Strategy Name
        self._create_strategy_name_section(layout)
        
        # 3. Strategy Direction
        self._create_strategy_direction_section(layout)
        
        # 4. Basic Information
        self._create_basic_info_section(layout)
        
        # 5. Buy/Sell Conditions
        self._create_conditions_section(layout)
        
        # 6. Strategy-Specific Configurations
        self._create_strategy_config_section(layout)
        
        # 7. Risk Management
        self._create_risk_management_section(layout)
        
        layout.addStretch()
        
        scroll_area.setWidget(form_widget)
        main_layout.addWidget(scroll_area)
        
        # Buttons at bottom
        button_layout = QHBoxLayout()
        
        self.save_btn = QPushButton("Save Strategy")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_btn.clicked.connect(self.save_strategy)
        button_layout.addWidget(self.save_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setMinimumHeight(40)
        self.clear_btn.clicked.connect(self.clear_form)
        button_layout.addWidget(self.clear_btn)
        
        self.load_btn = QPushButton("Load Strategy")
        self.load_btn.setMinimumHeight(40)
        self.load_btn.clicked.connect(self.load_strategy_dialog)
        button_layout.addWidget(self.load_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
    
    def _create_strategy_type_section(self, parent_layout):
        """Create Strategy Type section"""
        group = QGroupBox("1. Strategy Type")
        layout = QFormLayout()
        
        self.strategy_type_combo = QComboBox()
        self.strategy_type_combo.addItem("OHLC Price Strategy", "ohlc")
        self.strategy_type_combo.addItem("VWAP Strategy", "vwap")
        self.strategy_type_combo.addItem("EMA Strategy", "ema")
        self.strategy_type_combo.addItem("SuperTrend Strategy", "supertrend")
        self.strategy_type_combo.addItem("SMC (Smart Money Concepts)", "smc")
        self.strategy_type_combo.addItem("No Strategy", "no_strategy")
        self.strategy_type_combo.currentIndexChanged.connect(self._on_strategy_type_changed)
        layout.addRow("Strategy Type:", self.strategy_type_combo)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def _create_strategy_name_section(self, parent_layout):
        """Create Strategy Name section"""
        group = QGroupBox("2. Strategy Name")
        layout = QFormLayout()
        
        self.strategy_name_input = QLineEdit()
        self.strategy_name_input.setPlaceholderText("e.g., EMA_Crossover_EURUSD_M1")
        self.strategy_name_input.textChanged.connect(self._validate_strategy_name)
        layout.addRow("Strategy Name:", self.strategy_name_input)
        
        self.strategy_name_error_label = QLabel("")
        self.strategy_name_error_label.setStyleSheet("color: red; font-size: 11px;")
        layout.addRow("", self.strategy_name_error_label)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def _create_strategy_direction_section(self, parent_layout):
        """Create Strategy Direction section"""
        group = QGroupBox("3. Strategy Direction")
        layout = QFormLayout()
        
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("Long & Short", "both")
        self.direction_combo.addItem("Long-only", "long")
        self.direction_combo.addItem("Short-only", "short")
        self.direction_combo.currentIndexChanged.connect(self._on_direction_changed)
        layout.addRow("Direction:", self.direction_combo)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def _create_basic_info_section(self, parent_layout):
        """Create Basic Information section"""
        group = QGroupBox("4. Basic Information")
        layout = QFormLayout()
        
        # Symbol
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.setPlaceholderText("Select or enter symbol")
        layout.addRow("Symbol:", self.symbol_combo)
        
        # Timeframe
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItem("M1 (1 Minute)", mt5.TIMEFRAME_M1)
        self.timeframe_combo.addItem("M5 (5 Minutes)", mt5.TIMEFRAME_M5)
        self.timeframe_combo.addItem("M15 (15 Minutes)", mt5.TIMEFRAME_M15)
        self.timeframe_combo.addItem("M30 (30 Minutes)", mt5.TIMEFRAME_M30)
        self.timeframe_combo.addItem("H1 (1 Hour)", mt5.TIMEFRAME_H1)
        self.timeframe_combo.addItem("H4 (4 Hours)", mt5.TIMEFRAME_H4)
        self.timeframe_combo.addItem("D1 (Daily)", mt5.TIMEFRAME_D1)
        layout.addRow("Timeframe:", self.timeframe_combo)
        
        # Lot Size
        self.lot_size_spin = QDoubleSpinBox()
        self.lot_size_spin.setMinimum(0.01)
        self.lot_size_spin.setMaximum(100.0)
        self.lot_size_spin.setSingleStep(0.01)
        self.lot_size_spin.setDecimals(2)
        self.lot_size_spin.setValue(0.01)
        self.lot_size_spin.setToolTip("0.01 = 1 micro lot, 0.10 = 1 mini lot. Leave at 0.01 to use global default.")
        layout.addRow("Lot Size:", self.lot_size_spin)
        
        # Session Type
        self.session_type_combo = QComboBox()
        layout.addRow("Session Type:", self.session_type_combo)
        self._update_session_type_options()
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def _create_conditions_section(self, parent_layout):
        """Create Buy/Sell Conditions section"""
        # Buy Conditions
        self.buy_group = QGroupBox("5. Buy Conditions")
        buy_layout = QVBoxLayout()
        
        buy_header = QHBoxLayout()
        buy_header.addWidget(QLabel("Enable"))
        buy_header.addWidget(QLabel("Left Operand"))
        buy_header.addWidget(QLabel("Operator"))
        buy_header.addWidget(QLabel("Right Operand"))
        buy_header.addWidget(QLabel("OR"))
        buy_header.addStretch()
        buy_layout.addLayout(buy_header)
        
        self.buy_conditions_container = QWidget()
        self.buy_conditions_layout = QVBoxLayout(self.buy_conditions_container)
        self.buy_conditions_layout.setContentsMargins(0, 0, 0, 0)
        self.buy_conditions_layout.setSpacing(5)
        
        buy_scroll = QScrollArea()
        buy_scroll.setWidget(self.buy_conditions_container)
        buy_scroll.setWidgetResizable(True)
        buy_scroll.setMaximumHeight(200)
        buy_layout.addWidget(buy_scroll)
        
        buy_buttons = QHBoxLayout()
        add_buy_btn = QPushButton("Add Buy Condition")
        add_buy_btn.clicked.connect(lambda: self._add_condition_row(True))
        buy_buttons.addWidget(add_buy_btn)
        
        remove_buy_btn = QPushButton("Remove Last")
        remove_buy_btn.clicked.connect(lambda: self._remove_condition_row(True))
        buy_buttons.addWidget(remove_buy_btn)
        buy_buttons.addStretch()
        buy_layout.addLayout(buy_buttons)
        
        self.buy_group.setLayout(buy_layout)
        parent_layout.addWidget(self.buy_group)
        
        # Sell Conditions
        self.sell_group = QGroupBox("6. Sell Conditions")
        sell_layout = QVBoxLayout()
        
        sell_header = QHBoxLayout()
        sell_header.addWidget(QLabel("Enable"))
        sell_header.addWidget(QLabel("Left Operand"))
        sell_header.addWidget(QLabel("Operator"))
        sell_header.addWidget(QLabel("Right Operand"))
        sell_header.addWidget(QLabel("OR"))
        sell_header.addStretch()
        sell_layout.addLayout(sell_header)
        
        self.sell_conditions_container = QWidget()
        self.sell_conditions_layout = QVBoxLayout(self.sell_conditions_container)
        self.sell_conditions_layout.setContentsMargins(0, 0, 0, 0)
        self.sell_conditions_layout.setSpacing(5)
        
        sell_scroll = QScrollArea()
        sell_scroll.setWidget(self.sell_conditions_container)
        sell_scroll.setWidgetResizable(True)
        sell_scroll.setMaximumHeight(200)
        sell_layout.addWidget(sell_scroll)
        
        sell_buttons = QHBoxLayout()
        add_sell_btn = QPushButton("Add Sell Condition")
        add_sell_btn.clicked.connect(lambda: self._add_condition_row(False))
        sell_buttons.addWidget(add_sell_btn)
        
        remove_sell_btn = QPushButton("Remove Last")
        remove_sell_btn.clicked.connect(lambda: self._remove_condition_row(False))
        sell_buttons.addWidget(remove_sell_btn)
        sell_buttons.addStretch()
        sell_layout.addLayout(sell_buttons)
        
        self.sell_group.setLayout(sell_layout)
        parent_layout.addWidget(self.sell_group)
        
        # Initialize with one row each
        self._add_condition_row(True)
        self._add_condition_row(False)
    
    def _create_strategy_config_section(self, parent_layout):
        """Create strategy-specific configuration section"""
        self.config_group = QGroupBox("7. Strategy-Specific Configuration")
        self.config_layout = QFormLayout()
        self.config_group.setLayout(self.config_layout)
        parent_layout.addWidget(self.config_group)
        self._update_strategy_config_section()
    
    def _create_risk_management_section(self, parent_layout):
        """Create Risk Management section"""
        group = QGroupBox("8. Risk Management")
        layout = QVBoxLayout()
        
        # Stop Loss / Take Profit
        sl_tp_group = QGroupBox("Stop Loss / Take Profit")
        sl_tp_layout = QFormLayout()
        
        self.sl_type_combo = QComboBox()
        self.sl_type_combo.addItem("Price (Points)", "points")
        sl_tp_layout.addRow("SL Type:", self.sl_type_combo)
        
        self.sl_value_spin = QDoubleSpinBox()
        self.sl_value_spin.setMinimum(0.0)
        self.sl_value_spin.setMaximum(100000.0)
        self.sl_value_spin.setDecimals(2)
        self.sl_value_spin.setValue(20.0)
        sl_tp_layout.addRow("Stop Loss (points):", self.sl_value_spin)
        
        self.tp_value_spin = QDoubleSpinBox()
        self.tp_value_spin.setMinimum(0.0)
        self.tp_value_spin.setMaximum(100000.0)
        self.tp_value_spin.setDecimals(2)
        self.tp_value_spin.setValue(40.0)
        sl_tp_layout.addRow("Take Profit (points):", self.tp_value_spin)
        
        sl_tp_group.setLayout(sl_tp_layout)
        layout.addWidget(sl_tp_group)
        
        # Trailing Stop-Loss
        trailing_group = QGroupBox("Trailing Stop-Loss")
        trailing_layout = QFormLayout()
        
        self.enable_trailing_sl_check = QCheckBox("Enable Trailing SL")
        trailing_layout.addRow(self.enable_trailing_sl_check)
        
        self.trailing_sl_gap_spin = QDoubleSpinBox()
        self.trailing_sl_gap_spin.setMinimum(0.1)
        self.trailing_sl_gap_spin.setMaximum(10000.0)
        self.trailing_sl_gap_spin.setDecimals(2)
        self.trailing_sl_gap_spin.setValue(1.0)
        trailing_layout.addRow("SL Gap (points):", self.trailing_sl_gap_spin)
        
        trailing_group.setLayout(trailing_layout)
        layout.addWidget(trailing_group)
        
        # Profit Lock + Trailing
        profit_lock_group = QGroupBox("Profit Lock + Trailing")
        profit_lock_layout = QFormLayout()
        
        self.enable_profit_lock_check = QCheckBox("Enable Profit Lock")
        profit_lock_layout.addRow(self.enable_profit_lock_check)
        
        self.profit_lock_trigger_spin = QDoubleSpinBox()
        self.profit_lock_trigger_spin.setMinimum(0.01)
        self.profit_lock_trigger_spin.setMaximum(1000000.0)
        self.profit_lock_trigger_spin.setDecimals(2)
        self.profit_lock_trigger_spin.setValue(100.0)
        profit_lock_layout.addRow("Profit Lock Trigger ($):", self.profit_lock_trigger_spin)
        
        self.profit_lock_value_spin = QDoubleSpinBox()
        self.profit_lock_value_spin.setMinimum(0.01)
        self.profit_lock_value_spin.setMaximum(1000000.0)
        self.profit_lock_value_spin.setDecimals(2)
        self.profit_lock_value_spin.setValue(50.0)
        profit_lock_layout.addRow("Minimum Profit to Lock ($):", self.profit_lock_value_spin)
        
        self.profit_trail_step_spin = QDoubleSpinBox()
        self.profit_trail_step_spin.setMinimum(0.0)
        self.profit_trail_step_spin.setMaximum(1000000.0)
        self.profit_trail_step_spin.setDecimals(2)
        self.profit_trail_step_spin.setValue(100.0)
        profit_lock_layout.addRow("Trail Step ($):", self.profit_trail_step_spin)
        
        self.profit_trail_amount_spin = QDoubleSpinBox()
        self.profit_trail_amount_spin.setMinimum(0.0)
        self.profit_trail_amount_spin.setMaximum(1000000.0)
        self.profit_trail_amount_spin.setDecimals(2)
        self.profit_trail_amount_spin.setValue(50.0)
        profit_lock_layout.addRow("Trail Amount ($):", self.profit_trail_amount_spin)
        
        profit_lock_group.setLayout(profit_lock_layout)
        layout.addWidget(profit_lock_group)
        
        # Trail Wait & Trade (W&T)
        wt_group = QGroupBox("Trail Wait & Trade (W&T)")
        wt_layout = QFormLayout()
        
        self.enable_wt_check = QCheckBox("Enable W&T")
        wt_layout.addRow(self.enable_wt_check)
        
        self.wt_value_spin = QDoubleSpinBox()
        self.wt_value_spin.setMinimum(-1000000.0)
        self.wt_value_spin.setMaximum(1000000.0)
        self.wt_value_spin.setDecimals(2)
        self.wt_value_spin.setValue(-15.0)
        wt_layout.addRow("W&T Value (points):", self.wt_value_spin)
        
        self.wt_percentage_check = QCheckBox("Use percentage (%) instead of points")
        wt_layout.addRow(self.wt_percentage_check)
        
        wt_group.setLayout(wt_layout)
        layout.addWidget(wt_group)
        
        # Position Management
        position_group = QGroupBox("Position Management")
        position_layout = QFormLayout()
        
        self.preserve_position_check = QCheckBox("Preserve Position")
        self.preserve_position_check.setToolTip("Prevents duplicate positions (max 1 BUY and 1 SELL per strategy per symbol)")
        position_layout.addRow(self.preserve_position_check)
        
        self.sl_reentry_enabled_check = QCheckBox("Enable Re-Entry on SL")
        position_layout.addRow(self.sl_reentry_enabled_check)
        
        self.sl_reentry_mode_combo = QComboBox()
        self.sl_reentry_mode_combo.addItem("RE-ASAP", "RE_ASAP")
        self.sl_reentry_mode_combo.addItem("RE-ASAP Reverse", "RE_ASAP_REVERSE")
        self.sl_reentry_mode_combo.addItem("RE-COST", "RE_COST")
        self.sl_reentry_mode_combo.addItem("RE-COST Reverse", "RE_COST_REVERSE")
        position_layout.addRow("SL Re-Entry Mode:", self.sl_reentry_mode_combo)
        
        self.sl_reentry_count_spin = QSpinBox()
        self.sl_reentry_count_spin.setMinimum(0)
        self.sl_reentry_count_spin.setMaximum(20)
        self.sl_reentry_count_spin.setValue(0)
        position_layout.addRow("SL Re-Entry Max Count:", self.sl_reentry_count_spin)
        
        self.tp_reentry_enabled_check = QCheckBox("Enable Re-Entry on TP")
        position_layout.addRow(self.tp_reentry_enabled_check)
        
        self.tp_reentry_mode_combo = QComboBox()
        self.tp_reentry_mode_combo.addItem("RE-ASAP", "RE_ASAP")
        self.tp_reentry_mode_combo.addItem("RE-ASAP Reverse", "RE_ASAP_REVERSE")
        self.tp_reentry_mode_combo.addItem("RE-COST", "RE_COST")
        self.tp_reentry_mode_combo.addItem("RE-COST Reverse", "RE_COST_REVERSE")
        position_layout.addRow("TP Re-Entry Mode:", self.tp_reentry_mode_combo)
        
        self.tp_reentry_count_spin = QSpinBox()
        self.tp_reentry_count_spin.setMinimum(0)
        self.tp_reentry_count_spin.setMaximum(20)
        self.tp_reentry_count_spin.setValue(0)
        position_layout.addRow("TP Re-Entry Max Count:", self.tp_reentry_count_spin)
        
        position_group.setLayout(position_layout)
        layout.addWidget(position_group)
        
        # Trading Hours
        hours_group = QGroupBox("Trading Hours")
        hours_layout = QFormLayout()
        
        self.time_enabled_check = QCheckBox("Enable time restrictions")
        hours_layout.addRow(self.time_enabled_check)
        
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setTime(QTime(9, 0))
        hours_layout.addRow("Start Time:", self.start_time_edit)
        
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setTime(QTime(17, 0))
        hours_layout.addRow("End Time:", self.end_time_edit)
        
        hours_group.setLayout(hours_layout)
        layout.addWidget(hours_group)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def _on_strategy_type_changed(self):
        """Handle strategy type change"""
        self._update_session_type_options()
        self._update_strategy_config_section()
        self._update_condition_operands()
        self._update_condition_visibility()
    
    def _on_direction_changed(self):
        """Handle direction change - show/hide condition sections"""
        self._update_condition_visibility()
    
    def _update_condition_visibility(self):
        """Update visibility of buy/sell condition sections based on direction and strategy type"""
        direction = self.direction_combo.currentData()
        strategy_type = self.strategy_type_combo.currentData()
        
        # SuperTrend auto-generates signals - show note but keep sections visible
        if strategy_type == "supertrend":
            self.buy_group.setTitle("5. Buy Conditions (Disabled - SuperTrend auto-generates signals)")
            self.sell_group.setTitle("6. Sell Conditions (Disabled - SuperTrend auto-generates signals)")
        elif strategy_type == "smc":
            self.buy_group.setTitle("5. Buy Conditions (Filters - post-filter BOS/CHoCH signals)")
            self.sell_group.setTitle("6. Sell Conditions (Filters - post-filter BOS/CHoCH signals)")
        else:
            self.buy_group.setTitle("5. Buy Conditions")
            self.sell_group.setTitle("6. Sell Conditions")
        
        # Update visibility based on direction
        if direction == "long":
            self.buy_group.setVisible(True)
            self.sell_group.setVisible(False)
        elif direction == "short":
            self.buy_group.setVisible(False)
            self.sell_group.setVisible(True)
        else:  # both
            self.buy_group.setVisible(True)
            self.sell_group.setVisible(True)
    
    def _update_session_type_options(self):
        """Update session type options based on strategy type"""
        strategy_type = self.strategy_type_combo.currentData()
        current = self.session_type_combo.currentData()
        
        self.session_type_combo.clear()
        
        if strategy_type == "ohlc":
            self.session_type_combo.addItem("Daily (24h Mon–Fri)", "daily")
            self.session_type_combo.addItem("Asian Session (05:30–14:30 IST)", "asian")
            self.session_type_combo.addItem("European Session (13:30–22:30 IST)", "european")
            self.session_type_combo.addItem("US Session (18:30–03:30 IST)", "us")
        elif strategy_type == "vwap":
            self.session_type_combo.addItem("NY Session (18:30–03:30 IST)", "NY")
            self.session_type_combo.addItem("London Session (13:30–22:30 IST)", "London")
            self.session_type_combo.addItem("Asia Session (05:30–14:30 IST)", "Asia")
            self.session_type_combo.addItem("All Sessions", "All")
        else:  # EMA, SuperTrend, SMC, No Strategy
            self.session_type_combo.addItem("All Candles", "All")
        
        # Restore selection if possible
        if current is not None:
            idx = self.session_type_combo.findData(current)
            if idx >= 0:
                self.session_type_combo.setCurrentIndex(idx)
    
    def _update_strategy_config_section(self):
        """Update strategy-specific configuration section"""
        # Clear existing widgets
        while self.config_layout.count():
            child = self.config_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        strategy_type = self.strategy_type_combo.currentData()
        
        if strategy_type == "vwap":
            # VWAP Configuration
            self.vwap_std_bands_input = QLineEdit()
            self.vwap_std_bands_input.setText("1, 1.5, 2")
            self.vwap_std_bands_input.setToolTip("Comma-separated standard deviation bands (e.g., '1, 1.5, 2')")
            self.config_layout.addRow("Standard Deviation Bands:", self.vwap_std_bands_input)
            
            self.vwap_swing_period_spin = QSpinBox()
            self.vwap_swing_period_spin.setMinimum(5)
            self.vwap_swing_period_spin.setMaximum(50)
            self.vwap_swing_period_spin.setValue(10)
            self.config_layout.addRow("Swing Period:", self.vwap_swing_period_spin)
        
        elif strategy_type == "ema":
            # EMA Configuration
            self.ema1_period_spin = QSpinBox()
            self.ema1_period_spin.setMinimum(1)
            self.ema1_period_spin.setMaximum(500)
            self.ema1_period_spin.setValue(20)
            self.config_layout.addRow("EMA 1 Period:", self.ema1_period_spin)
            
            self.ema2_period_spin = QSpinBox()
            self.ema2_period_spin.setMinimum(1)
            self.ema2_period_spin.setMaximum(500)
            self.ema2_period_spin.setValue(50)
            self.config_layout.addRow("EMA 2 Period:", self.ema2_period_spin)
            
            self.ema3_period_spin = QSpinBox()
            self.ema3_period_spin.setMinimum(1)
            self.ema3_period_spin.setMaximum(500)
            self.ema3_period_spin.setValue(100)
            self.config_layout.addRow("EMA 3 Period:", self.ema3_period_spin)
            
            self.ema4_period_spin = QSpinBox()
            self.ema4_period_spin.setMinimum(1)
            self.ema4_period_spin.setMaximum(500)
            self.ema4_period_spin.setValue(200)
            self.config_layout.addRow("EMA 4 Period:", self.ema4_period_spin)
        
        elif strategy_type == "supertrend":
            # SuperTrend Configuration
            self.st_atr_period_spin = QSpinBox()
            self.st_atr_period_spin.setMinimum(1)
            self.st_atr_period_spin.setMaximum(500)
            self.st_atr_period_spin.setValue(10)
            self.config_layout.addRow("ATR Period:", self.st_atr_period_spin)
            
            self.st_atr_multiplier_spin = QDoubleSpinBox()
            self.st_atr_multiplier_spin.setMinimum(0.1)
            self.st_atr_multiplier_spin.setMaximum(50.0)
            self.st_atr_multiplier_spin.setDecimals(1)
            self.st_atr_multiplier_spin.setValue(3.0)
            self.config_layout.addRow("ATR Multiplier:", self.st_atr_multiplier_spin)
            
            self.st_atr_method_combo = QComboBox()
            self.st_atr_method_combo.addItem("ATR (Wilder)", "wilder")
            self.st_atr_method_combo.addItem("SMA(TR)", "sma")
            self.config_layout.addRow("ATR Method:", self.st_atr_method_combo)
        
        elif strategy_type == "smc":
            # SMC Configuration
            self.smc_pivot_left_spin = QSpinBox()
            self.smc_pivot_left_spin.setMinimum(1)
            self.smc_pivot_left_spin.setMaximum(10)
            self.smc_pivot_left_spin.setValue(2)
            self.config_layout.addRow("Pivot Left Bars:", self.smc_pivot_left_spin)
            
            self.smc_pivot_right_spin = QSpinBox()
            self.smc_pivot_right_spin.setMinimum(1)
            self.smc_pivot_right_spin.setMaximum(10)
            self.smc_pivot_right_spin.setValue(2)
            self.config_layout.addRow("Pivot Right Bars:", self.smc_pivot_right_spin)
            
            self.smc_emit_on_combo = QComboBox()
            self.smc_emit_on_combo.addItem("CHoCH only (bias flips)", "CHoCH")
            self.smc_emit_on_combo.addItem("BOS only (continuation)", "BOS")
            self.smc_emit_on_combo.addItem("Both (BOS + CHoCH)", "BOTH")
            self.config_layout.addRow("Emit Signals On:", self.smc_emit_on_combo)
        
        # Hide group if no config needed
        if strategy_type in ["ohlc", "no_strategy"]:
            self.config_group.setVisible(False)
        else:
            self.config_group.setVisible(True)
    
    def _update_condition_operands(self):
        """Update available operands based on strategy type"""
        strategy_type = self.strategy_type_combo.currentData()
        
        # Base operands (always available)
        operands = [
            ("Current Price", "current_price"),
            ("Previous Open", "previous_open"),
            ("Previous High", "previous_high"),
            ("Previous Low", "previous_low"),
            ("Previous Close", "previous_close"),
            ("Open", "open"),
            ("High", "high"),
            ("Low", "low"),
            ("Close", "close"),
            ("(H + L)/2", "hl2"),
            ("(H + L + C)/3", "hlc3"),
            ("(O + H + L + C)/4", "ohlc4"),
        ]
        
        # Add strategy-specific operands
        if strategy_type == "ema":
            # Add EMA fields (will be populated with actual periods from config)
            operands.extend([
                ("EMA_20", "ema_20"),
                ("EMA_50", "ema_50"),
                ("EMA_100", "ema_100"),
                ("EMA_200", "ema_200"),
            ])
        elif strategy_type == "vwap":
            operands.extend([
                ("VWAP", "vwap"),
                ("VWAP Upper 1.0σ", "vwap_upper_1.0"),
                ("VWAP Upper 1.5σ", "vwap_upper_1.5"),
                ("VWAP Upper 2.0σ", "vwap_upper_2.0"),
                ("VWAP Lower 1.0σ", "vwap_lower_1.0"),
                ("VWAP Lower 1.5σ", "vwap_lower_1.5"),
                ("VWAP Lower 2.0σ", "vwap_lower_2.0"),
            ])
        elif strategy_type == "supertrend":
            operands.extend([
                ("SuperTrend Value", "supertrend_value"),
                ("SuperTrend Upper", "supertrend_upper"),
                ("SuperTrend Lower", "supertrend_lower"),
            ])
        elif strategy_type == "smc":
            operands.extend([
                ("SMC Pivot High", "smc_pivot_high"),
                ("SMC Pivot Low", "smc_pivot_low"),
            ])
        
        # Update all condition rows
        operators = [
            ("Greater_Than (>)", ">"),
            ("Lower_Than (<)", "<"),
            ("Equals (==)", "=="),
            ("Crosses Above", "crosses_above"),
            ("Crosses Under", "crosses_under"),
            ("Any_Cross", "any_cross"),
        ]
        
        # Add VWAP-specific operators
        if strategy_type == "vwap":
            operators.extend([
                ("Within_Band", "within_band"),
                ("Outside_Band", "outside_band"),
            ])
        
        for row in self.buy_condition_rows:
            row.set_operands(operands)
            row.set_operators(operators)
        
        for row in self.sell_condition_rows:
            row.set_operands(operands)
            row.set_operators(operators)
    
    def _add_condition_row(self, is_buy: bool):
        """Add a new condition row"""
        row = ConditionRowWidget()
        
        # Set operands and operators
        self._update_condition_operands_for_row(row)
        
        if is_buy:
            self.buy_condition_rows.append(row)
            self.buy_conditions_layout.addWidget(row)
        else:
            self.sell_condition_rows.append(row)
            self.sell_conditions_layout.addWidget(row)
    
    def _update_condition_operands_for_row(self, row: ConditionRowWidget):
        """Update operands for a single row"""
        strategy_type = self.strategy_type_combo.currentData()
        
        operands = [
            ("Current Price", "current_price"),
            ("Previous Open", "previous_open"),
            ("Previous High", "previous_high"),
            ("Previous Low", "previous_low"),
            ("Previous Close", "previous_close"),
            ("Open", "open"),
            ("High", "high"),
            ("Low", "low"),
            ("Close", "close"),
            ("(H + L)/2", "hl2"),
            ("(H + L + C)/3", "hlc3"),
            ("(O + H + L + C)/4", "ohlc4"),
        ]
        
        if strategy_type == "ema":
            operands.extend([
                ("EMA_20", "ema_20"),
                ("EMA_50", "ema_50"),
                ("EMA_100", "ema_100"),
                ("EMA_200", "ema_200"),
            ])
        elif strategy_type == "vwap":
            operands.extend([
                ("VWAP", "vwap"),
                ("VWAP Upper 1.0σ", "vwap_upper_1.0"),
                ("VWAP Upper 1.5σ", "vwap_upper_1.5"),
                ("VWAP Upper 2.0σ", "vwap_upper_2.0"),
                ("VWAP Lower 1.0σ", "vwap_lower_1.0"),
                ("VWAP Lower 1.5σ", "vwap_lower_1.5"),
                ("VWAP Lower 2.0σ", "vwap_lower_2.0"),
            ])
        elif strategy_type == "supertrend":
            operands.extend([
                ("SuperTrend Value", "supertrend_value"),
                ("SuperTrend Upper", "supertrend_upper"),
                ("SuperTrend Lower", "supertrend_lower"),
            ])
        elif strategy_type == "smc":
            operands.extend([
                ("SMC Pivot High", "smc_pivot_high"),
                ("SMC Pivot Low", "smc_pivot_low"),
            ])
        
        operators = [
            ("Greater_Than (>)", ">"),
            ("Lower_Than (<)", "<"),
            ("Equals (==)", "=="),
            ("Crosses Above", "crosses_above"),
            ("Crosses Under", "crosses_under"),
            ("Any_Cross", "any_cross"),
        ]
        
        if strategy_type == "vwap":
            operators.extend([
                ("Within_Band", "within_band"),
                ("Outside_Band", "outside_band"),
            ])
        
        row.set_operands(operands)
        row.set_operators(operators)
    
    def _remove_condition_row(self, is_buy: bool):
        """Remove last condition row"""
        if is_buy:
            if self.buy_condition_rows:
                row = self.buy_condition_rows.pop()
                self.buy_conditions_layout.removeWidget(row)
                row.deleteLater()
        else:
            if self.sell_condition_rows:
                row = self.sell_condition_rows.pop()
                self.sell_conditions_layout.removeWidget(row)
                row.deleteLater()
    
    def _validate_strategy_name(self):
        """Validate strategy name"""
        name = self.strategy_name_input.text().strip()
        
        if not name:
            self.strategy_name_error_label.setText("")
            return
        
        # Check format (alphanumeric, underscores, hyphens)
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            self.strategy_name_error_label.setText("Invalid format. Use only letters, numbers, underscores, and hyphens.")
            return
        
        # Check uniqueness
        if self.strategy_manager.get_strategy(name) is not None:
            if name != self.editing_strategy_name:
                self.strategy_name_error_label.setText("Strategy name already exists.")
                return
        
        self.strategy_name_error_label.setText("")
    
    def update_symbol_list(self):
        """Update symbol combo box"""
        self.symbol_combo.clear()
        
        # Add symbols from data feed
        for symbol in self.data_feed.symbols:
            self.symbol_combo.addItem(symbol)
        
        # Add symbols from MT5 if connected
        if self.mt5 and self.mt5.is_connected():
            try:
                available_symbols = self.mt5.get_available_symbols()
                for symbol in available_symbols:
                    if self.symbol_combo.findText(symbol) == -1:
                        self.symbol_combo.addItem(symbol)
            except Exception as e:
                logger.debug(f"Error getting symbols from MT5: {e}")
    
    def _on_tick_received(self, symbol: str, tick_data: dict):
        """Handle tick received - update symbol list"""
        if self.symbol_combo.findText(symbol) == -1:
            self.symbol_combo.addItem(symbol)
    
    def clear_form(self):
        """Clear the form"""
        self.strategy_type_combo.setCurrentIndex(0)
        self.strategy_name_input.clear()
        self.direction_combo.setCurrentIndex(0)
        self.symbol_combo.setCurrentIndex(-1)
        self.timeframe_combo.setCurrentIndex(0)
        self.lot_size_spin.setValue(0.01)
        
        # Clear conditions
        for row in self.buy_condition_rows[:]:
            self.buy_conditions_layout.removeWidget(row)
            row.deleteLater()
        self.buy_condition_rows.clear()
        
        for row in self.sell_condition_rows[:]:
            self.sell_conditions_layout.removeWidget(row)
            row.deleteLater()
        self.sell_condition_rows.clear()
        
        # Add one row each
        self._add_condition_row(True)
        self._add_condition_row(False)
        
        # Clear risk management
        self.sl_value_spin.setValue(20.0)
        self.tp_value_spin.setValue(40.0)
        self.enable_trailing_sl_check.setChecked(False)
        self.trailing_sl_gap_spin.setValue(1.0)
        self.enable_profit_lock_check.setChecked(False)
        self.enable_wt_check.setChecked(False)
        self.preserve_position_check.setChecked(False)
        self.time_enabled_check.setChecked(False)
        
        self.editing_strategy_name = None
    
    def save_strategy(self):
        """Save the strategy"""
        # Validation
        name = self.strategy_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Please enter a strategy name")
            return
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            QMessageBox.warning(self, "Validation Error", "Strategy name must contain only letters, numbers, underscores, and hyphens")
            return
        
        symbol = self.symbol_combo.currentText().strip()
        if not symbol:
            QMessageBox.warning(self, "Validation Error", "Please select or enter a symbol")
            return
        
        # Check uniqueness
        existing = self.strategy_manager.get_strategy(name)
        if existing and name != self.editing_strategy_name:
            QMessageBox.warning(self, "Validation Error", f"Strategy '{name}' already exists")
            return
        
        # Get strategy type
        strategy_type = self.strategy_type_combo.currentData()
        timeframe = self.timeframe_combo.currentData()
        
        # Create strategy based on type
        try:
            if strategy_type == "ohlc":
                strategy = self._create_ohlc_strategy(name, symbol, timeframe)
            elif strategy_type == "vwap":
                strategy = self._create_vwap_strategy(name, symbol, timeframe)
            elif strategy_type == "ema":
                strategy = self._create_ema_strategy(name, symbol, timeframe)
            elif strategy_type == "supertrend":
                strategy = self._create_supertrend_strategy(name, symbol, timeframe)
            elif strategy_type == "smc":
                strategy = self._create_smc_strategy(name, symbol, timeframe)
            elif strategy_type == "no_strategy":
                strategy = self._create_no_strategy(name, symbol, timeframe)
            else:
                QMessageBox.warning(self, "Error", f"Unknown strategy type: {strategy_type}")
                return
            
            # Apply risk management settings
            self._apply_risk_management(strategy)
            
            # Save to strategy manager
            if self.strategy_manager.add_strategy(strategy):
                # Save to disk
                from ..strategy.strategy_persistence import StrategyPersistence
                persistence = StrategyPersistence()
                if persistence.save_strategy(strategy):
                    QMessageBox.information(self, "Success", f"Strategy '{name}' saved successfully")
                    system_log_service.log("MESSAGE", f"Strategy {name} created", strategy=name)
                    self.strategy_saved.emit(name)
                    self.clear_form()
                else:
                    QMessageBox.warning(self, "Warning", f"Strategy saved but could not write to disk")
            else:
                QMessageBox.warning(self, "Error", f"Could not add strategy '{name}'")
        
        except Exception as e:
            logger.error(f"Error saving strategy: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error saving strategy: {str(e)}")
    
    def _create_ohlc_strategy(self, name: str, symbol: str, timeframe: int) -> OHLCPriceStrategy:
        """Create OHLC Price Strategy"""
        session_type = self.session_type_combo.currentData()
        strategy = OHLCPriceStrategy(name, symbol, session_type, timeframe)
        
        # Add buy conditions
        buy_conditions = self._parse_conditions(self.buy_condition_rows)
        for cond_data in buy_conditions:
            if cond_data["enabled"]:
                condition = OHLCPriceCondition(
                    price_reference='Current Price',
                    operator=cond_data["operator"],
                    left_field=cond_data["left_operand"],
                    right_field=cond_data["right_operand"],
                    connector=cond_data.get("connector", "AND")
                )
                strategy.buy_conditions.append(condition)
        
        # Add sell conditions
        sell_conditions = self._parse_conditions(self.sell_condition_rows)
        for cond_data in sell_conditions:
            if cond_data["enabled"]:
                condition = OHLCPriceCondition(
                    price_reference='Current Price',
                    operator=cond_data["operator"],
                    left_field=cond_data["left_operand"],
                    right_field=cond_data["right_operand"],
                    connector=cond_data.get("connector", "AND")
                )
                strategy.sell_conditions.append(condition)
        
        return strategy
    
    def _create_vwap_strategy(self, name: str, symbol: str, timeframe: int) -> VWAPStrategy:
        """Create VWAP Strategy"""
        session_type = self.session_type_combo.currentData()
        strategy = VWAPStrategy(name, symbol, session_type, timeframe)
        
        # Set VWAP configuration
        if hasattr(self, 'vwap_std_bands_input'):
            bands_str = self.vwap_std_bands_input.text().strip()
            try:
                strategy.std_bands = [float(x.strip()) for x in bands_str.split(',')]
            except:
                strategy.std_bands = [1.0, 1.5, 2.0]
        
        if hasattr(self, 'vwap_swing_period_spin'):
            strategy.swing_period = self.vwap_swing_period_spin.value()
        
        # Add buy/sell conditions
        buy_conditions = self._parse_conditions(self.buy_condition_rows)
        for cond_data in buy_conditions:
            if cond_data["enabled"]:
                condition = VWAPCondition(
                    price_reference='Current Price',
                    operator=cond_data["operator"],
                    left_field=cond_data["left_operand"],
                    right_field=cond_data["right_operand"],
                    connector=cond_data.get("connector", "AND")
                )
                strategy.buy_conditions.append(condition)
        
        sell_conditions = self._parse_conditions(self.sell_condition_rows)
        for cond_data in sell_conditions:
            if cond_data["enabled"]:
                condition = VWAPCondition(
                    price_reference='Current Price',
                    operator=cond_data["operator"],
                    left_field=cond_data["left_operand"],
                    right_field=cond_data["right_operand"],
                    connector=cond_data.get("connector", "AND")
                )
                strategy.sell_conditions.append(condition)
        
        return strategy
    
    def _create_ema_strategy(self, name: str, symbol: str, timeframe: int) -> EMAStrategy:
        """Create EMA Strategy"""
        # Get EMA periods
        ema1 = self.ema1_period_spin.value() if hasattr(self, 'ema1_period_spin') else 20
        ema2 = self.ema2_period_spin.value() if hasattr(self, 'ema2_period_spin') else 50
        ema3 = self.ema3_period_spin.value() if hasattr(self, 'ema3_period_spin') else 100
        ema4 = self.ema4_period_spin.value() if hasattr(self, 'ema4_period_spin') else 200
        
        ema_periods = {
            "ema_1": ema1,
            "ema_2": ema2,
            "ema_3": ema3,
            "ema_4": ema4,
        }
        
        strategy = EMAStrategy(name, symbol, timeframe, ema_periods=ema_periods)
        
        # Add buy/sell conditions
        buy_conditions = self._parse_conditions(self.buy_condition_rows)
        for cond_data in buy_conditions:
            if cond_data["enabled"]:
                condition = EMACondition(
                    price_reference='Current Price',
                    operator=cond_data["operator"],
                    left_field=cond_data["left_operand"],
                    right_field=cond_data["right_operand"],
                    connector=cond_data.get("connector", "AND")
                )
                strategy.buy_conditions.append(condition)
        
        sell_conditions = self._parse_conditions(self.sell_condition_rows)
        for cond_data in sell_conditions:
            if cond_data["enabled"]:
                condition = EMACondition(
                    price_reference='Current Price',
                    operator=cond_data["operator"],
                    left_field=cond_data["left_operand"],
                    right_field=cond_data["right_operand"],
                    connector=cond_data.get("connector", "AND")
                )
                strategy.sell_conditions.append(condition)
        
        return strategy
    
    def _create_supertrend_strategy(self, name: str, symbol: str, timeframe: int) -> SuperTrendStrategy:
        """Create SuperTrend Strategy"""
        atr_period = self.st_atr_period_spin.value() if hasattr(self, 'st_atr_period_spin') else 10
        atr_multiplier = self.st_atr_multiplier_spin.value() if hasattr(self, 'st_atr_multiplier_spin') else 3.0
        atr_method = self.st_atr_method_combo.currentData() if hasattr(self, 'st_atr_method_combo') else "wilder"
        
        use_wilder = (atr_method == "wilder")
        
        strategy = SuperTrendStrategy(
            name, symbol, timeframe,
            period=atr_period,
            multiplier=atr_multiplier,
            use_wilder_atr=use_wilder
        )
        
        # SuperTrend auto-generates signals, conditions are ignored
        # But we still allow them to be set for potential future use
        
        return strategy
    
    def _create_smc_strategy(self, name: str, symbol: str, timeframe: int) -> SMCStrategy:
        """Create SMC Strategy"""
        pivot_left = self.smc_pivot_left_spin.value() if hasattr(self, 'smc_pivot_left_spin') else 2
        pivot_right = self.smc_pivot_right_spin.value() if hasattr(self, 'smc_pivot_right_spin') else 2
        emit_on = self.smc_emit_on_combo.currentData() if hasattr(self, 'smc_emit_on_combo') else "CHoCH"
        
        # Parse buy/sell filters from conditions
        buy_filters = self._parse_conditions(self.buy_condition_rows)
        sell_filters = self._parse_conditions(self.sell_condition_rows)
        
        strategy = SMCStrategy(
            name, symbol, timeframe,
            pivot_left=pivot_left,
            pivot_right=pivot_right,
            emit_on=emit_on,
            buy_filters=buy_filters if buy_filters else None,
            sell_filters=sell_filters if sell_filters else None
        )
        
        return strategy
    
    def _create_no_strategy(self, name: str, symbol: str, timeframe: int) -> BaseStrategy:
        """Create No Strategy (direct execution)"""
        # Create a simple base strategy
        strategy = BaseStrategy(name, symbol)
        strategy.timeframe = timeframe
        # No conditions needed - direct execution based on direction
        return strategy
    
    def _parse_conditions(self, rows: List[ConditionRowWidget]) -> List[Dict]:
        """Parse conditions from rows"""
        conditions = []
        for row in rows:
            data = row.get_data()
            if data["enabled"]:
                conditions.append(data)
        return conditions
    
    def _apply_risk_management(self, strategy: BaseStrategy):
        """Apply risk management settings to strategy"""
        # Direction
        direction = self.direction_combo.currentData()
        strategy.trade_direction = direction
        
        # Lot size
        lot_size = self.lot_size_spin.value()
        if lot_size == 0.01:
            strategy.lot_size = None  # Use global default
        else:
            strategy.lot_size = lot_size
        
        # SL/TP
        strategy.sl_type = "Price (Points)"
        strategy.sl_value = self.sl_value_spin.value()
        strategy.tp_value = self.tp_value_spin.value()
        strategy.use_ratio = False  # Manual TP value
        
        # Trailing SL
        strategy.enable_trailing_sl = self.enable_trailing_sl_check.isChecked()
        strategy.trailing_sl_gap = self.trailing_sl_gap_spin.value()
        
        # Profit Lock
        strategy.enable_profit_lock = self.enable_profit_lock_check.isChecked()
        strategy.profit_lock_trigger = self.profit_lock_trigger_spin.value()
        strategy.profit_lock_value = self.profit_lock_value_spin.value()
        strategy.profit_trail_step = self.profit_trail_step_spin.value()
        strategy.profit_trail_amount = self.profit_trail_amount_spin.value()
        
        # W&T
        strategy.enable_wt = self.enable_wt_check.isChecked()
        strategy.wt_value = self.wt_value_spin.value()
        strategy.wt_is_percentage = self.wt_percentage_check.isChecked()
        
        # Position Management
        strategy.preserve_position = self.preserve_position_check.isChecked()
        
        # Re-Entry
        strategy.reentry_on_sl_enabled = self.sl_reentry_enabled_check.isChecked()
        strategy.reentry_on_sl_mode = self.sl_reentry_mode_combo.currentData() if strategy.reentry_on_sl_enabled else None
        strategy.reentry_on_sl_count = self.sl_reentry_count_spin.value() if strategy.reentry_on_sl_enabled else 0
        
        strategy.reentry_on_tp_enabled = self.tp_reentry_enabled_check.isChecked()
        strategy.reentry_on_tp_mode = self.tp_reentry_mode_combo.currentData() if strategy.reentry_on_tp_enabled else None
        strategy.reentry_on_tp_count = self.tp_reentry_count_spin.value() if strategy.reentry_on_tp_enabled else 0
        
        # Trading Hours
        if self.time_enabled_check.isChecked():
            start_time = self.start_time_edit.time().toPyTime()
            end_time = self.end_time_edit.time().toPyTime()
            strategy.add_time_rule(start_time, end_time)
    
    def load_strategy_dialog(self):
        """Show dialog to load a strategy"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox
        
        strategies = self.strategy_manager.get_all_strategies()
        if not strategies:
            QMessageBox.information(self, "No Strategies", "No strategies available to load")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Load Strategy")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        list_widget = QListWidget()
        for strategy in strategies:
            list_widget.addItem(f"{strategy.name} ({strategy.symbol})")
        layout.addWidget(list_widget)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec():
            selected = list_widget.currentRow()
            if selected >= 0:
                strategy = strategies[selected]
                self.load_strategy(strategy)
    
    def load_strategy(self, strategy: BaseStrategy):
        """Load a strategy into the form"""
        try:
            self.clear_form()
            self.editing_strategy_name = strategy.name
            
            # Basic info
            self.strategy_name_input.setText(strategy.name)
            self.symbol_combo.setCurrentText(strategy.symbol)
            
            # Determine strategy type
            if isinstance(strategy, OHLCPriceStrategy):
                self.strategy_type_combo.setCurrentIndex(0)  # OHLC
                self.session_type_combo.setCurrentText(strategy.session_type)
            elif isinstance(strategy, VWAPStrategy):
                self.strategy_type_combo.setCurrentIndex(1)  # VWAP
                self.session_type_combo.setCurrentText(strategy.session_type)
            elif isinstance(strategy, EMAStrategy):
                self.strategy_type_combo.setCurrentIndex(2)  # EMA
            elif isinstance(strategy, SuperTrendStrategy):
                self.strategy_type_combo.setCurrentIndex(3)  # SuperTrend
            elif isinstance(strategy, SMCStrategy):
                self.strategy_type_combo.setCurrentIndex(4)  # SMC
            else:
                self.strategy_type_combo.setCurrentIndex(5)  # No Strategy
            
            # Timeframe
            if hasattr(strategy, 'timeframe') and strategy.timeframe:
                for i in range(self.timeframe_combo.count()):
                    if self.timeframe_combo.itemData(i) == strategy.timeframe:
                        self.timeframe_combo.setCurrentIndex(i)
                        break
            
            # Direction
            direction = getattr(strategy, 'trade_direction', 'both')
            if direction == 'long':
                self.direction_combo.setCurrentIndex(1)
            elif direction == 'short':
                self.direction_combo.setCurrentIndex(2)
            else:
                self.direction_combo.setCurrentIndex(0)
            
            # Lot size
            if hasattr(strategy, 'lot_size') and strategy.lot_size:
                self.lot_size_spin.setValue(strategy.lot_size)
            
            # Load conditions (if strategy has buy/sell conditions)
            if hasattr(strategy, 'buy_conditions') and strategy.buy_conditions:
                # Clear existing rows
                for row in self.buy_condition_rows[:]:
                    self.buy_conditions_layout.removeWidget(row)
                    row.deleteLater()
                self.buy_condition_rows.clear()
                
                # Add rows for each condition
                for cond in strategy.buy_conditions:
                    row = ConditionRowWidget()
                    self._update_condition_operands_for_row(row)
                    row.set_data({
                        "enabled": True,
                        "left_operand": getattr(cond, 'left_field', None),
                        "operator": getattr(cond, 'operator', None),
                        "right_operand": getattr(cond, 'right_field', None),
                        "connector": getattr(cond, 'connector', 'AND')
                    })
                    self.buy_condition_rows.append(row)
                    self.buy_conditions_layout.addWidget(row)
            
            if hasattr(strategy, 'sell_conditions') and strategy.sell_conditions:
                # Clear existing rows
                for row in self.sell_condition_rows[:]:
                    self.sell_conditions_layout.removeWidget(row)
                    row.deleteLater()
                self.sell_condition_rows.clear()
                
                # Add rows for each condition
                for cond in strategy.sell_conditions:
                    row = ConditionRowWidget()
                    self._update_condition_operands_for_row(row)
                    row.set_data({
                        "enabled": True,
                        "left_operand": getattr(cond, 'left_field', None),
                        "operator": getattr(cond, 'operator', None),
                        "right_operand": getattr(cond, 'right_field', None),
                        "connector": getattr(cond, 'connector', 'AND')
                    })
                    self.sell_condition_rows.append(row)
                    self.sell_conditions_layout.addWidget(row)
            
            # Load risk management
            if hasattr(strategy, 'sl_value'):
                self.sl_value_spin.setValue(strategy.sl_value)
            if hasattr(strategy, 'tp_value'):
                self.tp_value_spin.setValue(strategy.tp_value)
            if hasattr(strategy, 'enable_trailing_sl'):
                self.enable_trailing_sl_check.setChecked(strategy.enable_trailing_sl)
            if hasattr(strategy, 'trailing_sl_gap'):
                self.trailing_sl_gap_spin.setValue(strategy.trailing_sl_gap)
            if hasattr(strategy, 'enable_profit_lock'):
                self.enable_profit_lock_check.setChecked(strategy.enable_profit_lock)
            if hasattr(strategy, 'profit_lock_trigger'):
                self.profit_lock_trigger_spin.setValue(strategy.profit_lock_trigger)
            if hasattr(strategy, 'profit_lock_value'):
                self.profit_lock_value_spin.setValue(strategy.profit_lock_value)
            if hasattr(strategy, 'profit_trail_step'):
                self.profit_trail_step_spin.setValue(strategy.profit_trail_step)
            if hasattr(strategy, 'profit_trail_amount'):
                self.profit_trail_amount_spin.setValue(strategy.profit_trail_amount)
            if hasattr(strategy, 'enable_wt'):
                self.enable_wt_check.setChecked(strategy.enable_wt)
            if hasattr(strategy, 'wt_value'):
                self.wt_value_spin.setValue(strategy.wt_value)
            if hasattr(strategy, 'wt_is_percentage'):
                self.wt_percentage_check.setChecked(strategy.wt_is_percentage)
            if hasattr(strategy, 'preserve_position'):
                self.preserve_position_check.setChecked(strategy.preserve_position)
            if hasattr(strategy, 'reentry_on_sl_enabled'):
                self.sl_reentry_enabled_check.setChecked(strategy.reentry_on_sl_enabled)
            if hasattr(strategy, 'reentry_on_sl_mode'):
                idx = self.sl_reentry_mode_combo.findData(strategy.reentry_on_sl_mode)
                if idx >= 0:
                    self.sl_reentry_mode_combo.setCurrentIndex(idx)
            if hasattr(strategy, 'reentry_on_sl_count'):
                self.sl_reentry_count_spin.setValue(strategy.reentry_on_sl_count)
            if hasattr(strategy, 'reentry_on_tp_enabled'):
                self.tp_reentry_enabled_check.setChecked(strategy.reentry_on_tp_enabled)
            if hasattr(strategy, 'reentry_on_tp_mode'):
                idx = self.tp_reentry_mode_combo.findData(strategy.reentry_on_tp_mode)
                if idx >= 0:
                    self.tp_reentry_mode_combo.setCurrentIndex(idx)
            if hasattr(strategy, 'reentry_on_tp_count'):
                self.tp_reentry_count_spin.setValue(strategy.reentry_on_tp_count)
            
            # Trading hours
            if hasattr(strategy, 'time_rules') and strategy.time_rules:
                self.time_enabled_check.setChecked(True)
                rule = strategy.time_rules[0]
                start_time = rule.get('start_time')
                end_time = rule.get('end_time')
                if start_time:
                    if isinstance(start_time, str):
                        parts = start_time.split(':')
                        start_time = QTime(int(parts[0]), int(parts[1]))
                    else:
                        start_time = QTime(start_time.hour, start_time.minute)
                    self.start_time_edit.setTime(start_time)
                if end_time:
                    if isinstance(end_time, str):
                        parts = end_time.split(':')
                        end_time = QTime(int(parts[0]), int(parts[1]))
                    else:
                        end_time = QTime(end_time.hour, end_time.minute)
                    self.end_time_edit.setTime(end_time)
            
            # Load strategy-specific config
            if isinstance(strategy, VWAPStrategy):
                if hasattr(self, 'vwap_std_bands_input'):
                    bands = getattr(strategy, 'std_bands', [1.0, 1.5, 2.0])
                    self.vwap_std_bands_input.setText(', '.join(str(b) for b in bands))
                if hasattr(self, 'vwap_swing_period_spin'):
                    self.vwap_swing_period_spin.setValue(getattr(strategy, 'swing_period', 10))
            
            elif isinstance(strategy, EMAStrategy):
                periods = getattr(strategy, 'ema_periods', {})
                if hasattr(self, 'ema1_period_spin'):
                    self.ema1_period_spin.setValue(periods.get('ema_1', 20))
                if hasattr(self, 'ema2_period_spin'):
                    self.ema2_period_spin.setValue(periods.get('ema_2', 50))
                if hasattr(self, 'ema3_period_spin'):
                    self.ema3_period_spin.setValue(periods.get('ema_3', 100))
                if hasattr(self, 'ema4_period_spin'):
                    self.ema4_period_spin.setValue(periods.get('ema_4', 200))
            
            elif isinstance(strategy, SuperTrendStrategy):
                if hasattr(self, 'st_atr_period_spin'):
                    self.st_atr_period_spin.setValue(getattr(strategy, 'period', 10))
                if hasattr(self, 'st_atr_multiplier_spin'):
                    self.st_atr_multiplier_spin.setValue(getattr(strategy, 'multiplier', 3.0))
                if hasattr(self, 'st_atr_method_combo'):
                    use_wilder = getattr(strategy, 'use_wilder_atr', True)
                    idx = self.st_atr_method_combo.findData("wilder" if use_wilder else "sma")
                    if idx >= 0:
                        self.st_atr_method_combo.setCurrentIndex(idx)
            
            elif isinstance(strategy, SMCStrategy):
                if hasattr(self, 'smc_pivot_left_spin'):
                    self.smc_pivot_left_spin.setValue(getattr(strategy, 'pivot_left', 2))
                if hasattr(self, 'smc_pivot_right_spin'):
                    self.smc_pivot_right_spin.setValue(getattr(strategy, 'pivot_right', 2))
                if hasattr(self, 'smc_emit_on_combo'):
                    emit_on = getattr(strategy, 'emit_on', 'CHoCH')
                    idx = self.smc_emit_on_combo.findData(emit_on)
                    if idx >= 0:
                        self.smc_emit_on_combo.setCurrentIndex(idx)
            
            QMessageBox.information(self, "Strategy Loaded", f"Strategy '{strategy.name}' loaded successfully")
        
        except Exception as e:
            logger.error(f"Error loading strategy: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error loading strategy: {str(e)}")

