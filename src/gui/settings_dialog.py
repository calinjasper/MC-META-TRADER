"""
Settings Dialog
Configuration management
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QSpinBox, QPushButton, QGroupBox,
                             QTabWidget, QWidget, QMessageBox, QCheckBox, QLabel)
from PyQt6.QtCore import Qt

from ..config import Config
from ..utils.font_utils import apply_font_to_widget, get_stylesheet_font_string


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
        
        # Set dark theme background
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLineEdit, QSpinBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444;
                border-radius: 3px;
                padding: 5px;
            }
            QLineEdit:focus, QSpinBox:focus {
                border: 1px solid #2196F3;
            }
            QLabel {
                color: #ffffff;
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
        """)
        
        layout = QVBoxLayout(self)
        
        # Create tabs
        tabs = QTabWidget()
        tab_font_style = get_stylesheet_font_string('medium', 'medium')
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid #444;
                background-color: #1e1e1e;
            }}
            QTabBar::tab {{
                {tab_font_style}
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                background-color: #2b2b2b;
                color: #ffffff;
            }}
            QTabBar::tab:selected {{
                background-color: #1e1e1e;
                color: #2196F3;
                border-bottom: 2px solid #2196F3;
            }}
            QTabBar::tab:hover {{
                background-color: #3a3a3a;
            }}
        """)
        
        # MT5 Settings tab
        mt5_tab = QWidget()
        mt5_layout = QFormLayout(mt5_tab)
        
        self.mt5_path_input = QLineEdit()
        apply_font_to_widget(self.mt5_path_input, 'normal', 'regular')
        mt5_layout.addRow("MT5 Path (empty for auto):", self.mt5_path_input)
        
        self.mt5_login_input = QSpinBox()
        self.mt5_login_input.setMinimum(0)
        self.mt5_login_input.setMaximum(999999999)
        apply_font_to_widget(self.mt5_login_input, 'normal', 'regular')
        mt5_layout.addRow("Login:", self.mt5_login_input)
        
        self.mt5_password_input = QLineEdit()
        self.mt5_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        apply_font_to_widget(self.mt5_password_input, 'normal', 'regular')
        mt5_layout.addRow("Password:", self.mt5_password_input)
        
        self.mt5_server_input = QLineEdit()
        apply_font_to_widget(self.mt5_server_input, 'normal', 'regular')
        mt5_layout.addRow("Server:", self.mt5_server_input)
        
        self.mt5_timeout_input = QSpinBox()
        self.mt5_timeout_input.setMinimum(1000)
        self.mt5_timeout_input.setMaximum(60000)
        self.mt5_timeout_input.setSingleStep(1000)
        apply_font_to_widget(self.mt5_timeout_input, 'normal', 'regular')
        mt5_layout.addRow("Timeout (ms):", self.mt5_timeout_input)
        
        tabs.addTab(mt5_tab, "MT5 Connection")
        
        # Trading Settings tab
        trading_tab = QWidget()
        trading_layout = QFormLayout(trading_tab)
        
        self.default_symbol_input = QLineEdit()
        apply_font_to_widget(self.default_symbol_input, 'normal', 'regular')
        trading_layout.addRow("Default Symbol:", self.default_symbol_input)
        
        self.default_lot_input = QLineEdit()
        apply_font_to_widget(self.default_lot_input, 'normal', 'regular')
        trading_layout.addRow("Default Lot Size:", self.default_lot_input)
        
        self.max_positions_input = QSpinBox()
        self.max_positions_input.setMinimum(1)
        self.max_positions_input.setMaximum(100)
        apply_font_to_widget(self.max_positions_input, 'normal', 'regular')
        trading_layout.addRow("Max Positions:", self.max_positions_input)
        
        tabs.addTab(trading_tab, "Trading")
        
        # Telegram Settings tab
        telegram_tab = QWidget()
        telegram_layout = QFormLayout(telegram_tab)
        
        self.telegram_enabled_check = QCheckBox("Enable Telegram Notifications")
        apply_font_to_widget(self.telegram_enabled_check, 'normal', 'regular')
        telegram_layout.addRow("", self.telegram_enabled_check)
        
        self.telegram_bot_token_input = QLineEdit()
        self.telegram_bot_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.telegram_bot_token_input.setPlaceholderText("Enter bot token from @BotFather")
        apply_font_to_widget(self.telegram_bot_token_input, 'normal', 'regular')
        telegram_layout.addRow("Bot Token:", self.telegram_bot_token_input)
        
        self.telegram_channel_id_input = QLineEdit()
        self.telegram_channel_id_input.setPlaceholderText("@channel or -1001234567890 (optional if auto-create)")
        apply_font_to_widget(self.telegram_channel_id_input, 'normal', 'regular')
        telegram_layout.addRow("Channel ID/Username:", self.telegram_channel_id_input)
        
        self.telegram_channel_name_input = QLineEdit()
        self.telegram_channel_name_input.setPlaceholderText("Channel name for auto-creation")
        apply_font_to_widget(self.telegram_channel_name_input, 'normal', 'regular')
        telegram_layout.addRow("Channel Name:", self.telegram_channel_name_input)
        
        self.telegram_auto_create_check = QCheckBox("Auto-create channel")
        apply_font_to_widget(self.telegram_auto_create_check, 'normal', 'regular')
        telegram_layout.addRow("", self.telegram_auto_create_check)
        
        test_btn = QPushButton("Test Connection")
        apply_font_to_widget(test_btn, 'normal', 'medium')
        test_btn.clicked.connect(self.test_telegram_connection)
        telegram_layout.addRow("", test_btn)
        
        self.telegram_status_label = QLabel("")
        apply_font_to_widget(self.telegram_status_label, 'normal', 'regular')
        telegram_layout.addRow("Status:", self.telegram_status_label)
        
        tabs.addTab(telegram_tab, "Telegram")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        button_font_style = get_stylesheet_font_string('medium', 'semi_bold')
        save_btn.setStyleSheet(f"{button_font_style} padding: 6px 20px; border-radius: 4px;")
        apply_font_to_widget(save_btn, 'medium', 'semi_bold')
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"{button_font_style} padding: 6px 20px; border-radius: 4px;")
        apply_font_to_widget(cancel_btn, 'medium', 'semi_bold')
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
        self.max_positions_input.setValue(trading_config.get('max_positions', 10))
        
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
        
        self.config.set('trading.max_positions', self.max_positions_input.value())
        
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

