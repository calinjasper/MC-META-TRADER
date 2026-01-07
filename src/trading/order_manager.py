
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
                          comment: str = "Auto Trade", strategy_name: Optional[str] = None) -> Optional[Dict]:
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
            system_log_service.log("ERROR", f"Order rejected: MT5 not connected ({symbol})", strategy=strategy_name or "")
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
            system_log_service.log("ERROR", f"Order rejected: MT5 not connected ({symbol})", strategy=strategy_name or "")
            return {
                'success': False,
                'error': 'MT5 not connected',
                'retcode': 0,
                'comment': 'MT5 not connected'
            }
        
        # #region agent log
        import json
        import time as time_module
        log_path = r"c:\Users\Calin Jasper\Music\mc_meta\.cursor\debug.log"
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({"id":f"log_{int(time_module.time()*1000)}_order_place_entry","timestamp":int(time_module.time()*1000),"location":"order_manager.py:75","message":"place_market_order entry","data":{"symbol":symbol,"order_type":order_type,"volume":volume,"sl":sl,"tp":tp,"mt5_connected":self.mt5.is_connected()},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + "\n")
        except: pass
        # #endregion
        
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
                # #region agent log
                try:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"id":f"log_{int(time_module.time()*1000)}_order_place_none","timestamp":int(time_module.time()*1000),"location":"order_manager.py:95","message":"place_order returned None","data":{"symbol":symbol,"order_type":order_type,"elapsed":elapsed_time},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + "\n")
                except: pass
                # #endregion
            else:
                result_type = type(result).__name__
                logger.info(f"OrderManager.place_market_order: mt5.place_order returned: type={result_type}, value={result}")
                # #region agent log
                try:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"id":f"log_{int(time_module.time()*1000)}_order_place_result","timestamp":int(time_module.time()*1000),"location":"order_manager.py:99","message":"place_order result","data":{"symbol":symbol,"order_type":order_type,"result_type":result_type,"success":result.get('success',False) if isinstance(result,dict) else None,"retcode":result.get('retcode') if isinstance(result,dict) else None},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + "\n")
                except: pass
                # #endregion
                
        except Exception as e:
            exception_occurred = True
            elapsed_time = time.time() - start_time
            logger.error(f"OrderManager.place_market_order: Exception in mt5.place_order after {elapsed_time:.2f} seconds: {e}", exc_info=True)
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({"id":f"log_{int(time_module.time()*1000)}_order_place_exception","timestamp":int(time_module.time()*1000),"location":"order_manager.py:101","message":"place_order exception","data":{"symbol":symbol,"order_type":order_type,"error":str(e),"elapsed":elapsed_time},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + "\n")
            except: pass
            # #endregion
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
            
            # Check if this might be a connection/server issue
            connection_ok = self.mt5.is_connected()
            error_detail = "no response from server"
            
            if not connection_ok:
                error_detail = "MT5 connection lost"
            elif elapsed_time > 10.0:
                error_detail = "server timeout (no response after 10+ seconds)"
            else:
                error_detail = "no response from server - check MT5 connection and AutoTrading settings"
            
            system_log_service.log("ERROR", f"Order failed: {error_detail} for {symbol} ({order_type})", strategy=strategy_name or "")
            return {
                'success': False,
                'error': f'Order failed: {error_detail}',
                'retcode': 0,
                'comment': error_detail
            }
        
        # Check if result contains error information
        if result.get('error'):
            error_msg = result.get('error', 'Unknown error')
            retcode = result.get('retcode', 0)
            logger.warning(f"Order placement error for {symbol}: {error_msg} (retcode={retcode})")
            
            # Retry logic for invalid stops (retcode 10016) - BEFORE early return
            if retcode == 10016 and (sl > 0 or tp > 0):
                logger.info(f"Order failed with invalid stops (retcode 10016). Retrying without SL/TP for {symbol}")
                original_sl = sl
                original_tp = tp
                
                # Retry without SL/TP
                retry_result = self.mt5.place_order(
                    symbol=symbol,
                    order_type=mt5_order_type,
                    volume=volume,
                    price=0.0,  # Market order
                    sl=0.0,  # No SL on retry
                    tp=0.0,  # No TP on retry
                    comment=comment
                )
                
                if retry_result and retry_result.get('success') and retry_result.get('retcode') in [10009, 10010]:
                    ticket = retry_result.get('order')
                    logger.info(f"Order placed without SL/TP. Ticket: {ticket}. Now adding SL/TP...")
                    
                    # Wait a moment for position to be fully established
                    time.sleep(0.2)
                    
                    # Modify position to add SL/TP
                    if original_sl > 0 or original_tp > 0:
                        if ticket and isinstance(ticket, int):
                            modify_success = self.modify_position(ticket, original_sl, original_tp)
                        else:
                            logger.error(f"Cannot modify position: invalid ticket {ticket}")
                            modify_success = False
                        
                        if modify_success:
                            logger.info(f"Successfully added SL/TP to position {ticket}")
                            retry_result['sl'] = original_sl
                            retry_result['tp'] = original_tp
                        else:
                            logger.warning(f"Order placed but failed to add SL/TP to position {ticket}")
                    
                    # Update result to reflect success
                    retry_result['timestamp'] = datetime.now()
                    retry_result['symbol'] = symbol
                    retry_result['order_type'] = order_type
                    self.order_history.append(retry_result)
                    
                    ticket_str = str(ticket) if ticket else 'N/A'
                    system_log_service.log("TRADING", f"Order {ticket_str} placed without SL/TP, then modified", strategy=strategy_name or "")
                    
                    return retry_result
                else:
                    # Retry also failed - log and continue with original error
                    retry_retcode = retry_result.get('retcode') if retry_result else None
                    logger.warning(f"Retry without SL/TP also failed for {symbol}. Retcode: {retry_retcode}")
            
            # Log error (but don't return yet if retry was attempted)
            system_log_service.log("ERROR", f"Order rejected for {symbol} ({order_type}): {error_msg}", strategy=strategy_name or "")
            # Return result with error flag
            return {
                'success': False,
                'retcode': retcode,
                'comment': error_msg,
                'error': error_msg
            }
        
        # Check if order was successful
        # Success retcodes:
        # 10009 (TRADE_RETCODE_DONE) = fully executed (position opened)
        # 10010 (TRADE_RETCODE_DONE_PARTIAL) = partially executed (partial position opened)
        # 10008 (TRADE_RETCODE_PLACED) = order placed but pending (not a position yet, but order accepted)
        retcode = result.get('retcode', 0)
        success = result.get('success', False)
        
        # Consider these retcodes as successful order placement
        success_retcodes = [
            10009,  # TRADE_RETCODE_DONE - fully executed
            10010,  # TRADE_RETCODE_DONE_PARTIAL - partially executed
            10008,  # TRADE_RETCODE_PLACED - order placed (pending execution)
        ]
        
        is_success = success or retcode in success_retcodes
        
        if is_success:
            result['timestamp'] = datetime.now()
            result['symbol'] = symbol
            result['order_type'] = order_type
            self.order_history.append(result)
            ticket = result.get('order', 'N/A')
            
            # Determine status message based on retcode
            if retcode == 10009:
                status_msg = "fully executed"
            elif retcode == 10010:
                status_msg = "partially executed"
            elif retcode == 10008:
                status_msg = "placed (pending execution)"
            else:
                status_msg = "placed"
            
            logger.info(f"✅ Market order {status_msg}: {order_type} {volume} {symbol}, Ticket: {ticket}, Retcode: {retcode}")
            system_log_service.log("TRADING", f"Order {ticket} {status_msg} for {symbol} ({order_type})")
        else:
            # Order failed - log detailed error
            # Note: Retry logic for retcode 10016 is handled in the error block above
            comment = result.get('comment', 'No comment')
            error_msg = result.get('error', '')
            
            # Build comprehensive error message
            # Prefer error field (which now includes retcode meaning from mt5_connector)
            # Otherwise fall back to comment with retcode
            if error_msg:
                full_error = error_msg  # Already includes retcode meaning from mt5_connector
            elif comment and comment != 'No comment':
                full_error = f"{comment} (retcode: {retcode})"
            else:
                # Fallback: provide retcode meaning
                retcode_meanings = {
                    10004: "Requote - price changed",
                    10006: "Order rejected by broker",
                    10007: "Order cancelled",
                    10011: "General error",
                    10012: "Timeout",
                    10013: "Invalid request",
                    10014: "Invalid volume",
                    10015: "Invalid price",
                    10016: "Invalid stop loss or take profit",
                    10017: "Trading disabled",
                    10018: "Market closed",
                    10019: "Insufficient funds",
                    10020: "Price changed",
                    10031: "Connection error",
                }
                retcode_msg = retcode_meanings.get(retcode, f"Unknown error (code: {retcode})")
                full_error = f"{retcode_msg} (retcode: {retcode})"
            
            logger.error(f"Order failed for {symbol} {order_type}: {full_error}")
            # Log error with strategy name if provided
            error_log_msg = f"Order failed for {symbol} ({order_type}): {full_error}"
            system_log_service.log("ERROR", error_log_msg, strategy=strategy_name or "")
            
            # Log specific retcode for debugging
            logger.error(f"Order failure details - Retcode: {retcode}, Comment: {comment}, Error: {error_msg}")
        
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
        logger.info(f"modify_position: Modifying position {ticket} - SL={sl:.5f}, TP={tp:.5f}")
        
        # Get position info first to validate
        positions = self.mt5.get_positions()
        position = None
        for pos in positions:
            if pos.get('ticket') == ticket:
                position = pos
                break
        
        if not position:
            logger.error(f"modify_position: Position {ticket} not found")
            system_log_service.log("ERROR", f"Failed to modify position {ticket}: Position not found", strategy="")
            return False
        
        symbol = position.get('symbol', 'UNKNOWN')
        entry_price = position.get('price_open', 0.0)
        current_sl = position.get('sl', 0.0)
        current_tp = position.get('tp', 0.0)
        
        logger.info(f"modify_position: Current values for {ticket} ({symbol}) - Entry={entry_price:.5f}, SL={current_sl:.5f}, TP={current_tp:.5f}")
        logger.info(f"modify_position: Requested values - SL={sl:.5f}, TP={tp:.5f}")
        
        ok = self.mt5.modify_position(ticket, sl, tp)
        
        if ok:
            logger.info(f"modify_position: Successfully modified position {ticket}")
            system_log_service.log("TRADING", f"Position modified (ticket {ticket}) SL={sl:.5f} TP={tp:.5f}")
            
            # Verify the modification
            import time
            time.sleep(0.2)
            positions_after = self.mt5.get_positions()
            for pos_after in positions_after:
                if pos_after.get('ticket') == ticket:
                    actual_sl = pos_after.get('sl', 0.0)
                    actual_tp = pos_after.get('tp', 0.0)
                    logger.info(f"modify_position: Verified values after modification - SL={actual_sl:.5f}, TP={actual_tp:.5f}")
                    
                    # Check if values match
                    sl_ok = (abs(actual_sl - sl) < 0.00001) if sl > 0 else (actual_sl <= 0)
                    tp_ok = (abs(actual_tp - tp) < 0.00001) if tp > 0 else (actual_tp <= 0)
                    
                    if not sl_ok or not tp_ok:
                        logger.warning(f"modify_position: Modification verification failed for {ticket}")
                        logger.warning(f"  SL: requested={sl:.5f}, actual={actual_sl:.5f}, match={sl_ok}")
                        logger.warning(f"  TP: requested={tp:.5f}, actual={actual_tp:.5f}, match={tp_ok}")
                    break
        else:
            error_detail = self.mt5.get_last_error() if hasattr(self.mt5, "get_last_error") else None
            # Get error code from MT5 if available
            try:
                import MetaTrader5 as mt5
                error_code = mt5.last_error()[0] if hasattr(mt5, 'last_error') else None
            except:
                error_code = None
            logger.error(f"modify_position: Failed to modify position {ticket} ({symbol})")
            logger.error(f"  Entry price: {entry_price:.5f}")
            logger.error(f"  Requested SL: {sl:.5f}, TP: {tp:.5f}")
            logger.error(f"  Current SL: {current_sl:.5f}, TP: {current_tp:.5f}")
            if error_code:
                logger.error(f"  Error code: {error_code}")
            if error_detail:
                logger.error(f"  Error detail: {error_detail}")
            
            detail_suffix = f" | Code: {error_code}, Detail: {error_detail}" if (error_code or error_detail) else ""
            system_log_service.log("ERROR", f"Failed to modify position (ticket {ticket}){detail_suffix}", strategy="")
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

