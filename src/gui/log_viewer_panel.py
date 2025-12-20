"""
Log Viewer Panel
Displays application logs in real-time
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QPushButton, QLabel, QComboBox, QLineEdit, QFileDialog,
                             QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QTextCharFormat, QColor, QTextCursor
from datetime import datetime
import logging
from pathlib import Path


class LogHandler(QObject, logging.Handler):
    """Custom logging handler that emits signals for UI updates"""
    
    log_received = pyqtSignal(str, str, str, str)  # level, message, timestamp, logger_name
    
    def __init__(self):
        QObject.__init__(self)
        logging.Handler.__init__(self)
        self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    def emit(self, record):
        """Emit log record as signal"""
        try:
            msg = self.format(record)
            level = record.levelname
            timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
            logger_name = record.name
            self.log_received.emit(level, msg, timestamp, logger_name)
        except Exception:
            self.handleError(record)


class LogViewerPanel(QWidget):
    """Panel displaying application logs in real-time"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_buffer = []  # Store logs for filtering
        self.max_logs = 10000  # Maximum number of logs to keep
        self.current_filter_level = "ALL"
        self.setup_ui()
        self.setup_log_handler()
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        
        # Title and controls
        header_layout = QHBoxLayout()
        
        title = QLabel("Application Logs")
        title.setStyleSheet("font-weight: bold; font-size: 16px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Filter by level
        level_label = QLabel("Level:")
        header_layout.addWidget(level_label)
        
        self.level_filter = QComboBox()
        self.level_filter.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.level_filter.currentTextChanged.connect(self.filter_logs)
        header_layout.addWidget(self.level_filter)
        
        # Search box
        search_label = QLabel("Search:")
        header_layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search logs...")
        self.search_box.textChanged.connect(self.filter_logs)
        self.search_box.setMaximumWidth(200)
        header_layout.addWidget(self.search_box)
        
        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_logs)
        header_layout.addWidget(clear_btn)
        
        # Export button
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_logs)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # Log display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFontFamily("Consolas")
        self.log_text.setFontPointSize(9)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
        """)
        layout.addWidget(self.log_text)
    
    def setup_log_handler(self):
        """Setup custom log handler"""
        self.log_handler = LogHandler()
        self.log_handler.log_received.connect(self.append_log)
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        
        # Set level to capture all logs
        self.log_handler.setLevel(logging.DEBUG)
    
    def append_log(self, level: str, message: str, timestamp: str, logger_name: str):
        """
        Append log entry to display
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            timestamp: Timestamp string
            logger_name: Name of logger
        """
        # Store in buffer
        log_entry = {
            'level': level,
            'message': message,
            'timestamp': timestamp,
            'logger_name': logger_name
        }
        self.log_buffer.append(log_entry)
        
        # Limit buffer size
        if len(self.log_buffer) > self.max_logs:
            self.log_buffer = self.log_buffer[-self.max_logs:]
        
        # Apply current filter
        if self._should_display(log_entry):
            self._display_log_entry(log_entry)
    
    def _should_display(self, log_entry: dict) -> bool:
        """Check if log entry should be displayed based on current filters"""
        # Level filter
        if self.current_filter_level != "ALL":
            if log_entry['level'] != self.current_filter_level:
                return False
        
        # Search filter
        search_text = self.search_box.text().lower()
        if search_text:
            if search_text not in log_entry['message'].lower():
                return False
        
        return True
    
    def _display_log_entry(self, log_entry: dict):
        """Display a log entry in the text widget"""
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Set color based on level
        format = QTextCharFormat()
        if log_entry['level'] == 'ERROR' or log_entry['level'] == 'CRITICAL':
            format.setForeground(QColor('#f48771'))  # Red
        elif log_entry['level'] == 'WARNING':
            format.setForeground(QColor('#dcdcaa'))  # Yellow
        elif log_entry['level'] == 'INFO':
            format.setForeground(QColor('#4ec9b0'))  # Cyan
        elif log_entry['level'] == 'DEBUG':
            format.setForeground(QColor('#808080'))  # Gray
        else:
            format.setForeground(QColor('#d4d4d4'))  # Default white
        
        cursor.setCharFormat(format)
        cursor.insertText(f"{log_entry['timestamp']} - {log_entry['level']} - {log_entry['message']}\n")
        
        # Auto-scroll to bottom
        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()
    
    def filter_logs(self):
        """Filter and redisplay logs based on current filters"""
        self.current_filter_level = self.level_filter.currentText()
        
        # Clear and redisplay filtered logs
        self.log_text.clear()
        
        for log_entry in self.log_buffer:
            if self._should_display(log_entry):
                self._display_log_entry(log_entry)
    
    def clear_logs(self):
        """Clear log display and buffer"""
        reply = QMessageBox.question(
            self,
            "Clear Logs",
            "Clear all logs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.log_text.clear()
            self.log_buffer.clear()
            # Intentionally do not append any synthetic/dummy log entries.
    
    def export_logs(self):
        """Export logs to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for log_entry in self.log_buffer:
                    f.write(f"{log_entry['timestamp']} - {log_entry['level']} - {log_entry['message']}\n")
            
            QMessageBox.information(self, "Success", f"Logs exported to:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export logs:\n{str(e)}")
    
    def closeEvent(self, event):
        """Clean up when panel is closed"""
        # Remove handler from logger
        if hasattr(self, 'log_handler'):
            root_logger = logging.getLogger()
            root_logger.removeHandler(self.log_handler)
        event.accept()

