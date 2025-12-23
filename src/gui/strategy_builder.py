"""
Strategy Builder
Interface for creating indicator-based and time-based strategies
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
                             QPushButton, QGroupBox, QCheckBox, QTimeEdit,
                             QListWidget, QListWidgetItem, QMessageBox, QLabel,
                             QScrollArea)
from PyQt6.QtCore import Qt, QTime
from typing import Dict, Optional

from ..data_feed import DataFeed
from ..strategy.strategy_manager import StrategyManager
from ..strategy.base_strategy import BaseStrategy
from ..mt5_connector import MT5Connector
from ..indicators import SMA, EMA, RSI, MACD, BollingerBands, Stochastic


class StrategyBuilder(QWidget):
    """Strategy builder interface"""
    
    def __init__(self, data_feed: DataFeed, strategy_manager: StrategyManager,
                 mt5: MT5Connector):
        super().__init__()
        self.data_feed = data_feed
        self.strategy_manager = strategy_manager
        self.mt5 = mt5
        
        # Track last bar time for each symbol/timeframe to detect new bars
        self.last_bar_times = {}  # (symbol, timeframe) -> datetime
        
        self.setup_ui()
        
        # Connect to data feed signals for real-time updates
        if hasattr(data_feed, 'tick_received'):
            # Update symbol list when new ticks arrive (indicates new symbol added)
            self.data_feed.tick_received.connect(self._on_tick_received)
            # Update RSI value in real-time when new tick data arrives (like price streaming)
            self.data_feed.tick_received.connect(self._on_tick_for_rsi_update)
        
        # Setup timer to update indicator values continuously
        # MT5's RSI includes current forming bar, so it updates in real-time
        from PyQt6.QtCore import QTimer
        self.value_update_timer = QTimer()
        self.value_update_timer.timeout.connect(self._check_and_update_indicator)
        # Update every 0.5 seconds for live RSI values (MT5's RSI includes current bar)
        self.value_update_timer.start(500)
    
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
        
        # Strategy name and symbol
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., My RSI Strategy")
        basic_layout.addRow("Strategy Name:", self.name_input)
        
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.setPlaceholderText("Select or enter symbol")
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed_for_builder)
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
        
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)
        
        # Indicators section
        indicators_group = QGroupBox("Indicators")
        indicators_layout = QVBoxLayout()
        
        indicator_select_layout = QHBoxLayout()
        self.indicator_combo = QComboBox()
        self.indicator_combo.addItems([
            "SMA", "EMA", "RSI", "MACD", "Bollinger Bands", "Stochastic"
        ])
        indicator_select_layout.addWidget(self.indicator_combo)
        
        self.period_spin = QSpinBox()
        self.period_spin.setMinimum(1)
        self.period_spin.setMaximum(200)
        self.period_spin.setValue(14)
        indicator_select_layout.addWidget(QLabel("Period:"))
        indicator_select_layout.addWidget(self.period_spin)
        
        add_indicator_btn = QPushButton("Add Indicator")
        add_indicator_btn.clicked.connect(self.add_indicator)
        indicator_select_layout.addWidget(add_indicator_btn)
        
        indicators_layout.addLayout(indicator_select_layout)
        
        self.indicators_list = QListWidget()
        indicators_layout.addWidget(self.indicators_list)
        
        indicators_group.setLayout(indicators_layout)
        layout.addWidget(indicators_group)
        
        # Entry conditions
        entry_group = QGroupBox("Entry Conditions")
        entry_layout = QVBoxLayout()
        
        # Current indicator value display
        current_value_layout = QHBoxLayout()
        current_value_layout.addWidget(QLabel("Current Indicator Value:"))
        self.current_value_label = QLabel("--")
        self.current_value_label.setStyleSheet("font-weight: bold; color: #4CAF50; font-size: 14px;")
        self.current_value_label.setToolTip("Live indicator value (updates every second). For RSI, uses MT5's built-in calculation.")
        current_value_layout.addWidget(self.current_value_label)
        
        refresh_value_btn = QPushButton("Refresh Value")
        refresh_value_btn.clicked.connect(self.update_current_indicator_value)
        current_value_layout.addWidget(refresh_value_btn)
        
        use_current_btn = QPushButton("Use Current Value")
        use_current_btn.clicked.connect(self.use_current_value)
        current_value_layout.addWidget(use_current_btn)
        
        current_value_layout.addStretch()
        entry_layout.addLayout(current_value_layout)
        
        condition_layout = QHBoxLayout()
        self.entry_indicator_combo = QComboBox()
        self.entry_indicator_combo.currentTextChanged.connect(self.update_current_indicator_value)
        condition_layout.addWidget(QLabel("Indicator:"))
        condition_layout.addWidget(self.entry_indicator_combo)
        
        self.entry_operator_combo = QComboBox()
        self.entry_operator_combo.addItems([">", "<", ">=", "<=", "=="])
        condition_layout.addWidget(self.entry_operator_combo)
        
        self.entry_value_spin = QDoubleSpinBox()
        self.entry_value_spin.setMinimum(-1000)
        self.entry_value_spin.setMaximum(1000)
        self.entry_value_spin.setDecimals(5)
        condition_layout.addWidget(self.entry_value_spin)
        
        self.entry_signal_combo = QComboBox()
        self.entry_signal_combo.addItems(["BUY", "SELL"])
        condition_layout.addWidget(self.entry_signal_combo)
        
        add_entry_btn = QPushButton("Add Entry Condition")
        add_entry_btn.clicked.connect(self.add_entry_condition)
        condition_layout.addWidget(add_entry_btn)
        
        entry_layout.addLayout(condition_layout)
        
        self.entry_conditions_list = QListWidget()
        entry_layout.addWidget(self.entry_conditions_list)
        
        entry_group.setLayout(entry_layout)
        layout.addWidget(entry_group)

        # Buy & Sell Conditions (indicator-based)
        buy_sell_group = QGroupBox("Buy & Sell Conditions")
        buy_sell_layout = QVBoxLayout()

        # Buy row
        buy_row = QHBoxLayout()
        buy_row.addWidget(QLabel("Buy:"))
        self.buy_indicator_combo = QComboBox()
        buy_row.addWidget(self.buy_indicator_combo)
        self.buy_operator_combo = QComboBox()
        self.buy_operator_combo.addItems([">", "<", ">=", "<=", "=="])
        buy_row.addWidget(self.buy_operator_combo)
        self.buy_value_spin = QDoubleSpinBox()
        self.buy_value_spin.setMinimum(-100000.0)
        self.buy_value_spin.setMaximum(100000.0)
        self.buy_value_spin.setDecimals(5)
        buy_row.addWidget(self.buy_value_spin)
        add_buy_btn = QPushButton("Add Buy Condition")
        add_buy_btn.clicked.connect(self.add_buy_condition)
        buy_row.addWidget(add_buy_btn)
        buy_sell_layout.addLayout(buy_row)

        self.buy_conditions_list = QListWidget()
        buy_sell_layout.addWidget(self.buy_conditions_list)

        # Sell row
        sell_row = QHBoxLayout()
        sell_row.addWidget(QLabel("Sell:"))
        self.sell_indicator_combo = QComboBox()
        sell_row.addWidget(self.sell_indicator_combo)
        self.sell_operator_combo = QComboBox()
        self.sell_operator_combo.addItems([">", "<", ">=", "<=", "=="])
        sell_row.addWidget(self.sell_operator_combo)
        self.sell_value_spin = QDoubleSpinBox()
        self.sell_value_spin.setMinimum(-100000.0)
        self.sell_value_spin.setMaximum(100000.0)
        self.sell_value_spin.setDecimals(5)
        sell_row.addWidget(self.sell_value_spin)
        add_sell_btn = QPushButton("Add Sell Condition")
        add_sell_btn.clicked.connect(self.add_sell_condition)
        sell_row.addWidget(add_sell_btn)
        buy_sell_layout.addLayout(sell_row)

        self.sell_conditions_list = QListWidget()
        buy_sell_layout.addWidget(self.sell_conditions_list)

        buy_sell_group.setLayout(buy_sell_layout)
        layout.addWidget(buy_sell_group)
        
        # Trade Monitoring Mode (AlgoTest architecture)
        monitoring_group = QGroupBox("Trade Monitoring Mode")
        monitoring_layout = QFormLayout()
        
        self.monitoring_mode_combo = QComboBox()
        self.monitoring_mode_combo.addItem("LTP (Last Traded Price)", "LTP")
        self.monitoring_mode_combo.addItem("Candle Close (1-Min)", "CANDLE_CLOSE")
        self.monitoring_mode_combo.setToolTip(
            "LTP: Executes immediately when conditions are met (continuous monitoring)\n"
            "Candle Close: Executes on 1-minute candle close (59th second)"
        )
        monitoring_layout.addRow("Monitoring Mode:", self.monitoring_mode_combo)
        
        monitoring_group.setLayout(monitoring_layout)
        layout.addWidget(monitoring_group)
        
        # Stop Loss / Take Profit
        sl_tp_group = QGroupBox("Stop Loss / Take Profit")
        sl_tp_layout = QFormLayout()
        
        # SL Type
        self.sl_type_combo = QComboBox()
        self.sl_type_combo.addItems(["Price (Pips)", "Price (Points)", "Percentage"])
        self.sl_type_combo.currentTextChanged.connect(self.on_sl_type_changed)
        sl_tp_layout.addRow("SL Type:", self.sl_type_combo)
        
        # SL Value
        self.sl_value_spin = QDoubleSpinBox()
        self.sl_value_spin.setMinimum(0.0)
        self.sl_value_spin.setMaximum(10000.0)
        self.sl_value_spin.setDecimals(2)
        self.sl_value_spin.setValue(20.0)  # Default 20 pips
        self.sl_value_spin.valueChanged.connect(self.on_sl_value_changed)
        sl_tp_layout.addRow("Stop Loss:", self.sl_value_spin)
        
        # Use 1:2 Ratio checkbox
        self.use_ratio_check = QCheckBox("Use 1:2 Risk:Reward Ratio (TP = 2x SL)")
        self.use_ratio_check.setChecked(True)
        self.use_ratio_check.toggled.connect(self.on_ratio_toggled)
        sl_tp_layout.addRow("", self.use_ratio_check)
        
        # TP Value (disabled if ratio is checked)
        self.tp_value_spin = QDoubleSpinBox()
        self.tp_value_spin.setMinimum(0.0)
        self.tp_value_spin.setMaximum(10000.0)
        self.tp_value_spin.setDecimals(2)
        self.tp_value_spin.setValue(40.0)  # Default 40 pips (2x SL)
        self.tp_value_spin.setEnabled(False)  # Disabled when ratio is used
        sl_tp_layout.addRow("Take Profit:", self.tp_value_spin)
        
        sl_tp_group.setLayout(sl_tp_layout)
        layout.addWidget(sl_tp_group)
        
        # Re-Entry Configuration (AlgoTest architecture)
        reentry_group = QGroupBox("Re-Entry on SL or Target")
        reentry_layout = QHBoxLayout()  # Horizontal layout for side-by-side
        
        # Re-Entry on Stop Loss
        sl_reentry_group = QGroupBox("Re-Entry on Stop Loss")
        sl_reentry_layout = QFormLayout()
        
        self.sl_reentry_enabled = QCheckBox("Enable Re-Entry on SL")
        sl_reentry_layout.addRow(self.sl_reentry_enabled)
        
        self.sl_reentry_mode_combo = QComboBox()
        self.sl_reentry_mode_combo.addItem("RE-ASAP", "RE_ASAP")
        self.sl_reentry_mode_combo.addItem("RE-ASAP Reverse", "RE_ASAP_REVERSE")
        self.sl_reentry_mode_combo.addItem("RE-COST", "RE_COST")
        self.sl_reentry_mode_combo.addItem("RE-COST Reverse", "RE_COST_REVERSE")
        self.sl_reentry_mode_combo.setToolTip(
            "RE-ASAP: Re-enter immediately after SL hit\n"
            "RE-ASAP Reverse: Re-enter immediately in reverse position\n"
            "RE-COST: Re-enter at original entry price\n"
            "RE-COST Reverse: Re-enter in reverse at original entry price"
        )
        sl_reentry_layout.addRow("Mode:", self.sl_reentry_mode_combo)
        
        self.sl_reentry_count_spin = QSpinBox()
        self.sl_reentry_count_spin.setMinimum(0)
        self.sl_reentry_count_spin.setMaximum(20)
        self.sl_reentry_count_spin.setValue(0)
        self.sl_reentry_count_spin.setToolTip("Maximum number of re-entries on SL (0-20)")
        sl_reentry_layout.addRow("Max Count:", self.sl_reentry_count_spin)
        
        sl_reentry_group.setLayout(sl_reentry_layout)
        reentry_layout.addWidget(sl_reentry_group)
        
        # Re-Entry on Take Profit
        tp_reentry_group = QGroupBox("Re-Entry on Take Profit")
        tp_reentry_layout = QFormLayout()
        
        self.tp_reentry_enabled = QCheckBox("Enable Re-Entry on TP")
        tp_reentry_layout.addRow(self.tp_reentry_enabled)
        
        self.tp_reentry_mode_combo = QComboBox()
        self.tp_reentry_mode_combo.addItem("RE-ASAP", "RE_ASAP")
        self.tp_reentry_mode_combo.addItem("RE-ASAP Reverse", "RE_ASAP_REVERSE")
        self.tp_reentry_mode_combo.addItem("RE-COST", "RE_COST")
        self.tp_reentry_mode_combo.addItem("RE-COST Reverse", "RE_COST_REVERSE")
        self.tp_reentry_mode_combo.setToolTip(
            "RE-ASAP: Re-enter immediately after TP hit\n"
            "RE-ASAP Reverse: Re-enter immediately in reverse position\n"
            "RE-COST: Re-enter at original entry price\n"
            "RE-COST Reverse: Re-enter in reverse at original entry price"
        )
        tp_reentry_layout.addRow("Mode:", self.tp_reentry_mode_combo)
        
        self.tp_reentry_count_spin = QSpinBox()
        self.tp_reentry_count_spin.setMinimum(0)
        self.tp_reentry_count_spin.setMaximum(20)
        self.tp_reentry_count_spin.setValue(0)
        self.tp_reentry_count_spin.setToolTip("Maximum number of re-entries on TP (0-20)")
        tp_reentry_layout.addRow("Max Count:", self.tp_reentry_count_spin)
        
        tp_reentry_group.setLayout(tp_reentry_layout)
        reentry_layout.addWidget(tp_reentry_group)
        
        reentry_group.setLayout(reentry_layout)
        layout.addWidget(reentry_group)
        
        # Time rules
        time_group = QGroupBox("Trading Hours")
        time_layout = QFormLayout()
        
        self.time_enabled_check = QCheckBox("Enable time restrictions")
        time_layout.addRow(self.time_enabled_check)
        
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setTime(QTime(9, 0))
        time_layout.addRow("Start Time:", self.start_time_edit)
        
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setTime(QTime(17, 0))
        time_layout.addRow("End Time:", self.end_time_edit)
        
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)
        
        # Add stretch at the end to push everything up
        layout.addStretch()
        
        # Set the form widget to scroll area
        scroll_area.setWidget(form_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
        # Buttons (always visible at bottom, outside scroll area)
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save Strategy")
        save_btn.clicked.connect(self.save_strategy)
        save_btn.setMinimumHeight(35)
        button_layout.addWidget(save_btn)
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_form)
        clear_btn.setMinimumHeight(35)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # Initialize
        self.clear_form()
        self.update_symbol_list()
    
    def update_symbol_list(self):
        """Update symbol combo box with all available symbols"""
        self.symbol_combo.clear()
        
        # First, add symbols that are already in the data feed
        for symbol in self.data_feed.symbols:
            self.symbol_combo.addItem(symbol)
        
        # Also add all available symbols from MT5 if connected
        if self.mt5 and self.mt5.is_connected():
            try:
                available_symbols = self.mt5.get_available_symbols()
                for symbol in available_symbols:
                    # Only add if not already in the list
                    if self.symbol_combo.findText(symbol) == -1:
                        self.symbol_combo.addItem(symbol)
            except Exception as e:
                pass  # Silently fail if can't get symbols
        
        # Make combo box editable so user can type symbol names
        self.symbol_combo.setEditable(True)
        self.symbol_combo.lineEdit().setPlaceholderText("Select or type symbol")
    
    def _on_tick_received(self, symbol: str, tick_data: dict):
        """Handle tick received signal to update symbol list"""
        # Check if this symbol is new
        if self.symbol_combo.findText(symbol) == -1:
            self.symbol_combo.addItem(symbol)
    
    def _on_tick_for_rsi_update(self, symbol: str, tick_data: dict):
        """Handle tick received signal - update RSI value in real-time"""
        # Only update if RSI indicator is selected and symbol matches
        current_symbol = self.symbol_combo.currentText().strip()
        if not current_symbol or current_symbol.upper() != symbol.upper():
            return
        
        indicator_text = self.entry_indicator_combo.currentText()
        if not indicator_text:
            return
        
        # Check if RSI is selected
        indicator_name = indicator_text.split("(")[0].strip() if "(" in indicator_text else indicator_text.strip()
        if indicator_name.upper() == "RSI":
            # Update RSI value on each tick (MT5's RSI includes current forming bar)
            # This gives live updates matching MT5's chart
            self.update_current_indicator_value()
    
    def on_symbol_changed_for_builder(self, symbol: str):
        """Handle symbol change in builder - update indicator value"""
        if symbol:
            # Update current indicator value when symbol changes
            self.update_current_indicator_value()
    
    def on_sl_type_changed(self, text: str):
        """Handle SL type change - update value range"""
        if "Pips" in text:
            self.sl_value_spin.setMaximum(10000.0)
            self.sl_value_spin.setDecimals(1)
        elif "Points" in text:
            self.sl_value_spin.setMaximum(10000.0)
            self.sl_value_spin.setDecimals(5)
        else:  # Percentage
            self.sl_value_spin.setMaximum(100.0)
            self.sl_value_spin.setDecimals(2)
        # Update TP if ratio is enabled
        if self.use_ratio_check.isChecked():
            self.on_ratio_toggled(True)
    
    def on_ratio_toggled(self, checked: bool):
        """Handle 1:2 ratio checkbox toggle"""
        self.tp_value_spin.setEnabled(not checked)
        if checked:
            # Auto-calculate TP as 2x SL
            tp_value = self.sl_value_spin.value() * 2.0
            self.tp_value_spin.setValue(tp_value)
    
    def on_sl_value_changed(self, value: float):
        """Handle SL value change - update TP if ratio is enabled"""
        if self.use_ratio_check.isChecked():
            self.tp_value_spin.setValue(value * 2.0)
    
    def _check_and_update_indicator(self):
        """Check if new bar closed and update indicator if needed"""
        symbol = self.symbol_combo.currentText().strip()
        if not symbol:
            return
        
        indicator_text = self.entry_indicator_combo.currentText()
        if not indicator_text:
            return
        
        # Check if RSI is selected
        indicator_name = indicator_text.split("(")[0].strip() if "(" in indicator_text else indicator_text.strip()
        if indicator_name.upper() == "RSI":
            import MetaTrader5 as mt5
            timeframe = self.timeframe_combo.currentData()
            if timeframe is None:
                timeframe = mt5.TIMEFRAME_M1
            
            # Check if a new bar has closed
            key = (symbol.upper(), timeframe)
            last_bar_time = self.mt5.get_last_bar_time(symbol, timeframe)
            
            if last_bar_time:
                # Check if this is a new bar
                if key not in self.last_bar_times or self.last_bar_times[key] != last_bar_time:
                    # New bar closed - update RSI value
                    self.last_bar_times[key] = last_bar_time
                    self.update_current_indicator_value()
    
    def update_current_indicator_value(self):
        """Calculate and display current indicator value"""
        symbol = self.symbol_combo.currentText().strip()
        if not symbol:
            self.current_value_label.setText("-- (Select symbol)")
            return
        
        indicator_text = self.entry_indicator_combo.currentText()
        if not indicator_text:
            self.current_value_label.setText("-- (Select indicator)")
            return
        
        # Get correct symbol name (case-sensitive from data feed or MT5)
        correct_symbol = symbol
        if symbol not in self.data_feed.symbols:
            if self.mt5 and self.mt5.is_connected():
                if not self.data_feed.add_symbol(symbol):
                    self.current_value_label.setText("-- (Symbol not available)")
                    return
                # After adding, find the correct case symbol
                for feed_symbol in self.data_feed.symbols:
                    if feed_symbol.upper() == symbol.upper():
                        correct_symbol = feed_symbol
                        break
        else:
            # Symbol is in feed, use it as-is (already correct case)
            correct_symbol = symbol
        
        # Get selected timeframe
        import MetaTrader5 as mt5
        timeframe = self.timeframe_combo.currentData()
        if timeframe is None:
            timeframe = mt5.TIMEFRAME_M1  # Default to M1
        
        # Parse indicator name and period
        indicator_name = indicator_text.split("(")[0].strip() if "(" in indicator_text else indicator_text.strip()
        period = 14
        if "(" in indicator_text:
            try:
                period = int(indicator_text.split("(")[1].split(")")[0])
            except:
                pass
        
        # For RSI, use MT5's built-in calculation for accuracy with live updates
        if indicator_name.upper() == "RSI":
            if self.mt5 and self.mt5.is_connected():
                import logging
                logger = logging.getLogger(__name__)
                
                # Verify symbol is available in MT5
                symbol_info = self.mt5.get_symbol_info(correct_symbol)
                if not symbol_info:
                    logger.warning(f"Symbol {correct_symbol} not found in MT5, trying {symbol}")
                    symbol_info = self.mt5.get_symbol_info(symbol)
                    if symbol_info:
                        correct_symbol = symbol_info['name']
                        logger.info(f"Using correct symbol name: {correct_symbol}")
                
                try:
                    # Use MT5's RSI calculation (includes current forming bar)
                    # This gives exact MT5 values that update in real-time
                    logger.debug(f"Getting MT5 RSI for {correct_symbol}, timeframe={timeframe}, period={period}")
                    
                    # Try with correct symbol name first
                    mt5_rsi = self.mt5.get_rsi(correct_symbol, timeframe, period, 300)
                    
                    # If that fails, try with original symbol (in case MT5 accepts it)
                    if mt5_rsi is None and correct_symbol != symbol:
                        logger.debug(f"Trying original symbol {symbol} for RSI")
                        mt5_rsi = self.mt5.get_rsi(symbol, timeframe, period, 300)
                    
                    if mt5_rsi is not None:
                        logger.debug(f"MT5 RSI value: {mt5_rsi:.2f} for {correct_symbol}")
                        self.current_value_label.setText(f"{mt5_rsi:.2f} (MT5 Exact)")
                        return
                    else:
                        logger.warning(f"MT5 RSI returned None for {correct_symbol}, falling back to calculated")
                except Exception as e:
                    logger.error(f"Error getting MT5 RSI: {e}", exc_info=True)
            
            # Fallback to our calculation if MT5 method fails
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Using calculated RSI fallback for {correct_symbol}")
            rates = self.data_feed.get_rates(correct_symbol, timeframe, 300)
            if not rates:
                if self.mt5 and self.mt5.is_connected():
                    rates = self.mt5.get_rates(correct_symbol, timeframe, 300)
            
            if not rates or len(rates) < period + 1:
                self.current_value_label.setText("-- (Insufficient data)")
                return
            
            try:
                from ..indicators import RSI
                indicator = RSI(period)
                indicator.update(rates)
                value = indicator.get_value()
                if value is not None:
                    self.current_value_label.setText(f"{value:.2f} (Calculated)")
                    return
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error calculating RSI: {e}")
            
            self.current_value_label.setText("-- (Calculation error)")
            return
        
        # For other indicators, use our calculation
        rates = self.data_feed.get_rates(symbol, timeframe, 300)
        if not rates:
            if self.mt5 and self.mt5.is_connected():
                rates = self.mt5.get_rates(symbol, timeframe, 300)
        
        if not rates or len(rates) < 20:
            self.current_value_label.setText("-- (Insufficient data)")
            return
        
        # Calculate indicator
        try:
            from ..indicators import SMA, EMA, MACD, BollingerBands, Stochastic
            
            indicator = None
            if indicator_name.upper() == "SMA":
                indicator = SMA(period)
            elif indicator_name.upper() == "EMA":
                indicator = EMA(period)
            elif indicator_name.upper() == "MACD":
                indicator = MACD()
            elif "BOLLINGER" in indicator_name.upper() or indicator_name.upper() == "BB":
                indicator = BollingerBands(period)
            elif "STOCH" in indicator_name.upper():
                indicator = Stochastic(period)
            
            if indicator:
                indicator.update(rates)
                value = indicator.get_value()
                if value is not None:
                    self.current_value_label.setText(f"{value:.5f}")
                    return
        
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating indicator value: {e}")
        
        self.current_value_label.setText("-- (Calculation error)")
    
    def use_current_value(self):
        """Use the current indicator value in the value spin box"""
        value_text = self.current_value_label.text()
        if value_text and value_text != "--" and "(" not in value_text:
            try:
                value = float(value_text)
                self.entry_value_spin.setValue(value)
            except ValueError:
                pass
    
    def add_indicator(self):
        """Add an indicator"""
        indicator_name = self.indicator_combo.currentText()
        period = self.period_spin.value()
        
        item_text = f"{indicator_name}({period})"
        self.indicators_list.addItem(item_text)
        
        # Update entry indicator combo
        self.entry_indicator_combo.addItem(item_text)
        # Update buy/sell combos
        self.buy_indicator_combo.addItem(item_text)
        self.sell_indicator_combo.addItem(item_text)
    
    def add_entry_condition(self):
        """Add an entry condition"""
        indicator = self.entry_indicator_combo.currentText()
        operator = self.entry_operator_combo.currentText()
        value = self.entry_value_spin.value()
        signal = self.entry_signal_combo.currentText()
        
        condition_text = f"{indicator} {operator} {value} -> {signal}"
        self.entry_conditions_list.addItem(condition_text)

    def add_buy_condition(self):
        """Add a buy condition (indicator-based)"""
        indicator = self.buy_indicator_combo.currentText()
        operator = self.buy_operator_combo.currentText()
        value = self.buy_value_spin.value()
        condition_text = f"{indicator} {operator} {value}"
        self.buy_conditions_list.addItem(condition_text)

    def add_sell_condition(self):
        """Add a sell condition (indicator-based)"""
        indicator = self.sell_indicator_combo.currentText()
        operator = self.sell_operator_combo.currentText()
        value = self.sell_value_spin.value()
        condition_text = f"{indicator} {operator} {value}"
        self.sell_conditions_list.addItem(condition_text)
    
    def clear_form(self):
        """Clear the form"""
        self.name_input.clear()
        self.indicators_list.clear()
        self.entry_conditions_list.clear()
        self.entry_indicator_combo.clear()
        self.buy_conditions_list.clear()
        self.sell_conditions_list.clear()
        self.buy_indicator_combo.clear()
        self.sell_indicator_combo.clear()
        self.time_enabled_check.setChecked(False)
        # Clear re-entry settings
        self.sl_reentry_enabled.setChecked(False)
        self.sl_reentry_count_spin.setValue(0)
        self.tp_reentry_enabled.setChecked(False)
        self.tp_reentry_count_spin.setValue(0)
        # Clear editing flag
        if hasattr(self, 'editing_strategy_name'):
            self.editing_strategy_name = None
    
    def load_strategy(self, strategy):
        """Load a strategy into the form for editing"""
        from ..strategy.base_strategy import BaseStrategy
        
        if not isinstance(strategy, BaseStrategy):
            return
        
        # Set editing flag
        self.editing_strategy_name = strategy.name
        
        # Clear form first
        self.clear_form()
        self.editing_strategy_name = strategy.name  # Restore after clear
        
        # Load basic info
        self.name_input.setText(strategy.name)
        self.symbol_combo.setCurrentText(strategy.symbol)
        
        # Load timeframe
        if hasattr(strategy, 'timeframe'):
            import MetaTrader5 as mt5
            timeframe = strategy.timeframe
            for i in range(self.timeframe_combo.count()):
                if self.timeframe_combo.itemData(i) == timeframe:
                    self.timeframe_combo.setCurrentIndex(i)
                    break
        
        # Load indicators
        for ind_name, indicator in strategy.indicators.items():
            period = getattr(indicator, 'period', 14)
            indicator_type = type(indicator).__name__
            item_text = f"{indicator_type}({period})"
            self.indicators_list.addItem(item_text)
            self.entry_indicator_combo.addItem(item_text)
            self.buy_indicator_combo.addItem(item_text)
            self.sell_indicator_combo.addItem(item_text)
        
        # Load entry conditions
        if hasattr(strategy, 'entry_conditions_text'):
            for condition_text in strategy.entry_conditions_text:
                self.entry_conditions_list.addItem(condition_text)

        # Load buy/sell conditions
        if hasattr(strategy, 'buy_conditions_text'):
            for condition_text in strategy.buy_conditions_text:
                self.buy_conditions_list.addItem(condition_text)
        if hasattr(strategy, 'sell_conditions_text'):
            for condition_text in strategy.sell_conditions_text:
                self.sell_conditions_list.addItem(condition_text)
        
        # Load trade monitoring mode
        monitoring_mode = getattr(strategy, 'trade_monitoring_mode', 'LTP')
        for i in range(self.monitoring_mode_combo.count()):
            if self.monitoring_mode_combo.itemData(i) == monitoring_mode:
                self.monitoring_mode_combo.setCurrentIndex(i)
                break
        
        # Load SL/TP configuration
        if hasattr(strategy, 'sl_type') and strategy.sl_type:
            sl_type_text = strategy.sl_type
            for i in range(self.sl_type_combo.count()):
                if self.sl_type_combo.itemText(i) == sl_type_text:
                    self.sl_type_combo.setCurrentIndex(i)
                    break
        
        if hasattr(strategy, 'sl_value'):
            self.sl_value_spin.setValue(strategy.sl_value)
        
        if hasattr(strategy, 'use_ratio'):
            self.use_ratio_check.setChecked(strategy.use_ratio)
        
        if hasattr(strategy, 'tp_value'):
            self.tp_value_spin.setValue(strategy.tp_value)
        
        # Load re-entry configuration
        if hasattr(strategy, 'reentry_on_sl_enabled'):
            self.sl_reentry_enabled.setChecked(strategy.reentry_on_sl_enabled)
            if strategy.reentry_on_sl_enabled:
                mode = getattr(strategy, 'reentry_on_sl_mode', 'RE_ASAP')
                for i in range(self.sl_reentry_mode_combo.count()):
                    if self.sl_reentry_mode_combo.itemData(i) == mode:
                        self.sl_reentry_mode_combo.setCurrentIndex(i)
                        break
                self.sl_reentry_count_spin.setValue(getattr(strategy, 'reentry_on_sl_count', 0))
        
        if hasattr(strategy, 'reentry_on_tp_enabled'):
            self.tp_reentry_enabled.setChecked(strategy.reentry_on_tp_enabled)
            if strategy.reentry_on_tp_enabled:
                mode = getattr(strategy, 'reentry_on_tp_mode', 'RE_ASAP')
                for i in range(self.tp_reentry_mode_combo.count()):
                    if self.tp_reentry_mode_combo.itemData(i) == mode:
                        self.tp_reentry_mode_combo.setCurrentIndex(i)
                        break
                self.tp_reentry_count_spin.setValue(getattr(strategy, 'reentry_on_tp_count', 0))
        
        # Load time rules
        if strategy.time_rules:
            self.time_enabled_check.setChecked(True)
            first_rule = strategy.time_rules[0]
            from PyQt6.QtCore import QTime
            from datetime import time as dt_time
            
            # Handle time object (from datetime.time)
            start_time_obj = first_rule['start_time']
            end_time_obj = first_rule['end_time']
            
            if isinstance(start_time_obj, dt_time):
                start_time = QTime(start_time_obj.hour, start_time_obj.minute, start_time_obj.second)
            elif isinstance(start_time_obj, str):
                # Try parsing string format
                try:
                    parts = start_time_obj.split(':')
                    start_time = QTime(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
                except:
                    start_time = QTime(9, 0)
            else:
                start_time = QTime(9, 0)
            
            if isinstance(end_time_obj, dt_time):
                end_time = QTime(end_time_obj.hour, end_time_obj.minute, end_time_obj.second)
            elif isinstance(end_time_obj, str):
                try:
                    parts = end_time_obj.split(':')
                    end_time = QTime(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)
                except:
                    end_time = QTime(17, 0)
            else:
                end_time = QTime(17, 0)
            
            self.start_time_edit.setTime(start_time)
            self.end_time_edit.setTime(end_time)
    
    def save_strategy(self):
        """Save the strategy"""
        name = self.name_input.text().strip()
        symbol = self.symbol_combo.currentText().strip().upper()
        
        if not name or not symbol:
            QMessageBox.warning(self, "Validation Error", "Please enter strategy name and symbol")
            return
        
        # Check if editing existing strategy (name change not allowed)
        is_editing = hasattr(self, 'editing_strategy_name') and self.editing_strategy_name
        if is_editing and name != self.editing_strategy_name:
            QMessageBox.warning(self, "Error", "Cannot change strategy name when editing. Please use the original name.")
            self.name_input.setText(self.editing_strategy_name)
            return
        
        if self.indicators_list.count() == 0:
            QMessageBox.warning(self, "Validation Error", "Please add at least one indicator")
            return
        
        if (self.entry_conditions_list.count() == 0 and
            self.buy_conditions_list.count() == 0 and
            self.sell_conditions_list.count() == 0):
            QMessageBox.warning(self, "Validation Error", "Please add at least one entry, buy, or sell condition")
            return
        
        # Get selected timeframe
        timeframe = self.timeframe_combo.currentData()
        if timeframe is None:
            import MetaTrader5 as mt5
            timeframe = mt5.TIMEFRAME_M1  # Default to M1
        
        # Create strategy
        strategy = CustomStrategy(name, symbol, self, timeframe)
        
        # Add indicators - use consistent naming
        indicator_map = {}  # Map display name to actual indicator name
        for i in range(self.indicators_list.count()):
            item_text = self.indicators_list.item(i).text()
            # Parse indicator (simplified)
            if "SMA" in item_text:
                period = int(item_text.split("(")[1].split(")")[0])
                indicator = SMA(period)
                ind_name = "SMA"
                strategy.add_indicator(ind_name, indicator)
                indicator_map[item_text] = ind_name
            elif "EMA" in item_text:
                period = int(item_text.split("(")[1].split(")")[0])
                indicator = EMA(period)
                ind_name = "EMA"
                strategy.add_indicator(ind_name, indicator)
                indicator_map[item_text] = ind_name
            elif "RSI" in item_text:
                period = int(item_text.split("(")[1].split(")")[0])
                indicator = RSI(period)
                ind_name = "RSI"
                strategy.add_indicator(ind_name, indicator)
                indicator_map[item_text] = ind_name
            elif "MACD" in item_text:
                # MACD might have multiple parameters, use default for now
                indicator = MACD()
                ind_name = "MACD"
                strategy.add_indicator(ind_name, indicator)
                indicator_map[item_text] = ind_name
            elif "Bollinger" in item_text or "BB" in item_text:
                period = int(item_text.split("(")[1].split(")")[0]) if "(" in item_text else 20
                indicator = BollingerBands(period)
                ind_name = "BollingerBands"
                strategy.add_indicator(ind_name, indicator)
                indicator_map[item_text] = ind_name
            elif "Stochastic" in item_text:
                period = int(item_text.split("(")[1].split(")")[0]) if "(" in item_text else 14
                indicator = Stochastic(period)
                ind_name = "Stochastic"
                strategy.add_indicator(ind_name, indicator)
                indicator_map[item_text] = ind_name
        
        # Store entry conditions text for persistence
        entry_conditions_text = []
        
        # Add entry conditions with proper parsing
        def create_entry_condition(condition_text: str):
            """Parse condition text and create evaluable condition function"""
            # Parse format: "Indicator(period) operator value -> signal"
            # Example: "RSI(14) > 70 -> SELL"
            try:
                # Split by "->" to get condition and signal
                if "->" not in condition_text:
                    return None
                
                condition_part, signal_part = condition_text.split("->", 1)
                signal = signal_part.strip().upper()
                
                if signal not in ['BUY', 'SELL']:
                    return None
                
                # Parse indicator and condition
                condition_part = condition_part.strip()
                
                # Extract operator
                operators = ['>=', '<=', '==', '>', '<']
                operator = None
                operator_pos = -1
                
                for op in operators:
                    pos = condition_part.find(op)
                    if pos >= 0:
                        operator = op
                        operator_pos = pos
                        break
                
                if operator is None:
                    return None
                
                # Split into indicator and value
                indicator_part = condition_part[:operator_pos].strip()
                value_str = condition_part[operator_pos + len(operator):].strip()
                
                try:
                    value = float(value_str)
                except ValueError:
                    return None
                
                # Extract indicator name (remove period if present)
                # Format: "Indicator(period)" or just "Indicator"
                indicator_name = indicator_part
                if '(' in indicator_part:
                    indicator_name = indicator_part.split('(')[0].strip()
                
                # Normalize indicator name for matching
                indicator_name_upper = indicator_name.upper()
                
                # Create condition function
                def condition(data: Dict):
                    import logging
                    logger = logging.getLogger(__name__)
                    
                    indicators = data.get('indicators', {})
                    logger.debug(f"Evaluating condition: {indicator_name} {operator} {value} -> {signal}")
                    logger.debug(f"Available indicators: {list(indicators.keys())}")
                    
                    # Try exact match first
                    indicator_value = indicators.get(indicator_name)
                    
                    # Try case-insensitive match
                    if indicator_value is None:
                        for key, val in indicators.items():
                            if key.upper() == indicator_name_upper:
                                indicator_value = val
                                logger.debug(f"Found indicator {key} (case-insensitive match) = {val}")
                                break
                    
                    if indicator_value is None:
                        logger.warning(f"Indicator '{indicator_name}' not found in {list(indicators.keys())}")
                        return None
                    
                    logger.debug(f"Indicator value: {indicator_value}, comparing with {operator} {value}")
                    
                    # Evaluate condition
                    result = False
                    if operator == '>':
                        result = indicator_value > value
                    elif operator == '<':
                        result = indicator_value < value
                    elif operator == '>=':
                        result = indicator_value >= value
                    elif operator == '<=':
                        result = indicator_value <= value
                    elif operator == '==':
                        result = abs(indicator_value - value) < 0.0001  # Float comparison
                    
                    logger.debug(f"Condition result: {result} (value {indicator_value} {operator} {value})")
                    
                    if result:
                        logger.info(f"Condition met! {indicator_name} = {indicator_value} {operator} {value} -> {signal}")
                        return signal
                    return None
                
                return condition
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error parsing condition '{condition_text}': {e}")
                return None
        
        for i in range(self.entry_conditions_list.count()):
            condition_text = self.entry_conditions_list.item(i).text()
            entry_conditions_text.append(condition_text)  # Store for persistence
            condition = create_entry_condition(condition_text)
            if condition:
                strategy.add_entry_condition(condition)
            else:
                QMessageBox.warning(self, "Invalid Condition", 
                                  f"Could not parse condition: {condition_text}")
        
        # Store entry conditions text in strategy for persistence
        strategy.entry_conditions_text = entry_conditions_text

        # Buy/Sell indicator conditions
        def create_side_condition(condition_text: str, signal: str):
            try:
                operators = ['>=', '<=', '==', '>', '<']
                operator = None
                operator_pos = -1
                for op in operators:
                    pos = condition_text.find(op)
                    if pos >= 0:
                        operator = op
                        operator_pos = pos
                        break
                if operator is None:
                    return None
                indicator_part = condition_text[:operator_pos].strip()
                value_str = condition_text[operator_pos + len(operator):].strip()
                value = float(value_str)

                def condition(data: Dict):
                    indicators = data.get('indicators', {})
                    indicator_value = indicators.get(indicator_part)
                    if indicator_value is None:
                        return None
                    if operator == '>':
                        ok = indicator_value > value
                    elif operator == '<':
                        ok = indicator_value < value
                    elif operator == '>=':
                        ok = indicator_value >= value
                    elif operator == '<=':
                        ok = indicator_value <= value
                    elif operator == '==':
                        ok = abs(indicator_value - value) < 0.0001
                    else:
                        ok = False
                    return signal if ok else None

                return condition
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error parsing side condition '{condition_text}': {e}")
                return None

        buy_conditions_text = []
        strategy.buy_condition_funcs = []
        for i in range(self.buy_conditions_list.count()):
            ctext = self.buy_conditions_list.item(i).text()
            buy_conditions_text.append(ctext)
            cond = create_side_condition(ctext, "BUY")
            if cond:
                strategy.buy_condition_funcs.append(cond)

        sell_conditions_text = []
        strategy.sell_condition_funcs = []
        for i in range(self.sell_conditions_list.count()):
            ctext = self.sell_conditions_list.item(i).text()
            sell_conditions_text.append(ctext)
            cond = create_side_condition(ctext, "SELL")
            if cond:
                strategy.sell_condition_funcs.append(cond)

        strategy.buy_conditions_text = buy_conditions_text
        strategy.sell_conditions_text = sell_conditions_text
        
        # Store trade monitoring mode
        strategy.trade_monitoring_mode = self.monitoring_mode_combo.currentData()
        
        # Store SL/TP configuration
        strategy.sl_type = self.sl_type_combo.currentText()
        strategy.sl_value = self.sl_value_spin.value()
        strategy.use_ratio = self.use_ratio_check.isChecked()
        strategy.tp_value = self.tp_value_spin.value() if not strategy.use_ratio else strategy.sl_value * 2.0
        
        # Store Re-Entry configuration
        strategy.reentry_on_sl_enabled = self.sl_reentry_enabled.isChecked()
        strategy.reentry_on_sl_mode = self.sl_reentry_mode_combo.currentData() if strategy.reentry_on_sl_enabled else None
        strategy.reentry_on_sl_count = self.sl_reentry_count_spin.value() if strategy.reentry_on_sl_enabled else 0
        
        strategy.reentry_on_tp_enabled = self.tp_reentry_enabled.isChecked()
        strategy.reentry_on_tp_mode = self.tp_reentry_mode_combo.currentData() if strategy.reentry_on_tp_enabled else None
        strategy.reentry_on_tp_count = self.tp_reentry_count_spin.value() if strategy.reentry_on_tp_enabled else 0
        
        # Add time rules
        if self.time_enabled_check.isChecked():
            start_time = self.start_time_edit.time().toPyTime()
            end_time = self.end_time_edit.time().toPyTime()
            strategy.add_time_rule(start_time, end_time)
        
        # Ensure symbol is in data feed
        if symbol not in self.data_feed.symbols:
            if self.mt5 and self.mt5.is_connected():
                if not self.data_feed.add_symbol(symbol):
                    QMessageBox.warning(self, "Warning", 
                                      f"Symbol {symbol} could not be added to data feed. "
                                      f"Strategy will not receive market data updates.")
        
        # Enable strategy by default
        strategy.enable()
        
        # Add to strategy manager
        if self.strategy_manager.add_strategy(strategy):
            # Save strategy to disk for persistence
            from ..strategy.strategy_persistence import StrategyPersistence
            persistence = StrategyPersistence()
            if persistence.save_strategy(strategy):
                QMessageBox.information(self, "Success", 
                                      f"Strategy '{name}' saved and enabled successfully")
            else:
                QMessageBox.warning(self, "Warning", 
                                  f"Strategy '{name}' added but could not save to disk")
            self.clear_form()
        else:
            QMessageBox.warning(self, "Error", f"Strategy '{name}' already exists")


class CustomStrategy(BaseStrategy):
    """Custom strategy created from builder"""
    
    def __init__(self, name: str, symbol: str, builder: StrategyBuilder = None, timeframe: int = None):
        super().__init__(name, symbol)
        self.builder = builder
        self.entry_conditions_text = []  # Store condition text for persistence
        self.buy_conditions_text = []
        self.sell_conditions_text = []
        self.buy_condition_funcs = []
        self.sell_condition_funcs = []
        # Default to M1 if not specified
        import MetaTrader5 as mt5
        self.timeframe = timeframe if timeframe is not None else mt5.TIMEFRAME_M1
    
    def generate_signal(self, market_data: Dict):
        """Generate signal using buy/sell condition functions first, then entry conditions."""
        # Evaluate buy first
        for cond in self.buy_condition_funcs:
            try:
                res = cond(market_data)
                if res == 'BUY':
                    return 'BUY'
            except Exception:
                continue
        # Evaluate sell second
        for cond in self.sell_condition_funcs:
            try:
                res = cond(market_data)
                if res == 'SELL':
                    return 'SELL'
            except Exception:
                continue
        # Fallback to legacy entry conditions (could return BUY/SELL)
        return self.check_entry_conditions(market_data)

