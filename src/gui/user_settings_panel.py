"""
User Settings Panel
Allows users to configure MT5 account credentials and verify account with performance dashboard
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QPushButton, QLabel, QGroupBox, QMessageBox,
                             QProgressBar, QFrame, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import logging
import statistics
import MetaTrader5 as mt5

# UTC timezone support for MT5 timestamps
try:
    from zoneinfo import ZoneInfo
    UTC = ZoneInfo("UTC")
except ImportError:
    try:
        import pytz
        UTC = pytz.UTC
    except ImportError:
        from datetime import timezone
        UTC = timezone.utc

from ..mt5_connector import MT5Connector
from ..config import Config

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    """Calculate performance metrics from deal history"""
    
    @staticmethod
    def calculate_metrics(deals: List[Dict], account_balance: float) -> Dict:
        """Calculate all performance metrics from deals"""
        if not deals:
            return {
                'gross_profit': 0.0,
                'gross_loss': 0.0,
                'total_pl': 0.0,
                'commissions': 0.0,
                'swaps': 0.0,
                'dividends': 0.0,
                'profit_factor': 0.0,
                'recovery_factor': 0.0,
                'max_drawdown': 0.0,
                'max_deposit_load': 0.0,
                'trades_per_week': 0.0,
                'average_hold_time': 0.0,
                'sharpe_ratio': 0.0,
                'total_trades': 0
            }
        
        # Separate entry and exit deals
        # MT5: entry == 0 (DEAL_ENTRY_IN) = Entry deal, entry == 1 (DEAL_ENTRY_OUT) = Exit deal
        entry_deals = [d for d in deals if d.get('entry') == 0]  # DEAL_ENTRY_IN
        exit_deals = [d for d in deals if d.get('entry') == 1]   # DEAL_ENTRY_OUT
        
        # Calculate gross profit and loss
        gross_profit = sum(d.get('profit', 0.0) for d in exit_deals if d.get('profit', 0.0) > 0)
        gross_loss = abs(sum(d.get('profit', 0.0) for d in exit_deals if d.get('profit', 0.0) < 0))
        total_pl = sum(d.get('profit', 0.0) for d in exit_deals)
        
        # Calculate commissions, swaps, dividends
        commissions = sum(d.get('commission', 0.0) for d in deals)
        swaps = sum(d.get('swap', 0.0) for d in deals)
        dividends = sum(d.get('profit', 0.0) for d in deals if 'dividend' in str(d.get('comment', '')).lower())
        
        # Profit Factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        
        # Calculate equity curve for drawdown
        equity_curve = []
        running_equity = account_balance
        max_equity = account_balance
        max_drawdown = 0.0
        
        # Sort deals by time
        sorted_deals = sorted(exit_deals, key=lambda x: x.get('time', datetime.min))
        
        for deal in sorted_deals:
            running_equity += deal.get('profit', 0.0)
            equity_curve.append(running_equity)
            if running_equity > max_equity:
                max_equity = running_equity
            drawdown = (max_equity - running_equity) / max_equity * 100 if max_equity > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Recovery Factor
        recovery_factor = total_pl / max_drawdown if max_drawdown > 0 else 0.0
        
        # Max Deposit Load (simplified - would need margin history)
        max_deposit_load = 0.0  # Would need margin history to calculate properly
        
        # Trades per week
        if sorted_deals:
            first_trade = sorted_deals[0].get('time', datetime.now())
            last_trade = sorted_deals[-1].get('time', datetime.now())
            if isinstance(first_trade, datetime) and isinstance(last_trade, datetime):
                days = (last_trade - first_trade).days
                weeks = max(days / 7.0, 1.0)
                trades_per_week = len(exit_deals) / weeks
            else:
                trades_per_week = 0.0
        else:
            trades_per_week = 0.0
        
        # Average Hold Time
        hold_times = []
        for exit_deal in exit_deals:
            position_id = exit_deal.get('position_id', 0)
            # Find corresponding entry deal
            entry_deal = next((d for d in entry_deals if d.get('position_id') == position_id), None)
            if entry_deal:
                entry_time = entry_deal.get('time', datetime.now())
                exit_time = exit_deal.get('time', datetime.now())
                if isinstance(entry_time, datetime) and isinstance(exit_time, datetime):
                    hold_time = (exit_time - entry_time).total_seconds() / 60.0  # minutes
                    hold_times.append(hold_time)
        
        average_hold_time = sum(hold_times) / len(hold_times) if hold_times else 0.0
        
        # Sharpe Ratio (simplified calculation)
        if len(equity_curve) > 1:
            returns = []
            for i in range(1, len(equity_curve)):
                if equity_curve[i-1] > 0:
                    ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
                    returns.append(ret)
            
            if returns and len(returns) > 1:
                mean_return = statistics.mean(returns)
                std_return = statistics.stdev(returns)
                sharpe_ratio = (mean_return / std_return) if std_return > 0 else 0.0
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
        
        return {
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'total_pl': total_pl,
            'commissions': commissions,
            'swaps': swaps,
            'dividends': dividends,
            'profit_factor': profit_factor,
            'recovery_factor': recovery_factor,
            'max_drawdown': max_drawdown,
            'max_deposit_load': max_deposit_load,
            'trades_per_week': trades_per_week,
            'average_hold_time': average_hold_time,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len(exit_deals)
        }


class VerifyAccountThread(QThread):
    """Thread for verifying account without blocking UI"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, login: int, password: str, server: str, path: str = "", timeout: int = 10000):
        super().__init__()
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self.timeout = timeout
    
    def run(self):
        """Run account verification"""
        try:
            # Initialize MT5
            if self.path:
                if not mt5.initialize(path=self.path):
                    self.error.emit(f"MT5 initialization failed: {mt5.last_error()}")
                    return
            else:
                if not mt5.initialize():
                    self.error.emit(f"MT5 initialization failed: {mt5.last_error()}")
                    return
            
            # Login
            if not mt5.login(self.login, password=self.password, server=self.server, timeout=self.timeout):
                error_info = mt5.last_error()
                error_msg = error_info[1] if isinstance(error_info, tuple) else str(error_info)
                mt5.shutdown()
                self.error.emit(f"Login failed: {error_msg}")
                return
            
            # Get account info
            account_info = mt5.account_info()
            if account_info is None:
                mt5.shutdown()
                self.error.emit("Could not retrieve account info")
                return
            
            # Get terminal info for trading permissions
            terminal_info = mt5.terminal_info()
            
            # Get deal history
            date_from = datetime.now() - timedelta(days=90)  # Last 90 days
            date_to = datetime.now()
            date_from_ts = int(date_from.timestamp())
            date_to_ts = int(date_to.timestamp())
            deals = mt5.history_deals_get(date_from_ts, date_to_ts)
            
            deal_list = []
            if deals:
                for deal in deals:
                    deal_list.append({
                        'ticket': deal.ticket,
                        'order': deal.order,
                        'time': datetime.fromtimestamp(deal.time, tz=UTC),
                        'type': deal.type,
                        'entry': deal.entry,
                        'position_id': deal.position_id,
                        'price': deal.price,
                        'volume': deal.volume,
                        'profit': deal.profit,
                        'swap': deal.swap,
                        'commission': deal.commission,
                        'symbol': deal.symbol,
                        'comment': deal.comment
                    })
            
            # Calculate metrics
            metrics = PerformanceCalculator.calculate_metrics(deal_list, account_info.balance)
            
            # Prepare result
            result = {
                'account_info': {
                    'login': account_info.login,
                    'balance': account_info.balance,
                    'equity': account_info.equity,
                    'margin': account_info.margin,
                    'free_margin': account_info.margin_free,
                    'margin_level': account_info.margin_level,
                    'profit': account_info.profit,
                    'currency': account_info.currency,
                    'server': account_info.server,
                    'leverage': account_info.leverage,
                    'trade_mode': account_info.trade_mode
                },
                'terminal_info': {
                    'trade_allowed': terminal_info.trade_allowed if terminal_info else False,
                    'tradeapi_disabled': terminal_info.tradeapi_disabled if terminal_info else False
                },
                'metrics': metrics
            }
            
            mt5.shutdown()
            self.finished.emit(result)
            
        except Exception as e:
            logger.error(f"Error verifying account: {e}", exc_info=True)
            self.error.emit(f"Error: {str(e)}")


