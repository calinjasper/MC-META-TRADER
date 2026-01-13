"""
Strategy Indicator Configuration Dialog
Modal dialog for adding/editing a single indicator in strategy edit dialog
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QDialogButtonBox, 
                             QMessageBox)
from typing import Dict, Any, Optional
import logging

from .strategy_indicator_config_widget import StrategyIndicatorConfigWidget

logger = logging.getLogger(__name__)


class StrategyIndicatorConfigDialog(QDialog):
    """Dialog for adding/editing a single indicator"""
    
    def __init__(self, parent=None, indicator_name: Optional[str] = None, 
                 indicator_type: Optional[str] = None, 
                 config: Optional[Dict[str, Any]] = None):
        """
        Initialize the dialog
        
        Args:
            parent: Parent widget
            indicator_name: Existing indicator name (for editing)
            indicator_type: Existing indicator type (for editing)
            config: Existing indicator configuration (for editing)
        """
        super().__init__(parent)
        self.is_editing = indicator_name is not None
        
        if self.is_editing:
            self.setWindowTitle(f"Edit Indicator: {indicator_name}")
        else:
            self.setWindowTitle("Add Indicator")
        
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        self.setup_ui()
        
        # Load existing config if editing
        if self.is_editing and indicator_name and indicator_type and config:
            self.config_widget.set_config(indicator_name, indicator_type, config)
    
    def setup_ui(self):
        """Setup the UI"""
        # Apply dark theme styling
        self.setStyleSheet("""
            QDialog {
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
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                background-color: #2b2b2b;
                border: 1px solid #444;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #2196F3;
            }
            QDialogButtonBox QPushButton {
                min-width: 80px;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Configuration widget
        self.config_widget = StrategyIndicatorConfigWidget(self)
        layout.addWidget(self.config_widget)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def validate_and_accept(self):
        """Validate inputs and accept if valid"""
        try:
            config = self.config_widget.get_config()
            
            # Validate name
            name = config.get("name", "").strip()
            if not name:
                QMessageBox.warning(self, "Validation Error", "Indicator name is required.")
                return
            
            # Validate periods
            if config["type"] in ["SMA", "EMA", "RSI", "Volume"]:
                period = config.get("period", 0)
                if period < 1:
                    QMessageBox.warning(self, "Validation Error", "Period must be at least 1.")
                    return
            
            elif config["type"] == "MACD":
                fast = config.get("fast_period", 0)
                slow = config.get("slow_period", 0)
                signal = config.get("signal_period", 0)
                if fast < 1 or slow < 1 or signal < 1:
                    QMessageBox.warning(self, "Validation Error", "All periods must be at least 1.")
                    return
                if fast >= slow:
                    QMessageBox.warning(self, "Validation Error", "Fast period must be less than slow period.")
                    return
            
            self.accept()
            
        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", str(e))
        except Exception as e:
            logger.error(f"Error validating indicator config: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to validate configuration: {str(e)}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get the indicator configuration"""
        return self.config_widget.get_config()

