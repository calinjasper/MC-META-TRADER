"""
Order Manager
Handles order execution and position management
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
import MetaTrader5 as mt5
import threading
import time

from ..mt5_connector import MT5Connector
from .position_tracker import PositionTracker
from .trade_history import TradeHistory
from ..gui.system_log_service import system_log_service

logger = logging.getLogger(__name__)

# Log that enhanced diagnostic code is active
logger.info("OrderManager: Enhanced diagnostic logging is ACTIVE")


class OrderManager:
    """Manages trading orders and positions"""
    
    def __init__(self, mt5_connector: MT5Connector, persistence_file: Optional[str] = None):
        self.mt5 = mt5_connector
        self.order_history: List[Dict] = []
        self.position_tracker = PositionTracker()
        self.trade_history = TradeHistory(persistence_file=persistence_file)
    
    def place_market_order(self, symbol: str, order_type: str, volume: float,
                          sl: float = 0.0, tp: float = 0.0, 
                          comment: str = "Auto Trade") -> Optional[Dict]:
        """
        Place a market order
        
        Args:
            symbol: Trading symbol
            order_type: 'BUY' or 'SELL'
            volume: Lot size
            sl: Stop loss price (0 to disable)
            tp: Take profit price (0 to disable)
            comment: Order comment
            
        Returns:
            Order result dictionary or None if failed
        """
        if not self.mt5.is_connected():
            logger.error("MT5 not connected")
            system_log_service.log("ERROR", f"Order rejected: MT5 not connected ({symbol})")
            return None
        
        mt5_order_type = mt5.ORDER_TYPE_BUY if order_type.upper() == 'BUY' else mt5.ORDER_TYPE_SELL
        
        # Log diagnostic information before placing order
        logger.info(f"OrderManager.place_market_order: Starting order placement for {symbol} {order_type}")
        logger.info(f"OrderManager.place_market_order: Parameters - symbol={symbol}, type={mt5_order_type}, volume={volume}, sl={sl}, tp={tp}")
        
        # Check connection status with detailed logging
        connection_status = self.mt5.is_connected()
        logger.info(f"OrderManager.place_market_order: MT5 connection status = {connection_status}")
        if not connection_status:
            logger.error(f"OrderManager.place_market_order: MT5 connection check failed before placing order for {symbol}")
            system_log_service.log("ERROR", f"Order rejected: MT5 not connected ({symbol})")
            return {
                'success': False,
                'error': 'MT5 not connected',
                'retcode': 0,
                'comment': 'MT5 not connected'
            }
        
        # Store start time for timeout detection
        start_time = time.time()
        result = None
        exception_occurred = False
        
        try:
            logger.info(f"OrderManager.place_market_order: Calling self.mt5.place_order() for {symbol}")
            result = self.mt5.place_order(
                symbol=symbol,
                order_type=mt5_order_type,
                volume=volume,
                price=0.0,  # Market order
                sl=sl,
                tp=tp,
                comment=comment
            )
            elapsed_time = time.time() - start_time
            logger.info(f"OrderManager.place_market_order: self.mt5.place_order() returned after {elapsed_time:.2f} seconds")
            
            # Log return value with type information
            if result is None:
                logger.error(f"OrderManager.place_market_order: mt5.place_order returned None for {symbol} {order_type} order - no result from MT5 connector")
            else:
                result_type = type(result).__name__
                logger.info(f"OrderManager.place_market_order: mt5.place_order returned: type={result_type}, value={result}")
                
        except Exception as e:
            exception_occurred = True
            elapsed_time = time.time() - start_time
            logger.error(f"OrderManager.place_market_order: Exception in mt5.place_order after {elapsed_time:.2f} seconds: {e}", exc_info=True)
            result = {
                'success': False,
                'error': f"Exception: {str(e)}",
                'retcode': 0,
                'comment': f"Exception: {str(e)}"
            }
        
        # Log if call took too long (potential hanging)
        elapsed_time = time.time() - start_time
        if elapsed_time > 5.0:
            logger.warning(f"OrderManager.place_market_order: WARNING - place_order call took {elapsed_time:.2f} seconds (may indicate hanging)")
        
        # Explicit None check with detailed logging
        if result is None:
            logger.error(f"mt5.place_order returned None for {symbol} {order_type} order")
            logger.error(f"Diagnostics: MT5 connected={self.mt5.is_connected()}, symbol={symbol}, order_type={order_type}")
            system_log_service.log("ERROR", f"Order failed: no result from MT5 for {symbol} ({order_type})")
            return {
                'success': False,
                'error': 'MT5 place_order returned None - check MT5 connection and logs',
                'retcode': 0,
                'comment': 'MT5 place_order returned None'
            }
        
        # Check if result contains error information
        if result.get('error'):
            error_msg = result.get('error', 'Unknown error')
            retcode = result.get('retcode', 0)
            logger.warning(f"Order placement error for {symbol}: {error_msg} (retcode={retcode})")
            system_log_service.log("ERROR", f"Order rejected for {symbol} ({order_type}): {error_msg}")
            # Return result with error flag
            return {
                'success': False,
                'retcode': retcode,
                'comment': error_msg,
                'error': error_msg
            }
        
        # Only log as success if retcode indicates success
        retcode = result.get('retcode', 0)
        if result.get('success', False) or retcode == 10009:  # TRADE_RETCODE_DONE
            result['timestamp'] = datetime.now()
            result['symbol'] = symbol
            result['order_type'] = order_type
            self.order_history.append(result)
            ticket = result.get('order', 'N/A')
            logger.info(f"✅ Market order placed successfully: {order_type} {volume} {symbol}, Ticket: {ticket}, Retcode: {retcode}")
            system_log_service.log("TRADING", f"Order {ticket} placed for {symbol} ({order_type})")
        else:
            comment = result.get('comment', 'No comment')
            logger.warning(f"Order returned but may have failed: retcode={retcode}, comment={comment}, success={result.get('success', False)}")
            system_log_service.log("WARNING", f"Order status uncertain for {symbol} ({order_type}): retcode={retcode} {comment}")
        
        return result
    
    def close_position(self, ticket: int) -> bool:
        """Close a position by ticket"""
        ok = self.mt5.close_position(ticket)
        if ok:
            system_log_service.log("TRADING", f"Position closed (ticket {ticket})")
        else:
            system_log_service.log("ERROR", f"Failed to close position (ticket {ticket})")
        return ok
    
    def get_positions(self, symbol: str = None) -> List[Dict]:
        """Get open positions"""
        return self.mt5.get_positions(symbol)
    
    def get_position_by_ticket(self, ticket: int) -> Optional[Dict]:
        """Get position by ticket number"""
        positions = self.mt5.get_positions()
        for pos in positions:
            if pos['ticket'] == ticket:
                return pos
        return None
    
    def close_all_positions(self, symbol: str = None) -> int:
        """Close all open positions for a symbol (or all if symbol is None)"""
        positions = self.get_positions(symbol)
        closed_count = 0
        
        for pos in positions:
            if self.close_position(pos['ticket']):
                closed_count += 1
        
        logger.info(f"Closed {closed_count} positions")
        return closed_count
    
    def get_order_history(self) -> List[Dict]:
        """Get order history"""
        return self.order_history.copy()
    
    def modify_position(self, ticket: int, sl: float = 0.0, tp: float = 0.0) -> bool:
        """
        Modify stop loss and take profit of an open position
        
        Args:
            ticket: Position ticket
            sl: New stop loss price (0 to remove)
            tp: New take profit price (0 to remove)
            
        Returns:
            True if successful, False otherwise
        """
        ok = self.mt5.modify_position(ticket, sl, tp)
        if ok:
            system_log_service.log("TRADING", f"Position modified (ticket {ticket}) SL={sl} TP={tp}")
        else:
            system_log_service.log("ERROR", f"Failed to modify position (ticket {ticket})")
        return ok
    
    def close_position_partial(self, ticket: int, volume: float) -> bool:
        """
        Partially close a position
        
        Args:
            ticket: Position ticket
            volume: Volume to close (must be less than position volume)
            
        Returns:
            True if successful, False otherwise
        """
        return self.mt5.close_position_partial(ticket, volume)