class MetricBarWidget(QWidget):
    """Custom widget for displaying metric with progress bar"""
    
    def __init__(self, label: str, value: float, min_val: float, max_val: float, unit: str = ""):
        super().__init__()
        self.label = label
        self.value = value
        self.min_val = min_val
        self.max_val = max_val
        self.unit = unit
        self.setup_ui()
    
    def setup_ui(self):
        """Setup UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Label and value
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        label_widget = QLabel(self.label)
        label_widget.setStyleSheet("font-weight: bold; color: white;")
        label_widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(label_widget)
        header_layout.addStretch()
        
        value_text = f"{self.value:.2f}"
        if self.unit:
            value_text += f" {self.unit}"
        value_label = QLabel(value_text)
        value_label.setStyleSheet("font-weight: bold; color: white;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(value_label)
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(int(self.min_val * 100))
        self.progress_bar.setMaximum(int(self.max_val * 100))
        
        # Calculate normalized value for display
        normalized = ((self.value - self.min_val) / (self.max_val - self.min_val)) * 100
        normalized = max(0, min(100, normalized))
        self.progress_bar.setValue(int(normalized))
        
        # Color based on value
        if self.value < 0:
            color = "#f44336"  # Red
        elif self.value < (self.max_val - self.min_val) * 0.3:
            color = "#ff9800"  # Orange
        else:
            color = "#4CAF50"  # Green
        
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                background-color: #2b2b2b;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)
        
        # Range label
        range_label = QLabel(f"Range: {self.min_val} to {self.max_val}")
        range_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(range_label)
        
        layout.addWidget(self.progress_bar)
    
    def update_value(self, value: float):
        """Update the displayed value"""
        self.value = value
        value_text = f"{self.value:.2f}"
        if self.unit:
            value_text += f" {self.unit}"
        # Update label (find it in layout)
        header_layout = self.layout().itemAt(0).layout()
        value_label = header_layout.itemAt(header_layout.count() - 1).widget()
        if value_label:
            value_label.setText(value_text)
        
        # Update progress bar
        normalized = ((self.value - self.min_val) / (self.max_val - self.min_val)) * 100
        normalized = max(0, min(100, normalized))
        self.progress_bar.setValue(int(normalized))


class UserSettingsPanel(QWidget):
    """User Settings Panel with Account Verification"""
    
    def __init__(self, mt5_connector: MT5Connector, config: Config):
        super().__init__()
        self.mt5 = mt5_connector
        self.config = config
        self.verify_thread = None
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Scroll area for the entire panel
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        
        # Account Configuration Section
        account_group = QGroupBox("Account Configuration")
        account_group.setStyleSheet(self._get_group_style())
        account_layout = QFormLayout()
        account_layout.setSpacing(10)
        
        self.account_id_input = QLineEdit()
        self.account_id_input.setPlaceholderText("Enter Account ID (Login)")
        account_layout.addRow("Account ID:", self.account_id_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter Password")
        account_layout.addRow("Password:", self.password_input)
        
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("Enter Server Name")
        account_layout.addRow("Server:", self.server_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 8px;")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        self.verify_btn = QPushButton("Verify Account")
        self.verify_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.verify_btn.clicked.connect(self.verify_account)
        button_layout.addWidget(self.verify_btn)
        
        button_layout.addStretch()
        account_layout.addRow("", button_layout)
        
        account_group.setLayout(account_layout)
        scroll_layout.addWidget(account_group)
        
        # Account Status Section
        status_group = QGroupBox("Account Status")
        status_group.setStyleSheet(self._get_group_style())
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Not Verified")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #888;")
        status_layout.addWidget(self.status_label)
        
        self.account_details_label = QLabel("")
        self.account_details_label.setStyleSheet("color: #ccc;")
        self.account_details_label.setWordWrap(True)
        status_layout.addWidget(self.account_details_label)
        
        status_group.setLayout(status_layout)
        scroll_layout.addWidget(status_group)
        
        # Performance Dashboard Section
        dashboard_group = QGroupBox("Performance Dashboard")
        dashboard_group.setStyleSheet(self._get_group_style())
        dashboard_layout = QVBoxLayout()
        
        # Profit & Loss Overview
        pnl_section = QFrame()
        pnl_layout = QHBoxLayout(pnl_section)
        pnl_layout.setSpacing(20)
        
        # Left side - P&L values
        pnl_left = QVBoxLayout()
        
        self.gross_profit_label = QLabel("Gross Profit: +0.00")
        self.gross_profit_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        pnl_left.addWidget(self.gross_profit_label)
        
        self.gross_loss_label = QLabel("Gross Loss: -0.00")
        self.gross_loss_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #f44336;")
        pnl_left.addWidget(self.gross_loss_label)
        
        self.total_pl_label = QLabel("Total: 0.00")
        self.total_pl_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #888;")
        pnl_left.addWidget(self.total_pl_label)
        
        self.commissions_label = QLabel("Commissions: 0.00")
        self.commissions_label.setStyleSheet("color: #4CAF50;")
        pnl_left.addWidget(self.commissions_label)
        
        self.swaps_label = QLabel("Swaps: 0.00")
        self.swaps_label.setStyleSheet("color: #4CAF50;")
        pnl_left.addWidget(self.swaps_label)
        
        self.dividends_label = QLabel("Dividends: 0.00")
        self.dividends_label.setStyleSheet("color: #4CAF50;")
        pnl_left.addWidget(self.dividends_label)
        
        pnl_layout.addLayout(pnl_left)
        pnl_layout.addStretch()
        
        dashboard_layout.addWidget(pnl_section)
        
        # Performance Metrics
        metrics_label = QLabel("Performance Metrics")
        metrics_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        dashboard_layout.addWidget(metrics_label)
        
        # Metrics grid
        metrics_grid = QVBoxLayout()
        metrics_grid.setSpacing(10)
        
        # Create metric bars
        self.sharpe_ratio_widget = MetricBarWidget("Sharpe Ratio", 0.0, -1.0, 5.0)
        metrics_grid.addWidget(self.sharpe_ratio_widget)
        
        self.profit_factor_widget = MetricBarWidget("Profit Factor", 0.0, 0.0, 4.0)
        metrics_grid.addWidget(self.profit_factor_widget)
        
        self.recovery_factor_widget = MetricBarWidget("Recovery Factor", 0.0, -1.0, 7.0)
        metrics_grid.addWidget(self.recovery_factor_widget)
        
        self.max_drawdown_widget = MetricBarWidget("Max. Drawdown", 0.0, 0.0, 100.0, "%")
        metrics_grid.addWidget(self.max_drawdown_widget)
        
        self.max_deposit_load_widget = MetricBarWidget("Max. Deposit Load", 0.0, 0.0, 100.0, "%")
        metrics_grid.addWidget(self.max_deposit_load_widget)
        
        # Additional metrics
        additional_layout = QHBoxLayout()
        
        trades_widget = QFrame()
        trades_layout = QVBoxLayout(trades_widget)
        trades_label = QLabel("Trades per Week")
        trades_label.setStyleSheet("font-weight: bold; color: white;")
        trades_layout.addWidget(trades_label)
        self.trades_per_week_label = QLabel("0")
        self.trades_per_week_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        trades_layout.addWidget(self.trades_per_week_label)
        additional_layout.addWidget(trades_widget)
        
        hold_time_widget = QFrame()
        hold_time_layout = QVBoxLayout(hold_time_widget)
        hold_time_label = QLabel("Average Hold Time")
        hold_time_label.setStyleSheet("font-weight: bold; color: white;")
        hold_time_layout.addWidget(hold_time_label)
        self.hold_time_label = QLabel("0m")
        self.hold_time_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        hold_time_layout.addWidget(self.hold_time_label)
        additional_layout.addWidget(hold_time_widget)
        
        additional_layout.addStretch()
        metrics_grid.addLayout(additional_layout)
        
        dashboard_layout.addLayout(metrics_grid)
        dashboard_group.setLayout(dashboard_layout)
        scroll_layout.addWidget(dashboard_group)
        
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
    
    def _get_group_style(self) -> str:
        """Get consistent group box styling"""
        return """
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #fff;
            }
        """
    
    def load_settings(self):
        """Load settings from config"""
        mt5_config = self.config.get('mt5', {})
        self.account_id_input.setText(str(mt5_config.get('login', '')))
        self.password_input.setText(mt5_config.get('password', ''))
        self.server_input.setText(mt5_config.get('server', ''))
    
    def save_settings(self):
        """Save settings to config"""
        try:
            account_id = self.account_id_input.text().strip()
            password = self.password_input.text().strip()
            server = self.server_input.text().strip()
            
            if not account_id or not password or not server:
                QMessageBox.warning(self, "Validation Error", "Please fill in all fields")
                return
            
            try:
                login = int(account_id)
            except ValueError:
                QMessageBox.warning(self, "Validation Error", "Account ID must be a number")
                return
            
            # Save to config
            self.config.set('mt5.login', login)
            self.config.set('mt5.password', password)
            self.config.set('mt5.server', server)
            self.config.save()
            
            QMessageBox.information(self, "Success", "Settings saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
    
    def verify_account(self):
        """Verify account with MT5"""
        account_id = self.account_id_input.text().strip()
        password = self.password_input.text().strip()
        server = self.server_input.text().strip()
        
        if not account_id or not password or not server:
            QMessageBox.warning(self, "Validation Error", "Please fill in all account fields")
            return
        
        try:
            login = int(account_id)
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Account ID must be a number")
            return
        
        # Disable verify button during verification
        self.verify_btn.setEnabled(False)
        self.verify_btn.setText("Verifying...")
        
        self.status_label.setText("Verifying...")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ff9800;")
        
        # Get MT5 path from config
        mt5_path = self.config.get('mt5.path', '')
        timeout = self.config.get('mt5.timeout', 10000)
        
        # Start verification thread
        self.verify_thread = VerifyAccountThread(login, password, server, mt5_path, timeout)
        self.verify_thread.finished.connect(self.on_verification_success)
        self.verify_thread.error.connect(self.on_verification_error)
        self.verify_thread.start()
    
    def on_verification_success(self, result: Dict):
        """Handle successful verification"""
        account_info = result.get('account_info', {})
        terminal_info = result.get('terminal_info', {})
        metrics = result.get('metrics', {})
        
        # Connect to MT5 using verified credentials
        account_id = self.account_id_input.text().strip()
        password = self.password_input.text().strip()
        server = self.server_input.text().strip()
        mt5_path = self.config.get('mt5.path', '')
        timeout = self.config.get('mt5.timeout', 10000)
        
        try:
            login = int(account_id)
            # Connect to MT5
            if self.mt5.initialize(path=mt5_path, login=login, password=password, server=server, timeout=timeout):
                logger.info(f"Successfully connected to MT5 account {login} after verification")
            else:
                error_msg = f"Failed to connect to MT5: {self.mt5.get_last_error() or 'Unknown error'}"
                logger.warning(error_msg)
                QMessageBox.warning(self, "Connection Warning", 
                    f"Account verified successfully, but could not connect to MT5:\n\n{error_msg}\n\n"
                    f"You may need to connect manually.")
        except Exception as e:
            logger.error(f"Error connecting to MT5 after verification: {e}", exc_info=True)
            QMessageBox.warning(self, "Connection Warning", 
                f"Account verified successfully, but error connecting to MT5:\n\n{str(e)}")
        
        # Update status
        # Primary check: AutoTrading must be enabled (trade_allowed)
        # Secondary check: trade_mode > 0 is preferred but not required if AutoTrading is enabled
        # Some brokers allow trading with trade_mode=0 when AutoTrading is enabled
        trade_allowed = terminal_info.get('trade_allowed', False)
        trade_mode = account_info.get('trade_mode', 0)
        
        # Check if MT5 is now connected
        mt5_connected = self.mt5.is_connected()
        
        if trade_allowed:
            # AutoTrading is enabled - account is ready for trading
            # trade_mode=0 is a warning but doesn't block trading if AutoTrading is enabled
            if trade_mode > 0:
                if mt5_connected:
                    self.status_label.setText("✓ Account Verified & MT5 Connected - Ready for Trading")
                else:
                    self.status_label.setText("✓ Account Verified - Ready for Trading (MT5 Not Connected)")
                self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #4CAF50;")
            else:
                # AutoTrading enabled but trade_mode=0 - still ready but with warning
                if mt5_connected:
                    self.status_label.setText("✓ Account Verified & MT5 Connected - Ready (Trade Mode: 0)")
                else:
                    self.status_label.setText("✓ Account Verified - Ready (Trade Mode: 0, MT5 Not Connected)")
                self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #4CAF50;")
        else:
            # AutoTrading is disabled - account is NOT ready
            if mt5_connected:
                self.status_label.setText("⚠ MT5 Connected but AutoTrading Disabled")
            else:
                self.status_label.setText("⚠ Account Not Ready (AutoTrading Disabled, MT5 Not Connected)")
            self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ff9800;")
        
        # Update account details with proper alignment
        currency = account_info.get('currency', 'USD')
        mt5_status = "Connected" if mt5_connected else "Not Connected"
        mt5_status_color = "#4CAF50" if mt5_connected else "#f44336"
        details = f"""
        <table style="width: 100%; border-collapse: collapse;">
        <tr><td style="padding: 2px 10px 2px 0; text-align: left; width: 40%;"><b>Account:</b></td><td style="padding: 2px 0; text-align: left;">{account_info.get('login', 'N/A')}</td></tr>
        <tr><td style="padding: 2px 10px 2px 0; text-align: left;"><b>Balance:</b></td><td style="padding: 2px 0; text-align: left;">{account_info.get('balance', 0):.2f} {currency}</td></tr>
        <tr><td style="padding: 2px 10px 2px 0; text-align: left;"><b>Equity:</b></td><td style="padding: 2px 0; text-align: left;">{account_info.get('equity', 0):.2f} {currency}</td></tr>
        <tr><td style="padding: 2px 10px 2px 0; text-align: left;"><b>Margin:</b></td><td style="padding: 2px 0; text-align: left;">{account_info.get('margin', 0):.2f} {currency}</td></tr>
        <tr><td style="padding: 2px 10px 2px 0; text-align: left;"><b>Free Margin:</b></td><td style="padding: 2px 0; text-align: left;">{account_info.get('free_margin', 0):.2f} {currency}</td></tr>
        <tr><td style="padding: 2px 10px 2px 0; text-align: left;"><b>Leverage:</b></td><td style="padding: 2px 0; text-align: left;">1:{account_info.get('leverage', 0)}</td></tr>
        <tr><td style="padding: 2px 10px 2px 0; text-align: left;"><b>Server:</b></td><td style="padding: 2px 0; text-align: left;">{account_info.get('server', 'N/A')}</td></tr>
        <tr><td style="padding: 2px 10px 2px 0; text-align: left;"><b>MT5 Connection:</b></td><td style="padding: 2px 0; text-align: left;"><span style="color: {mt5_status_color};">{mt5_status}</span></td></tr>
        <tr><td style="padding: 2px 10px 2px 0; text-align: left;"><b>AutoTrading:</b></td><td style="padding: 2px 0; text-align: left;">{'Enabled' if trade_allowed else 'Disabled'}</td></tr>
        <tr><td style="padding: 2px 10px 2px 0; text-align: left;"><b>Trade Mode:</b></td><td style="padding: 2px 0; text-align: left;">{trade_mode} {'(Enabled)' if trade_mode > 0 else '(Disabled)'}</td></tr>
        </table>
        """
        self.account_details_label.setText(details)
        
        # Update P&L display
        currency = account_info.get('currency', 'USD')
        self.gross_profit_label.setText(f"Gross Profit: +{metrics.get('gross_profit', 0):.2f} {currency}")
        self.gross_loss_label.setText(f"Gross Loss: -{metrics.get('gross_loss', 0):.2f} {currency}")
        
        total_pl = metrics.get('total_pl', 0)
        total_color = "#4CAF50" if total_pl >= 0 else "#f44336"
        sign = "+" if total_pl >= 0 else ""
        self.total_pl_label.setText(f"Total: {sign}{total_pl:.2f} {currency}")
        self.total_pl_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {total_color};")
        
        self.commissions_label.setText(f"Commissions: {metrics.get('commissions', 0):.2f} {currency}")
        self.swaps_label.setText(f"Swaps: {metrics.get('swaps', 0):.2f} {currency}")
        self.dividends_label.setText(f"Dividends: {metrics.get('dividends', 0):.2f} {currency}")
        
        # Update metrics
        self.sharpe_ratio_widget.update_value(metrics.get('sharpe_ratio', 0.0))
        self.profit_factor_widget.update_value(metrics.get('profit_factor', 0.0))
        self.recovery_factor_widget.update_value(metrics.get('recovery_factor', 0.0))
        self.max_drawdown_widget.update_value(metrics.get('max_drawdown', 0.0))
        self.max_deposit_load_widget.update_value(metrics.get('max_deposit_load', 0.0))
        
        self.trades_per_week_label.setText(f"{metrics.get('trades_per_week', 0):.0f}")
        
        avg_hold_time = metrics.get('average_hold_time', 0)
        if avg_hold_time < 60:
            hold_time_text = f"{avg_hold_time:.0f}m"
        elif avg_hold_time < 1440:
            hold_time_text = f"{avg_hold_time / 60:.1f}h"
        else:
            hold_time_text = f"{avg_hold_time / 1440:.1f}d"
        self.hold_time_label.setText(hold_time_text)
        
        # Re-enable verify button
        self.verify_btn.setEnabled(True)
        self.verify_btn.setText("Verify Account")
    
    def on_verification_error(self, error_msg: str):
        """Handle verification error"""
        self.status_label.setText("✗ Verification Failed")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #f44336;")
        self.account_details_label.setText(f"<b>Error:</b> {error_msg}")
        
        QMessageBox.warning(self, "Verification Failed", f"Could not verify account:\n\n{error_msg}")
        
        # Re-enable verify button
        self.verify_btn.setEnabled(True)
        self.verify_btn.setText("Verify Account")

