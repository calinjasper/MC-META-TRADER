"""
Strategy Panel
View and manage active strategies
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QHeaderView, QLabel, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List, Optional

from ..strategy.strategy_manager import StrategyManager
from ..strategy.base_strategy import BaseStrategy
from ..trading.order_manager import OrderManager
from .system_logs_panel import SystemLogsPanel
from .system_log_service import system_log_service


class StrategyPanel(QWidget):
    """Strategy management panel"""
    
    strategy_enabled = pyqtSignal(str, bool)  # strategy_name, enabled
    strategy_edit_requested = pyqtSignal(str)  # strategy_name
    
    def __init__(self, strategy_manager: StrategyManager, order_manager: OrderManager, 
                 data_feed=None, mt5=None, manual_close_handler=None, execute_signal_handler=None):
        super().__init__()
        self.strategy_manager = strategy_manager
        self.order_manager = order_manager
        self.data_feed = data_feed
        self.mt5 = mt5
        self.manual_close_handler = manual_close_handler  # Callback for handling manual closes
        self.execute_signal_handler = execute_signal_handler  # Callback for executing strategy signals
        self.setup_ui()
        self.update_strategies()
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Active Strategies")
        title.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(title)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.update_strategies)
        button_layout.addWidget(refresh_btn)
        
        enable_all_btn = QPushButton("Enable All")
        enable_all_btn.clicked.connect(self.enable_all)
        button_layout.addWidget(enable_all_btn)
        
        disable_all_btn = QPushButton("Disable All")
        disable_all_btn.clicked.connect(self.disable_all)
        button_layout.addWidget(disable_all_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Strategies table
        self.strategies_table = QTableWidget()
        self.strategies_table.setColumnCount(8)
        self.strategies_table.setHorizontalHeaderLabels([
            "Name", "Symbol", "Status", "Entry Condition", "Last Signal", "Current RSI", "Signals", "Actions"
        ])
        self.strategies_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.strategies_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.strategies_table)

        # System Logs section (requested under Execution page, bottom)
        self.system_logs_panel = SystemLogsPanel(self)
        layout.addWidget(self.system_logs_panel)
    
    def update_strategies(self):
        """Update strategies table"""
        strategies = self.strategy_manager.get_all_strategies()
        
        self.strategies_table.setRowCount(len(strategies))
        
        for row, strategy in enumerate(strategies):
            # Name
            self.strategies_table.setItem(row, 0, QTableWidgetItem(strategy.name))
            
            # Symbol
            self.strategies_table.setItem(row, 1, QTableWidgetItem(strategy.symbol))
            
            # Status
            status = "Enabled" if strategy.enabled else "Disabled"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(Qt.GlobalColor.green if strategy.enabled else Qt.GlobalColor.red)
            self.strategies_table.setItem(row, 2, status_item)
            
            # Entry Condition
            entry_condition = "--"
            if hasattr(strategy, 'entry_conditions_text') and strategy.entry_conditions_text:
                # Show first entry condition, or combine if multiple
                if len(strategy.entry_conditions_text) == 1:
                    entry_condition = strategy.entry_conditions_text[0]
                else:
                    # Show first condition with count if multiple
                    entry_condition = f"{strategy.entry_conditions_text[0]} (+{len(strategy.entry_conditions_text)-1})"
            self.strategies_table.setItem(row, 3, QTableWidgetItem(entry_condition))
            
            # Last signal
            last_signal = strategy.last_signal if strategy.last_signal else "--"
            self.strategies_table.setItem(row, 4, QTableWidgetItem(last_signal))
            
            # Current indicator value (show RSI if available, or first indicator)
            current_indicator_value = "--"
            if self.data_feed and self.mt5 and self.mt5.is_connected():
                try:
                    import MetaTrader5 as mt5
                    
                    # Get strategy's timeframe
                    timeframe = getattr(strategy, 'timeframe', mt5.TIMEFRAME_M1)
                    
                    if strategy.indicators:
                        # For RSI, use MT5's built-in indicator directly
                        for ind_name, indicator in strategy.indicators.items():
                            try:
                                if ind_name.upper() == "RSI" or "RSI" in ind_name.upper():
                                    # Get RSI period from indicator
                                    rsi_period = getattr(indicator, 'period', 14)
                                    
                                    # Fetch RSI directly from MT5
                                    mt5_rsi = self.mt5.get_rsi(strategy.symbol, timeframe, rsi_period, 300)
                                    if mt5_rsi is not None:
                                        current_indicator_value = f"RSI: {mt5_rsi:.2f} (MT5)"
                                        break
                                    else:
                                        # Fallback to our calculation if MT5 fails
                                        rates = self.data_feed.get_rates(strategy.symbol, timeframe, 300)
                                        if not rates and self.mt5:
                                            rates = self.mt5.get_rates(strategy.symbol, timeframe, 300)
                                        if rates:
                                            indicator.update(rates)
                                            value = indicator.get_value()
                                            if value is not None:
                                                current_indicator_value = f"RSI: {value:.2f}"
                                                break
                                elif current_indicator_value == "--":
                                    # For other indicators, use our calculation
                                    rates = self.data_feed.get_rates(strategy.symbol, timeframe, 100)
                                    if not rates and self.mt5:
                                        rates = self.mt5.get_rates(strategy.symbol, timeframe, 100)
                                    if rates:
                                        indicator.update(rates)
                                        value = indicator.get_value()
                                        if value is not None:
                                            current_indicator_value = f"{ind_name}: {value:.2f}"
                            except Exception as e:
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.debug(f"Error getting indicator {ind_name} for strategy panel: {e}")
                                pass
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.debug(f"Error in strategy panel update: {e}")
                    pass
            
            self.strategies_table.setItem(row, 5, QTableWidgetItem(current_indicator_value))
            
            # Signal count
            signal_count = len(strategy.signal_history)
            self.strategies_table.setItem(row, 6, QTableWidgetItem(str(signal_count)))
            
            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(2)
            
            detail_btn = QPushButton("Detail")
            detail_btn.setMaximumWidth(60)
            detail_btn.clicked.connect(lambda checked, s=strategy.name: self.show_strategy_detail(s))
            action_layout.addWidget(detail_btn)
            
            # Execute button - only show for enabled strategies
            if strategy.enabled:
                execute_btn = QPushButton("Execute")
                execute_btn.setMaximumWidth(70)
                execute_btn.clicked.connect(lambda checked, s=strategy.name: self.manual_execute_strategy(s))
                action_layout.addWidget(execute_btn)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setMaximumWidth(60)
            edit_btn.clicked.connect(lambda checked, s=strategy.name: self.edit_strategy(s))
            action_layout.addWidget(edit_btn)
            
            if strategy.enabled:
                disable_btn = QPushButton("Disable")
                disable_btn.setMaximumWidth(70)
                disable_btn.clicked.connect(lambda checked, s=strategy.name: self.disable_strategy(s))
                action_layout.addWidget(disable_btn)
            else:
                enable_btn = QPushButton("Enable")
                enable_btn.setMaximumWidth(70)
                enable_btn.clicked.connect(lambda checked, s=strategy.name: self.enable_strategy(s))
                action_layout.addWidget(enable_btn)
            
            remove_btn = QPushButton("Remove")
            remove_btn.setMaximumWidth(70)
            remove_btn.clicked.connect(lambda checked, s=strategy.name: self.remove_strategy(s))
            action_layout.addWidget(remove_btn)
            
            self.strategies_table.setCellWidget(row, 7, action_widget)
    
    def enable_strategy(self, name: str):
        """Enable a strategy"""
        if self.strategy_manager.enable_strategy(name):
            strategy = self.strategy_manager.get_strategy(name)
            system_log_service.log(
                "MESSAGE",
                f"Strategy {name} enabled",
                strategy=name,
            )
            self.strategy_enabled.emit(name, True)
            self.update_strategies()
    
    def disable_strategy(self, name: str):
        """Disable a strategy"""
        if self.strategy_manager.disable_strategy(name):
            system_log_service.log(
                "MESSAGE",
                f"Strategy {name} disabled",
                strategy=name,
            )
            self.strategy_enabled.emit(name, False)
            self.update_strategies()
    
    def remove_strategy(self, name: str):
        """Remove a strategy"""
        if self.strategy_manager.remove_strategy(name):
            system_log_service.log(
                "MESSAGE",
                f"Strategy {name} deleted",
                strategy=name,
            )
            # Delete strategy file from disk
            from ..strategy.strategy_persistence import StrategyPersistence
            persistence = StrategyPersistence()
            persistence.delete_strategy(name)
            self.update_strategies()
    
    def enable_all(self):
        """Enable all strategies"""
        for strategy in self.strategy_manager.get_all_strategies():
            if not strategy.enabled:
                self.enable_strategy(strategy.name)
    
    def disable_all(self):
        """Disable all strategies"""
        for strategy in self.strategy_manager.get_all_strategies():
            if strategy.enabled:
                self.disable_strategy(strategy.name)
    
    
    def show_strategy_detail(self, name: str):
        """Show strategy detail dialog"""
        strategy = self.strategy_manager.get_strategy(name)
        if not strategy:
            return
        
        from .strategy_detail_dialog import StrategyDetailDialog
        dialog = StrategyDetailDialog(strategy, self)
        dialog.exec()
    
    def edit_strategy(self, name: str):
        """Edit a strategy - open edit dialog"""
        strategy = self.strategy_manager.get_strategy(name)
        if not strategy:
            return
        
        from .strategy_edit_dialog import StrategyEditDialog
        dialog = StrategyEditDialog(strategy, self.strategy_manager, self)
        if dialog.exec():
            system_log_service.log(
                "MESSAGE",
                f"Strategy {name} edited",
                strategy=name,
            )
            # Strategy was saved, refresh the table
            self.update_strategies()
    
    def manual_execute_strategy(self, strategy_name: str):
        """Manually execute a strategy if condition is currently met"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.execute_signal_handler:
            QMessageBox.warning(self, "Error", "Execute signal handler not available")
            return
        
        if not self.mt5 or not self.mt5.is_connected():
            QMessageBox.warning(self, "Error", "MT5 is not connected")
            return
        
        if not self.data_feed:
            QMessageBox.warning(self, "Error", "Data feed not available")
            return
        
        # Get the strategy
        strategy = self.strategy_manager.get_strategy(strategy_name)
        if not strategy:
            QMessageBox.warning(self, "Error", f"Strategy '{strategy_name}' not found")
            return
        
        if not strategy.enabled:
            QMessageBox.warning(self, "Error", f"Strategy '{strategy_name}' is disabled")
            return
        
        try:
            symbol = strategy.symbol
            
            # Find the correct symbol case from data feed (case-insensitive)
            actual_symbol = symbol
            for feed_symbol in self.data_feed.symbols:
                if feed_symbol.upper() == symbol.upper():
                    actual_symbol = feed_symbol
                    break
            
            # Ensure symbol is in data feed
            if actual_symbol not in self.data_feed.symbols:
                if self.mt5.is_connected():
                    self.data_feed.add_symbol(actual_symbol)
                    # Try to find the correct case after adding
                    for feed_symbol in self.data_feed.symbols:
                        if feed_symbol.upper() == symbol.upper():
                            actual_symbol = feed_symbol
                            break
            
            # Get current tick
            tick = self.data_feed.get_latest_tick(actual_symbol)
            if not tick:
                QMessageBox.warning(self, "Error", f"No tick data available for {actual_symbol}")
                return
            
            # Get rates for the strategy's timeframe
            import MetaTrader5 as mt5
            timeframe = getattr(strategy, 'timeframe', mt5.TIMEFRAME_M1)
            
            # Get rates from data feed first, then fallback to MT5
            rates = self.data_feed.get_rates(actual_symbol, timeframe, 300)
            if not rates and self.mt5.is_connected():
                rates = self.mt5.get_rates(actual_symbol, timeframe, 300)
            
            if not rates:
                QMessageBox.warning(self, "Error", f"Could not retrieve rates for {actual_symbol} (timeframe: {timeframe})")
                return
            
            # Prepare market data (similar to main_window.py update_strategies)
            market_data = {
                'tick': tick,
                'rates': rates,
                'indicators': {}
            }
            
            # Calculate indicators if strategy has them (similar to main_window.py)
            if strategy.indicators:
                for ind_name, indicator in strategy.indicators.items():
                    try:
                        # For RSI, fetch directly from MT5's built-in indicator
                        if ind_name.upper() == "RSI" or "RSI" in ind_name.upper():
                            rsi_period = getattr(indicator, 'period', 14)
                            mt5_rsi = self.mt5.get_rsi(actual_symbol, timeframe, rsi_period, 300)
                            if mt5_rsi is not None:
                                market_data['indicators'][ind_name] = mt5_rsi
                            else:
                                # Fallback to our calculation
                                indicator.update(rates)
                                latest_value = indicator.get_value()
                                if latest_value is not None:
                                    market_data['indicators'][ind_name] = latest_value
                        else:
                            # For other indicators, use our calculation
                            indicator.update(rates)
                            latest_value = indicator.get_value()
                            if latest_value is not None:
                                market_data['indicators'][ind_name] = latest_value
                    except Exception as e:
                        logger.error(f"Error calculating indicator {ind_name} for manual execute: {e}", exc_info=True)
            
            # Generate signal to check if condition is currently met
            signal = strategy.generate_signal(market_data)
            
            if signal:
                # Condition is met, execute the trade
                logger.info(f"Manual execute: Strategy {strategy_name} condition met, signal={signal}. Executing trade...")
                system_log_service.log(
                    "TRADING",
                    f"Strategy {strategy_name} manual execute triggered ({signal})",
                    strategy=strategy_name,
                )
                success, error_msg = self.execute_signal_handler(strategy, signal)
                if success:
                    QMessageBox.information(self, "Trade Executed", 
                                          f"Strategy '{strategy_name}' executed {signal} signal.\n"
                                          f"Check the orderbook for trade details.")
                    # Refresh strategies table to show updated positions
                    self.update_strategies()
                    if hasattr(self, 'update_positions'):
                        self.update_positions()
                else:
                    # Show detailed error message if available
                    error_details = error_msg if error_msg else "Unknown error occurred"
                    QMessageBox.warning(self, "Trade Execution Failed", 
                                      f"Failed to execute {signal} signal for strategy '{strategy_name}'.\n\n"
                                      f"Reason: {error_details}")
            else:
                # Condition not met - offer to place order directly
                reply = QMessageBox.question(
                    self, 
                    "Condition Not Met", 
                    f"Strategy '{strategy_name}' condition is not currently met.\n"
                    f"No signal generated.\n\n"
                    f"Would you like to place a direct market order anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Ask user which direction they want using a custom dialog
                    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel
                    
                    dialog = QDialog(self)
                    dialog.setWindowTitle("Select Order Direction")
                    dialog.setModal(True)
                    layout = QVBoxLayout(dialog)
                    
                    label = QLabel(f"Select order direction for {symbol}:")
                    layout.addWidget(label)
                    
                    def place_buy():
                        dialog.accept()
                        self.place_direct_order(strategy, "BUY")
                    
                    def place_sell():
                        dialog.accept()
                        self.place_direct_order(strategy, "SELL")
                    
                    buy_btn = QPushButton("BUY")
                    buy_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
                    buy_btn.clicked.connect(place_buy)
                    layout.addWidget(buy_btn)
                    
                    sell_btn = QPushButton("SELL")
                    sell_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 10px;")
                    sell_btn.clicked.connect(place_sell)
                    layout.addWidget(sell_btn)
                    
                    cancel_btn = QPushButton("Cancel")
                    cancel_btn.clicked.connect(dialog.reject)
                    layout.addWidget(cancel_btn)
                    
                    dialog.exec()
        
        except Exception as e:
            logger.error(f"Error in manual_execute_strategy for {strategy_name}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error executing strategy: {str(e)}")
    
    def place_direct_order(self, strategy, order_type: str):
        """Place a direct market order without checking conditions"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.execute_signal_handler:
            QMessageBox.warning(self, "Error", "Execute signal handler not available")
            return
        
        if not self.mt5 or not self.mt5.is_connected():
            QMessageBox.warning(self, "Error", "MT5 is not connected")
            return
        
        try:
            symbol = strategy.symbol
            
            # Find the correct symbol case from data feed (case-insensitive)
            actual_symbol = symbol
            if self.data_feed:
                for feed_symbol in self.data_feed.symbols:
                    if feed_symbol.upper() == symbol.upper():
                        actual_symbol = feed_symbol
                        break
            
            # Ensure symbol is in data feed
            if self.data_feed and actual_symbol not in self.data_feed.symbols:
                if self.mt5.is_connected():
                    self.data_feed.add_symbol(actual_symbol)
                    # Try to find the correct case after adding
                    for feed_symbol in self.data_feed.symbols:
                        if feed_symbol.upper() == symbol.upper():
                            actual_symbol = feed_symbol
                            break
            
            # Get current tick
            tick = None
            if self.data_feed:
                tick = self.data_feed.get_latest_tick(actual_symbol)
            
            if not tick and self.mt5.is_connected():
                tick = self.mt5.get_tick(actual_symbol)
            
            if not tick or 'ask' not in tick or 'bid' not in tick:
                QMessageBox.warning(self, "Error", f"Could not get current price for {actual_symbol}")
                return
            
            logger.info(f"Placing direct {order_type} order for {actual_symbol} (bypassing conditions)")
            
            # Execute the order using the same handler as strategy signals
            # This will handle SL/TP calculation and order placement
            success, error_msg = self.execute_signal_handler(strategy, order_type)
            
            if success:
                QMessageBox.information(
                    self, 
                    "Order Placed", 
                    f"Direct {order_type} order placed successfully for {strategy.name}.\n"
                    f"Symbol: {actual_symbol}\n"
                    f"Check the orderbook for trade details."
                )
                # Refresh strategies table to show updated positions
                self.update_strategies()
                self.update_positions()
            else:
                error_details = error_msg if error_msg else "Unknown error occurred"
                QMessageBox.warning(
                    self, 
                    "Order Failed", 
                    f"Failed to place {order_type} order for strategy '{strategy.name}'.\n\n"
                    f"Reason: {error_details}"
                )
        
        except Exception as e:
            logger.error(f"Error in place_direct_order for {strategy.name}: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error placing direct order: {str(e)}")

