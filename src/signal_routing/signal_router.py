"""
Signal Router
Routes signals to order execution
"""

import logging
from typing import Dict, Optional, List, Any
from datetime import datetime

from ..trading.order_manager import OrderManager
from ..trading.risk_manager import RiskManager
from .signal_rules import SignalRules

logger = logging.getLogger(__name__)


class SignalRouter:
    """Route signals to order execution"""
    
    def __init__(self, order_manager: OrderManager, risk_manager: RiskManager):
        """
        Initialize signal router
        
        Args:
            order_manager: Order manager for executing orders
            risk_manager: Risk manager for position sizing
        """
        self.order_manager = order_manager
        self.risk_manager = risk_manager
        self.signal_rules = SignalRules()
        self.execution_history: List[Dict] = []
    
    def route_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route signal to appropriate execution handler
        
        Args:
            signal: Parsed signal dictionary
            
        Returns:
            Execution result dictionary
        """
        action = signal.get('action', '').upper()
        symbol = signal.get('symbol')
        
        logger.info(f"Routing signal: {symbol} {action}")
        
        # Get current positions for rule processing
        current_positions = self.order_manager.get_positions(symbol) if symbol else []
        
        # Apply signal rules
        processed_signal = self.signal_rules.process_signal(signal, current_positions)
        
        # Route based on action
        result = None
        if action in ['BUY', 'SELL']:
            result = self._execute_entry_signal(processed_signal, current_positions)
        elif action in ['EXIT', 'CLOSE']:
            result = self._execute_exit_signal(processed_signal, current_positions)
        elif action == 'MODIFY':
            result = self._execute_modify_signal(processed_signal, current_positions)
        else:
            result = {
                'success': False,
                'error': f'Unknown action: {action}',
                'signal': signal
            }
        
        # Track execution
        self.execution_history.append({
            'time': datetime.now(),
            'signal': signal,
            'result': result
        })
        
        return result
    
    def _execute_entry_signal(self, signal: Dict[str, Any], positions: List[Dict]) -> Dict[str, Any]:
        """Execute BUY or SELL signal"""
        symbol = signal.get('symbol')
        action = signal.get('action')
        quantity = signal.get('quantity', 0.01)
        stop_loss = signal.get('stop_loss', 0.0)
        take_profit = signal.get('take_profit', 0.0)
        comment = signal.get('comment', 'External Signal')
        
        # Handle Cancel Previous rule
        if signal.get('close_existing'):
            existing_positions = signal.get('existing_positions', [])
            for pos in existing_positions:
                ticket = pos.get('ticket')
                if ticket:
                    logger.info(f"Closing existing position {ticket} due to Cancel Previous rule")
                    self.order_manager.close_position(ticket)
        
        # Handle Stop & Reverse rule
        if signal.get('stop_reverse'):
            reverse_positions = signal.get('reverse_positions', [])
            for pos in reverse_positions:
                ticket = pos.get('ticket')
                if ticket:
                    logger.info(f"Closing position {ticket} due to Stop & Reverse rule")
                    self.order_manager.close_position(ticket)
        
        # Execute new order
        try:
            result = self.order_manager.place_market_order(
                symbol=symbol,
                order_type=action,
                volume=quantity,
                sl=stop_loss,
                tp=take_profit,
                comment=comment
            )
            
            if result:
                # Check if order was actually successful
                retcode = result.get('retcode', 0)
                success_flag = result.get('success', False)
                
                # MT5 success codes: 10009 (TRADE_RETCODE_DONE), 10010 (TRADE_RETCODE_DONE_PARTIAL)
                if success_flag or retcode in [10009, 10010]:
                    return {
                        'success': True,
                        'message': f'{action} order placed successfully',
                        'order': result,
                        'signal': signal,
                        'retcode': retcode
                    }
                else:
                    # Order returned but failed
                    error_msg = result.get('comment', 'Unknown error')
                    retcode_msg = result.get('retcode', 'Unknown')
                    return {
                        'success': False,
                        'error': f'Order placement failed: {error_msg} (Code: {retcode_msg})',
                        'order': result,
                        'signal': signal,
                        'retcode': retcode
                    }
            else:
                # Get more detailed error information
                error_details = []
                
                # Check MT5 connection
                if not self.order_manager.mt5.is_connected():
                    error_details.append("MT5 not connected")
                
                # Check symbol availability - preserve symbol name correctly
                import MetaTrader5 as mt5
                symbol_name = str(symbol) if symbol else "Unknown"
                symbol_info = mt5.symbol_info(symbol_name) if symbol else None
                if symbol_info is None:
                    error_details.append(f"Symbol {symbol_name} not found in MT5")
                elif symbol_info.trade_mode == 0:
                    error_details.append(f"Symbol {symbol_name} is not tradeable (trading disabled)")
                
                # Check account status
                account_info = mt5.account_info()
                if account_info:
                    if account_info.trade_mode == 0:
                        error_details.append("Trading disabled on account")
                    if account_info.margin_free < 0:
                        error_details.append("Insufficient margin")
                
                # Build error message - ensure symbol is preserved correctly
                if error_details:
                    # Join with newlines for multi-line display, or with " - " for single line
                    if len(error_details) == 1:
                        error_msg = error_details[0]
                    else:
                        error_msg = " - ".join(error_details)
                else:
                    error_msg = f"Order placement failed for {symbol}. Possible causes: "
                    error_msg += "Connection issue with MT5, Trading disabled, Invalid parameters, Market closed, or Insufficient margin"
                
                return {
                    'success': False,
                    'error': error_msg,
                    'signal': signal
                }
        except Exception as e:
            logger.error(f"Error executing {action} signal: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f'Exception during order execution: {str(e)}',
                'signal': signal
            }
    
    def _execute_exit_signal(self, signal: Dict[str, Any], positions: List[Dict]) -> Dict[str, Any]:
        """Execute EXIT or CLOSE signal"""
        symbol = signal.get('symbol')
        
        if not positions:
            return {
                'success': False,
                'error': f'No open positions found for {symbol}',
                'signal': signal
            }
        
        closed_count = 0
        errors = []
        
        for pos in positions:
            ticket = pos.get('ticket')
            if ticket:
                try:
                    if self.order_manager.close_position(ticket):
                        closed_count += 1
                    else:
                        errors.append(f'Failed to close position {ticket}')
                except Exception as e:
                    errors.append(f'Error closing position {ticket}: {str(e)}')
        
        if closed_count > 0:
            return {
                'success': True,
                'message': f'Closed {closed_count} position(s)',
                'closed_count': closed_count,
                'errors': errors if errors else None,
                'signal': signal
            }
        else:
            return {
                'success': False,
                'error': 'Failed to close any positions',
                'errors': errors,
                'signal': signal
            }
    
    def _execute_modify_signal(self, signal: Dict[str, Any], positions: List[Dict]) -> Dict[str, Any]:
        """Execute MODIFY signal"""
        symbol = signal.get('symbol')
        stop_loss = signal.get('stop_loss', 0.0)
        take_profit = signal.get('take_profit', 0.0)
        
        if not positions:
            return {
                'success': False,
                'error': f'No open positions found for {symbol}',
                'signal': signal
            }
        
        modified_count = 0
        errors = []
        
        for pos in positions:
            ticket = pos.get('ticket')
            if ticket:
                try:
                    if self.order_manager.modify_position(ticket, stop_loss, take_profit):
                        modified_count += 1
                    else:
                        errors.append(f'Failed to modify position {ticket}')
                except Exception as e:
                    errors.append(f'Error modifying position {ticket}: {str(e)}')
        
        if modified_count > 0:
            return {
                'success': True,
                'message': f'Modified {modified_count} position(s)',
                'modified_count': modified_count,
                'errors': errors if errors else None,
                'signal': signal
            }
        else:
            return {
                'success': False,
                'error': 'Failed to modify any positions',
                'errors': errors,
                'signal': signal
            }
    
    def get_execution_history(self, limit: int = 100) -> List[Dict]:
        """Get recent execution history"""
        return self.execution_history[-limit:] if limit > 0 else self.execution_history

