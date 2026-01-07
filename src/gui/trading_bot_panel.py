"""
Trading Bot Panel
UI for configuring and managing OHLC-based trading bot
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
                             QPushButton, QGroupBox, QTimeEdit,
                             QMessageBox, QLabel, QScrollArea, QTextEdit,
                             QCheckBox)
from PyQt6.QtCore import Qt, QTimer, QTime
from typing import Dict, Optional
import logging
import re

from ..data_feed import DataFeed
from ..strategy.strategy_manager import StrategyManager
from ..mt5_connector import MT5Connector
from ..strategy.base_strategy import BaseStrategy
from ..strategy.ohlc_price_strategy import OHLCPriceStrategy, OHLCPriceCondition
from ..strategy.vwap_strategy import VWAPStrategy, VWAPCondition
from ..strategy.structure_strategy import StructureStrategy
from ..strategy.ema_strategy import EMAStrategy, EMACondition
from ..strategy.supertrend_strategy import SuperTrendStrategy
from ..strategy.mixed_condition import MixedCondition
from .market_data_panel import MarketDataPanel
from .system_log_service import system_log_service
from ..config import Config

logger = logging.getLogger(__name__)


class TradingBotPanel(QWidget):
    """Trading bot panel for OHLC-based price conditions"""

    class ConditionRow(QWidget):
        """Single condition row with operands, operator and AND/OR toggle."""

        def __init__(self, parent_panel: 'TradingBotPanel', is_buy: bool):
            super().__init__()
            self.parent_panel = parent_panel
            self.is_buy = is_buy
            self._build_ui()

        def _build_ui(self):
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(6)

            self.enable_check = QCheckBox()
            self.enable_check.setChecked(True)
            layout.addWidget(self.enable_check)

            self.left_combo = QComboBox()
            layout.addWidget(self.left_combo)

            self.operator_combo = QComboBox()
            layout.addWidget(self.operator_combo)

            self.right_combo = QComboBox()
            layout.addWidget(self.right_combo)

            self.or_check = QCheckBox("OR")
            self.or_check.setToolTip("If checked, combine with next row using OR; otherwise AND.")
            layout.addWidget(self.or_check)

            layout.addStretch()

        def set_options(self, operands: list, operators: list):
            """Populate operand/operator combos."""
            def fill_combo(combo: QComboBox, items: list):
                current = combo.currentData()
                combo.clear()
                for text, value in items:
                    combo.addItem(text, value)
                if current is not None:
                    idx = combo.findData(current)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)

            fill_combo(self.left_combo, operands)
            fill_combo(self.right_combo, operands)

            current_op = self.operator_combo.currentData()
            self.operator_combo.clear()
            for text, value in operators:
                self.operator_combo.addItem(text, value)
            if current_op is not None:
                idx = self.operator_combo.findData(current_op)
                if idx >= 0:
                    self.operator_combo.setCurrentIndex(idx)

        def get_data(self) -> Dict:
            return {
                "enabled": self.enable_check.isChecked(),
                "left_field": self.left_combo.currentData(),
                "right_field": self.right_combo.currentData(),
                "operator": self.operator_combo.currentData(),
                "connector": "OR" if self.or_check.isChecked() else "AND",
            }

        def set_data(self, data: Dict):
            self.enable_check.setChecked(data.get("enabled", True))
            if "left_field" in data:
                idx = self.left_combo.findData(data["left_field"])
                if idx >= 0:
                    self.left_combo.setCurrentIndex(idx)
            if "right_field" in data:
                idx = self.right_combo.findData(data["right_field"])
                if idx >= 0:
                    self.right_combo.setCurrentIndex(idx)
            if "operator" in data:
                idx = self.operator_combo.findData(data["operator"])
                if idx >= 0:
                    self.operator_combo.setCurrentIndex(idx)
            if data.get("connector", "AND") == "OR":
                self.or_check.setChecked(True)
            else:
                self.or_check.setChecked(False)
    
    def __init__(self, data_feed: DataFeed, strategy_manager: StrategyManager,
                 mt5: MT5Connector, market_data_panel: MarketDataPanel):
        super().__init__()
        self.data_feed = data_feed
        self.strategy_manager = strategy_manager
        self.mt5 = mt5
        self.market_data_panel = market_data_panel
        self.config = Config()
        
        # Current bot strategy (can be OHLC or VWAP)
        self.current_bot: Optional[BaseStrategy] = None
        self.editing_strategy_name: Optional[str] = None
        self.strategy_type: str = 'ohlc'  # Will be determined dynamically from conditions
        self.buy_rows = []
        self.sell_rows = []
        
        # Strategy type definitions
        self.strategy_types = {
            "ohlc": ("OHLC Price Strategy", "ohlc"),
            "vwap": ("VWAP Strategy", "vwap"),
            "ema": ("EMA Strategy", "ema"),
            "supertrend": ("SuperTrend Strategy", "supertrend"),
            "smc": ("SMC (Smart Money Concepts)", "smc"),
            "no_strategy": ("No Strategy", "no_strategy")
        }
        
        # Strategy type enable/disable state (default all enabled)
        self.strategy_type_enabled = {
            "ohlc": True,
            "vwap": True,
            "ema": True,
            "supertrend": True,
            "smc": True,
            "no_strategy": True
        }
        
        # Load enabled state from config
        self._load_strategy_type_enabled_state()
        
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second
        
        self.setup_ui()
        
        # Connect to data feed for symbol updates
        if hasattr(data_feed, 'tick_received'):
            self.data_feed.tick_received.connect(self._on_tick_received)
    
    def setup_ui(self):
        """Setup the UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Create scroll area for the form content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Create container widget for all form content
        form_widget = QWidget()
        layout = QVBoxLayout(form_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Strategy Name Section
        # Strategy Type Selection
        strategy_type_group = QGroupBox("Strategy Type")
        strategy_type_layout = QVBoxLayout()
        
        # Strategy Type Dropdown
        type_combo_layout = QFormLayout()
        self.strategy_type_combo = QComboBox()
        self._update_strategy_type_combo()
        self.strategy_type_combo.currentIndexChanged.connect(self._on_strategy_type_changed)
        type_combo_layout.addRow("Strategy Type:", self.strategy_type_combo)
        strategy_type_layout.addLayout(type_combo_layout)
        
        # Enable/Disable Checkboxes
        enable_disable_label = QLabel("Enable/Disable Strategy Types:")
        enable_disable_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        strategy_type_layout.addWidget(enable_disable_label)
        
        # Create checkboxes for each strategy type
        self.strategy_type_checkboxes = {}
        checkbox_layout = QVBoxLayout()
        checkbox_layout.setContentsMargins(10, 5, 5, 5)
        
        for key, (display_name, value) in self.strategy_types.items():
            checkbox = QCheckBox(display_name)
            checkbox.setChecked(self.strategy_type_enabled[key])
            checkbox.stateChanged.connect(lambda state, k=key: self._on_strategy_type_enable_changed(k, state))
            self.strategy_type_checkboxes[key] = checkbox
            checkbox_layout.addWidget(checkbox)
        
        strategy_type_layout.addLayout(checkbox_layout)
        strategy_type_group.setLayout(strategy_type_layout)
        layout.addWidget(strategy_type_group)
        
        strategy_name_group = QGroupBox("Strategy Name")
        strategy_name_layout = QFormLayout()
        
        self.strategy_name_input = QLineEdit()
        self.strategy_name_input.setPlaceholderText("e.g., EMA_Crossover_EURUSD_M1")
        self.strategy_name_input.textChanged.connect(self._validate_strategy_name)
        strategy_name_layout.addRow("Strategy Name:", self.strategy_name_input)
        
        self.strategy_name_error_label = QLabel("")
        self.strategy_name_error_label.setStyleSheet("color: red; font-size: 11px;")
        strategy_name_layout.addRow("", self.strategy_name_error_label)
        
        strategy_name_group.setLayout(strategy_name_layout)
        layout.addWidget(strategy_name_group)
        
        # Strategy Direction
        direction_group = QGroupBox("Strategy Direction")
        direction_layout = QFormLayout()

        self.direction_combo = QComboBox()
        self.direction_combo.addItem("Long & Short", "both")
        self.direction_combo.addItem("Long-only", "long")
        self.direction_combo.addItem("Short-only", "short")
        self.direction_combo.currentIndexChanged.connect(self._on_direction_changed)
        direction_layout.addRow("Direction:", self.direction_combo)

        direction_group.setLayout(direction_layout)
        layout.addWidget(direction_group)

        # Basic Information
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.setPlaceholderText("Select or enter symbol")
        basic_layout.addRow("Symbol:", self.symbol_combo)
        
        # Timeframe selection
        self.timeframe_combo = QComboBox()
        import MetaTrader5 as mt5
        self.timeframe_combo.addItem("M1 (1 Minute)", mt5.TIMEFRAME_M1)
        self.timeframe_combo.addItem("M5 (5 Minutes)", mt5.TIMEFRAME_M5)
        self.timeframe_combo.addItem("M15 (15 Minutes)", mt5.TIMEFRAME_M15)
        self.timeframe_combo.addItem("M30 (30 Minutes)", mt5.TIMEFRAME_M30)
        self.timeframe_combo.addItem("H1 (1 Hour)", mt5.TIMEFRAME_H1)
        self.timeframe_combo.addItem("H4 (4 Hours)", mt5.TIMEFRAME_H4)
        self.timeframe_combo.addItem("D1 (Daily)", mt5.TIMEFRAME_D1)
        self.timeframe_combo.setCurrentIndex(0)  # Default to M1
        basic_layout.addRow("Timeframe:", self.timeframe_combo)
        
        # Lot size for this strategy
        self.lot_size_spin = QDoubleSpinBox()
        self.lot_size_spin.setMinimum(0.01)
        self.lot_size_spin.setMaximum(100.0)
        self.lot_size_spin.setSingleStep(0.01)
        self.lot_size_spin.setDecimals(2)
        self.lot_size_spin.setValue(0.01)  # Default lot size
        self.lot_size_spin.setToolTip("Lot size for this strategy. Leave as default to use global default lot size.")
        basic_layout.addRow("Lot Size:", self.lot_size_spin)
        
        # Session type selector (different for OHLC vs VWAP)
        self.session_combo = QComboBox()
        self._update_session_combo()  # Will be updated based on strategy type
        basic_layout.addRow("Session Type:", self.session_combo)
        
        # VWAP-specific configuration (initially hidden)
        self.vwap_config_group = QGroupBox("VWAP Configuration")
        vwap_config_layout = QFormLayout()
        
        # Standard Deviation Bands
        self.std_bands_input = QLineEdit()
        self.std_bands_input.setPlaceholderText("1, 1.5, 2 (comma-separated)")
        self.std_bands_input.setText("1, 1.5, 2")
        vwap_config_layout.addRow("Standard Deviation Bands:", self.std_bands_input)
        
        # Swing Period
        self.swing_period_spin = QDoubleSpinBox()
        self.swing_period_spin.setMinimum(5)
        self.swing_period_spin.setMaximum(50)
        self.swing_period_spin.setValue(10)
        self.swing_period_spin.setDecimals(0)
        vwap_config_layout.addRow("Swing Period (candles):", self.swing_period_spin)
        
        self.vwap_config_group.setLayout(vwap_config_layout)
        self.vwap_config_group.setVisible(False)  # Hidden by default
        layout.addWidget(self.vwap_config_group)

        # EMA-specific configuration (initially hidden)
        self.ema_config_group = QGroupBox("EMA Configuration")
        ema_config_layout = QFormLayout()

        self.ema_20_spin = QDoubleSpinBox()
        self.ema_20_spin.setMinimum(1)
        self.ema_20_spin.setMaximum(1000)
        self.ema_20_spin.setDecimals(0)
        self.ema_20_spin.setValue(20)
        ema_config_layout.addRow("EMA 1 Period:", self.ema_20_spin)

        self.ema_50_spin = QDoubleSpinBox()
        self.ema_50_spin.setMinimum(1)
        self.ema_50_spin.setMaximum(2000)
        self.ema_50_spin.setDecimals(0)
        self.ema_50_spin.setValue(50)
        ema_config_layout.addRow("EMA 2 Period:", self.ema_50_spin)

        self.ema_100_spin = QDoubleSpinBox()
        self.ema_100_spin.setMinimum(1)
        self.ema_100_spin.setMaximum(5000)
        self.ema_100_spin.setDecimals(0)
        self.ema_100_spin.setValue(100)
        ema_config_layout.addRow("EMA 3 Period:", self.ema_100_spin)

        self.ema_200_spin = QDoubleSpinBox()
        self.ema_200_spin.setMinimum(1)
        self.ema_200_spin.setMaximum(10000)
        self.ema_200_spin.setDecimals(0)
        self.ema_200_spin.setValue(200)
        ema_config_layout.addRow("EMA 4 Period:", self.ema_200_spin)

        ema_help = QLabel(
            "EMA bots compare Current Price against the configured EMA values.\n"
            "Use operators like Crosses Above / Crosses Under for momentum signals."
        )
        ema_help.setStyleSheet("color: #ccc; font-size: 11px;")
        ema_config_layout.addRow("", ema_help)

        self.ema_config_group.setLayout(ema_config_layout)
        self.ema_config_group.setVisible(False)
        layout.addWidget(self.ema_config_group)

        # SuperTrend-specific configuration (initially hidden)
        self.supertrend_config_group = QGroupBox("SuperTrend Configuration")
        supertrend_config_layout = QFormLayout()

        self.supertrend_period_spin = QDoubleSpinBox()
        self.supertrend_period_spin.setMinimum(1)
        self.supertrend_period_spin.setMaximum(500)
        self.supertrend_period_spin.setDecimals(0)
        self.supertrend_period_spin.setValue(10)
        supertrend_config_layout.addRow("ATR Period:", self.supertrend_period_spin)

        self.supertrend_multiplier_spin = QDoubleSpinBox()
        self.supertrend_multiplier_spin.setMinimum(0.1)
        self.supertrend_multiplier_spin.setMaximum(50.0)
        self.supertrend_multiplier_spin.setDecimals(2)
        self.supertrend_multiplier_spin.setValue(3.0)
        supertrend_config_layout.addRow("ATR Multiplier:", self.supertrend_multiplier_spin)

        self.supertrend_atr_method_combo = QComboBox()
        self.supertrend_atr_method_combo.addItem("ATR (Wilder)", True)
        self.supertrend_atr_method_combo.addItem("SMA(TR)", False)
        supertrend_config_layout.addRow("ATR Method:", self.supertrend_atr_method_combo)

        supertrend_help = QLabel(
            "SuperTrend generates signals when the trend flips.\n"
            "It does not use manual Buy/Sell condition lists."
        )
        supertrend_help.setStyleSheet("color: #ccc; font-size: 11px;")
        supertrend_config_layout.addRow("", supertrend_help)

        self.supertrend_config_group.setLayout(supertrend_config_layout)
        self.supertrend_config_group.setVisible(False)
        layout.addWidget(self.supertrend_config_group)

        # SMC-specific configuration (initially hidden)
        self.smc_config_group = QGroupBox("SMC Configuration")
        smc_config_layout = QFormLayout()

        self.smc_pivot_left_spin = QDoubleSpinBox()
        self.smc_pivot_left_spin.setMinimum(1)
        self.smc_pivot_left_spin.setMaximum(10)
        self.smc_pivot_left_spin.setDecimals(0)
        self.smc_pivot_left_spin.setValue(2)
        smc_config_layout.addRow("Pivot Left Bars:", self.smc_pivot_left_spin)

        self.smc_pivot_right_spin = QDoubleSpinBox()
        self.smc_pivot_right_spin.setMinimum(1)
        self.smc_pivot_right_spin.setMaximum(10)
        self.smc_pivot_right_spin.setDecimals(0)
        self.smc_pivot_right_spin.setValue(2)
        smc_config_layout.addRow("Pivot Right Bars:", self.smc_pivot_right_spin)

        self.smc_emit_on_combo = QComboBox()
        self.smc_emit_on_combo.addItem("CHoCH only (bias flips)", "CHoCH")
        self.smc_emit_on_combo.addItem("BOS only (continuation)", "BOS")
        self.smc_emit_on_combo.addItem("Both (BOS + CHoCH)", "BOTH")
        smc_config_layout.addRow("Emit Signals On:", self.smc_emit_on_combo)

        smc_help = QLabel(
            "SMC is a market-structure engine.\n"
            "This bot auto-generates signals from pivots + BOS/CHoCH state.\n"
            "Manual Buy/Sell condition lists are disabled for SMC."
        )
        smc_help.setStyleSheet("color: #ccc; font-size: 11px;")
        smc_config_layout.addRow("", smc_help)

        self.smc_config_group.setLayout(smc_config_layout)
        self.smc_config_group.setVisible(False)
        layout.addWidget(self.smc_config_group)
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # Buy Conditions Section
        self.buy_group = QGroupBox("Buy Conditions")
        buy_layout = QVBoxLayout()
        
        buy_buttons = QHBoxLayout()
        add_buy_btn = QPushButton("Add Buy Condition Row")
        add_buy_btn.clicked.connect(lambda: self.add_condition_row(True))
        buy_buttons.addWidget(add_buy_btn)
        buy_buttons.addStretch()
        buy_layout.addLayout(buy_buttons)

        self.buy_rows_layout = QVBoxLayout()
        self.buy_rows_layout.setSpacing(6)
        buy_layout.addLayout(self.buy_rows_layout)
        buy_layout.addStretch()
        
        self.buy_group.setLayout(buy_layout)
        layout.addWidget(self.buy_group)
        
        # Sell Conditions Section
        self.sell_group = QGroupBox("Sell Conditions")
        sell_layout = QVBoxLayout()
        
        sell_buttons = QHBoxLayout()
        add_sell_btn = QPushButton("Add Sell Condition Row")
        add_sell_btn.clicked.connect(lambda: self.add_condition_row(False))
        sell_buttons.addWidget(add_sell_btn)
        sell_buttons.addStretch()
        sell_layout.addLayout(sell_buttons)

        self.sell_rows_layout = QVBoxLayout()
        self.sell_rows_layout.setSpacing(6)
        sell_layout.addLayout(self.sell_rows_layout)
        sell_layout.addStretch()
        
        self.sell_group.setLayout(sell_layout)
        layout.addWidget(self.sell_group)
        
        # Risk Management Section
        risk_group = QGroupBox("Risk Management")
        risk_layout = QVBoxLayout()
        
        # Stop Loss / Take Profit
        sltp_group = QGroupBox("Stop Loss / Take Profit")
        sltp_layout = QFormLayout()

        # Enable/Disable Stop Loss
        self.enable_sl_check = QComboBox()
        self.enable_sl_check.addItem("Enabled", True)
        self.enable_sl_check.addItem("Disabled", False)
        self.enable_sl_check.setCurrentIndex(0)  # Default: Enabled
        self.enable_sl_check.currentIndexChanged.connect(self._on_sl_enabled_changed)
        sltp_layout.addRow("Enable Stop Loss:", self.enable_sl_check)

        self.sl_type_combo = QComboBox()
        self.sl_type_combo.addItem("Price (Points)", "points")
        sltp_layout.addRow("SL Type:", self.sl_type_combo)

        self.sl_value_spin = QDoubleSpinBox()
        self.sl_value_spin.setMinimum(0.0)
        self.sl_value_spin.setMaximum(100000.0)
        self.sl_value_spin.setDecimals(2)
        self.sl_value_spin.setValue(20.0)
        self.sl_value_spin.setSuffix(" points")
        sltp_layout.addRow("Stop Loss:", self.sl_value_spin)

        # Enable/Disable Take Profit
        self.enable_tp_check = QComboBox()
        self.enable_tp_check.addItem("Enabled", True)
        self.enable_tp_check.addItem("Disabled", False)
        self.enable_tp_check.setCurrentIndex(0)  # Default: Enabled
        self.enable_tp_check.currentIndexChanged.connect(self._on_tp_enabled_changed)
        sltp_layout.addRow("Enable Take Profit:", self.enable_tp_check)

        self.tp_value_spin = QDoubleSpinBox()
        self.tp_value_spin.setMinimum(0.0)
        self.tp_value_spin.setMaximum(100000.0)
        self.tp_value_spin.setDecimals(2)
        self.tp_value_spin.setValue(40.0)
        self.tp_value_spin.setSuffix(" points")
        sltp_layout.addRow("Take Profit:", self.tp_value_spin)

        sltp_group.setLayout(sltp_layout)
        risk_layout.addWidget(sltp_group)

        # Trailing Stop-Loss Section
        trailing_sl_group = QGroupBox("Trailing Stop-Loss")
        trailing_sl_layout = QFormLayout()
        
        self.enable_trailing_sl_check = QComboBox()
        self.enable_trailing_sl_check.addItem("Disabled", False)
        self.enable_trailing_sl_check.addItem("Enabled", True)
        self.enable_trailing_sl_check.setToolTip(
            "When enabled, the stop-loss follows price in your favor at a fixed gap distance."
        )
        self.enable_trailing_sl_check.currentIndexChanged.connect(self._on_trailing_sl_toggled)
        trailing_sl_layout.addRow("Enable Trailing SL:", self.enable_trailing_sl_check)
        
        self.trailing_sl_gap_spin = QDoubleSpinBox()
        self.trailing_sl_gap_spin.setMinimum(0.1)
        self.trailing_sl_gap_spin.setMaximum(10000.0)
        self.trailing_sl_gap_spin.setDecimals(2)
        self.trailing_sl_gap_spin.setValue(1.0)
        self.trailing_sl_gap_spin.setSuffix(" points")
        self.trailing_sl_gap_spin.setToolTip(
            "Distance (price points) kept between current price and the trailing stop.\n"
            "Example: gap=10 points; if price rises 20 points, SL moves up 20 points minus gap, maintaining 10-point distance."
        )
        self.trailing_sl_gap_spin.setEnabled(False)
        trailing_sl_layout.addRow("SL Gap (price points):", self.trailing_sl_gap_spin)
        
        trailing_help = QLabel(
            "Trailing SL auto-moves the stop behind price.\n"
            "• Gap = how far SL stays behind price.\n"
            "• Works only after enabled and price moves profitably."
        )
        trailing_help.setStyleSheet("color: #ccc; font-size: 11px;")
        trailing_sl_layout.addRow("", trailing_help)
        
        trailing_sl_group.setLayout(trailing_sl_layout)
        risk_layout.addWidget(trailing_sl_group)
        
        # Profit Lock Section
        profit_lock_group = QGroupBox("Profit Lock + Trailing")
        profit_lock_layout = QFormLayout()
        
        self.enable_profit_lock_check = QComboBox()
        self.enable_profit_lock_check.addItem("Disabled", False)
        self.enable_profit_lock_check.addItem("Enabled", True)
        self.enable_profit_lock_check.setToolTip(
            "Locks in minimum profit once trigger is reached, then trails profit upward."
        )
        self.enable_profit_lock_check.currentIndexChanged.connect(self._on_profit_lock_toggled)
        profit_lock_layout.addRow("Enable Profit Lock", self.enable_profit_lock_check)
        
        self.profit_lock_trigger_spin = QDoubleSpinBox()
        self.profit_lock_trigger_spin.setMinimum(0.01)
        self.profit_lock_trigger_spin.setMaximum(1000000.0)
        self.profit_lock_trigger_spin.setDecimals(2)
        self.profit_lock_trigger_spin.setValue(100.0)
        self.profit_lock_trigger_spin.setSuffix(" (profit amount)")
        self.profit_lock_trigger_spin.setToolTip(
            "Profit amount that must be reached before profit lock activates.\n"
            "Example: $100 trigger -> when profit hits $100, locking starts."
        )
        self.profit_lock_trigger_spin.setEnabled(False)
        profit_lock_layout.addRow("Profit Lock Trigger (amount)", self.profit_lock_trigger_spin)
        
        self.profit_lock_value_spin = QDoubleSpinBox()
        self.profit_lock_value_spin.setMinimum(0.01)
        self.profit_lock_value_spin.setMaximum(1000000.0)
        self.profit_lock_value_spin.setDecimals(2)
        self.profit_lock_value_spin.setValue(50.0)
        self.profit_lock_value_spin.setSuffix(" (minimum profit)")
        self.profit_lock_value_spin.setToolTip(
            "Minimum profit to lock once trigger is reached.\n"
            "Example: Trigger $100, Lock $50 -> TP adjusts to secure $50 when profit hits $100."
        )
        self.profit_lock_value_spin.setEnabled(False)
        profit_lock_layout.addRow("Minimum Profit to Lock", self.profit_lock_value_spin)
        
        self.profit_trail_step_spin = QDoubleSpinBox()
        self.profit_trail_step_spin.setMinimum(0.0)
        self.profit_trail_step_spin.setMaximum(1000000.0)
        self.profit_trail_step_spin.setDecimals(2)
        self.profit_trail_step_spin.setValue(100.0)
        self.profit_trail_step_spin.setSuffix(" (profit increase)")
        self.profit_trail_step_spin.setToolTip(
            "Additional profit increase needed to move TP further after initial lock.\n"
            "Example: Step $50 -> each extra $50 profit advances TP."
        )
        self.profit_trail_step_spin.setEnabled(False)
        profit_lock_layout.addRow("Trail Step (profit increase threshold)", self.profit_trail_step_spin)
        
        self.profit_trail_amount_spin = QDoubleSpinBox()
        self.profit_trail_amount_spin.setMinimum(0.0)
        self.profit_trail_amount_spin.setMaximum(1000000.0)
        self.profit_trail_amount_spin.setDecimals(2)
        self.profit_trail_amount_spin.setValue(50.0)
        self.profit_trail_amount_spin.setSuffix(" (profit to add)")
        self.profit_trail_amount_spin.setToolTip(
            "Amount to add to TP each time the trail step is reached.\n"
            "Example: Step $50, Amount $25 -> every $50 extra profit raises TP by $25."
        )
        self.profit_trail_amount_spin.setEnabled(False)
        profit_lock_layout.addRow("Trail Amount (profit increment)", self.profit_trail_amount_spin)
        
        profit_help = QLabel(
            "Profit Lock flow:\n"
            "1) Trigger reached -> lock minimum profit.\n"
            "2) Each Trail Step of extra profit -> TP increases by Trail Amount.\n"
            "Example: Trigger $100, Lock $50, Step $50, Amount $25:\n"
            "  Profit $100 → lock $50; Profit $150 → lock $75; Profit $200 → lock $100."
        )
        profit_help.setStyleSheet("color: #ccc; font-size: 11px;")
        profit_lock_layout.addRow("", profit_help)
        
        profit_lock_group.setLayout(profit_lock_layout)
        risk_layout.addWidget(profit_lock_group)

        # Trail Wait & Trade (W&T) Section
        wt_group = QGroupBox("Trail Wait & Trade (W&T)")
        wt_layout = QFormLayout()

        self.enable_wt_check = QComboBox()
        self.enable_wt_check.addItem("Disabled", False)
        self.enable_wt_check.addItem("Enabled", True)
        self.enable_wt_check.setToolTip(
            "When enabled, a dynamic W&T line trails with price and closes the position when hit.\n"
            "BUY: trails up with new highs; triggers when price falls to W&T.\n"
            "SELL: trails down with new lows; triggers when price rises to W&T."
        )
        self.enable_wt_check.currentIndexChanged.connect(self._on_wt_toggled)
        wt_layout.addRow("Enable W&T:", self.enable_wt_check)

        self.wt_value_spin = QDoubleSpinBox()
        self.wt_value_spin.setMinimum(-1000000.0)
        self.wt_value_spin.setMaximum(1000000.0)
        self.wt_value_spin.setDecimals(2)
        self.wt_value_spin.setValue(-15.0)
        self.wt_value_spin.setSuffix(" points")
        self.wt_value_spin.setToolTip(
            "W&T gap value.\n"
            "Points mode: WT = price + wt_value (example: -15 means 15 points below).\n"
            "Percent mode: WT = price * (1 + wt_value/100)."
        )
        self.wt_value_spin.setEnabled(False)
        wt_layout.addRow("W&T Value:", self.wt_value_spin)

        self.wt_is_percentage_check = QCheckBox("Use percentage (%) instead of points")
        self.wt_is_percentage_check.setEnabled(False)
        self.wt_is_percentage_check.stateChanged.connect(self._on_wt_percentage_changed)
        wt_layout.addRow("", self.wt_is_percentage_check)

        wt_help = QLabel(
            "W&T notes:\n"
            "• BUY example: wt_value=-15 → trails as (max_price - 15); triggers on pullback.\n"
            "• SELL example: wt_value=+15 → trails as (min_price + 15); triggers on rebound."
        )
        wt_help.setStyleSheet("color: #ccc; font-size: 11px;")
        wt_layout.addRow("", wt_help)

        wt_group.setLayout(wt_layout)
        risk_layout.addWidget(wt_group)
        
        # Position Preservation
        position_preserve_group = QGroupBox("Position Management")
        position_preserve_layout = QFormLayout()
        
        self.preserve_position_check = QCheckBox("Preserve Position")
        self.preserve_position_check.setToolTip(
            "If enabled, prevents duplicate positions (BUY/SELL) per strategy per symbol. "
            "Each strategy can have max 1 BUY and 1 SELL position per symbol."
        )
        position_preserve_layout.addRow("", self.preserve_position_check)

        # Re-Entry on Stop Loss
        self.sl_reentry_enabled = QCheckBox("Enable Re-Entry on SL")
        position_preserve_layout.addRow(self.sl_reentry_enabled)

        self.sl_reentry_mode_combo = QComboBox()
        self.sl_reentry_mode_combo.addItem("RE-ASAP", "RE_ASAP")
        self.sl_reentry_mode_combo.addItem("RE-ASAP Reverse", "RE_ASAP_REVERSE")
        self.sl_reentry_mode_combo.addItem("RE-COST", "RE_COST")
        self.sl_reentry_mode_combo.addItem("RE-COST Reverse", "RE_COST_REVERSE")
        position_preserve_layout.addRow("SL Re-Entry Mode:", self.sl_reentry_mode_combo)

        self.sl_reentry_count_spin = QSpinBox()
        self.sl_reentry_count_spin.setMinimum(0)
        self.sl_reentry_count_spin.setMaximum(20)
        self.sl_reentry_count_spin.setValue(0)
        position_preserve_layout.addRow("SL Re-Entry Max Count:", self.sl_reentry_count_spin)

        # Re-Entry on Take Profit
        self.tp_reentry_enabled = QCheckBox("Enable Re-Entry on TP")
        position_preserve_layout.addRow(self.tp_reentry_enabled)

        self.tp_reentry_mode_combo = QComboBox()
        self.tp_reentry_mode_combo.addItem("RE-ASAP", "RE_ASAP")
        self.tp_reentry_mode_combo.addItem("RE-ASAP Reverse", "RE_ASAP_REVERSE")
        self.tp_reentry_mode_combo.addItem("RE-COST", "RE_COST")
        self.tp_reentry_mode_combo.addItem("RE-COST Reverse", "RE_COST_REVERSE")
        position_preserve_layout.addRow("TP Re-Entry Mode:", self.tp_reentry_mode_combo)

        self.tp_reentry_count_spin = QSpinBox()
        self.tp_reentry_count_spin.setMinimum(0)
        self.tp_reentry_count_spin.setMaximum(20)
        self.tp_reentry_count_spin.setValue(0)
        position_preserve_layout.addRow("TP Re-Entry Max Count:", self.tp_reentry_count_spin)

        # Trading Hours
        self.time_enabled_check = QCheckBox("Enable time restrictions")
        self.time_enabled_check.stateChanged.connect(self._on_time_toggle)
        position_preserve_layout.addRow(self.time_enabled_check)

        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("HH:mm")
        self.start_time_edit.setTime(QTime(9, 0))
        self.start_time_edit.setEnabled(False)
        position_preserve_layout.addRow("Start Time:", self.start_time_edit)

        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat("HH:mm")
        self.end_time_edit.setTime(QTime(17, 0))
        self.end_time_edit.setEnabled(False)
        position_preserve_layout.addRow("End Time:", self.end_time_edit)
        
        position_preserve_group.setLayout(position_preserve_layout)
        risk_layout.addWidget(position_preserve_group)
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)
        
        # Status and Control Section
        control_group = QGroupBox("Bot Control & Status")
        control_layout = QVBoxLayout()
        
        # Control buttons
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Bot")
        self.save_btn.clicked.connect(self.save_bot)
        self.save_btn.setMinimumHeight(35)
        button_layout.addWidget(self.save_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_form)
        self.clear_btn.setMinimumHeight(35)
        button_layout.addWidget(self.clear_btn)
        
        button_layout.addStretch()
        control_layout.addLayout(button_layout)
        
        # Status display
        self.status_label = QLabel("Status: Not Active")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        control_layout.addWidget(self.status_label)
        
        # OHLC display (for OHLC strategy)
        self.ohlc_label = QLabel("Previous Session OHLC: --")
        control_layout.addWidget(self.ohlc_label)

        # SMC display (for SMC strategy, initially hidden)
        self.smc_status_label = QLabel("SMC: --")
        self.smc_status_label.setVisible(False)
        control_layout.addWidget(self.smc_status_label)
        
        # VWAP display (for VWAP strategy, initially hidden)
        self.vwap_display_group = QGroupBox("Live VWAP Data")
        vwap_display_layout = QVBoxLayout()
        
        self.vwap_value_label = QLabel("VWAP: --")
        vwap_display_layout.addWidget(self.vwap_value_label)
        
        self.vwap_bands_label = QLabel("Bands: --")
        vwap_display_layout.addWidget(self.vwap_bands_label)
        
        self.vwap_distance_label = QLabel("Distance from VWAP: --")
        vwap_display_layout.addWidget(self.vwap_distance_label)
        
        self.vwap_session_label = QLabel("Session: --")
        vwap_display_layout.addWidget(self.vwap_session_label)
        
        self.vwap_volume_label = QLabel("Volume: --")
        vwap_display_layout.addWidget(self.vwap_volume_label)
        
        self.vwap_display_group.setLayout(vwap_display_layout)
        self.vwap_display_group.setVisible(False)  # Hidden by default
        control_layout.addWidget(self.vwap_display_group)

        # EMA display (for EMA strategy, initially hidden)
        self.ema_display_group = QGroupBox("Live EMA Data")
        ema_display_layout = QVBoxLayout()
        self.ema_1_label = QLabel("EMA 1: --")
        ema_display_layout.addWidget(self.ema_1_label)
        self.ema_2_label = QLabel("EMA 2: --")
        ema_display_layout.addWidget(self.ema_2_label)
        self.ema_3_label = QLabel("EMA 3: --")
        ema_display_layout.addWidget(self.ema_3_label)
        self.ema_4_label = QLabel("EMA 4: --")
        ema_display_layout.addWidget(self.ema_4_label)
        self.ema_display_group.setLayout(ema_display_layout)
        self.ema_display_group.setVisible(False)
        control_layout.addWidget(self.ema_display_group)

        # SuperTrend display (for SuperTrend strategy, initially hidden)
        self.supertrend_display_group = QGroupBox("Live SuperTrend Data")
        supertrend_display_layout = QVBoxLayout()
        self.supertrend_trend_label = QLabel("Trend: --")
        supertrend_display_layout.addWidget(self.supertrend_trend_label)
        self.supertrend_atr_label = QLabel("ATR: --")
        supertrend_display_layout.addWidget(self.supertrend_atr_label)
        self.supertrend_upper_label = QLabel("Upper Band: --")
        supertrend_display_layout.addWidget(self.supertrend_upper_label)
        self.supertrend_lower_label = QLabel("Lower Band: --")
        supertrend_display_layout.addWidget(self.supertrend_lower_label)
        self.supertrend_display_group.setLayout(supertrend_display_layout)
        self.supertrend_display_group.setVisible(False)
        control_layout.addWidget(self.supertrend_display_group)
        
        # Current price display
        self.current_price_label = QLabel("Current Price: --")
        control_layout.addWidget(self.current_price_label)
        
        # Log/History
        log_label = QLabel("Bot Activity Log:")
        log_label.setStyleSheet("font-weight: bold;")
        control_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setReadOnly(True)
        control_layout.addWidget(self.log_text)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Add stretch at the end
        layout.addStretch()
        
        # Set the form widget to scroll area
        scroll_area.setWidget(form_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
        # Initialize
        self.strategy_type = 'ohlc'  # Default to OHLC
        self._update_value_combos()  # Initialize value combos
        self._update_ui_visibility()  # Update UI visibility based on strategy type
        self.clear_form()
        self.update_symbol_list()

        # Keep EMA labels in sync with EMA config
        self.ema_20_spin.valueChanged.connect(lambda _: self._update_value_combos())
        self.ema_50_spin.valueChanged.connect(lambda _: self._update_value_combos())
        self.ema_100_spin.valueChanged.connect(lambda _: self._update_value_combos())
        self.ema_200_spin.valueChanged.connect(lambda _: self._update_value_combos())
    
    
    def update_symbol_list(self):
        """Update symbol combo box with available symbols"""
        self.symbol_combo.clear()
        
        # Add symbols from data feed
        for symbol in self.data_feed.symbols:
            self.symbol_combo.addItem(symbol)
        
        # Also add available symbols from MT5 if connected
        if self.mt5 and self.mt5.is_connected():
            try:
                available_symbols = self.mt5.get_available_symbols()
                for symbol in available_symbols:
                    if self.symbol_combo.findText(symbol) == -1:
                        self.symbol_combo.addItem(symbol)
            except Exception as e:
                logger.error(f"Error loading symbols: {e}")
        
        self.symbol_combo.setEditable(True)
        self.symbol_combo.lineEdit().setPlaceholderText("Select or type symbol")
    
    def _on_tick_received(self, symbol: str, tick_data: dict):
        """Handle tick received signal to update symbol list"""
        if self.symbol_combo.findText(symbol) == -1:
            self.symbol_combo.addItem(symbol)
    
    def _update_session_combo(self):
        """Update session combo based on strategy type"""
        self.session_combo.clear()
        if self.strategy_type == 'vwap':
            self.session_combo.addItem("NY Session (18:30–03:30 IST)", "NY")
            self.session_combo.addItem("London Session (13:30–22:30 IST)", "London")
            self.session_combo.addItem("Asia Session (05:30–14:30 IST)", "Asia")
            self.session_combo.addItem("All Sessions", "All")
            self.session_combo.setCurrentIndex(0)  # Default to NY
        elif self.strategy_type == 'smc':
            # SMC doesn't need session boundaries, but keep a slot for future extensions.
            self.session_combo.addItem("All Sessions", "All")
            self.session_combo.setCurrentIndex(0)
        elif self.strategy_type == 'ema':
            # EMA is calculated on candle history; no explicit session boundaries.
            self.session_combo.addItem("All Candles", "All")
            self.session_combo.setCurrentIndex(0)
        elif self.strategy_type == 'supertrend':
            # SuperTrend is calculated on candle history; no explicit session boundaries.
            self.session_combo.addItem("All Candles", "All")
            self.session_combo.setCurrentIndex(0)
        elif self.strategy_type == 'no_strategy':
            # No Strategy doesn't use session boundaries
            self.session_combo.addItem("All Candles", "All")
            self.session_combo.setCurrentIndex(0)
        else:  # ohlc
            self.session_combo.addItem("Daily (24h Mon–Fri)", "daily")
            self.session_combo.addItem("Asian Session (05:30–14:30 IST)", "asian")
            self.session_combo.addItem("European Session (13:30–22:30 IST)", "european")
            self.session_combo.addItem("US Session (18:30–03:30 IST)", "us")
            self.session_combo.setCurrentIndex(0)  # Default to Daily
    
    def _validate_strategy_name(self):
        """Validate strategy name for uniqueness and format"""
        name = self.strategy_name_input.text().strip()
        if not name:
            self.strategy_name_error_label.setText("Strategy name is required")
            return False
        
        # Check format (alphanumeric, underscores, hyphens)
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            self.strategy_name_error_label.setText("Invalid format. Use alphanumeric, underscores, or hyphens")
            return False
        
        # Check uniqueness (skip if editing same name)
        if hasattr(self, 'editing_strategy_name') and name == self.editing_strategy_name:
            self.strategy_name_error_label.setText("")
            return True
        
        existing_strategies = self.strategy_manager.get_all_strategies()
        for strategy in existing_strategies:
            if strategy.name == name:
                self.strategy_name_error_label.setText("Strategy name already exists")
                return False
        
        self.strategy_name_error_label.setText("")
        return True
    
    def _load_strategy_type_enabled_state(self):
        """Load strategy type enabled state from config"""
        enabled_state = self.config.get('strategy_types.enabled', {})
        for key in self.strategy_type_enabled.keys():
            if key in enabled_state:
                self.strategy_type_enabled[key] = enabled_state[key]
    
    def _save_strategy_type_enabled_state(self):
        """Save strategy type enabled state to config"""
        self.config.set('strategy_types.enabled', self.strategy_type_enabled.copy())
        self.config.save()
    
    def _update_strategy_type_combo(self):
        """Update strategy type combo box based on enabled state"""
        # Block signals to prevent triggering _on_strategy_type_changed during update
        self.strategy_type_combo.blockSignals(True)
        
        current_selection = self.strategy_type_combo.currentData()
        self.strategy_type_combo.clear()
        
        # Add only enabled strategy types
        for key, (display_name, value) in self.strategy_types.items():
            if self.strategy_type_enabled[key]:
                self.strategy_type_combo.addItem(display_name, value)
        
        # Restore previous selection if it's still enabled
        if current_selection:
            idx = self.strategy_type_combo.findData(current_selection)
            if idx >= 0:
                self.strategy_type_combo.setCurrentIndex(idx)
            elif self.strategy_type_combo.count() > 0:
                # If previous selection is disabled, select first enabled
                self.strategy_type_combo.setCurrentIndex(0)
                self.strategy_type = self.strategy_type_combo.currentData()
        elif self.strategy_type_combo.count() > 0:
            # No previous selection, select first enabled
            self.strategy_type_combo.setCurrentIndex(0)
            self.strategy_type = self.strategy_type_combo.currentData()
        
        # Unblock signals
        self.strategy_type_combo.blockSignals(False)
        
        # Update UI visibility if strategy type changed and UI elements are initialized
        if hasattr(self, 'strategy_type') and self.strategy_type and hasattr(self, 'vwap_config_group'):
            self._update_ui_visibility()
    
    def _on_strategy_type_enable_changed(self, key: str, state: int):
        """Handle strategy type enable/disable checkbox change"""
        # State 0 = Unchecked, 2 = Checked in PyQt6
        is_enabled = (state == 2)  # Qt.CheckState.Checked = 2
        self.strategy_type_enabled[key] = is_enabled
        
        # Save to config
        self._save_strategy_type_enabled_state()
        
        # Update combo box
        self._update_strategy_type_combo()
        
        # If currently selected type was disabled, select first enabled
        current_selection = self.strategy_type_combo.currentData()
        if not current_selection and self.strategy_type_combo.count() > 0:
            self.strategy_type_combo.setCurrentIndex(0)
            self.strategy_type = self.strategy_type_combo.currentData()
            self._update_ui_visibility()
    
    def _on_strategy_type_changed(self, index: int):
        """Handle strategy type change"""
        self.strategy_type = self.strategy_type_combo.currentData()
        self._update_ui_visibility()
    
    def _update_ui_visibility(self):
        """Update UI visibility based on strategy type"""
        # Return early if UI elements aren't initialized yet
        if not hasattr(self, 'vwap_config_group'):
            return
            
        # Show/hide VWAP-specific UI
        is_vwap = self.strategy_type == 'vwap'
        is_smc = self.strategy_type == 'smc'
        is_ema = self.strategy_type == 'ema'
        is_supertrend = self.strategy_type == 'supertrend'
        is_no_strategy = self.strategy_type == 'no_strategy'
        self.vwap_config_group.setVisible(is_vwap)
        self.vwap_display_group.setVisible(is_vwap)
        self.ema_config_group.setVisible(is_ema)
        self.ema_display_group.setVisible(is_ema)
        self.supertrend_config_group.setVisible(is_supertrend)
        self.supertrend_display_group.setVisible(is_supertrend)
        self.smc_config_group.setVisible(is_smc)
        self.smc_status_label.setVisible(is_smc)
        self.ohlc_label.setVisible((not is_vwap) and (not is_smc) and (not is_ema) and (not is_supertrend) and (not is_no_strategy))

        # Hide manual condition builders for SuperTrend (SMC now can use filters)
        # Show buy/sell conditions for no_strategy (but they're optional)
        self.buy_group.setVisible((not is_supertrend))
        self.sell_group.setVisible((not is_supertrend))
        
        # Update group titles to indicate conditions are optional for no_strategy
        if is_no_strategy:
            self.buy_group.setTitle("Buy Conditions (Optional - No Strategy mode executes directly)")
            self.sell_group.setTitle("Sell Conditions (Optional - No Strategy mode executes directly)")
        else:
            self.buy_group.setTitle("Buy Conditions")
            self.sell_group.setTitle("Sell Conditions")
        
        # Update value combo boxes for VWAP
        self._update_value_combos()
        
        # Clear form when switching types
        if self.current_bot:
            self.clear_form()
    
    def _update_value_combos(self):
        """Update operand/operator options based on strategy type for all rows."""
        operands = self._get_operand_options()
        operators = [
            ("Greater_Than", ">"),
            ("Lower_Than", "<"),
            ("Equals", "=="),
            ("Crossover", "Crosses Above"),
            ("Crossunder", "Crosses Under"),
            ("Any_Cross", "Any_Cross"),
        ]

        # VWAP specific extra operators (always available)
        operators.extend([
            ("Within_Band", "Within Band"),
            ("Outside_Band", "Outside Band"),
        ])

        for row in self.buy_rows + self.sell_rows:
            row.set_options(operands, operators)

    def _get_operand_options(self):
        """Get all available operand options (all indicators)."""
        operands = [
            ("Current Price", "price"),
            ("Previous Open", "prev_open"),
            ("Previous High", "prev_high"),
            ("Previous Low", "prev_low"),
            ("Previous Close", "prev_close"),
            ("Open", "open"),
            ("High", "high"),
            ("Low", "low"),
            ("Close", "close"),
            ("(H + L)/2", "hl2"),
            ("(H + L + C)/3", "hlc3"),
            ("(O + H + L + C)/4", "ohlc4"),
        ]
        
        # Add EMA options (configurable periods)
        p1 = int(self.ema_20_spin.value())
        p2 = int(self.ema_50_spin.value())
        p3 = int(self.ema_100_spin.value())
        p4 = int(self.ema_200_spin.value())
        operands.extend([
            (f"EMA_{p1}", f"ema_{p1}"),
            (f"EMA_{p2}", f"ema_{p2}"),
            (f"EMA_{p3}", f"ema_{p3}"),
            (f"EMA_{p4}", f"ema_{p4}"),
        ])
        
        # Add SuperTrend
        operands.extend([
            ("SuperTrend Value", "supertrend_value"),
            ("SuperTrend Upper", "supertrend_upper"),
            ("SuperTrend Lower", "supertrend_lower"),
        ])
        
        # Add VWAP
        operands.extend([
            ("VWAP", "vwap"),
            ("VWAP Upper 1.0σ", "vwap_upper_1.0"),
            ("VWAP Upper 1.5σ", "vwap_upper_1.5"),
            ("VWAP Upper 2.0σ", "vwap_upper_2.0"),
            ("VWAP Lower 1.0σ", "vwap_lower_1.0"),
            ("VWAP Lower 1.5σ", "vwap_lower_1.5"),
            ("VWAP Lower 2.0σ", "vwap_lower_2.0"),
        ])
        
        # Add SMC
        operands.extend([
            ("SMC Pivot High", "smc_pivot_high"),
            ("SMC Pivot Low", "smc_pivot_low"),
        ])
        
        return operands

    def _reset_condition_rows(self):
        """Clear all condition rows."""
        for layout in [self.buy_rows_layout, self.sell_rows_layout]:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)
        self.buy_rows = []
        self.sell_rows = []

    def add_condition_row(self, is_buy: bool, preset: Dict = None):
        """Add a condition row to buy or sell list."""
        row = TradingBotPanel.ConditionRow(self, is_buy)
        if is_buy:
            self.buy_rows.append(row)
            self.buy_rows_layout.addWidget(row)
        else:
            self.sell_rows.append(row)
            self.sell_rows_layout.addWidget(row)
        row.set_options(self._get_operand_options(), [
            ("Greater_Than", ">"),
            ("Lower_Than", "<"),
            ("Equals", "=="),
            ("Crossover", "Crosses Above"),
            ("Crossunder", "Crosses Under"),
            ("Any_Cross", "Any_Cross"),
            ("Within_Band", "Within Band"),
            ("Outside_Band", "Outside Band"),
        ] if self.strategy_type == 'vwap' else [
            ("Greater_Than", ">"),
            ("Lower_Than", "<"),
            ("Equals", "=="),
            ("Crossover", "Crosses Above"),
            ("Crossunder", "Crosses Under"),
            ("Any_Cross", "Any_Cross"),
        ])
        if preset:
            row.set_data(preset)

    def _ensure_minimum_rows(self):
        """Ensure at least one row exists for buy/sell sections."""
        if len(self.buy_rows) == 0:
            self.add_condition_row(True)
        if len(self.sell_rows) == 0:
            self.add_condition_row(False)
    
    def clear_form(self):
        """Clear the form"""
        self.strategy_name_input.clear()
        self.strategy_name_error_label.setText("")
        self._reset_condition_rows()
        self._ensure_minimum_rows()
        self.editing_strategy_name = None
        self.current_bot = None

        # Reset direction
        self.direction_combo.setCurrentIndex(self.direction_combo.findData("both"))
        
        # Reset risk management fields
        self.enable_trailing_sl_check.setCurrentIndex(0)  # Disabled
        self.trailing_sl_gap_spin.setValue(1.0)
        self.trailing_sl_gap_spin.setEnabled(False)
        
        self.enable_profit_lock_check.setCurrentIndex(0)  # Disabled
        self.profit_lock_trigger_spin.setValue(100.0)
        self.profit_lock_trigger_spin.setEnabled(False)
        self.profit_lock_value_spin.setValue(50.0)
        self.profit_lock_value_spin.setEnabled(False)
        self.profit_trail_step_spin.setValue(100.0)
        self.profit_trail_step_spin.setEnabled(False)
        self.profit_trail_amount_spin.setValue(50.0)
        self.profit_trail_amount_spin.setEnabled(False)

        # Reset W&T fields
        if hasattr(self, 'enable_wt_check'):
            self.enable_wt_check.setCurrentIndex(0)  # Disabled
        if hasattr(self, 'wt_value_spin'):
            self.wt_value_spin.setValue(-15.0)
            self.wt_value_spin.setSuffix(" points")
            self.wt_value_spin.setEnabled(False)
        if hasattr(self, 'wt_is_percentage_check'):
            self.wt_is_percentage_check.setChecked(False)
            self.wt_is_percentage_check.setEnabled(False)

        # Reset SL/TP
        self.enable_sl_check.setCurrentIndex(0)  # Enabled
        self.enable_tp_check.setCurrentIndex(0)  # Enabled
        self.sl_type_combo.setCurrentIndex(0)
        self.sl_value_spin.setValue(20.0)
        self.tp_value_spin.setValue(40.0)

        # Reset re-entry and time controls
        self.sl_reentry_enabled.setChecked(False)
        self.sl_reentry_mode_combo.setCurrentIndex(0)
        self.sl_reentry_count_spin.setValue(0)

        self.tp_reentry_enabled.setChecked(False)
        self.tp_reentry_mode_combo.setCurrentIndex(0)
        self.tp_reentry_count_spin.setValue(0)

        self.time_enabled_check.setChecked(False)
        self.start_time_edit.setTime(QTime(9, 0))
        self.end_time_edit.setTime(QTime(17, 0))
        self._on_time_toggle(0)
        
        self.update_status()
    
    def _on_trailing_sl_toggled(self, index: int):
        """Handle trailing SL enable/disable toggle"""
        enabled = self.enable_trailing_sl_check.currentData()
        self.trailing_sl_gap_spin.setEnabled(enabled)
    
    def _on_profit_lock_toggled(self, index: int):
        """Handle profit lock enable/disable toggle"""
        enabled = self.enable_profit_lock_check.currentData()
        self.profit_lock_trigger_spin.setEnabled(enabled)
        self.profit_lock_value_spin.setEnabled(enabled)
        self.profit_trail_step_spin.setEnabled(enabled)
        self.profit_trail_amount_spin.setEnabled(enabled)

    def _on_wt_toggled(self, index: int):
        """Handle W&T enable/disable toggle"""
        enabled = self.enable_wt_check.currentData()
        self.wt_value_spin.setEnabled(enabled)
        self.wt_is_percentage_check.setEnabled(enabled)

    def _on_wt_percentage_changed(self, state: int):
        """Update suffix when switching between points and percent mode."""
        is_pct = self.wt_is_percentage_check.isChecked()
        self.wt_value_spin.setSuffix(" %" if is_pct else " points")

    def _on_sl_enabled_changed(self, index: int):
        """Handle SL enable/disable toggle"""
        enabled = self.enable_sl_check.currentData()
        self.sl_type_combo.setEnabled(enabled)
        self.sl_value_spin.setEnabled(enabled)

    def _on_tp_enabled_changed(self, index: int):
        """Handle TP enable/disable toggle"""
        enabled = self.enable_tp_check.currentData()
        self.tp_value_spin.setEnabled(enabled)

    def _on_direction_changed(self, index: int):
        """Show/hide buy/sell blocks based on direction selection."""
        direction = self.direction_combo.currentData()
        self.buy_group.setVisible(direction in ("both", "long"))
        self.sell_group.setVisible(direction in ("both", "short"))

    def _on_time_toggle(self, state: int):
        """Enable/disable time range edits based on toggle."""
        enabled = self.time_enabled_check.isChecked()
        self.start_time_edit.setEnabled(enabled)
        self.end_time_edit.setEnabled(enabled)
    
    def save_bot(self):
        """Save the trading bot"""
        strategy_name = self.strategy_name_input.text().strip()
        symbol = self.symbol_combo.currentText().strip().upper()
        
        if not strategy_name or not symbol:
            QMessageBox.warning(self, "Validation Error", "Please enter strategy name and symbol")
            return
        
        # Validate strategy name
        if not self._validate_strategy_name():
            QMessageBox.warning(self, "Validation Error", "Please fix the strategy name errors")
            return
        
        # Check if editing existing strategy
        is_editing = self.editing_strategy_name is not None
        if is_editing and strategy_name != self.editing_strategy_name:
            QMessageBox.warning(self, "Error", "Cannot change strategy name when editing. Please use the original name.")
            self.strategy_name_input.setText(self.editing_strategy_name)
            return
        
        # Get strategy type from combo box
        strategy_type = self.strategy_type_combo.currentData()
        direction = self.direction_combo.currentData()
        if strategy_type not in ('supertrend'):
            active_buy = [r for r in self.buy_rows if r.get_data().get("enabled")]
            active_sell = [r for r in self.sell_rows if r.get_data().get("enabled")]
            # No Strategy: Conditions are optional - if no conditions, will execute directly based on direction
            # So we skip validation for no_strategy - it can have 0 conditions for direct execution
            if strategy_type != 'no_strategy' and strategy_type != 'smc':
                if direction in ("both", None):
                    if len(active_buy) == 0 and len(active_sell) == 0:
                        QMessageBox.warning(self, "Validation Error", "Please add at least one buy or sell condition")
                        return
                elif direction == "long":
                    if len(active_buy) == 0:
                        QMessageBox.warning(self, "Validation Error", "Please add at least one buy condition for Long-only direction")
                        return
                elif direction == "short":
                    if len(active_sell) == 0:
                        QMessageBox.warning(self, "Validation Error", "Please add at least one sell condition for Short-only direction")
                        return
        
        # Get timeframe and session type
        timeframe = self.timeframe_combo.currentData()
        session_type = self.session_combo.currentData()
        
        # Create or update strategy
        if is_editing and self.current_bot:
            # Update existing bot
            bot = self.current_bot
            bot.name = strategy_name  # Update name
            bot.symbol = symbol
            bot.session_type = session_type
            bot.timeframe = timeframe
        else:
            # Create new bot based on strategy type (default to OHLC for now)
            if strategy_type == 'vwap':
                bot = VWAPStrategy(strategy_name, symbol, session_type, timeframe)
                bot.set_mt5_connector(self.mt5)
                
                # Set VWAP-specific configuration
                std_bands_text = self.std_bands_input.text().strip()
                if std_bands_text:
                    try:
                        std_bands = [float(x.strip()) for x in std_bands_text.split(',')]
                        bot.std_bands = std_bands
                    except:
                        QMessageBox.warning(self, "Warning", "Invalid STD bands format. Using default.")
                        bot.std_bands = [1.0, 1.5, 2.0]
                
                bot.swing_period = int(self.swing_period_spin.value())
            elif strategy_type == 'ema':
                periods = {
                    'ema_1': int(self.ema_20_spin.value()),
                    'ema_2': int(self.ema_50_spin.value()),
                    'ema_3': int(self.ema_100_spin.value()),
                    'ema_4': int(self.ema_200_spin.value()),
                }
                bot = EMAStrategy(name=strategy_name, symbol=symbol, timeframe=timeframe, ema_periods=periods)
                bot.set_mt5_connector(self.mt5)
            elif strategy_type == 'smc' or strategy_type == 'structure':
                bot = StructureStrategy(
                    name=strategy_name,
                    symbol=symbol,
                    timeframe=timeframe,
                    pivot_left=int(self.smc_pivot_left_spin.value()),
                    pivot_right=int(self.smc_pivot_right_spin.value()),
                    emit_on=self.smc_emit_on_combo.currentData(),
                )
                bot.set_mt5_connector(self.mt5)
            elif strategy_type == 'supertrend':
                bot = SuperTrendStrategy(
                    name=strategy_name,
                    symbol=symbol,
                    timeframe=timeframe,
                    period=int(self.supertrend_period_spin.value()),
                    multiplier=float(self.supertrend_multiplier_spin.value()),
                    use_wilder_atr=bool(self.supertrend_atr_method_combo.currentData()),
                )
                bot.set_mt5_connector(self.mt5)
            elif strategy_type == 'no_strategy':
                from ..strategy.simple_condition_strategy import SimpleConditionStrategy
                bot = SimpleConditionStrategy(name=strategy_name, symbol=symbol, timeframe=timeframe)
                bot.set_mt5_connector(self.mt5)
            else:  # ohlc
                bot = OHLCPriceStrategy(strategy_name, symbol, session_type, timeframe)
                bot.set_market_data_panel(self.market_data_panel)
        
        # Clear existing conditions (not used by SMC)
        if hasattr(bot, 'buy_conditions'):
            bot.buy_conditions.clear()
        if hasattr(bot, 'sell_conditions'):
            bot.sell_conditions.clear()
        
        # Add buy/sell conditions (only for VWAP / OHLC / EMA / no_strategy). For SMC we store filters below.
        smc_filters = {"buy": [], "sell": []}
        if strategy_type not in ('smc', 'supertrend'):
            def _add_conditions(rows, add_func):
                added = 0
                for idx, row in enumerate(rows):
                    data = row.get_data()
                    if not data.get("enabled"):
                        continue
                    connector = data.get("connector", "AND")
                    left_field = data.get("left_field")
                    right_field = data.get("right_field")
                    operator = data.get("operator")
                    if not left_field or not right_field or not operator:
                        logger.warning(f"Skipping incomplete condition at row {idx+1}")
                        continue
                    if strategy_type == 'vwap':
                        condition = VWAPCondition(
                                price_reference='Current Price',
                                operator=operator,
                                vwap_field=right_field,
                                value=None,
                                left_field=left_field,
                                right_field=right_field,
                                connector=connector
                        )
                    elif strategy_type == 'ema':
                        condition = EMACondition(
                                price_reference='Current Price',
                                operator=operator,
                                ema_field=right_field if right_field.startswith("ema_") else None,
                                value=None,
                                left_field=left_field,
                                right_field=right_field,
                                connector=connector
                        )
                    else:  # ohlc or no_strategy - both use OHLCPriceCondition
                        condition = OHLCPriceCondition(
                                price_reference='Current Price',
                                operator=operator,
                                ohlc_field=right_field if right_field in ['open', 'high', 'low', 'close', 'hl2', 'hlc3', 'ohlc4'] else None,
                                value=None,
                                left_field=left_field,
                                right_field=right_field,
                                connector=connector
                            )
                    add_func(condition)
                    added += 1
                return added

            added_buy = _add_conditions(self.buy_rows, bot.add_buy_condition)
            added_sell = _add_conditions(self.sell_rows, bot.add_sell_condition)
            # No Strategy: Conditions are optional - if no conditions added, will execute directly based on direction
            # So we skip validation for no_strategy here as well
            if strategy_type != 'no_strategy':
                if direction in ("both", None):
                    if added_buy == 0 and added_sell == 0:
                        QMessageBox.warning(self, "Validation Error", "No valid conditions added. Please complete the fields.")
                        return
                elif direction == "long":
                    if added_buy == 0:
                        QMessageBox.warning(self, "Validation Error", "No valid buy conditions added for Long-only direction.")
                        return
                elif direction == "short":
                    if added_sell == 0:
                        QMessageBox.warning(self, "Validation Error", "No valid sell conditions added for Short-only direction.")
                        return
        else:
            # Collect SMC filter conditions for post-filtering
            def _collect(rows, target_key):
                for row in rows:
                    data = row.get_data()
                    if not data.get("enabled"):
                        continue
                    if not data.get("left_field") or not data.get("right_field") or not data.get("operator"):
                        continue
                    smc_filters[target_key].append({
                        "left_field": data.get("left_field"),
                        "right_field": data.get("right_field"),
                        "operator": data.get("operator"),
                        "connector": data.get("connector", "AND"),
                    })

            _collect(self.buy_rows, "buy")
            _collect(self.sell_rows, "sell")
        
        # Set risk management configuration
        bot.enable_trailing_sl = self.enable_trailing_sl_check.currentData()
        bot.trailing_sl_gap = self.trailing_sl_gap_spin.value() if bot.enable_trailing_sl else 0.0
        
        bot.enable_profit_lock = self.enable_profit_lock_check.currentData()
        bot.profit_lock_trigger = self.profit_lock_trigger_spin.value() if bot.enable_profit_lock else 0.0
        bot.profit_lock_value = self.profit_lock_value_spin.value() if bot.enable_profit_lock else 0.0
        bot.profit_trail_step = self.profit_trail_step_spin.value() if bot.enable_profit_lock else 0.0
        bot.profit_trail_amount = self.profit_trail_amount_spin.value() if bot.enable_profit_lock else 0.0

        # Trail Wait & Trade (W&T)
        bot.enable_wt = self.enable_wt_check.currentData()
        bot.wt_is_percentage = self.wt_is_percentage_check.isChecked() if bot.enable_wt else False
        bot.wt_value = self.wt_value_spin.value() if bot.enable_wt else 0.0
        
        # Set position preservation
        bot.preserve_position = self.preserve_position_check.isChecked()

        # Strategy direction
        bot.trade_direction = direction or "both"

        # Lot size configuration
        bot.lot_size = self.lot_size_spin.value()
        
        # SL/TP configuration (points)
        sl_enabled = self.enable_sl_check.currentData()
        tp_enabled = self.enable_tp_check.currentData()
        
        if sl_enabled:
            bot.sl_type = "Price (Points)"
            bot.sl_value = self.sl_value_spin.value()
        else:
            bot.sl_type = None  # Disabled
            bot.sl_value = 0.0
        
        bot.sl_enabled = sl_enabled
        
        if tp_enabled:
            bot.use_ratio = False
            bot.tp_value = self.tp_value_spin.value()
        else:
            bot.tp_value = 0.0  # Disabled
        
        bot.tp_enabled = tp_enabled

        # Re-Entry configuration
        bot.reentry_on_sl_enabled = self.sl_reentry_enabled.isChecked()
        bot.reentry_on_sl_mode = self.sl_reentry_mode_combo.currentData() if bot.reentry_on_sl_enabled else None
        bot.reentry_on_sl_count = self.sl_reentry_count_spin.value() if bot.reentry_on_sl_enabled else 0
        bot.reentry_on_sl_used = 0

        bot.reentry_on_tp_enabled = self.tp_reentry_enabled.isChecked()
        bot.reentry_on_tp_mode = self.tp_reentry_mode_combo.currentData() if bot.reentry_on_tp_enabled else None
        bot.reentry_on_tp_count = self.tp_reentry_count_spin.value() if bot.reentry_on_tp_enabled else 0
        bot.reentry_on_tp_used = 0

        # Trading hours
        bot.time_rules = []
        if self.time_enabled_check.isChecked():
            start_time = self.start_time_edit.time().toPyTime()
            end_time = self.end_time_edit.time().toPyTime()
            bot.add_time_rule(start_time, end_time)
        
        # Ensure symbol is in data feed
        if symbol not in self.data_feed.symbols:
            if self.mt5 and self.mt5.is_connected():
                if not self.data_feed.add_symbol(symbol):
                    QMessageBox.warning(self, "Warning",
                                      f"Symbol {symbol} could not be added to data feed. "
                                      f"Bot will not receive market data updates.")
        
        # Ensure OHLC data is fetched
        if hasattr(self.market_data_panel, 'fetch_ohlc_for_symbols'):
            self.market_data_panel.fetch_ohlc_for_symbols([symbol])
        
        # Enable bot by default
        bot.enable()
        
        # Add to strategy manager
        if is_editing:
            # Update existing strategy
            existing = self.strategy_manager.get_strategy(strategy_name)
            if existing:
                # Remove old and add new
                self.strategy_manager.remove_strategy(strategy_name)
            self.strategy_manager.add_strategy(bot)
            system_log_service.log(
                "MESSAGE",
                f"Strategy {strategy_name} edited",
                strategy=strategy_name,
            )
            QMessageBox.information(self, "Success", f"Strategy '{strategy_name}' updated successfully")
        else:
            if self.strategy_manager.add_strategy(bot):
                # Save to disk
                from ..strategy.strategy_persistence import StrategyPersistence
                persistence = StrategyPersistence()
                if persistence.save_strategy(bot):
                    system_log_service.log(
                        "MESSAGE",
                        f"Strategy {strategy_name} created",
                        strategy=strategy_name,
                    )
                    QMessageBox.information(self, "Success", f"Strategy '{strategy_name}' saved and enabled successfully")
                else:
                    system_log_service.log(
                        "WARNING",
                        f"Strategy {strategy_name} created but could not save to disk",
                        strategy=strategy_name,
                    )
                    QMessageBox.warning(self, "Warning", f"Strategy '{strategy_name}' added but could not save to disk")
            else:
                system_log_service.log(
                    "WARNING",
                    f"Strategy {strategy_name} could not be created (already exists)",
                    strategy=strategy_name,
                )
                QMessageBox.warning(self, "Error", f"Strategy '{strategy_name}' already exists")
        
        # Attach SMC filters if applicable
        if strategy_type == 'smc' and hasattr(bot, "set_filters"):
            bot.set_filters(smc_filters.get("buy", []), smc_filters.get("sell", []))
        
        self.current_bot = bot
        self.update_status()
    
    def update_status(self):
        """Update status display"""
        symbol = self.symbol_combo.currentText().strip()
        
        if not symbol:
            self.status_label.setText("Status: Not Active (No symbol selected)")
            self.ohlc_label.setText("Previous Session OHLC: --")
            self.current_price_label.setText("Current Price: --")
            if self.vwap_display_group.isVisible():
                self.vwap_value_label.setText("VWAP: --")
                self.vwap_bands_label.setText("Bands: --")
                self.vwap_distance_label.setText("Distance from VWAP: --")
                self.vwap_session_label.setText("Session: --")
                self.vwap_volume_label.setText("Volume: --")
            if self.ema_display_group.isVisible():
                self.ema_1_label.setText("EMA 1: --")
                self.ema_2_label.setText("EMA 2: --")
                self.ema_3_label.setText("EMA 3: --")
                self.ema_4_label.setText("EMA 4: --")
            if self.supertrend_display_group.isVisible():
                self.supertrend_trend_label.setText("Trend: --")
                self.supertrend_atr_label.setText("ATR: --")
                self.supertrend_upper_label.setText("Upper Band: --")
                self.supertrend_lower_label.setText("Lower Band: --")
            return
        
        # Get current price
        tick = self.data_feed.get_latest_tick(symbol)
        current_price = None
        if tick:
            current_price = (tick.get('bid', 0) + tick.get('ask', 0)) / 2.0
            if current_price == 0:
                current_price = tick.get('bid', tick.get('ask', 0))
            self.current_price_label.setText(f"Current Price: {current_price:.5f}")
        else:
            self.current_price_label.setText("Current Price: --")
        
        # Update based on strategy type
        if self.strategy_type == 'vwap':
            # Update VWAP display
            if self.current_bot and isinstance(self.current_bot, VWAPStrategy):
                vwap_indicator = self.current_bot.vwap_indicator
                volume_indicator = self.current_bot.volume_indicator
                
                if vwap_indicator:
                    vwap_value = vwap_indicator.get_vwap()
                    if vwap_value:
                        self.vwap_value_label.setText(f"VWAP: {vwap_value:.5f}")
                        
                        # Show bands
                        bands_text = []
                        for std_dev in self.current_bot.std_bands:
                            upper, lower = vwap_indicator.get_bands(std_dev)
                            if upper and lower:
                                bands_text.append(f"{std_dev}STD: [{lower:.5f}, {upper:.5f}]")
                        self.vwap_bands_label.setText("Bands: " + " | ".join(bands_text) if bands_text else "Bands: --")
                        
                        # Show distance from VWAP
                        if current_price:
                            distance_points, distance_std = vwap_indicator.get_distance_from_vwap(current_price)
                            if distance_points is not None and distance_std is not None:
                                self.vwap_distance_label.setText(
                                    f"Distance: {distance_points:.5f} points ({distance_std:.2f} STD)"
                                )
                            else:
                                self.vwap_distance_label.setText("Distance from VWAP: --")
                        else:
                            self.vwap_distance_label.setText("Distance from VWAP: --")
                        
                        # Show session info
                        session_info = vwap_indicator.get_session_info()
                        session_start = session_info.get('session_start_time')
                        if session_start:
                            self.vwap_session_label.setText(f"Session: {self.current_bot.session_type} (Started: {session_start.strftime('%H:%M:%S')})")
                        else:
                            self.vwap_session_label.setText(f"Session: {self.current_bot.session_type}")
                    else:
                        self.vwap_value_label.setText("VWAP: Calculating...")
                        self.vwap_bands_label.setText("Bands: --")
                        self.vwap_distance_label.setText("Distance from VWAP: --")
                        self.vwap_session_label.setText("Session: --")
                
                if volume_indicator:
                    current_volume = volume_indicator.get_current_volume()
                    volume_ma = volume_indicator.get_volume_ma()
                    volume_momentum = volume_indicator.get_volume_momentum()
                    if current_volume is not None:
                        volume_text = f"Volume: {current_volume:.0f}"
                        if volume_ma:
                            ratio = current_volume / volume_ma if volume_ma > 0 else 0
                            volume_text += f" (MA: {volume_ma:.0f}, Ratio: {ratio:.2f})"
                        if volume_momentum:
                            volume_text += f" [{volume_momentum}]"
                        self.vwap_volume_label.setText(volume_text)
                    else:
                        self.vwap_volume_label.setText("Volume: --")
            else:
                self.vwap_value_label.setText("VWAP: -- (No active bot)")
                self.vwap_bands_label.setText("Bands: --")
                self.vwap_distance_label.setText("Distance from VWAP: --")
                self.vwap_session_label.setText("Session: --")
                self.vwap_volume_label.setText("Volume: --")
        elif self.strategy_type == 'ema':
            if self.current_bot and isinstance(self.current_bot, EMAStrategy):
                ema_data = self.current_bot.get_ema_snapshot()
                if ema_data:
                    p1 = ema_data.get('periods', {}).get('ema_1')
                    p2 = ema_data.get('periods', {}).get('ema_2')
                    p3 = ema_data.get('periods', {}).get('ema_3')
                    p4 = ema_data.get('periods', {}).get('ema_4')
                    v1 = ema_data.get('values', {}).get('ema_1')
                    v2 = ema_data.get('values', {}).get('ema_2')
                    v3 = ema_data.get('values', {}).get('ema_3')
                    v4 = ema_data.get('values', {}).get('ema_4')

                    self.ema_1_label.setText(f"EMA ({p1}): {v1:.5f}" if v1 is not None else f"EMA ({p1}): --")
                    self.ema_2_label.setText(f"EMA ({p2}): {v2:.5f}" if v2 is not None else f"EMA ({p2}): --")
                    self.ema_3_label.setText(f"EMA ({p3}): {v3:.5f}" if v3 is not None else f"EMA ({p3}): --")
                    self.ema_4_label.setText(f"EMA ({p4}): {v4:.5f}" if v4 is not None else f"EMA ({p4}): --")
                else:
                    self.ema_1_label.setText("EMA 1: Calculating...")
                    self.ema_2_label.setText("EMA 2: --")
                    self.ema_3_label.setText("EMA 3: --")
                    self.ema_4_label.setText("EMA 4: --")
            else:
                self.ema_1_label.setText("EMA 1: -- (No active bot)")
                self.ema_2_label.setText("EMA 2: --")
                self.ema_3_label.setText("EMA 3: --")
                self.ema_4_label.setText("EMA 4: --")
        elif self.strategy_type == 'supertrend':
            if self.current_bot and isinstance(self.current_bot, SuperTrendStrategy):
                snap = self.current_bot.get_supertrend_snapshot()
                if snap:
                    trend = snap.get("trend")
                    trend_txt = "UP" if trend == 1 else "DOWN" if trend == -1 else "--"
                    self.supertrend_trend_label.setText(f"Trend: {trend_txt}")

                    atr_val = snap.get("atr")
                    self.supertrend_atr_label.setText(f"ATR: {atr_val:.5f}" if atr_val is not None else "ATR: --")

                    ub = snap.get("upper_band")
                    lb = snap.get("lower_band")
                    self.supertrend_upper_label.setText(f"Upper Band: {ub:.5f}" if ub is not None else "Upper Band: --")
                    self.supertrend_lower_label.setText(f"Lower Band: {lb:.5f}" if lb is not None else "Lower Band: --")
                else:
                    self.supertrend_trend_label.setText("Trend: Calculating...")
                    self.supertrend_atr_label.setText("ATR: --")
                    self.supertrend_upper_label.setText("Upper Band: --")
                    self.supertrend_lower_label.setText("Lower Band: --")
            else:
                self.supertrend_trend_label.setText("Trend: -- (No active bot)")
                self.supertrend_atr_label.setText("ATR: --")
                self.supertrend_upper_label.setText("Upper Band: --")
                self.supertrend_lower_label.setText("Lower Band: --")
        else:
            # Update OHLC display
            ohlc = self.market_data_panel.ohlc_data.get(symbol.upper())
            if ohlc:
                self.ohlc_label.setText(
                    f"Previous Session OHLC: O={ohlc.get('open', '--'):.5f}, "
                    f"H={ohlc.get('high', '--'):.5f}, L={ohlc.get('low', '--'):.5f}, "
                    f"C={ohlc.get('close', '--'):.5f}"
                )
            else:
                self.ohlc_label.setText("Previous Session OHLC: Not available (fetching...)")

        # Update Structure display (formerly SMC)
        if self.strategy_type == 'smc' or self.strategy_type == 'structure':
            if self.current_bot and isinstance(self.current_bot, StructureStrategy):
                ph = self.current_bot.last_pivot_high.price if self.current_bot.last_pivot_high else None
                pl = self.current_bot.last_pivot_low.price if self.current_bot.last_pivot_low else None
                ph_txt = f"{ph:.5f}" if ph is not None else "--"
                pl_txt = f"{pl:.5f}" if pl is not None else "--"
                bias = self.current_bot.bias or "--"
                ev = self.current_bot.last_structure_event or "--"
                self.smc_status_label.setText(f"Structure: Bias={bias} | Last={ev} | PH={ph_txt} | PL={pl_txt}")
            else:
                self.smc_status_label.setText("Structure: -- (No active bot)")
        
        # Check if bot is active
        if self.current_bot and self.current_bot.enabled:
            self.status_label.setText(f"Status: Active - {self.current_bot.name}")
        else:
            self.status_label.setText("Status: Not Active")

