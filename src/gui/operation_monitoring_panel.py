"""
Operation & Monitoring Panel
Displays Open P&L, Open Positions, and Trade Book for all active strategies
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView,
                             QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from typing import Optional, Dict, List
from datetime import datetime
import logging

from ..trading.order_manager import OrderManager
from ..strategy.strategy_manager import StrategyManager
from ..mt5_connector import MT5Connector
from .trade_book_panel import TradeBookPanel

logger = logging.getLogger(__name__)


class OperationMonitoringPanel(QWidget):
    """Panel for monitoring operations: Open P&L, Positions, and Trade Book"""
    
    def __init__(self, order_manager: OrderManager, strategy_manager: StrategyManager,
                 mt5: MT5Connector, parent=None):
        super().__init__(parent)
        self.order_manager = order_manager
        self.strategy_manager = strategy_manager
        self.mt5 = mt5
        
        # P&L tracking variables
        self.max_pnl = 0.0  # Maximum P&L reached
        self.min_pnl = 0.0  # Minimum P&L reached
        self.max_pnl_time = None  # When max was reached
        self.min_pnl_time = None  # When min was reached
        
        self.setup_ui()
        self.setup_timers()
        self.update_positions()
        self.update_open_pnl()
    
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
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # Open P&L Section
        pnl_group = QWidget()
        pnl_layout = QVBoxLayout(pnl_group)
        pnl_layout.setContentsMargins(10, 10, 10, 10)
        
        pnl_title = QLabel("Open P&L (All Active Strategies)")
        pnl_title.setStyleSheet("font-weight: bold; font-size: 16px; color: #ffffff;")
        pnl_layout.addWidget(pnl_title)
        
        # P&L display layout
        pnl_display_layout = QHBoxLayout()
        
        self.pnl_label = QLabel("Open P&L: $0.00")
        self.pnl_label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px;")
        self.pnl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pnl_display_layout.addWidget(self.pnl_label)
        
        self.max_pnl_label = QLabel("MAX: $0.00")
        self.max_pnl_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px; color: #4CAF50;")
        self.max_pnl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pnl_display_layout.addWidget(self.max_pnl_label)
        
        self.min_pnl_label = QLabel("MIN: $0.00")
        self.min_pnl_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px; color: #F44336;")
        self.min_pnl_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pnl_display_layout.addWidget(self.min_pnl_label)
        
        pnl_layout.addLayout(pnl_display_layout)
        
        layout.addWidget(pnl_group)
        
        # Open Positions Section
        positions_label = QLabel("Open Positions")
        positions_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        layout.addWidget(positions_label)
        
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(9)
        self.positions_table.setHorizontalHeaderLabels([
            "Ticket", "Symbol", "Type", "Volume", "Price", "SL", "TP", "Profit", "Actions"
        ])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.positions_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.positions_table)
        
        # Trade Book Section
        trade_book_label = QLabel("Trade Book")
        trade_book_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        layout.addWidget(trade_book_label)
        
        self.trade_book_panel = TradeBookPanel(self.order_manager, self)
        layout.addWidget(self.trade_book_panel)
    
    def setup_timers(self):
        """Setup update timers"""
        # Timer for position and P&L updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._on_timer_update)
        self.update_timer.start(1000)  # Update every second
        logger.debug("OperationMonitoringPanel: Timer started (1000ms interval)")
    
    def _on_timer_update(self):
        """Handle timer update - called every second"""
        try:
            if self.mt5.is_connected():
                self.update_positions()
                self.update_open_pnl()
            else:
                # MT5 disconnected - update UI to show empty state
                logger.debug("OperationMonitoringPanel: Timer update skipped - MT5 not connected")
        except Exception as e:
            logger.error(f"OperationMonitoringPanel: Error in timer update: {e}", exc_info=True)
    
    def _extract_strategy_name_from_comment(self, comment: str) -> Optional[str]:
        """
        Extract strategy name from position comment field.
        Handles various formats:
        - "Strategy: MyStrategy"
        - "Strategy: MyStrategy (Re-Entry BUY)"
        - "Strategy: MyStrategy (extra text)"
        
        Args:
            comment: Position comment string
            
        Returns:
            Strategy name if found, None otherwise
        """
        if not comment or 'Strategy:' not in comment:
            return None
        
        try:
            # Split on 'Strategy:' and take the part after it
            parts = comment.split('Strategy:', 1)
            if len(parts) > 1:
                # Get the strategy name part (before any parentheses or extra text)
                strategy_part = parts[1].strip()
                # Remove anything after opening parenthesis if present
                if '(' in strategy_part:
                    strategy_part = strategy_part.split('(')[0].strip()
                # Normalize: trim whitespace
                strategy_name = strategy_part.strip()
                return strategy_name if strategy_name else None
        except Exception as e:
            logger.debug(f"Error extracting strategy name from comment '{comment}': {e}")
        
        return None
    
    def calculate_open_pnl(self) -> float:
        """
        Calculate total P&L from all positions belonging to active strategies.
        
        Returns:
            Total P&L as float
        """
        total_pnl = 0.0
        
        if not self.mt5.is_connected():
            logger.debug("calculate_open_pnl: MT5 not connected, returning 0.0")
            return total_pnl
        
        # Get all active strategies
        active_strategies = self.strategy_manager.get_enabled_strategies()
        if not active_strategies:
            logger.debug("calculate_open_pnl: No active strategies, returning 0.0")
            return total_pnl
        
        # Create normalized set of strategy names for quick lookup (trimmed)
        strategy_names = {s.name.strip() for s in active_strategies}
        
        logger.debug(f"calculate_open_pnl: Active strategies: {sorted(strategy_names)}")
        
        # Get all MT5 positions
        all_positions = self.order_manager.get_positions()
        if not all_positions:
            logger.debug("calculate_open_pnl: No positions found, returning 0.0")
            return total_pnl
        
        logger.debug(f"calculate_open_pnl: Found {len(all_positions)} total positions")
        
        # Track statistics for logging
        positions_included = 0
        positions_excluded = 0
        positions_without_strategy = 0
        positions_strategy_mismatch = []
        
        # Filter positions by strategy (from comment field)
        for pos in all_positions:
            comment = pos.get('comment', '')
            ticket = pos.get('ticket', 'N/A')
            profit = pos.get('profit', 0.0)
            
            # Extract strategy name from comment
            strategy_name = self._extract_strategy_name_from_comment(comment)
            
            if strategy_name is None:
                positions_without_strategy += 1
                logger.debug(f"calculate_open_pnl: Position {ticket} has no strategy in comment: '{comment}'")
                continue
            
            # Normalize strategy name for comparison (trim)
            strategy_name_normalized = strategy_name.strip()
            strategy_name_lower = strategy_name_normalized.lower()
            
            # Check if strategy name matches any active strategy (case-insensitive)
            # First try exact match, then case-insensitive match
            matches = (strategy_name_normalized in strategy_names or 
                      any(name.lower() == strategy_name_lower for name in strategy_names))
            
            if matches:
                total_pnl += profit
                positions_included += 1
                logger.debug(f"calculate_open_pnl: Position {ticket} included: strategy='{strategy_name}', profit={profit:.2f}")
            else:
                positions_excluded += 1
                positions_strategy_mismatch.append((ticket, strategy_name))
                logger.debug(f"calculate_open_pnl: Position {ticket} excluded: strategy='{strategy_name}' not in active strategies")
        
        # Log summary
        logger.info(
            f"calculate_open_pnl: Total P&L=${total_pnl:,.2f}, "
            f"Included={positions_included}, Excluded={positions_excluded}, "
            f"NoStrategy={positions_without_strategy}"
        )
        
        if positions_strategy_mismatch:
            logger.debug(f"calculate_open_pnl: Positions with strategy mismatch: {positions_strategy_mismatch}")
        
        return total_pnl
    
    def update_open_pnl(self):
        """Update Open P&L display and track MAX/MIN"""
        pnl = self.calculate_open_pnl()
        
        # Track MAX/MIN
        max_updated = False
        min_updated = False
        
        if pnl > self.max_pnl:
            old_max = self.max_pnl
            self.max_pnl = pnl
            self.max_pnl_time = datetime.now()
            max_updated = True
            logger.info(f"update_open_pnl: MAX P&L updated: ${old_max:,.2f} -> ${pnl:,.2f} at {self.max_pnl_time.strftime('%H:%M:%S')}")
        
        if pnl < self.min_pnl:
            old_min = self.min_pnl
            self.min_pnl = pnl
            self.min_pnl_time = datetime.now()
            min_updated = True
            logger.info(f"update_open_pnl: MIN P&L updated: ${old_min:,.2f} -> ${pnl:,.2f} at {self.min_pnl_time.strftime('%H:%M:%S')}")
        
        if not max_updated and not min_updated:
            logger.debug(f"update_open_pnl: P&L=${pnl:,.2f} (MAX=${self.max_pnl:,.2f}, MIN=${self.min_pnl:,.2f})")
        
        # Format current P&L with commas
        if pnl >= 0:
            pnl_text = f"Open P&L: ${pnl:,.2f}"
            color = "#4CAF50"  # Green
        else:
            pnl_text = f"Open P&L: -${abs(pnl):,.2f}"
            color = "#F44336"  # Red
        
        self.pnl_label.setText(pnl_text)
        self.pnl_label.setStyleSheet(
            f"font-size: 24px; font-weight: bold; padding: 10px; color: {color};"
        )
        
        # Format MAX P&L
        if self.max_pnl >= 0:
            max_text = f"MAX: ${self.max_pnl:,.2f}"
        else:
            max_text = f"MAX: -${abs(self.max_pnl):,.2f}"
        if self.max_pnl_time:
            time_str = self.max_pnl_time.strftime("%H:%M:%S")
            max_text += f" ({time_str})"
        self.max_pnl_label.setText(max_text)
        
        # Format MIN P&L
        if self.min_pnl >= 0:
            min_text = f"MIN: ${self.min_pnl:,.2f}"
        else:
            min_text = f"MIN: -${abs(self.min_pnl):,.2f}"
        if self.min_pnl_time:
            time_str = self.min_pnl_time.strftime("%H:%M:%S")
            min_text += f" ({time_str})"
        self.min_pnl_label.setText(min_text)
    
    def update_positions(self):
        """Update positions table"""
        try:
            if not self.mt5.is_connected():
                self.positions_table.setRowCount(0)
                logger.debug("update_positions: MT5 not connected, clearing positions table")
                return
            
            positions = self.order_manager.get_positions()
            
            if positions is None:
                logger.warning("update_positions: get_positions() returned None")
                positions = []
            
            logger.debug(f"update_positions: Updating table with {len(positions)} positions")
            self.positions_table.setRowCount(len(positions))
            
            for row, pos in enumerate(positions):
                # Ticket
                self.positions_table.setItem(row, 0, QTableWidgetItem(str(pos['ticket'])))
                
                # Symbol
                self.positions_table.setItem(row, 1, QTableWidgetItem(pos['symbol']))
                
                # Type
                pos_type = "BUY" if pos['type'] == 0 else "SELL"
                self.positions_table.setItem(row, 2, QTableWidgetItem(pos_type))
                
                # Volume
                self.positions_table.setItem(row, 3, QTableWidgetItem(f"{pos['volume']:.2f}"))
                
                # Price
                self.positions_table.setItem(row, 4, QTableWidgetItem(f"{pos['price_open']:.5f}"))
                
                # Stop Loss
                sl = pos.get('sl', 0.0)
                sl_text = f"{sl:.5f}" if sl > 0 else "--"
                self.positions_table.setItem(row, 5, QTableWidgetItem(sl_text))
                
                # Take Profit
                tp = pos.get('tp', 0.0)
                tp_text = f"{tp:.5f}" if tp > 0 else "--"
                self.positions_table.setItem(row, 6, QTableWidgetItem(tp_text))
                
                # Profit
                profit_item = QTableWidgetItem(f"{pos['profit']:.2f}")
                if pos['profit'] >= 0:
                    profit_item.setForeground(QColor("#4CAF50"))
                else:
                    profit_item.setForeground(QColor("#F44336"))
                self.positions_table.setItem(row, 7, profit_item)
                
                # Actions
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(2, 2, 2, 2)
                
                close_btn = QPushButton("Close")
                close_btn.clicked.connect(lambda checked, t=pos['ticket']: self.close_position(t))
                action_layout.addWidget(close_btn)
                action_layout.addStretch()
                
                self.positions_table.setCellWidget(row, 8, action_widget)
        
        except Exception as e:
            logger.error(f"update_positions: Error updating positions table: {e}", exc_info=True)
            # Ensure table is in a valid state even on error
            try:
                self.positions_table.setRowCount(0)
            except:
                pass
    
    def close_position(self, ticket: int):
        """Close a position"""
        if not self.mt5.is_connected():
            QMessageBox.warning(self, "Error", "MT5 not connected")
            return
        
        reply = QMessageBox.question(
            self,
            "Close Position",
            f"Are you sure you want to close position {ticket}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            result = self.order_manager.close_position(ticket)
            if result and result.get('success'):
                QMessageBox.information(self, "Success", f"Position {ticket} closed successfully")
                self.update_positions()
                self.update_open_pnl()
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'Failed to close position'
                QMessageBox.critical(self, "Error", f"Failed to close position: {error_msg}")

