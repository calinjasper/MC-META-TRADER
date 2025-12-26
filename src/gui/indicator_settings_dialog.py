"""
Indicator Settings Dialog
Modal dialog for configuring indicator parameters, style, and visibility
"""

import logging
from typing import Dict, Any
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QWidget, QLabel, QSpinBox, QDoubleSpinBox,
                             QComboBox, QLineEdit, QPushButton, QSlider,
                             QCheckBox, QColorDialog, QFormLayout, QGroupBox,
                             QDialogButtonBox, QScrollArea)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


class IndicatorSettingsDialog(QDialog):
    """Modal dialog for editing indicator settings"""
    
    def __init__(self, indicator_type: str, current_settings: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.indicator_type = indicator_type
        self.settings = current_settings.copy()
        
        # Initialize VWAP band widgets dictionary
        self.vwap_band_widgets = {}
        self.vwap_bands_scroll_layout = None
        
        self.setWindowTitle(f"{indicator_type} Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the tabbed dialog UI"""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create tabs
        self.inputs_tab = self.create_inputs_tab()
        self.style_tab = self.create_style_tab()
        self.visibility_tab = self.create_visibility_tab()
        
        self.tabs.addTab(self.inputs_tab, "Inputs")
        self.tabs.addTab(self.style_tab, "Style")
        self.tabs.addTab(self.visibility_tab, "Visibility")
        
        layout.addWidget(self.tabs)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def create_inputs_tab(self) -> QWidget:
        """Create the inputs tab based on indicator type"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        if self.indicator_type == "EMA":
            self.ema_inputs(layout)
        elif self.indicator_type == "VWAP":
            self.vwap_inputs(layout)
        elif self.indicator_type == "SuperTrend":
            self.supertrend_inputs(layout)
        elif self.indicator_type == "SMC":
            self.smc_inputs(layout)
        elif self.indicator_type == "OHLC":
            self.ohlc_inputs(layout)
        elif self.indicator_type == "RSI":
            self.rsi_inputs(layout)
        elif self.indicator_type == "MACD":
            self.macd_inputs(layout)
        elif self.indicator_type == "Bollinger Bands":
            self.bollinger_inputs(layout)
        
        return widget
    
    def ema_inputs(self, layout: QFormLayout):
        """EMA indicator inputs"""
        layout.addRow(QLabel("<b>EMA Configuration</b>"))
        
        self.ema_period1 = QSpinBox()
        self.ema_period1.setRange(1, 500)
        self.ema_period1.setValue(20)
        layout.addRow("EMA 1 Period:", self.ema_period1)
        
        self.ema_period2 = QSpinBox()
        self.ema_period2.setRange(1, 500)
        self.ema_period2.setValue(50)
        layout.addRow("EMA 2 Period:", self.ema_period2)
        
        self.ema_period3 = QSpinBox()
        self.ema_period3.setRange(1, 500)
        self.ema_period3.setValue(100)
        layout.addRow("EMA 3 Period:", self.ema_period3)
        
        self.ema_period4 = QSpinBox()
        self.ema_period4.setRange(1, 500)
        self.ema_period4.setValue(200)
        layout.addRow("EMA 4 Period:", self.ema_period4)
    
    def vwap_inputs(self, layout: QFormLayout):
        """VWAP indicator inputs"""
        layout.addRow(QLabel("<b>VWAP Configuration</b>"))
        
        # Band configuration section
        bands_group = QGroupBox("Standard Deviation Bands")
        bands_layout = QVBoxLayout()
        
        # Scroll area for bands (in case many bands are added)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Store band widgets
        self.vwap_band_widgets = {}  # std_dev -> {checkbox, upper_color_btn, lower_color_btn, remove_btn}
        
        # Add band button
        add_band_btn = QPushButton("Add Band")
        add_band_btn.clicked.connect(self._add_vwap_band_row)
        scroll_layout.addWidget(add_band_btn)
        
        scroll.setWidget(scroll_widget)
        bands_layout.addWidget(scroll)
        bands_group.setLayout(bands_layout)
        layout.addRow(bands_group)
        
        self.vwap_swing_period = QSpinBox()
        self.vwap_swing_period.setRange(1, 100)
        self.vwap_swing_period.setValue(10)
        layout.addRow("Swing Period (candles):", self.vwap_swing_period)
        
        # Store reference to scroll layout for adding bands
        self.vwap_bands_scroll_layout = scroll_layout
    
    def supertrend_inputs(self, layout: QFormLayout):
        """SuperTrend indicator inputs"""
        layout.addRow(QLabel("<b>SuperTrend Configuration</b>"))
        
        self.st_atr_period = QSpinBox()
        self.st_atr_period.setRange(1, 100)
        self.st_atr_period.setValue(10)
        layout.addRow("ATR Period:", self.st_atr_period)
        
        self.st_atr_multiplier = QDoubleSpinBox()
        self.st_atr_multiplier.setRange(0.1, 10.0)
        self.st_atr_multiplier.setSingleStep(0.1)
        self.st_atr_multiplier.setValue(3.0)
        layout.addRow("ATR Multiplier:", self.st_atr_multiplier)
        
        self.st_atr_method = QComboBox()
        self.st_atr_method.addItems(["ATR (Wilder)", "SMA(TR)"])
        layout.addRow("ATR Method:", self.st_atr_method)
    
    def smc_inputs(self, layout: QFormLayout):
        """SMC indicator inputs"""
        layout.addRow(QLabel("<b>SMC Configuration</b>"))
        
        self.smc_pivot_left = QSpinBox()
        self.smc_pivot_left.setRange(1, 20)
        self.smc_pivot_left.setValue(2)
        layout.addRow("Pivot Left Bars:", self.smc_pivot_left)
        
        self.smc_pivot_right = QSpinBox()
        self.smc_pivot_right.setRange(1, 20)
        self.smc_pivot_right.setValue(2)
        layout.addRow("Pivot Right Bars:", self.smc_pivot_right)
        
        self.smc_emit_signals = QComboBox()
        self.smc_emit_signals.addItems([
            "CHoCH only (bias flips)",
            "BOS only (continuation)",
            "Both (BOS + CHoCH)"
        ])
        layout.addRow("Emit Signals On:", self.smc_emit_signals)
    
    def ohlc_inputs(self, layout: QFormLayout):
        """OHLC indicator inputs"""
        layout.addRow(QLabel("<b>OHLC Configuration</b>"))
        
        self.ohlc_session_type = QComboBox()
        self.ohlc_session_type.addItems([
            "Auto (Detect Session)",
            "Daily",
            "Weekly",
            "Monthly",
            "Asian Session",
            "European Session",
            "US Session"
        ])
        layout.addRow("Session Type:", self.ohlc_session_type)
        
        # Checkboxes for which lines to show
        self.ohlc_show_open = QCheckBox("Show Open")
        self.ohlc_show_open.setChecked(True)
        layout.addRow("", self.ohlc_show_open)
        
        self.ohlc_show_high = QCheckBox("Show High")
        self.ohlc_show_high.setChecked(True)
        layout.addRow("", self.ohlc_show_high)
        
        self.ohlc_show_low = QCheckBox("Show Low")
        self.ohlc_show_low.setChecked(True)
        layout.addRow("", self.ohlc_show_low)
        
        self.ohlc_show_close = QCheckBox("Show Close")
        self.ohlc_show_close.setChecked(True)
        layout.addRow("", self.ohlc_show_close)
    
    def rsi_inputs(self, layout: QFormLayout):
        """RSI indicator inputs"""
        layout.addRow(QLabel("<b>RSI Configuration</b>"))
        
        self.rsi_period = QSpinBox()
        self.rsi_period.setRange(1, 100)
        self.rsi_period.setValue(14)
        layout.addRow("Period:", self.rsi_period)
        
        self.rsi_overbought = QSpinBox()
        self.rsi_overbought.setRange(50, 100)
        self.rsi_overbought.setValue(70)
        layout.addRow("Overbought Level:", self.rsi_overbought)
        
        self.rsi_oversold = QSpinBox()
        self.rsi_oversold.setRange(0, 50)
        self.rsi_oversold.setValue(30)
        layout.addRow("Oversold Level:", self.rsi_oversold)
        
        self.rsi_show_levels = QCheckBox("Show Overbought/Oversold Levels")
        self.rsi_show_levels.setChecked(True)
        layout.addRow("", self.rsi_show_levels)
    
    def macd_inputs(self, layout: QFormLayout):
        """MACD indicator inputs"""
        layout.addRow(QLabel("<b>MACD Configuration</b>"))
        
        self.macd_fast_period = QSpinBox()
        self.macd_fast_period.setRange(1, 100)
        self.macd_fast_period.setValue(12)
        layout.addRow("Fast EMA Period:", self.macd_fast_period)
        
        self.macd_slow_period = QSpinBox()
        self.macd_slow_period.setRange(1, 100)
        self.macd_slow_period.setValue(26)
        layout.addRow("Slow EMA Period:", self.macd_slow_period)
        
        self.macd_signal_period = QSpinBox()
        self.macd_signal_period.setRange(1, 100)
        self.macd_signal_period.setValue(9)
        layout.addRow("Signal EMA Period:", self.macd_signal_period)
    
    def bollinger_inputs(self, layout: QFormLayout):
        """Bollinger Bands indicator inputs"""
        layout.addRow(QLabel("<b>Bollinger Bands Configuration</b>"))
        
        self.bb_period = QSpinBox()
        self.bb_period.setRange(1, 200)
        self.bb_period.setValue(20)
        layout.addRow("Period:", self.bb_period)
        
        self.bb_num_std = QDoubleSpinBox()
        self.bb_num_std.setRange(0.1, 5.0)
        self.bb_num_std.setSingleStep(0.1)
        self.bb_num_std.setValue(2.0)
        layout.addRow("Standard Deviations:", self.bb_num_std)
        
        self.bb_show_middle = QCheckBox("Show Middle Band (SMA)")
        self.bb_show_middle.setChecked(True)
        layout.addRow("", self.bb_show_middle)
    
    def create_style_tab(self) -> QWidget:
        """Create the style tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Color configuration group
        color_group = QGroupBox("Colors")
        color_layout = QFormLayout()
        
        if self.indicator_type == "EMA":
            self.create_ema_style_controls(color_layout)
        elif self.indicator_type == "VWAP":
            self.create_vwap_style_controls(color_layout)
        elif self.indicator_type == "SuperTrend":
            self.create_supertrend_style_controls(color_layout)
        elif self.indicator_type == "SMC":
            self.create_smc_style_controls(color_layout)
        elif self.indicator_type == "OHLC":
            self.create_ohlc_style_controls(color_layout)
        elif self.indicator_type == "RSI":
            self.create_rsi_style_controls(color_layout)
        elif self.indicator_type == "MACD":
            self.create_macd_style_controls(color_layout)
        elif self.indicator_type == "Bollinger Bands":
            self.create_bollinger_style_controls(color_layout)
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # Line width
        width_group = QGroupBox("Line Width")
        width_layout = QFormLayout()
        
        self.line_width = QSlider(Qt.Orientation.Horizontal)
        self.line_width.setRange(1, 5)
        self.line_width.setValue(2)
        self.line_width_label = QLabel("2")
        self.line_width.valueChanged.connect(
            lambda v: self.line_width_label.setText(str(v))
        )
        
        width_h_layout = QHBoxLayout()
        width_h_layout.addWidget(self.line_width)
        width_h_layout.addWidget(self.line_width_label)
        
        width_layout.addRow("Width:", width_h_layout)
        width_group.setLayout(width_layout)
        layout.addWidget(width_group)
        
        layout.addStretch()
        
        return widget
    
    def create_ema_style_controls(self, layout: QFormLayout):
        """EMA style controls"""
        self.ema_colors = []
        default_colors = ['#FFA726', '#42A5F5', '#AB47BC', '#66BB6A']
        
        for i, color in enumerate(default_colors, 1):
            color_btn = QPushButton()
            color_btn.setFixedSize(60, 25)
            color_btn.setStyleSheet(f"background-color: {color}; border: 1px solid #ccc;")
            color_btn.clicked.connect(
                lambda checked, btn=color_btn, idx=i-1: self.choose_color(btn, idx)
            )
            self.ema_colors.append({'button': color_btn, 'color': color})
            layout.addRow(f"EMA {i} Color:", color_btn)
    
    def create_vwap_style_controls(self, layout: QFormLayout):
        """VWAP style controls"""
        self.vwap_color_btn = QPushButton()
        self.vwap_color_btn.setFixedSize(60, 25)
        self.vwap_color_btn.setStyleSheet("background-color: #00FFFF; border: 1px solid #ccc;")
        self.vwap_color_btn.clicked.connect(
            lambda: self.choose_single_color(self.vwap_color_btn, 'vwap')
        )
        self.vwap_color = '#00FFFF'
        layout.addRow("VWAP Line Color:", self.vwap_color_btn)
    
    def create_supertrend_style_controls(self, layout: QFormLayout):
        """SuperTrend style controls"""
        self.st_up_color_btn = QPushButton()
        self.st_up_color_btn.setFixedSize(60, 25)
        self.st_up_color_btn.setStyleSheet("background-color: #00E676; border: 1px solid #ccc;")
        self.st_up_color_btn.clicked.connect(
            lambda: self.choose_single_color(self.st_up_color_btn, 'st_up')
        )
        self.st_up_color = '#00E676'
        layout.addRow("Uptrend Color:", self.st_up_color_btn)
        
        self.st_down_color_btn = QPushButton()
        self.st_down_color_btn.setFixedSize(60, 25)
        self.st_down_color_btn.setStyleSheet("background-color: #FF1744; border: 1px solid #ccc;")
        self.st_down_color_btn.clicked.connect(
            lambda: self.choose_single_color(self.st_down_color_btn, 'st_down')
        )
        self.st_down_color = '#FF1744'
        layout.addRow("Downtrend Color:", self.st_down_color_btn)
    
    def create_smc_style_controls(self, layout: QFormLayout):
        """SMC style controls"""
        self.smc_pivot_high_btn = QPushButton()
        self.smc_pivot_high_btn.setFixedSize(60, 25)
        self.smc_pivot_high_btn.setStyleSheet("background-color: #FFCA28; border: 1px solid #ccc;")
        self.smc_pivot_high_btn.clicked.connect(
            lambda: self.choose_single_color(self.smc_pivot_high_btn, 'smc_high')
        )
        self.smc_high_color = '#FFCA28'
        layout.addRow("Pivot High Color:", self.smc_pivot_high_btn)
        
        self.smc_pivot_low_btn = QPushButton()
        self.smc_pivot_low_btn.setFixedSize(60, 25)
        self.smc_pivot_low_btn.setStyleSheet("background-color: #29B6F6; border: 1px solid #ccc;")
        self.smc_pivot_low_btn.clicked.connect(
            lambda: self.choose_single_color(self.smc_pivot_low_btn, 'smc_low')
        )
        self.smc_low_color = '#29B6F6'
        layout.addRow("Pivot Low Color:", self.smc_pivot_low_btn)
    
    def create_ohlc_style_controls(self, layout: QFormLayout):
        """OHLC style controls"""
        self.ohlc_open_btn = QPushButton()
        self.ohlc_open_btn.setFixedSize(60, 25)
        self.ohlc_open_btn.setStyleSheet("background-color: #4CAF50; border: 1px solid #ccc;")
        self.ohlc_open_btn.clicked.connect(
            lambda: self.choose_single_color(self.ohlc_open_btn, 'ohlc_open')
        )
        self.ohlc_open_color = '#4CAF50'
        layout.addRow("Open Color:", self.ohlc_open_btn)
        
        self.ohlc_high_btn = QPushButton()
        self.ohlc_high_btn.setFixedSize(60, 25)
        self.ohlc_high_btn.setStyleSheet("background-color: #2196F3; border: 1px solid #ccc;")
        self.ohlc_high_btn.clicked.connect(
            lambda: self.choose_single_color(self.ohlc_high_btn, 'ohlc_high')
        )
        self.ohlc_high_color = '#2196F3'
        layout.addRow("High Color:", self.ohlc_high_btn)
        
        self.ohlc_low_btn = QPushButton()
        self.ohlc_low_btn.setFixedSize(60, 25)
        self.ohlc_low_btn.setStyleSheet("background-color: #FF9800; border: 1px solid #ccc;")
        self.ohlc_low_btn.clicked.connect(
            lambda: self.choose_single_color(self.ohlc_low_btn, 'ohlc_low')
        )
        self.ohlc_low_color = '#FF9800'
        layout.addRow("Low Color:", self.ohlc_low_btn)
        
        self.ohlc_close_btn = QPushButton()
        self.ohlc_close_btn.setFixedSize(60, 25)
        self.ohlc_close_btn.setStyleSheet("background-color: #9C27B0; border: 1px solid #ccc;")
        self.ohlc_close_btn.clicked.connect(
            lambda: self.choose_single_color(self.ohlc_close_btn, 'ohlc_close')
        )
        self.ohlc_close_color = '#9C27B0'
        layout.addRow("Close Color:", self.ohlc_close_btn)
    
    def create_rsi_style_controls(self, layout: QFormLayout):
        """RSI style controls"""
        self.rsi_color_btn = QPushButton()
        self.rsi_color_btn.setFixedSize(60, 25)
        self.rsi_color_btn.setStyleSheet("background-color: #FF6B6B; border: 1px solid #ccc;")
        self.rsi_color_btn.clicked.connect(
            lambda: self.choose_single_color(self.rsi_color_btn, 'rsi')
        )
        self.rsi_color = '#FF6B6B'
        layout.addRow("RSI Line Color:", self.rsi_color_btn)
        
        self.rsi_overbought_color_btn = QPushButton()
        self.rsi_overbought_color_btn.setFixedSize(60, 25)
        self.rsi_overbought_color_btn.setStyleSheet("background-color: #FF1744; border: 1px solid #ccc;")
        self.rsi_overbought_color_btn.clicked.connect(
            lambda: self.choose_single_color(self.rsi_overbought_color_btn, 'rsi_overbought')
        )
        self.rsi_overbought_color = '#FF1744'
        layout.addRow("Overbought Level Color:", self.rsi_overbought_color_btn)
        
        self.rsi_oversold_color_btn = QPushButton()
        self.rsi_oversold_color_btn.setFixedSize(60, 25)
        self.rsi_oversold_color_btn.setStyleSheet("background-color: #00E676; border: 1px solid #ccc;")
        self.rsi_oversold_color_btn.clicked.connect(
            lambda: self.choose_single_color(self.rsi_oversold_color_btn, 'rsi_oversold')
        )
        self.rsi_oversold_color = '#00E676'
        layout.addRow("Oversold Level Color:", self.rsi_oversold_color_btn)
    
    def create_macd_style_controls(self, layout: QFormLayout):
        """MACD style controls"""
        self.macd_line_color_btn = QPushButton()
        self.macd_line_color_btn.setFixedSize(60, 25)
        self.macd_line_color_btn.setStyleSheet("background-color: #2196F3; border: 1px solid #ccc;")
        self.macd_line_color_btn.clicked.connect(
            lambda: self.choose_single_color(self.macd_line_color_btn, 'macd_line')
        )
        self.macd_line_color = '#2196F3'
        layout.addRow("MACD Line Color:", self.macd_line_color_btn)
        
        self.macd_signal_color_btn = QPushButton()
        self.macd_signal_color_btn.setFixedSize(60, 25)
        self.macd_signal_color_btn.setStyleSheet("background-color: #FF9800; border: 1px solid #ccc;")
        self.macd_signal_color_btn.clicked.connect(
            lambda: self.choose_single_color(self.macd_signal_color_btn, 'macd_signal')
        )
        self.macd_signal_color = '#FF9800'
        layout.addRow("Signal Line Color:", self.macd_signal_color_btn)
        
        self.macd_histogram_color_btn = QPushButton()
        self.macd_histogram_color_btn.setFixedSize(60, 25)
        self.macd_histogram_color_btn.setStyleSheet("background-color: #9E9E9E; border: 1px solid #ccc;")
        self.macd_histogram_color_btn.clicked.connect(
            lambda: self.choose_single_color(self.macd_histogram_color_btn, 'macd_histogram')
        )
        self.macd_histogram_color = '#9E9E9E'
        layout.addRow("Histogram Color:", self.macd_histogram_color_btn)
    
    def create_bollinger_style_controls(self, layout: QFormLayout):
        """Bollinger Bands style controls"""
        self.bb_upper_color_btn = QPushButton()
        self.bb_upper_color_btn.setFixedSize(60, 25)
        self.bb_upper_color_btn.setStyleSheet("background-color: #FF6B6B; border: 1px solid #ccc;")
        self.bb_upper_color_btn.clicked.connect(
            lambda: self.choose_single_color(self.bb_upper_color_btn, 'bb_upper')
        )
        self.bb_upper_color = '#FF6B6B'
        layout.addRow("Upper Band Color:", self.bb_upper_color_btn)
        
        self.bb_middle_color_btn = QPushButton()
        self.bb_middle_color_btn.setFixedSize(60, 25)
        self.bb_middle_color_btn.setStyleSheet("background-color: #42A5F5; border: 1px solid #ccc;")
        self.bb_middle_color_btn.clicked.connect(
            lambda: self.choose_single_color(self.bb_middle_color_btn, 'bb_middle')
        )
        self.bb_middle_color = '#42A5F5'
        layout.addRow("Middle Band Color:", self.bb_middle_color_btn)
        
        self.bb_lower_color_btn = QPushButton()
        self.bb_lower_color_btn.setFixedSize(60, 25)
        self.bb_lower_color_btn.setStyleSheet("background-color: #66BB6A; border: 1px solid #ccc;")
        self.bb_lower_color_btn.clicked.connect(
            lambda: self.choose_single_color(self.bb_lower_color_btn, 'bb_lower')
        )
        self.bb_lower_color = '#66BB6A'
        layout.addRow("Lower Band Color:", self.bb_lower_color_btn)
    
    def create_visibility_tab(self) -> QWidget:
        """Create the visibility tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.show_indicator_checkbox = QCheckBox("Show Indicator")
        self.show_indicator_checkbox.setChecked(True)
        layout.addWidget(self.show_indicator_checkbox)
        
        layout.addStretch()
        
        return widget
    
    def choose_color(self, button: QPushButton, index: int):
        """Open color dialog for EMA colors"""
        color = QColorDialog.getColor()
        if color.isValid():
            button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #ccc;")
            self.ema_colors[index]['color'] = color.name()
    
    def choose_single_color(self, button: QPushButton, color_type: str):
        """Open color dialog for single color indicators"""
        color = QColorDialog.getColor()
        if color.isValid():
            button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #ccc;")
            if color_type == 'vwap':
                self.vwap_color = color.name()
            elif color_type == 'st_up':
                self.st_up_color = color.name()
            elif color_type == 'st_down':
                self.st_down_color = color.name()
            elif color_type == 'smc_high':
                self.smc_high_color = color.name()
            elif color_type == 'smc_low':
                self.smc_low_color = color.name()
            elif color_type.startswith('vwap_band_upper_'):
                std_dev = float(color_type.replace('vwap_band_upper_', ''))
                if std_dev in self.vwap_band_widgets:
                    self.vwap_band_widgets[std_dev]['upper_color'] = color.name()
            elif color_type.startswith('vwap_band_lower_'):
                std_dev = float(color_type.replace('vwap_band_lower_', ''))
                if std_dev in self.vwap_band_widgets:
                    self.vwap_band_widgets[std_dev]['lower_color'] = color.name()
            elif color_type == 'ohlc_open':
                self.ohlc_open_color = color.name()
            elif color_type == 'ohlc_high':
                self.ohlc_high_color = color.name()
            elif color_type == 'ohlc_low':
                self.ohlc_low_color = color.name()
            elif color_type == 'ohlc_close':
                self.ohlc_close_color = color.name()
            elif color_type == 'rsi':
                self.rsi_color = color.name()
            elif color_type == 'rsi_overbought':
                self.rsi_overbought_color = color.name()
            elif color_type == 'rsi_oversold':
                self.rsi_oversold_color = color.name()
            elif color_type == 'macd_line':
                self.macd_line_color = color.name()
            elif color_type == 'macd_signal':
                self.macd_signal_color = color.name()
            elif color_type == 'macd_histogram':
                self.macd_histogram_color = color.name()
            elif color_type == 'bb_upper':
                self.bb_upper_color = color.name()
            elif color_type == 'bb_middle':
                self.bb_middle_color = color.name()
            elif color_type == 'bb_lower':
                self.bb_lower_color = color.name()
    
    def _add_vwap_band_row(self, std_dev: float = None):
        """Add a new band row to VWAP configuration"""
        if std_dev is None:
            # Find next available std_dev value
            existing = [float(k) for k in self.vwap_band_widgets.keys()]
            if existing:
                std_dev = max(existing) + 0.5
            else:
                std_dev = 1.0
        
        # Default colors
        default_colors = {
            1.0: {'upper': '#FF6B6B', 'lower': '#66BB6A'},
            1.5: {'upper': '#FF5252', 'lower': '#4CAF50'},
            2.0: {'upper': '#F44336', 'lower': '#388E3C'},
            2.5: {'upper': '#D32F2F', 'lower': '#2E7D32'},
            3.0: {'upper': '#B71C1C', 'lower': '#1B5E20'}
        }
        
        colors = default_colors.get(std_dev, {'upper': '#FF6B6B', 'lower': '#66BB6A'})
        
        # Create row widget
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(5, 2, 5, 2)
        
        # Checkbox for visibility
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        
        # Std dev value (editable)
        std_dev_spin = QDoubleSpinBox()
        std_dev_spin.setRange(0.1, 10.0)
        std_dev_spin.setSingleStep(0.1)
        std_dev_spin.setDecimals(1)
        std_dev_spin.setValue(std_dev)
        std_dev_spin.setMinimumWidth(60)
        
        # Store original std_dev for update_key closure
        original_std_dev = std_dev
        
        # Update key when value changes
        def update_key(new_val):
            if new_val != original_std_dev and new_val not in self.vwap_band_widgets:
                old_widgets = self.vwap_band_widgets.pop(original_std_dev, None)
                if old_widgets:
                    self.vwap_band_widgets[new_val] = old_widgets
        
        std_dev_spin.valueChanged.connect(update_key)
        
        # Upper color button
        upper_color_btn = QPushButton()
        upper_color_btn.setFixedSize(60, 25)
        upper_color_btn.setStyleSheet(f"background-color: {colors['upper']}; border: 1px solid #ccc;")
        upper_color_type = f'vwap_band_upper_{std_dev}'
        upper_color_btn.clicked.connect(
            lambda checked, btn=upper_color_btn, ctype=upper_color_type: self.choose_single_color(btn, ctype)
        )
        
        # Lower color button
        lower_color_btn = QPushButton()
        lower_color_btn.setFixedSize(60, 25)
        lower_color_btn.setStyleSheet(f"background-color: {colors['lower']}; border: 1px solid #ccc;")
        lower_color_type = f'vwap_band_lower_{std_dev}'
        lower_color_btn.clicked.connect(
            lambda checked, btn=lower_color_btn, ctype=lower_color_type: self.choose_single_color(btn, ctype)
        )
        
        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.setFixedSize(60, 25)
        remove_btn.clicked.connect(lambda checked, sd=std_dev, rw=row_widget: self._remove_vwap_band_row(sd, rw))
        
        # Add widgets to row
        row_layout.addWidget(checkbox)
        row_layout.addWidget(QLabel(f"Band"))
        row_layout.addWidget(std_dev_spin)
        row_layout.addWidget(QLabel("σ:"))
        row_layout.addWidget(QLabel("Upper"))
        row_layout.addWidget(upper_color_btn)
        row_layout.addWidget(QLabel("Lower"))
        row_layout.addWidget(lower_color_btn)
        row_layout.addWidget(remove_btn)
        row_layout.addStretch()
        
        # Store widgets
        self.vwap_band_widgets[std_dev] = {
            'checkbox': checkbox,
            'std_dev_spin': std_dev_spin,
            'upper_color_btn': upper_color_btn,
            'lower_color_btn': lower_color_btn,
            'upper_color': colors['upper'],
            'lower_color': colors['lower'],
            'row_widget': row_widget
        }
        
        # Insert before "Add Band" button (which is at index 0)
        self.vwap_bands_scroll_layout.insertWidget(
            self.vwap_bands_scroll_layout.count() - 1, row_widget
        )
    
    def _remove_vwap_band_row(self, std_dev: float, row_widget: QWidget):
        """Remove a band row from VWAP configuration"""
        if std_dev in self.vwap_band_widgets:
            del self.vwap_band_widgets[std_dev]
        row_widget.setParent(None)
        row_widget.deleteLater()
    
    def load_settings(self):
        """Load current settings into the dialog"""
        if self.indicator_type == "EMA":
            periods = self.settings.get('periods', [20, 50, 100, 200])
            if len(periods) >= 4:
                self.ema_period1.setValue(periods[0])
                self.ema_period2.setValue(periods[1])
                self.ema_period3.setValue(periods[2])
                self.ema_period4.setValue(periods[3])
            
            colors = self.settings.get('colors', ['#FFA726', '#42A5F5', '#AB47BC', '#66BB6A'])
            for i, color in enumerate(colors[:4]):
                if i < len(self.ema_colors):
                    self.ema_colors[i]['color'] = color
                    self.ema_colors[i]['button'].setStyleSheet(
                        f"background-color: {color}; border: 1px solid #ccc;"
                    )
        
        elif self.indicator_type == "VWAP":
            bands = self.settings.get('bands', [1.0, 1.5, 2.0])
            band_visibility = self.settings.get('band_visibility', {1.0: True, 1.5: False, 2.0: False})
            band_colors = self.settings.get('band_colors', {
                1.0: {'upper': '#FF6B6B', 'lower': '#66BB6A'},
                1.5: {'upper': '#FF5252', 'lower': '#4CAF50'},
                2.0: {'upper': '#F44336', 'lower': '#388E3C'}
            })
            
            # Clear existing band widgets
            for std_dev in list(self.vwap_band_widgets.keys()):
                self._remove_vwap_band_row(std_dev, self.vwap_band_widgets[std_dev]['row_widget'])
            
            # Add band rows from settings
            for std_dev in bands:
                colors = band_colors.get(std_dev, {'upper': '#FF6B6B', 'lower': '#66BB6A'})
                self._add_vwap_band_row(std_dev)
                if std_dev in self.vwap_band_widgets:
                    self.vwap_band_widgets[std_dev]['checkbox'].setChecked(band_visibility.get(std_dev, False))
                    self.vwap_band_widgets[std_dev]['upper_color'] = colors.get('upper', '#FF6B6B')
                    self.vwap_band_widgets[std_dev]['lower_color'] = colors.get('lower', '#66BB6A')
                    self.vwap_band_widgets[std_dev]['upper_color_btn'].setStyleSheet(
                        f"background-color: {colors.get('upper', '#FF6B6B')}; border: 1px solid #ccc;"
                    )
                    self.vwap_band_widgets[std_dev]['lower_color_btn'].setStyleSheet(
                        f"background-color: {colors.get('lower', '#66BB6A')}; border: 1px solid #ccc;"
                    )
            
            self.vwap_swing_period.setValue(self.settings.get('swing_period', 10))
            
            color = self.settings.get('color', '#00FFFF')
            self.vwap_color = color
            self.vwap_color_btn.setStyleSheet(f"background-color: {color}; border: 1px solid #ccc;")
        
        elif self.indicator_type == "SuperTrend":
            self.st_atr_period.setValue(self.settings.get('atr_period', 10))
            self.st_atr_multiplier.setValue(self.settings.get('atr_multiplier', 3.0))
            method = self.settings.get('atr_method', 'ATR (Wilder)')
            index = self.st_atr_method.findText(method)
            if index >= 0:
                self.st_atr_method.setCurrentIndex(index)
            
            self.st_up_color = self.settings.get('up_color', '#00E676')
            self.st_down_color = self.settings.get('down_color', '#FF1744')
            self.st_up_color_btn.setStyleSheet(
                f"background-color: {self.st_up_color}; border: 1px solid #ccc;"
            )
            self.st_down_color_btn.setStyleSheet(
                f"background-color: {self.st_down_color}; border: 1px solid #ccc;"
            )
        
        elif self.indicator_type == "SMC":
            self.smc_pivot_left.setValue(self.settings.get('pivot_left', 2))
            self.smc_pivot_right.setValue(self.settings.get('pivot_right', 2))
            emit_signals = self.settings.get('emit_signals', 'CHoCH only (bias flips)')
            index = self.smc_emit_signals.findText(emit_signals)
            if index >= 0:
                self.smc_emit_signals.setCurrentIndex(index)
            
            self.smc_high_color = self.settings.get('high_color', '#FFCA28')
            self.smc_low_color = self.settings.get('low_color', '#29B6F6')
            self.smc_pivot_high_btn.setStyleSheet(
                f"background-color: {self.smc_high_color}; border: 1px solid #ccc;"
            )
            self.smc_pivot_low_btn.setStyleSheet(
                f"background-color: {self.smc_low_color}; border: 1px solid #ccc;"
            )
        
        elif self.indicator_type == "OHLC":
            # Map session_type to dropdown index
            session_type = self.settings.get('session_type', 'auto')
            session_map = {
                'auto': 0,
                'daily': 1,
                'weekly': 2,
                'monthly': 3,
                'asian': 4,
                'european': 5,
                'us': 6
            }
            index = session_map.get(session_type.lower(), 0)
            self.ohlc_session_type.setCurrentIndex(index)
            
            self.ohlc_show_open.setChecked(self.settings.get('show_open', True))
            self.ohlc_show_high.setChecked(self.settings.get('show_high', True))
            self.ohlc_show_low.setChecked(self.settings.get('show_low', True))
            self.ohlc_show_close.setChecked(self.settings.get('show_close', True))
            
            self.ohlc_open_color = self.settings.get('open_color', '#4CAF50')
            self.ohlc_high_color = self.settings.get('high_color', '#2196F3')
            self.ohlc_low_color = self.settings.get('low_color', '#FF9800')
            self.ohlc_close_color = self.settings.get('close_color', '#9C27B0')
            
            self.ohlc_open_btn.setStyleSheet(f"background-color: {self.ohlc_open_color}; border: 1px solid #ccc;")
            self.ohlc_high_btn.setStyleSheet(f"background-color: {self.ohlc_high_color}; border: 1px solid #ccc;")
            self.ohlc_low_btn.setStyleSheet(f"background-color: {self.ohlc_low_color}; border: 1px solid #ccc;")
            self.ohlc_close_btn.setStyleSheet(f"background-color: {self.ohlc_close_color}; border: 1px solid #ccc;")
        
        elif self.indicator_type == "RSI":
            self.rsi_period.setValue(self.settings.get('period', 14))
            self.rsi_overbought.setValue(self.settings.get('overbought', 70))
            self.rsi_oversold.setValue(self.settings.get('oversold', 30))
            self.rsi_show_levels.setChecked(self.settings.get('show_levels', True))
            
            self.rsi_color = self.settings.get('color', '#FF6B6B')
            self.rsi_overbought_color = self.settings.get('overbought_color', '#FF1744')
            self.rsi_oversold_color = self.settings.get('oversold_color', '#00E676')
            
            self.rsi_color_btn.setStyleSheet(f"background-color: {self.rsi_color}; border: 1px solid #ccc;")
            self.rsi_overbought_color_btn.setStyleSheet(f"background-color: {self.rsi_overbought_color}; border: 1px solid #ccc;")
            self.rsi_oversold_color_btn.setStyleSheet(f"background-color: {self.rsi_oversold_color}; border: 1px solid #ccc;")
        
        elif self.indicator_type == "MACD":
            self.macd_fast_period.setValue(self.settings.get('fast_period', 12))
            self.macd_slow_period.setValue(self.settings.get('slow_period', 26))
            self.macd_signal_period.setValue(self.settings.get('signal_period', 9))
            
            self.macd_line_color = self.settings.get('macd_color', '#2196F3')
            self.macd_signal_color = self.settings.get('signal_color', '#FF9800')
            self.macd_histogram_color = self.settings.get('histogram_color', '#9E9E9E')
            
            self.macd_line_color_btn.setStyleSheet(f"background-color: {self.macd_line_color}; border: 1px solid #ccc;")
            self.macd_signal_color_btn.setStyleSheet(f"background-color: {self.macd_signal_color}; border: 1px solid #ccc;")
            self.macd_histogram_color_btn.setStyleSheet(f"background-color: {self.macd_histogram_color}; border: 1px solid #ccc;")
        
        elif self.indicator_type == "Bollinger Bands":
            self.bb_period.setValue(self.settings.get('period', 20))
            self.bb_num_std.setValue(self.settings.get('num_std', 2.0))
            self.bb_show_middle.setChecked(self.settings.get('show_middle', True))
            
            self.bb_upper_color = self.settings.get('upper_color', '#FF6B6B')
            self.bb_middle_color = self.settings.get('middle_color', '#42A5F5')
            self.bb_lower_color = self.settings.get('lower_color', '#66BB6A')
            
            self.bb_upper_color_btn.setStyleSheet(f"background-color: {self.bb_upper_color}; border: 1px solid #ccc;")
            self.bb_middle_color_btn.setStyleSheet(f"background-color: {self.bb_middle_color}; border: 1px solid #ccc;")
            self.bb_lower_color_btn.setStyleSheet(f"background-color: {self.bb_lower_color}; border: 1px solid #ccc;")
        
        # Common settings
        self.line_width.setValue(self.settings.get('line_width', 2))
        self.show_indicator_checkbox.setChecked(self.settings.get('visible', True))
    
    def get_settings(self) -> Dict[str, Any]:
        """Get the settings from the dialog"""
        settings = {'visible': self.show_indicator_checkbox.isChecked()}
        
        if self.indicator_type == "EMA":
            settings['periods'] = [
                self.ema_period1.value(),
                self.ema_period2.value(),
                self.ema_period3.value(),
                self.ema_period4.value()
            ]
            settings['colors'] = [c['color'] for c in self.ema_colors]
        
        elif self.indicator_type == "VWAP":
            # Get bands from widgets
            bands = []
            band_visibility = {}
            band_colors = {}
            
            for std_dev, widgets in self.vwap_band_widgets.items():
                # Get current std_dev value from spinbox
                current_std_dev = widgets['std_dev_spin'].value()
                bands.append(current_std_dev)
                band_visibility[current_std_dev] = widgets['checkbox'].isChecked()
                band_colors[current_std_dev] = {
                    'upper': widgets.get('upper_color', '#FF6B6B'),
                    'lower': widgets.get('lower_color', '#66BB6A')
                }
            
            # Sort bands
            bands = sorted(bands)
            
            settings['bands'] = bands if bands else [1.0]
            settings['band_visibility'] = band_visibility if band_visibility else {1.0: True}
            settings['band_colors'] = band_colors if band_colors else {
                1.0: {'upper': '#FF6B6B', 'lower': '#66BB6A'}
            }
            
            settings['swing_period'] = self.vwap_swing_period.value()
            settings['color'] = self.vwap_color
        
        elif self.indicator_type == "SuperTrend":
            settings['atr_period'] = self.st_atr_period.value()
            settings['atr_multiplier'] = self.st_atr_multiplier.value()
            settings['atr_method'] = self.st_atr_method.currentText()
            settings['up_color'] = self.st_up_color
            settings['down_color'] = self.st_down_color
        
        elif self.indicator_type == "SMC":
            settings['pivot_left'] = self.smc_pivot_left.value()
            settings['pivot_right'] = self.smc_pivot_right.value()
            settings['emit_signals'] = self.smc_emit_signals.currentText()
            settings['high_color'] = self.smc_high_color
            settings['low_color'] = self.smc_low_color
        
        elif self.indicator_type == "OHLC":
            # Map dropdown index back to session_type
            session_index = self.ohlc_session_type.currentIndex()
            session_types = ['auto', 'daily', 'weekly', 'monthly', 'asian', 'european', 'us']
            settings['session_type'] = session_types[session_index] if session_index < len(session_types) else 'auto'
            
            settings['show_open'] = self.ohlc_show_open.isChecked()
            settings['show_high'] = self.ohlc_show_high.isChecked()
            settings['show_low'] = self.ohlc_show_low.isChecked()
            settings['show_close'] = self.ohlc_show_close.isChecked()
            
            settings['open_color'] = self.ohlc_open_color
            settings['high_color'] = self.ohlc_high_color
            settings['low_color'] = self.ohlc_low_color
            settings['close_color'] = self.ohlc_close_color
        
        elif self.indicator_type == "RSI":
            settings['period'] = self.rsi_period.value()
            settings['overbought'] = self.rsi_overbought.value()
            settings['oversold'] = self.rsi_oversold.value()
            settings['show_levels'] = self.rsi_show_levels.isChecked()
            settings['color'] = self.rsi_color
            settings['overbought_color'] = self.rsi_overbought_color
            settings['oversold_color'] = self.rsi_oversold_color
        
        elif self.indicator_type == "MACD":
            settings['fast_period'] = self.macd_fast_period.value()
            settings['slow_period'] = self.macd_slow_period.value()
            settings['signal_period'] = self.macd_signal_period.value()
            settings['macd_color'] = self.macd_line_color
            settings['signal_color'] = self.macd_signal_color
            settings['histogram_color'] = self.macd_histogram_color
        
        elif self.indicator_type == "Bollinger Bands":
            settings['period'] = self.bb_period.value()
            settings['num_std'] = self.bb_num_std.value()
            settings['show_middle'] = self.bb_show_middle.isChecked()
            settings['upper_color'] = self.bb_upper_color
            settings['middle_color'] = self.bb_middle_color
            settings['lower_color'] = self.bb_lower_color
        
        settings['line_width'] = self.line_width.value()
        
        return settings

