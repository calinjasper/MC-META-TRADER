"""
Quick Settings Panel
Trading presets and default values configuration
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QComboBox, QDoubleSpinBox, QPushButton, QLabel,
                             QGroupBox, QCheckBox, QMessageBox, QDialog,
                             QDialogButtonBox)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Dict, Optional

from ..config import Config


class TradingPresetDialog(QDialog):
    """Dialog for saving/loading trading presets"""
    
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Trading Presets")
        self.setModal(True)
        self.setup_ui()
        self.load_presets()
    
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        
        # Preset selection
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setEditable(True)
        self.preset_combo.currentTextChanged.connect(self.on_preset_selected)
        preset_layout.addWidget(self.preset_combo)
        
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(self.load_preset)
        preset_layout.addWidget(load_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_preset)
        preset_layout.addWidget(save_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_preset)
        preset_layout.addWidget(delete_btn)
        
        layout.addLayout(preset_layout)
        
        # Preset values
        form_layout = QFormLayout()
        
        self.default_lot_spin = QDoubleSpinBox()
        self.default_lot_spin.setMinimum(0.01)
        self.default_lot_spin.setMaximum(100.0)
        self.default_lot_spin.setSingleStep(0.01)
        self.default_lot_spin.setDecimals(2)
        self.default_lot_spin.setValue(0.01)
        form_layout.addRow("Default Lot Size:", self.default_lot_spin)
        
        self.default_sl_spin = QDoubleSpinBox()
        self.default_sl_spin.setMinimum(0.0)
        self.default_sl_spin.setMaximum(10000.0)
        self.default_sl_spin.setDecimals(2)
        self.default_sl_spin.setValue(20.0)
        form_layout.addRow("Default SL (Pips):", self.default_sl_spin)
        
        self.default_tp_spin = QDoubleSpinBox()
        self.default_tp_spin.setMinimum(0.0)
        self.default_tp_spin.setMaximum(10000.0)
        self.default_tp_spin.setDecimals(2)
        self.default_tp_spin.setValue(40.0)
        form_layout.addRow("Default TP (Pips):", self.default_tp_spin)
        
        self.risk_per_trade_spin = QDoubleSpinBox()
        self.risk_per_trade_spin.setMinimum(0.1)
        self.risk_per_trade_spin.setMaximum(10.0)
        self.risk_per_trade_spin.setDecimals(1)
        self.risk_per_trade_spin.setValue(2.0)
        self.risk_per_trade_spin.setSuffix("%")
        form_layout.addRow("Risk Per Trade:", self.risk_per_trade_spin)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_presets(self):
        """Load preset names"""
        presets = self.config.get('trading.presets', {})
        self.preset_combo.clear()
        self.preset_combo.addItem("Default")
        for preset_name in presets.keys():
            self.preset_combo.addItem(preset_name)
    
    def on_preset_selected(self, name: str):
        """Handle preset selection"""
        if name == "Default":
            self.load_default_values()
        else:
            self.load_preset_values(name)
    
    def load_default_values(self):
        """Load default values from config"""
        self.default_lot_spin.setValue(self.config.get('trading.default_lot_size', 0.01))
        self.default_sl_spin.setValue(self.config.get('trading.default_sl_pips', 20.0))
        self.default_tp_spin.setValue(self.config.get('trading.default_tp_pips', 40.0))
        self.risk_per_trade_spin.setValue(self.config.get('trading.risk_per_trade', 2.0))
    
    def load_preset_values(self, preset_name: str):
        """Load preset values"""
        presets = self.config.get('trading.presets', {})
        if preset_name in presets:
            preset = presets[preset_name]
            self.default_lot_spin.setValue(preset.get('lot_size', 0.01))
            self.default_sl_spin.setValue(preset.get('sl_pips', 20.0))
            self.default_tp_spin.setValue(preset.get('tp_pips', 40.0))
            self.risk_per_trade_spin.setValue(preset.get('risk_per_trade', 2.0))
    
    def load_preset(self):
        """Load selected preset"""
        name = self.preset_combo.currentText()
        if name == "Default":
            self.load_default_values()
        else:
            self.load_preset_values(name)
    
    def save_preset(self):
        """Save current values as preset"""
        name = self.preset_combo.currentText().strip()
        if not name or name == "Default":
            QMessageBox.warning(self, "Error", "Please enter a valid preset name")
            return
        
        presets = self.config.get('trading.presets', {})
        presets[name] = {
            'lot_size': self.default_lot_spin.value(),
            'sl_pips': self.default_sl_spin.value(),
            'tp_pips': self.default_tp_spin.value(),
            'risk_per_trade': self.risk_per_trade_spin.value()
        }
        
        self.config.set('trading.presets', presets)
        self.config.save()
        
        self.load_presets()
        self.preset_combo.setCurrentText(name)
        QMessageBox.information(self, "Success", f"Preset '{name}' saved")
    
    def delete_preset(self):
        """Delete selected preset"""
        name = self.preset_combo.currentText()
        if name == "Default":
            QMessageBox.warning(self, "Error", "Cannot delete default preset")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            presets = self.config.get('trading.presets', {})
            if name in presets:
                del presets[name]
                self.config.set('trading.presets', presets)
                self.config.save()
                self.load_presets()
                self.preset_combo.setCurrentIndex(0)
                QMessageBox.information(self, "Success", f"Preset '{name}' deleted")
    
    def get_values(self) -> Dict:
        """Get current values"""
        return {
            'lot_size': self.default_lot_spin.value(),
            'sl_pips': self.default_sl_spin.value(),
            'tp_pips': self.default_tp_spin.value(),
            'risk_per_trade': self.risk_per_trade_spin.value()
        }


class QuickSettingsPanel(QWidget):
    """Quick Settings Panel Widget"""
    
    settings_changed = pyqtSignal(dict)  # Emitted when settings change
    
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup quick settings UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        group = QGroupBox("Quick Settings")
        form_layout = QFormLayout()
        
        # Default lot size
        self.default_lot_combo = QComboBox()
        self.default_lot_combo.addItems(["0.01", "0.1", "1.0", "Custom"])
        self.default_lot_combo.currentTextChanged.connect(self.on_lot_changed)
        form_layout.addRow("Default Lot:", self.default_lot_combo)
        
        self.custom_lot_spin = QDoubleSpinBox()
        self.custom_lot_spin.setMinimum(0.01)
        self.custom_lot_spin.setMaximum(100.0)
        self.custom_lot_spin.setSingleStep(0.01)
        self.custom_lot_spin.setDecimals(2)
        self.custom_lot_spin.setValue(0.01)
        self.custom_lot_spin.setEnabled(False)
        self.custom_lot_spin.valueChanged.connect(self.on_settings_changed)
        form_layout.addRow("Custom Lot:", self.custom_lot_spin)
        
        # Default SL/TP
        self.default_sl_spin = QDoubleSpinBox()
        self.default_sl_spin.setMinimum(0.0)
        self.default_sl_spin.setMaximum(10000.0)
        self.default_sl_spin.setDecimals(2)
        self.default_sl_spin.setValue(20.0)
        self.default_sl_spin.setSuffix(" pips")
        self.default_sl_spin.valueChanged.connect(self.on_settings_changed)
        form_layout.addRow("Default SL:", self.default_sl_spin)
        
        self.default_tp_spin = QDoubleSpinBox()
        self.default_tp_spin.setMinimum(0.0)
        self.default_tp_spin.setMaximum(10000.0)
        self.default_tp_spin.setDecimals(2)
        self.default_tp_spin.setValue(40.0)
        self.default_tp_spin.setSuffix(" pips")
        self.default_tp_spin.valueChanged.connect(self.on_settings_changed)
        form_layout.addRow("Default TP:", self.default_tp_spin)
        
        # Risk per trade
        self.risk_per_trade_spin = QDoubleSpinBox()
        self.risk_per_trade_spin.setMinimum(0.1)
        self.risk_per_trade_spin.setMaximum(10.0)
        self.risk_per_trade_spin.setDecimals(1)
        self.risk_per_trade_spin.setValue(2.0)
        self.risk_per_trade_spin.setSuffix("%")
        self.risk_per_trade_spin.valueChanged.connect(self.on_settings_changed)
        form_layout.addRow("Risk Per Trade:", self.risk_per_trade_spin)
        
        group.setLayout(form_layout)
        layout.addWidget(group)
        
        # Presets button
        presets_btn = QPushButton("Manage Presets...")
        presets_btn.clicked.connect(self.show_presets_dialog)
        layout.addWidget(presets_btn)
        
        layout.addStretch()
    
    def on_lot_changed(self, text: str):
        """Handle lot size selection change"""
        if text == "Custom":
            self.custom_lot_spin.setEnabled(True)
        else:
            self.custom_lot_spin.setEnabled(False)
            if text != "Custom":
                self.custom_lot_spin.setValue(float(text))
        self.on_settings_changed()
    
    def on_settings_changed(self):
        """Handle settings change"""
        settings = self.get_settings()
        self.settings_changed.emit(settings)
        self.save_settings()
    
    def get_settings(self) -> Dict:
        """Get current settings"""
        lot_size = self.custom_lot_spin.value()
        if self.default_lot_combo.currentText() != "Custom":
            lot_size = float(self.default_lot_combo.currentText())
        
        return {
            'lot_size': lot_size,
            'sl_pips': self.default_sl_spin.value(),
            'tp_pips': self.default_tp_spin.value(),
            'risk_per_trade': self.risk_per_trade_spin.value()
        }
    
    def load_settings(self):
        """Load settings from config"""
        lot_size = self.config.get('trading.default_lot_size', 0.01)
        if lot_size in [0.01, 0.1, 1.0]:
            self.default_lot_combo.setCurrentText(str(lot_size))
        else:
            self.default_lot_combo.setCurrentText("Custom")
            self.custom_lot_spin.setValue(lot_size)
        
        self.default_sl_spin.setValue(self.config.get('trading.default_sl_pips', 20.0))
        self.default_tp_spin.setValue(self.config.get('trading.default_tp_pips', 40.0))
        self.risk_per_trade_spin.setValue(self.config.get('trading.risk_per_trade', 2.0))
    
    def save_settings(self):
        """Save settings to config"""
        settings = self.get_settings()
        self.config.set('trading.default_lot_size', settings['lot_size'])
        self.config.set('trading.default_sl_pips', settings['sl_pips'])
        self.config.set('trading.default_tp_pips', settings['tp_pips'])
        self.config.set('trading.risk_per_trade', settings['risk_per_trade'])
        self.config.save()
    
    def show_presets_dialog(self):
        """Show trading presets dialog"""
        dialog = TradingPresetDialog(self.config, self)
        if dialog.exec():
            values = dialog.get_values()
            # Apply preset values
            lot_size = values['lot_size']
            if lot_size in [0.01, 0.1, 1.0]:
                self.default_lot_combo.setCurrentText(str(lot_size))
            else:
                self.default_lot_combo.setCurrentText("Custom")
                self.custom_lot_spin.setValue(lot_size)
            
            self.default_sl_spin.setValue(values['sl_pips'])
            self.default_tp_spin.setValue(values['tp_pips'])
            self.risk_per_trade_spin.setValue(values['risk_per_trade'])
            
            self.on_settings_changed()

