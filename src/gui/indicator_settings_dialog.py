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
                             QDialogButtonBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


class IndicatorSettingsDialog(QDialog):
    """Modal dialog for editing indicator settings"""
    
    def __init__(self, indicator_type: str, current_settings: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.indicator_type = indicator_type
        self.settings = current_settings.copy()
        
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
        
        self.vwap_bands = QLineEdit()
        self.vwap_bands.setText("1, 1.5, 2")
        self.vwap_bands.setPlaceholderText("e.g., 1, 1.5, 2")
        layout.addRow("Standard Deviation Bands:", self.vwap_bands)
        
        self.vwap_swing_period = QSpinBox()
        self.vwap_swing_period.setRange(1, 100)
        self.vwap_swing_period.setValue(10)
        layout.addRow("Swing Period (candles):", self.vwap_swing_period)
        
        layout.addRow(QLabel("<i>Bands format: comma-separated values</i>"))
    
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
            self.vwap_bands.setText(", ".join(str(b) for b in bands))
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
            # Parse bands from text
            bands_text = self.vwap_bands.text()
            try:
                bands = [float(b.strip()) for b in bands_text.split(',')]
                settings['bands'] = bands
            except:
                settings['bands'] = [1.0, 1.5, 2.0]
            
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
        
        settings['line_width'] = self.line_width.value()
        
        return settings

