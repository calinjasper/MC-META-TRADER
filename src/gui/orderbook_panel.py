"""
Orderbook Panel
Displays trade history (open and closed positions) with CSV export
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QHeaderView, QLabel,
                             QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from typing import List, Dict, Optional
from datetime import datetime
import csv
try:
    import MetaTrader5 as mt5
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1
except ImportError:
    # Fallback if MT5 not available
    DEAL_ENTRY_IN = 0
    DEAL_ENTRY_OUT = 1

from ..trading.order_manager import OrderManager
from ..mt5_connector import MT5Connector
import logging

logger = logging.getLogger(__name__)


class OrderbookPanel(QWidget):
    """Panel displaying trade history (orderbook)"""
    
    def __init__(self, order_manager: OrderManager, mt5_connector: MT5Connector, parent=None):
        super().__init__(parent)
        self.order_manager = order_manager
        self.mt5 = mt5_connector
        self.setup_ui()
        self.update_orderbook()
    
    def _get_exit_condition_from_mt5(self, ticket: int, fallback: str = "Manual") -> str:
        """
        Get exit condition from MT5 deal history
        
        Args:
            ticket: Position ticket
            fallback: Fallback value if not found
            
        Returns:
            Exit condition string
        """
        try:
            if not self.mt5 or not self.mt5.is_connected():
                return fallback
            
            deals = self.mt5.get_deal_history()
            for deal in deals:
                # Find exit deal for this position
                if (deal.get('position_id') == ticket or deal.get('order') == ticket) and deal.get('entry') == 1:
                    exit_condition = deal.get('exit_condition', fallback)
                    if exit_condition and exit_condition != fallback:
                        return exit_condition
            
            return fallback
        except Exception as e:
            logger.error(f"Error getting exit condition from MT5 for ticket {ticket}: {e}", exc_info=True)
            return fallback
    
    def _get_exit_details_from_mt5(self, ticket: int) -> tuple:
        """
        Get exit price, time, and profit from MT5 deal history
        
        Args:
            ticket: Position ticket
            
        Returns:
            Tuple of (exit_price, exit_time, profit) or (0.0, None, 0.0) if not found
        """
        try:
            if not self.mt5 or not self.mt5.is_connected():
                return (0.0, None, 0.0)
            
            deals = self.mt5.get_deal_history()
            for deal in deals:
                # Find exit deal for this position
                if (deal.get('position_id') == ticket or deal.get('order') == ticket) and deal.get('entry') == 1:
                    exit_price = deal.get('price', 0.0)
                    profit = deal.get('profit', 0.0)
                    exit_time = deal.get('time')
                    if isinstance(exit_time, datetime):
                        pass  # Already datetime
                    elif isinstance(exit_time, (int, float)):
                        exit_time = datetime.fromtimestamp(exit_time)
                    else:
                        exit_time = None
                    return (exit_price, exit_time, profit)
            
            return (0.0, None, 0.0)
        except Exception as e:
            logger.error(f"Error getting exit details from MT5 for ticket {ticket}: {e}", exc_info=True)
            return (0.0, None, 0.0)
    
    def _get_sl_tp_for_position(self, entry_deal: Dict) -> tuple:
        """
        Get SL/TP for a position by checking multiple sources
        
        Returns:
            Tuple of (sl, tp) prices
        """
        order_ticket = entry_deal.get('order', 0)
        if not order_ticket:
            return (0.0, 0.0)
        
        sl, tp = (0.0, 0.0)
        
        # 1. Check position tracker (closed positions history)
        if hasattr(self.order_manager, 'position_tracker'):
            closed_pos = self.order_manager.position_tracker.get_closed_position(order_ticket)
            if closed_pos:
                sl = closed_pos.get('sl', 0.0)
                tp = closed_pos.get('tp', 0.0)
                if sl > 0 or tp > 0:
                    return (sl, tp)
        
        # 2. Check order manager history
        order_history = self.order_manager.get_order_history()
        for order in order_history:
            if order.get('order') == order_ticket:
                sl = order.get('sl', 0.0)
                tp = order.get('tp', 0.0)
                if sl > 0 or tp > 0:
                    return (sl, tp)
        
        # 3. Check MT5 order history directly
        if self.mt5 and self.mt5.is_connected():
            mt5_order = self.mt5.get_order_history_by_ticket(order_ticket)
            if mt5_order:
                sl = mt5_order.get('sl', 0.0)
                tp = mt5_order.get('tp', 0.0)
                if sl > 0 or tp > 0:
                    return (sl, tp)
        
        return (sl, tp)
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        
        # Title and buttons
        header_layout = QHBoxLayout()
        
        title = QLabel("Orderbook")
        title.setStyleSheet("font-weight: bold; font-size: 16px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.update_orderbook)
        header_layout.addWidget(refresh_btn)
        
        export_btn = QPushButton("Export to CSV")
        export_btn.clicked.connect(self.export_to_csv)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # Orderbook table
        self.orderbook_table = QTableWidget()
        self.orderbook_table.setColumnCount(11)
        self.orderbook_table.setHorizontalHeaderLabels([
            "Strategy Name", "Entry Time", "Entry Price", "Entry Condition",
            "SL", "TP", "Exit Time", "Exit Price", "Exit Condition",
            "Symbol", "Status"
        ])
        self.orderbook_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.orderbook_table.setAlternatingRowColors(True)
        self.orderbook_table.setSortingEnabled(True)
        
        layout.addWidget(self.orderbook_table)
    
    def update_orderbook(self):
        """Update orderbook with trade history"""
        try:
            # Get all trades from TradeHistory (most reliable source)
            if not hasattr(self.order_manager, 'trade_history'):
                logger.error("OrderManager does not have trade_history")
                orderbook_entries = []
            else:
                all_trades = self.order_manager.trade_history.get_all_trades()
                logger.info(f"Retrieved {len(all_trades)} trades from TradeHistory")
                
                # Get current open positions from MT5 to sync status
                open_positions = {}
                open_tickets = set()
                try:
                    positions = self.order_manager.get_positions()
                    for pos in positions:
                        ticket = pos.get('ticket', 0)
                        if ticket:
                            open_positions[ticket] = pos
                            open_tickets.add(ticket)
                except Exception as e:
                    logger.error(f"Error getting open positions: {e}", exc_info=True)
                
                # Sync trade history with MT5 positions
                # If trade shows "Open" but position doesn't exist in MT5, it was closed
                for trade in all_trades:
                    ticket = trade.get('ticket', 0)
                    if not ticket:
                        continue
                    
                    # If trade is marked "Open" but position doesn't exist in MT5, it was closed
                    if trade.get('status') == 'Open' and ticket not in open_tickets:
                        logger.info(f"Trade {ticket} marked as Open but not in MT5 positions - syncing as closed")
                        # Get exit condition from MT5
                        exit_condition = self._get_exit_condition_from_mt5(ticket, 'Manual')
                        # Get exit details from MT5 deal history
                        exit_price, exit_time, profit = self._get_exit_details_from_mt5(ticket)
                        
                        # Update trade in history
                        try:
                            self.order_manager.trade_history.close_trade(
                                ticket=ticket,
                                exit_price=exit_price,
                                exit_time=exit_time or datetime.now(),
                                exit_condition=exit_condition,
                                profit=profit
                            )
                            logger.info(f"Synced closed trade {ticket} in history: {exit_condition}")
                        except Exception as e:
                            logger.error(f"Error syncing trade {ticket}: {e}", exc_info=True)
                
                # Add any MT5 positions not in trade history (positions opened outside system)
                for ticket, pos in open_positions.items():
                    if not self.order_manager.trade_history.get_trade(ticket):
                        # Position exists in MT5 but not in trade history - add it
                        strategy_name = self._extract_strategy_name(pos.get('comment', ''))
                        entry_condition = self._get_entry_condition(pos.get('comment', ''))
                        self.order_manager.trade_history.add_trade(
                            ticket=ticket,
                            strategy_name=strategy_name,
                            symbol=pos.get('symbol', ''),
                            entry_price=pos.get('price_open', 0.0),
                            entry_time=pos.get('time', datetime.now()),
                            entry_condition=entry_condition,
                            sl=pos.get('sl', 0.0),
                            tp=pos.get('tp', 0.0),
                            volume=pos.get('volume', 0.01),
                            direction='BUY' if pos.get('type', 0) == 0 else 'SELL'
                        )
                        logger.info(f"Added missing trade {ticket} to history from MT5")
                
                # Re-get trades after sync
                all_trades = self.order_manager.trade_history.get_all_trades()
                
                # Convert trades to orderbook entries
                orderbook_entries = []
                for trade in all_trades:
                    try:
                        ticket = trade.get('ticket', 0)
                        
                        # Determine actual status from MT5
                        actual_status = 'Open' if ticket in open_tickets else 'Closed'
                        
                        # Update profit for open trades from current positions
                        if actual_status == 'Open' and ticket in open_positions:
                            current_pos = open_positions[ticket]
                            trade['profit'] = current_pos.get('profit', 0.0)
                        
                        # Format entry time
                        entry_time = trade.get('entry_time')
                        if isinstance(entry_time, (int, float)):
                            entry_time = datetime.fromtimestamp(entry_time)
                        elif not isinstance(entry_time, datetime):
                            entry_time = datetime.now()
                        
                        # Format exit time
                        exit_time = trade.get('exit_time')
                        if exit_time:
                            if isinstance(exit_time, (int, float)):
                                exit_time = datetime.fromtimestamp(exit_time)
                            elif not isinstance(exit_time, datetime):
                                exit_time = None
                        
                        # Determine exit condition
                        if actual_status == 'Open':
                            exit_condition = 'Open'
                        elif trade.get('exit_condition'):
                            exit_condition = trade.get('exit_condition')
                        else:
                            # Try to get from MT5 if missing
                            exit_condition = self._get_exit_condition_from_mt5(ticket, 'Manual')
                        
                        orderbook_entries.append({
                            'strategy_name': trade.get('strategy_name', '--'),
                            'entry_time': entry_time,
                            'entry_price': trade.get('entry_price', 0.0),
                            'entry_condition': trade.get('entry_condition', '--'),
                            'sl': trade.get('sl', 0.0),
                            'tp': trade.get('tp', 0.0),
                            'exit_time': exit_time,
                            'exit_price': trade.get('exit_price'),
                            'exit_condition': exit_condition,
                            'symbol': trade.get('symbol', '--'),
                            'status': actual_status,  # Use actual status from MT5
                            'profit': trade.get('profit', 0.0),
                            'ticket': ticket
                        })
                    except Exception as e:
                        logger.error(f"Error processing trade {trade.get('ticket', 'unknown')}: {e}", exc_info=True)
                
                # Sort by entry time (newest first)
                orderbook_entries.sort(key=lambda x: x['entry_time'] if isinstance(x['entry_time'], datetime) else datetime.min, reverse=True)
                
                logger.info(f"Total orderbook entries: {len(orderbook_entries)} (Open: {len([e for e in orderbook_entries if e['status'] == 'Open'])}, Closed: {len([e for e in orderbook_entries if e['status'] == 'Closed'])})")
            
        except Exception as e:
            logger.error(f"Error in update_orderbook: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Error updating orderbook: {str(e)}")
            orderbook_entries = []
        
        # Update table
        self.orderbook_table.setRowCount(len(orderbook_entries))
        
        for row, entry in enumerate(orderbook_entries):
            # Strategy Name
            self.orderbook_table.setItem(row, 0, QTableWidgetItem(entry['strategy_name']))
            
            # Entry Time
            entry_time_str = entry['entry_time'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(entry['entry_time'], datetime) else str(entry['entry_time'])
            self.orderbook_table.setItem(row, 1, QTableWidgetItem(entry_time_str))
            
            # Entry Price
            self.orderbook_table.setItem(row, 2, QTableWidgetItem(f"{entry['entry_price']:.5f}"))
            
            # Entry Condition
            self.orderbook_table.setItem(row, 3, QTableWidgetItem(entry['entry_condition']))
            
            # SL
            sl_text = f"{entry['sl']:.5f}" if entry['sl'] > 0 else "--"
            self.orderbook_table.setItem(row, 4, QTableWidgetItem(sl_text))
            
            # TP
            tp_text = f"{entry['tp']:.5f}" if entry['tp'] > 0 else "--"
            self.orderbook_table.setItem(row, 5, QTableWidgetItem(tp_text))
            
            # Exit Time
            exit_time_str = "--"
            if entry['exit_time']:
                if isinstance(entry['exit_time'], datetime):
                    exit_time_str = entry['exit_time'].strftime("%Y-%m-%d %H:%M:%S")
                else:
                    exit_time_str = str(entry['exit_time'])
            self.orderbook_table.setItem(row, 6, QTableWidgetItem(exit_time_str))
            
            # Exit Price
            exit_price_str = f"{entry['exit_price']:.5f}" if entry['exit_price'] else "--"
            self.orderbook_table.setItem(row, 7, QTableWidgetItem(exit_price_str))
            
            # Exit Condition
            exit_condition = entry.get('exit_condition', 'Manual')
            exit_condition_item = QTableWidgetItem(exit_condition)
            if exit_condition == 'TP':
                exit_condition_item.setForeground(Qt.GlobalColor.green)
            elif exit_condition == 'SL':
                exit_condition_item.setForeground(Qt.GlobalColor.red)
            self.orderbook_table.setItem(row, 8, exit_condition_item)
            
            # Symbol
            self.orderbook_table.setItem(row, 9, QTableWidgetItem(entry['symbol']))
            
            # Status
            status_item = QTableWidgetItem(entry['status'])
            if entry['status'] == 'Open':
                status_item.setForeground(Qt.GlobalColor.blue)
            else:
                # Color based on profit
                profit = entry.get('profit', 0.0)
                if profit > 0:
                    status_item.setForeground(Qt.GlobalColor.green)
                elif profit < 0:
                    status_item.setForeground(Qt.GlobalColor.red)
            self.orderbook_table.setItem(row, 10, status_item)
    
    def _extract_strategy_name(self, comment: str) -> str:
        """Extract strategy name from order comment"""
        if not comment:
            return "--"
        
        if 'Strategy:' in comment:
            return comment.split('Strategy:')[1].strip()
        
        return comment[:50]  # Truncate if too long
    
    def _get_entry_condition(self, comment: str) -> str:
        """Extract entry condition from comment or return default"""
        # Try to extract condition from comment
        # This is a placeholder - in a real implementation, you might store
        # entry conditions in a separate tracking system
        if 'Condition:' in comment:
            return comment.split('Condition:')[1].strip()
        
        return "--"
    
    def _get_sl_tp_from_order(self, order_ticket: int) -> tuple:
        """Get SL/TP from order history"""
        order_history = self.order_manager.get_order_history()
        for order in order_history:
            if order.get('order') == order_ticket:
                return (order.get('sl', 0.0), order.get('tp', 0.0))
        return (0.0, 0.0)
    
    def export_to_csv(self):
        """Export orderbook to CSV file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Orderbook to CSV",
            f"orderbook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                headers = [
                    "Strategy Name", "Entry Time", "Entry Price", "Entry Condition",
                    "SL", "TP", "Exit Time", "Exit Price", "Exit Condition",
                    "Symbol", "Status"
                ]
                writer.writerow(headers)
                
                # Write data
                for row in range(self.orderbook_table.rowCount()):
                    row_data = []
                    for col in range(self.orderbook_table.columnCount()):
                        item = self.orderbook_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            
            QMessageBox.information(self, "Success", f"Orderbook exported to:\n{file_path}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV:\n{str(e)}")
    
    def _determine_exit_reason(self, direction: str, entry_price: float, exit_price: float, sl: float, tp: float) -> str:
        """Determine exit reason based on prices"""
        if direction == 'BUY':
            if sl > 0 and exit_price <= sl:
                return "SL"
            elif tp > 0 and exit_price >= tp:
                return "TP"
        else:  # SELL
            if sl > 0 and exit_price >= sl:
                return "SL"
            elif tp > 0 and exit_price <= tp:
                return "TP"
        return "Manual"

