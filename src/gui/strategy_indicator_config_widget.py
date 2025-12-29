"""
Strategy Indicator Configuration Widget
Reusable widget for configuring indicator parameters in strategy edit dialog
"""

from PyQt6.QtWidgets import (QWidget, QFormLayout, QSpinBox, QComboBox, 
                             QCheckBox, QLineEdit, QLabel)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class StrategyIndicatorConfigWidget(QWidget):
    """Widget for configuring a single indicator's parameters"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_indicator_type = None
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QFormLayout(self)
        layout.setSpacing(10)
        
        # Indicator type selector
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "SMA",
            "EMA", 
            "RSI",
            "MACD",
            "VWAP",
            "Volume"
        ])
        self.type_combo.currentTextChanged.connect(self.on_indicator_type_changed)
        layout.addRow("Indicator Type:", self.type_combo)
        
        # Indicator name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., RSI, EMA_1, MACD")
        layout.addRow("Indicator Name:", self.name_input)
        
        # Container for dynamic inputs (will be populated based on type)
        self.inputs_container = QWidget()
        self.inputs_layout = QFormLayout(self.inputs_container)
        self.inputs_layout.setSpacing(8)
        layout.addRow(self.inputs_container)
        
        # Initialize with first type
        self.on_indicator_type_changed(self.type_combo.currentText())
    
    def on_indicator_type_changed(self, indicator_type: str):
        """Update UI based on selected indicator type"""
        self.current_indicator_type = indicator_type
        
        # Clear existing inputs
        while self.inputs_layout.count():
            child = self.inputs_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add inputs based on type
        if indicator_type == "SMA":
            self.period_spin = QSpinBox()
            self.period_spin.setMinimum(1)
            self.period_spin.setMaximum(1000)
            self.period_spin.setValue(20)
            self.inputs_layout.addRow("Period:", self.period_spin)
            
        elif indicator_type == "EMA":
            self.period_spin = QSpinBox()
            self.period_spin.setMinimum(1)
            self.period_spin.setMaximum(1000)
            self.period_spin.setValue(20)
            self.inputs_layout.addRow("Period:", self.period_spin)
            
        elif indicator_type == "RSI":
            self.period_spin = QSpinBox()
            self.period_spin.setMinimum(1)
            self.period_spin.setMaximum(1000)
            self.period_spin.setValue(14)
            self.inputs_layout.addRow("Period:", self.period_spin)
            
        elif indicator_type == "MACD":
            self.fast_period_spin = QSpinBox()
            self.fast_period_spin.setMinimum(1)
            self.fast_period_spin.setMaximum(1000)
            self.fast_period_spin.setValue(12)
            self.inputs_layout.addRow("Fast Period:", self.fast_period_spin)
            
            self.slow_period_spin = QSpinBox()
            self.slow_period_spin.setMinimum(1)
            self.slow_period_spin.setMaximum(1000)
            self.slow_period_spin.setValue(26)
            self.inputs_layout.addRow("Slow Period:", self.slow_period_spin)
            
            self.signal_period_spin = QSpinBox()
            self.signal_period_spin.setMinimum(1)
            self.signal_period_spin.setMaximum(1000)
            self.signal_period_spin.setValue(9)
            self.inputs_layout.addRow("Signal Period:", self.signal_period_spin)
            
        elif indicator_type == "VWAP":
            self.session_type_combo = QComboBox()
            self.session_type_combo.addItems(["NY", "London", "Asia", "All"])
            self.session_type_combo.setCurrentText("NY")
            self.inputs_layout.addRow("Session Type:", self.session_type_combo)
            
            self.use_typical_price_check = QCheckBox()
            self.use_typical_price_check.setChecked(True)
            self.inputs_layout.addRow("Use Typical Price:", self.use_typical_price_check)
            
        elif indicator_type == "Volume":
            self.period_spin = QSpinBox()
            self.period_spin.setMinimum(1)
            self.period_spin.setMaximum(1000)
            self.period_spin.setValue(20)
            self.inputs_layout.addRow("Period:", self.period_spin)
        
        # Set default name if empty
        if not self.name_input.text():
            if indicator_type == "MACD":
                self.name_input.setText("MACD")
            elif indicator_type == "VWAP":
                self.name_input.setText("VWAP")
            elif indicator_type == "Volume":
                self.name_input.setText("Volume")
            else:
                self.name_input.setText(indicator_type)
    
    def get_config(self) -> Dict[str, Any]:
        """Get the indicator configuration"""
        name = self.name_input.text().strip()
        if not name:
            raise ValueError("Indicator name is required")
        
        config = {
            "name": name,
            "type": self.current_indicator_type
        }
        
        if self.current_indicator_type in ["SMA", "EMA", "RSI", "Volume"]:
            config["period"] = self.period_spin.value()
            
        elif self.current_indicator_type == "MACD":
            config["fast_period"] = self.fast_period_spin.value()
            config["slow_period"] = self.slow_period_spin.value()
            config["signal_period"] = self.signal_period_spin.value()
            
        elif self.current_indicator_type == "VWAP":
            config["session_type"] = self.session_type_combo.currentText()
            config["use_typical_price"] = self.use_typical_price_check.isChecked()
        
        return config
    
    def set_config(self, name: str, indicator_type: str, config: Dict[str, Any]):
        """Set the widget values from existing configuration"""
        self.name_input.setText(name)
        self.type_combo.setCurrentText(indicator_type)
        self.on_indicator_type_changed(indicator_type)
        
        if indicator_type in ["SMA", "EMA", "RSI", "Volume"]:
            period = config.get("period", 20)
            if hasattr(self, 'period_spin'):
                self.period_spin.setValue(period)
                
        elif indicator_type == "MACD":
            if hasattr(self, 'fast_period_spin'):
                self.fast_period_spin.setValue(config.get("fast_period", 12))
            if hasattr(self, 'slow_period_spin'):
                self.slow_period_spin.setValue(config.get("slow_period", 26))
            if hasattr(self, 'signal_period_spin'):
                self.signal_period_spin.setValue(config.get("signal_period", 9))
                
        elif indicator_type == "VWAP":
            if hasattr(self, 'session_type_combo'):
                session_type = config.get("session_type", "NY")
                idx = self.session_type_combo.findText(session_type)
                if idx >= 0:
                    self.session_type_combo.setCurrentIndex(idx)
            if hasattr(self, 'use_typical_price_check'):
                self.use_typical_price_check.setChecked(config.get("use_typical_price", True))

