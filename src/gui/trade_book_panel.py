"""
Trade Book Panel
Displays comprehensive trade history with exit condition detection from logs
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView,
                             QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from pathlib import Path
import re
import logging
import csv

from ..trading.order_manager import OrderManager

logger = logging.getLogger(__name__)


class TradeBookPanel(QWidget):
    """Panel displaying comprehensive trade history (trade book)"""
    
    def __init__(self, order_manager: OrderManager, parent=None):
        super().__init__(parent)
        self.order_manager = order_manager
        self.exit_condition_cache = {}  # Cache for log parsing results
        self.setup_ui()
        self.update_trade_book()
    
    def setup_ui(self):
        """Setup the UI"""
        # Apply dark theme styling
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
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
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #444;
                border: 1px solid #444;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background-color: #2196F3;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: #ffffff;
                padding: 8px;
                border: 1px solid #444;
                font-weight: bold;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Title and buttons
        header_layout = QHBoxLayout()
        
        title = QLabel("Trade Book")
        title.setStyleSheet("font-weight: bold; font-size: 16px; color: #ffffff;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.update_trade_book)
        header_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self.export_to_csv)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # Trade book table
        self.trade_book_table = QTableWidget()
        self.trade_book_table.setColumnCount(9)
        self.trade_book_table.setHorizontalHeaderLabels([
            "Strategy Name", "Entry Date", "Entry Time", "Entry Price",
            "Entry Condition", "Exit Time", "Exit Price", "Exit Reason", "Symbol"
        ])
        self.trade_book_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.trade_book_table.setAlternatingRowColors(True)
        self.trade_book_table.setSortingEnabled(True)
        
        layout.addWidget(self.trade_book_table)
    
    def _get_exit_condition_from_log(self, ticket: int, exit_time: datetime) -> Optional[str]:
        """
        Parse log file to determine exit condition from log messages
        
        Args:
            ticket: Position ticket
            exit_time: Exit time to search around
            
        Returns:
            Exit condition string (SL/TP) or None if not found
        """
        # Check cache first
        cache_key = f"{ticket}_{exit_time.timestamp()}"
        if cache_key in self.exit_condition_cache:
            return self.exit_condition_cache[cache_key]
        
        log_file = Path("logs/trading_platform.log")
        if not log_file.exists():
            return None
        
        # Search window: ±5 minutes from exit_time
        search_start = exit_time - timedelta(minutes=5)
        search_end = exit_time + timedelta(minutes=5)
        
        # Patterns to search for (in order of priority)
        patterns = [
            (r"Stop loss triggered for position " + str(ticket), "SL"),
            (r"Take profit triggered for position " + str(ticket), "TP"),
            (r"Trailing SL triggered for position " + str(ticket), "SL"),
            (r"Closing position " + str(ticket) + r" due to SL", "SL"),
            (r"Closing position " + str(ticket) + r" due to TP", "TP"),
        ]
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # Parse timestamp from log line
                    # Format: 2025-12-11 22:34:03,892 - ...
                    match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+', line)
                    if not match:
                        continue
                    
                    log_timestamp_str = match.group(1)
                    try:
                        log_time = datetime.strptime(log_timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        continue
                    
                    # Check if log time is within search window
                    if search_start <= log_time <= search_end:
                        # Check for pattern matches
                        for pattern, condition in patterns:
                            if re.search(pattern, line):
                                # Cache the result
                                self.exit_condition_cache[cache_key] = condition
                                return condition
        except Exception as e:
            logger.error(f"Error parsing log for ticket {ticket}: {e}", exc_info=True)
        
        # Cache None result to avoid repeated parsing
        self.exit_condition_cache[cache_key] = None
        return None
    
    def update_trade_book(self):
        """Update trade book with trade history"""
        try:
            # Get all trades from TradeHistory
            if not hasattr(self.order_manager, 'trade_history'):
                logger.error("OrderManager does not have trade_history")
                trades = []
            else:
                trades = self.order_manager.trade_history.get_all_trades()
                # This refresh runs frequently; keep logs at DEBUG to avoid flooding the log file.
                logger.debug(f"Retrieved {len(trades)} trades from TradeHistory")
            
            # Sort by entry time (newest first)
            trades.sort(key=lambda x: x.get('entry_time', datetime.min) if isinstance(x.get('entry_time'), datetime) else datetime.min, reverse=True)
            
            # Update table
            self.trade_book_table.setRowCount(len(trades))
            
            for row, trade in enumerate(trades):
                ticket = trade.get('ticket', 0)
                
                # Strategy Name
                strategy_name = trade.get('strategy_name', '--')
                self.trade_book_table.setItem(row, 0, QTableWidgetItem(strategy_name))
                
                # Entry Date and Time
                entry_time = trade.get('entry_time')
                if entry_time:
                    if isinstance(entry_time, (int, float)):
                        entry_time = datetime.fromtimestamp(entry_time)
                    elif not isinstance(entry_time, datetime):
                        entry_time = None
                    
                    if entry_time:
                        entry_date_str = entry_time.strftime('%Y-%m-%d')
                        entry_time_str = entry_time.strftime('%H:%M:%S')
                    else:
                        entry_date_str = "--"
                        entry_time_str = "--"
                else:
                    entry_date_str = "--"
                    entry_time_str = "--"
                
                self.trade_book_table.setItem(row, 1, QTableWidgetItem(entry_date_str))
                self.trade_book_table.setItem(row, 2, QTableWidgetItem(entry_time_str))
                
                # Entry Price
                entry_price = trade.get('entry_price', 0.0)
                entry_price_str = f"{entry_price:.5f}" if entry_price > 0 else "--"
                self.trade_book_table.setItem(row, 3, QTableWidgetItem(entry_price_str))
                
                # Entry Condition
                entry_condition = trade.get('entry_condition', '--')
                self.trade_book_table.setItem(row, 4, QTableWidgetItem(entry_condition))
                
                # Exit Time
                exit_time = trade.get('exit_time')
                if exit_time:
                    if isinstance(exit_time, (int, float)):
                        exit_time = datetime.fromtimestamp(exit_time)
                    elif not isinstance(exit_time, datetime):
                        exit_time = None
                    
                    if exit_time:
                        exit_time_str = exit_time.strftime('%H:%M:%S')
                    else:
                        exit_time_str = "--"
                else:
                    exit_time_str = "--"
                
                self.trade_book_table.setItem(row, 5, QTableWidgetItem(exit_time_str))
                
                # Exit Price
                exit_price = trade.get('exit_price')
                exit_price_str = f"{exit_price:.5f}" if exit_price else "--"
                self.trade_book_table.setItem(row, 6, QTableWidgetItem(exit_price_str))
                
                # Exit Reason (from trade history exit_condition or exit_reason, with log fallback)
                exit_reason = "--"
                status = trade.get('status', 'Open')
                
                if status == 'Closed':
                    # Priority: exit_reason > exit_condition > log parsing
                    exit_reason = trade.get('exit_reason') or trade.get('exit_condition', '--')
                    
                    # If still not set and we have exit_time, try to get from log
                    if (exit_reason == '--' or not exit_reason) and exit_time:
                        log_exit_condition = self._get_exit_condition_from_log(ticket, exit_time)
                        if log_exit_condition:
                            exit_reason = log_exit_condition
                        else:
                            # Fallback to trade history exit_condition
                            exit_reason = trade.get('exit_condition', 'Manual')
                    elif not exit_reason or exit_reason == '--':
                        # Final fallback
                        exit_reason = trade.get('exit_condition', 'Manual')
                elif status == 'Open':
                    exit_reason = "Open"
                
                exit_reason_item = QTableWidgetItem(exit_reason)
                # Color code: SL = red, TP = green
                if exit_reason == "SL":
                    exit_reason_item.setForeground(Qt.GlobalColor.red)
                elif exit_reason == "TP":
                    exit_reason_item.setForeground(Qt.GlobalColor.green)
                
                self.trade_book_table.setItem(row, 7, exit_reason_item)
                
                # Symbol
                symbol = trade.get('symbol', '--')
                self.trade_book_table.setItem(row, 8, QTableWidgetItem(symbol))
            
            # This refresh runs frequently; keep logs at DEBUG to avoid flooding the log file.
            logger.debug(f"Updated trade book with {len(trades)} trades")
            
        except Exception as e:
            logger.error(f"Error updating trade book: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Error updating trade book: {str(e)}")
    
    def export_to_csv(self):
        """Export trade book to CSV file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Trade Book to CSV",
            f"trade_book_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    "Strategy Name", "Entry Date", "Entry Time", "Entry Price",
                    "Entry Condition", "Exit Time", "Exit Price", "Exit Reason", "Symbol"
                ])
                
                # Write data
                for row in range(self.trade_book_table.rowCount()):
                    row_data = []
                    for col in range(self.trade_book_table.columnCount()):
                        item = self.trade_book_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "Success", f"Trade book exported to:\n{file_path}")
        except Exception as e:
            logger.error(f"Error exporting trade book: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to export CSV:\n{str(e)}")

    def export_to_csv_path(self, file_path: Path) -> int:
        """
        Export trade book to a CSV file path (used for auto-save on exit).
        
        Args:
            file_path: Destination CSV path.
        
        Returns:
            Number of rows written.
        """
        trades = []
        try:
            trades = self.order_manager.trade_history.get_all_trades() if hasattr(self.order_manager, "trade_history") else []
        except Exception as e:
            logger.error(f"Error retrieving trades for export: {e}", exc_info=True)

        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "Strategy Name", "Entry Date", "Entry Time", "Entry Price",
                "Entry Condition", "Exit Time", "Exit Price", "Exit Reason", "Symbol"
            ])

            for trade in trades:
                entry_time = trade.get('entry_time')
                if isinstance(entry_time, (int, float)):
                    entry_time = datetime.fromtimestamp(entry_time)
                entry_date_str = entry_time.strftime('%Y-%m-%d') if isinstance(entry_time, datetime) else "--"
                entry_time_str = entry_time.strftime('%H:%M:%S') if isinstance(entry_time, datetime) else "--"

                exit_time = trade.get('exit_time')
                if isinstance(exit_time, (int, float)):
                    exit_time = datetime.fromtimestamp(exit_time)
                exit_time_str = exit_time.strftime('%H:%M:%S') if isinstance(exit_time, datetime) else "--"

                writer.writerow([
                    trade.get('strategy_name', '--'),
                    entry_date_str,
                    entry_time_str,
                    f"{trade.get('entry_price', 0.0):.5f}" if trade.get('entry_price', 0.0) else "--",
                    trade.get('entry_condition', '--'),
                    exit_time_str,
                    f"{trade.get('exit_price', 0.0):.5f}" if trade.get('exit_price', 0.0) else "--",
                    trade.get('exit_reason') or trade.get('exit_condition', '--') or "Manual",
                    trade.get('symbol', '--')
                ])
        return len(trades)

