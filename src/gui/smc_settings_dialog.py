"""
SMC Settings Dialog
Dialog for configuring SMC strategy settings (pivot bars and emit_on)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QSpinBox, QComboBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Optional


class SMCSettingsDialog(QDialog):
    """Dialog for configuring SMC strategy settings"""
    
    def __init__(self, parent=None, current_settings: Optional[Dict] = None):
        super().__init__(parent)
        self.current_settings = current_settings or {
            'pivot_left': 2,
            'pivot_right': 2,
            'emit_on': 'NONE'
        }
        self.setWindowTitle("SMC Strategy Settings")
        self.setMinimumWidth(400)
        self.setMinimumHeight(200)
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QSpinBox, QComboBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px;
            }
            QSpinBox:focus, QComboBox:focus {
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
        
        # Form layout for settings
        form_layout = QFormLayout()
        
        # Pivot Left Bars
        self.pivot_left_spin = QSpinBox()
        self.pivot_left_spin.setMinimum(1)
        self.pivot_left_spin.setMaximum(10)
        self.pivot_left_spin.setValue(2)
        self.pivot_left_spin.setToolTip("Number of bars to the left required for pivot confirmation")
        form_layout.addRow("Pivot Left Bars:", self.pivot_left_spin)
        
        # Pivot Right Bars
        self.pivot_right_spin = QSpinBox()
        self.pivot_right_spin.setMinimum(1)
        self.pivot_right_spin.setMaximum(10)
        self.pivot_right_spin.setValue(2)
        self.pivot_right_spin.setToolTip("Number of bars to the right required for pivot confirmation")
        form_layout.addRow("Pivot Right Bars:", self.pivot_right_spin)
        
        # Emit Signals On
        self.emit_on_combo = QComboBox()
        self.emit_on_combo.addItem("NONE (Pivot Lines)", "NONE")
        self.emit_on_combo.addItem("CHoCH only (bias flips)", "CHoCH")
        self.emit_on_combo.addItem("BOS only (continuation)", "BOS")
        self.emit_on_combo.addItem("Both (BOS + CHoCH)", "BOTH")
        self.emit_on_combo.setToolTip(
            "Controls which SMC prices are tracked:\n"
            "NONE: Track pivot high/low lines\n"
            "CHoCH: Track CHoCH event line\n"
            "BOS: Track BOS event line\n"
            "BOTH: Track both CHoCH and BOS lines"
        )
        form_layout.addRow("Emit Signals On:", self.emit_on_combo)
        
        # Help text
        help_label = QLabel(
            "These settings control which SMC prices are available as operands in conditions.\n"
            "Pivot lines are always available. Event prices depend on 'Emit Signals On' setting."
        )
        help_label.setStyleSheet("color: #ccc; font-size: 11px; padding: 10px;")
        help_label.setWordWrap(True)
        
        layout.addLayout(form_layout)
        layout.addWidget(help_label)
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def load_settings(self):
        """Load current settings into UI widgets"""
        self.pivot_left_spin.setValue(self.current_settings.get('pivot_left', 2))
        self.pivot_right_spin.setValue(self.current_settings.get('pivot_right', 2))
        
        emit_on = self.current_settings.get('emit_on', 'NONE')
        idx = self.emit_on_combo.findData(emit_on)
        if idx >= 0:
            self.emit_on_combo.setCurrentIndex(idx)
    
    def get_settings(self) -> Dict:
        """Get current settings from UI widgets"""
        return {
            'pivot_left': self.pivot_left_spin.value(),
            'pivot_right': self.pivot_right_spin.value(),
            'emit_on': self.emit_on_combo.currentData()
        }
