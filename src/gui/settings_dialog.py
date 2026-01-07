"""
Settings Dialog
Configuration management
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QSpinBox, QPushButton, QGroupBox,
                             QTabWidget, QWidget, QMessageBox, QCheckBox, QLabel)
from PyQt6.QtCore import Qt

from ..config import Config


class SettingsDialog(QDialog):
    """Settings configuration dialog"""
    
    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the UI"""
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Create tabs
        tabs = QTabWidget()
        
        # MT5 Settings tab
        mt5_tab = QWidget()
        mt5_layout = QFormLayout(mt5_tab)
        
        self.mt5_path_input = QLineEdit()
        mt5_layout.addRow("MT5 Path (empty for auto):", self.mt5_path_input)
        
        self.mt5_login_input = QSpinBox()
        self.mt5_login_input.setMinimum(0)
        self.mt5_login_input.setMaximum(999999999)
        mt5_layout.addRow("Login:", self.mt5_login_input)
        
        self.mt5_password_input = QLineEdit()
        self.mt5_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        mt5_layout.addRow("Password:", self.mt5_password_input)
        
        self.mt5_server_input = QLineEdit()
        mt5_layout.addRow("Server:", self.mt5_server_input)
        
        self.mt5_timeout_input = QSpinBox()
        self.mt5_timeout_input.setMinimum(1000)
        self.mt5_timeout_input.setMaximum(60000)
        self.mt5_timeout_input.setSingleStep(1000)
        mt5_layout.addRow("Timeout (ms):", self.mt5_timeout_input)
        
        tabs.addTab(mt5_tab, "MT5 Connection")
        
        # Trading Settings tab
        trading_tab = QWidget()
        trading_layout = QFormLayout(trading_tab)
        
        self.default_symbol_input = QLineEdit()
        trading_layout.addRow("Default Symbol:", self.default_symbol_input)
        
        self.default_lot_input = QLineEdit()
        trading_layout.addRow("Default Lot Size:", self.default_lot_input)
        
        self.max_positions_input = QSpinBox()
        self.max_positions_input.setMinimum(0)  # 0 = unlimited
        self.max_positions_input.setMaximum(100)
        self.max_positions_input.setSpecialValueText("Unlimited")
        trading_layout.addRow("Max Positions:", self.max_positions_input)
        
        tabs.addTab(trading_tab, "Trading")
        
        # Telegram Settings tab
        telegram_tab = QWidget()
        telegram_layout = QFormLayout(telegram_tab)
        
        self.telegram_enabled_check = QCheckBox("Enable Telegram Notifications")
        telegram_layout.addRow("", self.telegram_enabled_check)
        
        self.telegram_bot_token_input = QLineEdit()
        self.telegram_bot_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.telegram_bot_token_input.setPlaceholderText("Enter bot token from @BotFather")
        telegram_layout.addRow("Bot Token:", self.telegram_bot_token_input)
        
        self.telegram_channel_id_input = QLineEdit()
        self.telegram_channel_id_input.setPlaceholderText("@channel or -1001234567890 (optional if auto-create)")
        telegram_layout.addRow("Channel ID/Username:", self.telegram_channel_id_input)
        
        self.telegram_channel_name_input = QLineEdit()
        self.telegram_channel_name_input.setPlaceholderText("Channel name for auto-creation")
        telegram_layout.addRow("Channel Name:", self.telegram_channel_name_input)
        
        self.telegram_auto_create_check = QCheckBox("Auto-create channel")
        telegram_layout.addRow("", self.telegram_auto_create_check)
        
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self.test_telegram_connection)
        telegram_layout.addRow("", test_btn)
        
        self.telegram_status_label = QLabel("")
        telegram_layout.addRow("Status:", self.telegram_status_label)
        
        tabs.addTab(telegram_tab, "Telegram")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_settings(self):
        """Load settings from config"""
        # MT5 settings
        mt5_config = self.config.get('mt5', {})
        self.mt5_path_input.setText(mt5_config.get('path', ''))
        self.mt5_login_input.setValue(mt5_config.get('login', 0))
        self.mt5_password_input.setText(mt5_config.get('password', ''))
        self.mt5_server_input.setText(mt5_config.get('server', ''))
        self.mt5_timeout_input.setValue(mt5_config.get('timeout', 10000))
        
        # Trading settings
        trading_config = self.config.get('trading', {})
        self.default_symbol_input.setText(trading_config.get('default_symbol', 'EURUSD'))
        self.default_lot_input.setText(str(trading_config.get('default_lot_size', 0.01)))
        # Convert None (unlimited) to 0 for UI, otherwise use the value
        max_pos = trading_config.get('max_positions', None)
        self.max_positions_input.setValue(0 if max_pos is None else max_pos)
        
        # Telegram settings
        telegram_config = self.config.get('telegram', {})
        self.telegram_enabled_check.setChecked(telegram_config.get('enabled', False))
        self.telegram_bot_token_input.setText(telegram_config.get('bot_token', ''))
        self.telegram_channel_id_input.setText(telegram_config.get('channel_id', ''))
        self.telegram_channel_name_input.setText(telegram_config.get('channel_name', 'TradingBot_Alerts'))
        self.telegram_auto_create_check.setChecked(telegram_config.get('auto_create_channel', True))
        self.telegram_status_label.setText("Not tested")
    
    def save_settings(self):
        """Save settings to config"""
        # Validate
        if not self.mt5_login_input.value():
            QMessageBox.warning(self, "Validation Error", "Login is required")
            return
        
        if not self.mt5_password_input.text():
            QMessageBox.warning(self, "Validation Error", "Password is required")
            return
        
        if not self.mt5_server_input.text():
            QMessageBox.warning(self, "Validation Error", "Server is required")
            return
        
        # Save MT5 settings
        self.config.set('mt5.path', self.mt5_path_input.text())
        self.config.set('mt5.login', self.mt5_login_input.value())
        self.config.set('mt5.password', self.mt5_password_input.text())
        self.config.set('mt5.server', self.mt5_server_input.text())
        self.config.set('mt5.timeout', self.mt5_timeout_input.value())
        
        # Save trading settings
        self.config.set('trading.default_symbol', self.default_symbol_input.text().upper())
        try:
            lot_size = float(self.default_lot_input.text())
            self.config.set('trading.default_lot_size', lot_size)
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Invalid lot size")
            return
        
        # Convert 0 (unlimited) to None for config
        max_pos_value = self.max_positions_input.value()
        self.config.set('trading.max_positions', None if max_pos_value == 0 else max_pos_value)
        
        # Save Telegram settings
        self.config.set('telegram.enabled', self.telegram_enabled_check.isChecked())
        self.config.set('telegram.bot_token', self.telegram_bot_token_input.text())
        self.config.set('telegram.channel_id', self.telegram_channel_id_input.text())
        self.config.set('telegram.channel_name', self.telegram_channel_name_input.text())
        self.config.set('telegram.auto_create_channel', self.telegram_auto_create_check.isChecked())
        
        # Save to file
        self.config.save()
        
        QMessageBox.information(self, "Success", "Settings saved successfully")
        self.accept()
    
    def test_telegram_connection(self):
        """Test Telegram bot connection"""
        bot_token = self.telegram_bot_token_input.text().strip()
        if not bot_token:
            QMessageBox.warning(self, "Error", "Please enter bot token")
            return
        
        try:
            from ..notifications.telegram_bot import TelegramBot
            channel_id = self.telegram_channel_id_input.text().strip() or None
            channel_name = self.telegram_channel_name_input.text().strip() or "TradingBot_Alerts"
            
            bot = TelegramBot(bot_token, channel_id, channel_name)
            if bot._initialized:
                self.telegram_status_label.setText("✅ Connected")
                self.telegram_status_label.setStyleSheet("color: green;")
                QMessageBox.information(self, "Success", "Telegram bot connected successfully!")
            else:
                self.telegram_status_label.setText("❌ Connection failed")
                self.telegram_status_label.setStyleSheet("color: red;")
                QMessageBox.warning(self, "Error", "Failed to connect to Telegram bot. Check your token.")
        except Exception as e:
            self.telegram_status_label.setText(f"❌ Error: {str(e)}")
            self.telegram_status_label.setStyleSheet("color: red;")
            QMessageBox.critical(self, "Error", f"Error testing connection: {str(e)}")

