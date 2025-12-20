"""
Signal Management Panel
UI for monitoring and managing external signals
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QPushButton, QGroupBox, QLineEdit, QSpinBox,
                             QCheckBox, QFormLayout, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from typing import Optional, Dict, Any
from datetime import datetime

from ..signal_routing.signal_server import SignalServer
from ..signal_routing.signal_router import SignalRouter


class SignalPanel(QWidget):
    """Signal management and monitoring panel"""
    
    def __init__(self, signal_server: Optional[SignalServer], signal_router: SignalRouter):
        super().__init__()
        self.signal_server = signal_server
        self.signal_router = signal_router
        self.setup_ui()
        self.setup_timers()
        self.update_display()
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Server Status Section
        status_group = QGroupBox("Signal Server Status")
        status_layout = QFormLayout()
        
        self.status_label = QLabel("Stopped")
        self.status_label.setStyleSheet("font-weight: bold; color: #f44336;")
        status_layout.addRow("Status:", self.status_label)
        
        self.port_label = QLabel("--")
        status_layout.addRow("Port:", self.port_label)
        
        self.queue_size_label = QLabel("0")
        status_layout.addRow("Queue Size:", self.queue_size_label)
        
        self.processed_label = QLabel("0")
        status_layout.addRow("Processed:", self.processed_label)
        
        self.failed_label = QLabel("0")
        self.failed_label.setStyleSheet("color: #f44336;")
        status_layout.addRow("Failed:", self.failed_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # Signal History Table
        history_label = QLabel("Signal History")
        history_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(history_label)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Time", "Symbol", "Action", "Quantity", "SL", "TP", "Status"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setMaximumHeight(300)
        layout.addWidget(self.history_table)
        
        # Execution History Table
        exec_label = QLabel("Execution History")
        exec_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(exec_label)
        
        self.exec_table = QTableWidget()
        self.exec_table.setColumnCount(5)
        self.exec_table.setHorizontalHeaderLabels([
            "Time", "Symbol", "Action", "Result", "Message"
        ])
        self.exec_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.exec_table.setAlternatingRowColors(True)
        layout.addWidget(self.exec_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.update_display)
        button_layout.addWidget(refresh_btn)
        
        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self.clear_history)
        button_layout.addWidget(clear_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Server Info
        info_group = QGroupBox("Server Information")
        info_layout = QVBoxLayout()
        
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #888; font-size: 10px;")
        info_layout.addWidget(self.info_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
    
    def setup_timers(self):
        """Setup update timers"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(2000)  # Update every 2 seconds
    
    def update_display(self):
        """Update the display with current signal server status"""
        if not self.signal_server:
            self.status_label.setText("Not Available")
            self.status_label.setStyleSheet("font-weight: bold; color: #888;")
            self.port_label.setText("--")
            return
        
        # Update status
        if self.signal_server.is_running():
            self.status_label.setText("Running")
            self.status_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
            self.port_label.setText(str(self.signal_server.port))
        else:
            self.status_label.setText("Stopped")
            self.status_label.setStyleSheet("font-weight: bold; color: #f44336;")
            self.port_label.setText(str(self.signal_server.port))
        
        # Update queue stats
        if hasattr(self.signal_server, 'signal_queue'):
            stats = self.signal_server.signal_queue.get_stats()
            self.queue_size_label.setText(str(stats.get('queue_size', 0)))
            self.processed_label.setText(str(stats.get('processed', 0)))
            self.failed_label.setText(str(stats.get('failed', 0)))
        
        # Update signal history
        self.update_signal_history()
        
        # Update execution history
        self.update_execution_history()
        
        # Update info
        if self.signal_server.is_running():
            self.info_label.setText(
                f"Signal server is running on port {self.signal_server.port}.\n"
                f"Send signals to: http://localhost:{self.signal_server.port}/signal\n"
                f"Health check: http://localhost:{self.signal_server.port}/health"
            )
        else:
            self.info_label.setText("Signal server is not running.")
    
    def update_signal_history(self):
        """Update signal history table"""
        if not self.signal_router or not hasattr(self.signal_router, 'signal_rules'):
            return
        
        history = self.signal_router.signal_rules.get_signal_history(limit=50)
        
        self.history_table.setRowCount(len(history))
        
        for row, entry in enumerate(history):
            signal = entry.get('signal', {})
            time_str = entry.get('time', datetime.now())
            if isinstance(time_str, datetime):
                time_str = time_str.strftime("%H:%M:%S")
            
            # Time
            self.history_table.setItem(row, 0, QTableWidgetItem(str(time_str)))
            
            # Symbol
            self.history_table.setItem(row, 1, QTableWidgetItem(signal.get('symbol', '--')))
            
            # Action
            action = signal.get('action', '--')
            action_item = QTableWidgetItem(action)
            if action == 'BUY':
                action_item.setForeground(QColor("#4CAF50"))
            elif action == 'SELL':
                action_item.setForeground(QColor("#f44336"))
            self.history_table.setItem(row, 2, action_item)
            
            # Quantity
            self.history_table.setItem(row, 3, QTableWidgetItem(str(signal.get('quantity', 0))))
            
            # SL
            sl = signal.get('stop_loss', 0)
            sl_text = f"{sl:.5f}" if sl > 0 else "--"
            self.history_table.setItem(row, 4, QTableWidgetItem(sl_text))
            
            # TP
            tp = signal.get('take_profit', 0)
            tp_text = f"{tp:.5f}" if tp > 0 else "--"
            self.history_table.setItem(row, 5, QTableWidgetItem(tp_text))
            
            # Status (queued/processed)
            status = "Queued"  # Default
            self.history_table.setItem(row, 6, QTableWidgetItem(status))
    
    def update_execution_history(self):
        """Update execution history table"""
        if not self.signal_router:
            return
        
        history = self.signal_router.get_execution_history(limit=50)
        
        self.exec_table.setRowCount(len(history))
        
        for row, entry in enumerate(history):
            time_str = entry.get('time', datetime.now())
            if isinstance(time_str, datetime):
                time_str = time_str.strftime("%H:%M:%S")
            
            result = entry.get('result', {})
            signal = entry.get('signal', {})
            
            # Time
            self.exec_table.setItem(row, 0, QTableWidgetItem(str(time_str)))
            
            # Symbol
            self.exec_table.setItem(row, 1, QTableWidgetItem(signal.get('symbol', '--')))
            
            # Action
            action = signal.get('action', '--')
            action_item = QTableWidgetItem(action)
            if action == 'BUY':
                action_item.setForeground(QColor("#4CAF50"))
            elif action == 'SELL':
                action_item.setForeground(QColor("#f44336"))
            self.exec_table.setItem(row, 2, action_item)
            
            # Result
            success = result.get('success', False)
            result_item = QTableWidgetItem("Success" if success else "Failed")
            result_item.setForeground(QColor("#4CAF50") if success else QColor("#f44336"))
            self.exec_table.setItem(row, 3, result_item)
            
            # Message
            message = result.get('message') or result.get('error', '--')
            self.exec_table.setItem(row, 4, QTableWidgetItem(str(message)))
    
    def clear_history(self):
        """Clear signal history"""
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Clear all signal and execution history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if hasattr(self.signal_router, 'signal_rules'):
                self.signal_router.signal_rules.signal_history.clear()
            if hasattr(self.signal_router, 'execution_history'):
                self.signal_router.execution_history.clear()
            self.update_display()

