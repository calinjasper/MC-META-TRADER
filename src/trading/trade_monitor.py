"""
Trade Monitor
Monitors open positions and checks SL/TP based on LTP or Candle Close mode
Based on AlgoTest architecture
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum

from ..mt5_connector import MT5Connector
from .advanced_risk_manager import TrailingStopLoss, ProfitManager, TrailWaitAndTrade

logger = logging.getLogger(__name__)


class TradeMonitoringMode(Enum):
    """Trade monitoring mode"""
    LTP = "LTP"  # Last Traded Price - continuous monitoring
    CANDLE_CLOSE = "CANDLE_CLOSE"  # Candle Close - check at 1-minute candle close (59th second)


class TradeMonitor:
    """
    Monitors open positions and checks SL/TP conditions
    
    Based on AlgoTest architecture:
    - LTP Mode: Executes immediately when conditions are met (continuous monitoring)
    - Candle Close Mode: Executes on 1-minute candle close (59th second)
    """
    
    def __init__(self, mt5_connector: MT5Connector):
        self.mt5 = mt5_connector
        self.monitoring_mode = TradeMonitoringMode.LTP  # Default to LTP
        self.last_candle_check_time: Dict[str, datetime] = {}  # Track last candle check per symbol
        self.last_second_checked: Dict[str, int] = {}  # Track last second checked for candle close
        
        # Advanced risk management tracking
        self.active_trailing_sl: Dict[int, TrailingStopLoss] = {}  # ticket -> TrailingStopLoss instance
        self.active_profit_locks: Dict[int, ProfitManager] = {}  # ticket -> ProfitManager instance
        self.active_wt: Dict[int, TrailWaitAndTrade] = {}  # ticket -> W&T instance
        self.position_configs: Dict[int, Dict] = {}  # ticket -> config dict (for reference)
        
    def set_monitoring_mode(self, mode: TradeMonitoringMode):
        """Set the trade monitoring mode"""
        self.monitoring_mode = mode
        logger.info(f"Trade monitoring mode set to: {mode.value}")
    
    def should_check_conditions(self, symbol: str) -> bool:
        """
        Determine if conditions should be checked based on monitoring mode
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if conditions should be checked, False otherwise
        """
        if self.monitoring_mode == TradeMonitoringMode.LTP:
            # LTP mode: check continuously (every time this is called)
            return True
        
        elif self.monitoring_mode == TradeMonitoringMode.CANDLE_CLOSE:
            # Candle Close mode: check only at 1-minute candle close (59th second)
            now = datetime.now()
            current_second = now.second
            
            # Check if we're at the 59th second (candle close)
            if current_second == 59:
                # Only check once per minute (avoid multiple checks in same second)
                last_second = self.last_second_checked.get(symbol, -1)
                if last_second != 59:
                    self.last_second_checked[symbol] = 59
                    logger.debug(f"Candle close detected for {symbol} at {now}")
                    return True
            
            return False
        
        return True
    
    def check_stop_loss_take_profit(self, position: Dict, current_price: float) -> Optional[str]:
        """
        Check if stop loss or take profit should be triggered
        
        Args:
            position: Position dictionary from MT5
            current_price: Current market price (bid for SELL, ask for BUY)
            
        Returns:
            'SL' if stop loss triggered, 'TP' if take profit triggered, None otherwise
        """
        pos_type = position.get('type', 0)  # 0 = BUY, 1 = SELL
        ticket = position.get('ticket')
        entry_price = position.get('price_open', 0.0)
        sl_price = position.get('sl', 0.0)
        tp_price = position.get('tp', 0.0)
        symbol = position.get('symbol', 'UNKNOWN')
        
        if not entry_price:
            logger.warning(f"Position {ticket} ({symbol}) has no entry price, skipping SL/TP check")
            return None
        
        # Log position details for debugging (only at debug level to avoid spam)
        logger.debug(f"Checking SL/TP for position {ticket} ({symbol}): "
                    f"Type={'BUY' if pos_type == 0 else 'SELL'}, "
                    f"Entry={entry_price:.5f}, SL={sl_price:.5f}, TP={tp_price:.5f}, Current={current_price:.5f}")
        
        # Check stop loss
        if sl_price > 0:
            if pos_type == 0:  # BUY position
                if current_price <= sl_price:
                    logger.info(f"Stop loss triggered for position {ticket}: "
                              f"BUY @ {entry_price}, SL @ {sl_price}, Current @ {current_price}")
                    return 'SL'
                else:
                    logger.debug(f"Position {ticket} SL check: Current {current_price:.5f} > SL {sl_price:.5f} (gap: {current_price - sl_price:.5f})")
            else:  # SELL position
                if current_price >= sl_price:
                    logger.info(f"Stop loss triggered for position {ticket}: "
                              f"SELL @ {entry_price}, SL @ {sl_price}, Current @ {current_price}")
                    return 'SL'
                else:
                    logger.debug(f"Position {ticket} SL check: Current {current_price:.5f} < SL {sl_price:.5f} (gap: {sl_price - current_price:.5f})")
        else:
            logger.debug(f"Position {ticket} has no SL set (SL={sl_price})")
        
        # Check take profit
        if tp_price > 0:
            if pos_type == 0:  # BUY position
                if current_price >= tp_price:
                    logger.info(f"✅ Take profit triggered for position {ticket}: "
                              f"BUY @ {entry_price:.5f}, TP @ {tp_price:.5f}, Current @ {current_price:.5f}")
                    return 'TP'
                else:
                    gap = tp_price - current_price
                    # Log at info level if very close to TP (within 0.1% or 10 points)
                    if gap <= max(tp_price * 0.001, 10 * 0.01):  # 0.1% or 10 points (0.10 price units)
                        logger.info(f"Position {ticket} TP check: Current {current_price:.5f} < TP {tp_price:.5f} (gap: {gap:.5f} - very close!)")
                    else:
                        logger.debug(f"Position {ticket} TP check: Current {current_price:.5f} < TP {tp_price:.5f} (gap: {gap:.5f})")
            else:  # SELL position
                if current_price <= tp_price:
                    logger.info(f"✅ Take profit triggered for position {ticket}: "
                              f"SELL @ {entry_price:.5f}, TP @ {tp_price:.5f}, Current @ {current_price:.5f}")
                    return 'TP'
                else:
                    gap = current_price - tp_price
                    # Log at info level if very close to TP (within 0.1% or 10 points)
                    if gap <= max(tp_price * 0.001, 10 * 0.01):  # 0.1% or 10 points (0.10 price units)
                        logger.info(f"Position {ticket} TP check: Current {current_price:.5f} > TP {tp_price:.5f} (gap: {gap:.5f} - very close!)")
                    else:
                        logger.debug(f"Position {ticket} TP check: Current {current_price:.5f} > TP {tp_price:.5f} (gap: {gap:.5f})")
        else:
            logger.warning(f"⚠️ Position {ticket} ({symbol}) has no TP set (TP={tp_price}) - position will not auto-close on TP. "
                          f"Entry: {entry_price:.5f}, Current: {current_price:.5f}")
        
        return None
    
    def monitor_positions(self, positions: List[Dict], 
                         get_current_price_func: callable) -> List[Dict]:
        """
        Monitor positions and check SL/TP conditions
        
        Args:
            positions: List of position dictionaries
            get_current_price_func: Function that takes (symbol, position_type) and returns current price
            
        Returns:
            List of positions that need to be closed (with 'action' key: 'SL' or 'TP')
        """
        positions_to_close = []
        
        for position in positions:
            symbol = position.get('symbol')
            if not symbol:
                continue
            
            # Check if we should check conditions based on monitoring mode
            if not self.should_check_conditions(symbol):
                continue
            
            # Get current price based on position type
            pos_type = position.get('type', 0)  # 0 = BUY, 1 = SELL
            current_price = get_current_price_func(symbol, pos_type)
            
            if not current_price:
                continue
            
            # Check SL/TP
            action = self.check_stop_loss_take_profit(position, current_price)
            if action:
                position_copy = position.copy()
                position_copy['action'] = action
                position_copy['trigger_price'] = current_price
                positions_to_close.append(position_copy)
        
        return positions_to_close
    
    def update_trailing_stop_loss(self, position: Dict, current_price: float,
                                 trailing_distance: float, 
                                 check_only: bool = False) -> Optional[float]:
        """
        Update trailing stop loss for a position
        
        Based on AlgoTest:
        - LTP Mode: Updates continuously, checks continuously
        - Candle Close Mode: Updates continuously, but only checks at candle close
        
        Args:
            position: Position dictionary
            current_price: Current market price
            trailing_distance: Distance for trailing stop (in price points)
            check_only: If True, only check if TSL should trigger (don't update)
            
        Returns:
            New SL price if updated, None if should trigger close, current_sl if unchanged
        """
        pos_type = position.get('type', 0)  # 0 = BUY, 1 = SELL
        entry_price = position.get('price_open', 0.0)
        current_sl = position.get('sl', 0.0)
        
        if not entry_price:
            return None
        
        # Calculate new trailing stop loss
        if pos_type == 0:  # BUY position
            # For BUY: TSL moves up as price goes up
            new_sl = current_price - trailing_distance
            # Only move SL up, never down
            if current_sl > 0 and new_sl <= current_sl:
                new_sl = current_sl
            
            # Check if current price hit the trailing stop
            if check_only:
                if current_sl > 0 and current_price <= current_sl:
                    return None  # Signal to close position
                return current_sl  # Keep current SL
            
        else:  # SELL position
            # For SELL: TSL moves down as price goes down
            new_sl = current_price + trailing_distance
            # Only move SL down, never up
            if current_sl > 0 and new_sl >= current_sl:
                new_sl = current_sl
            
            # Check if current price hit the trailing stop
            if check_only:
                if current_sl > 0 and current_price >= current_sl:
                    return None  # Signal to close position
                return current_sl  # Keep current SL
        
        # Return new SL if it changed
        if new_sl != current_sl:
            return new_sl
        
        return current_sl
    
    def register_position_for_advanced_risk(self, position: Dict, config: Dict):
        """
        Register a position for advanced risk management (trailing SL and/or profit lock)
        
        Args:
            position: Position dictionary from MT5
            config: Configuration dict with keys:
                - enable_trailing_sl: bool
                - trailing_sl_gap: float (if trailing SL enabled)
                - enable_profit_lock: bool
                - profit_lock_trigger: float (if profit lock enabled)
                - profit_lock_value: float
                - profit_trail_step: float
                - profit_trail_amount: float
                - enable_wt: bool
                - wt_value: float
                - wt_is_percentage: bool
        """
        ticket = position.get('ticket')
        if not ticket:
            logger.warning("Cannot register position for advanced risk: no ticket")
            return
        
        entry_price = position.get('price_open', 0.0)
        if not entry_price:
            logger.warning(f"Cannot register position {ticket} for advanced risk: no entry price")
            return
        
        pos_type = position.get('type', 0)  # 0 = BUY, 1 = SELL
        position_type_str = 'BUY' if pos_type == 0 else 'SELL'
        
        # Initialize trailing stop-loss if enabled
        if config.get('enable_trailing_sl', False):
            sl_gap = config.get('trailing_sl_gap', 0.0)
            if sl_gap > 0:
                try:
                    trailing_sl = TrailingStopLoss(entry_price, sl_gap, position_type_str)
                    self.active_trailing_sl[ticket] = trailing_sl
                    logger.info(f"Registered trailing SL for position {ticket}: {position_type_str} @ {entry_price}, Gap: {sl_gap}")
                except Exception as e:
                    logger.error(f"Failed to initialize trailing SL for position {ticket}: {e}", exc_info=True)
        
        # Initialize profit lock if enabled
        if config.get('enable_profit_lock', False):
            lock_trigger = config.get('profit_lock_trigger', 0.0)
            lock_value = config.get('profit_lock_value', 0.0)
            trail_step = config.get('profit_trail_step', 0.0)
            trail_amount = config.get('profit_trail_amount', 0.0)
            
            if lock_trigger > 0 and lock_value > 0:
                try:
                    # Get symbol and volume from position
                    symbol = position.get('symbol', '')
                    volume = position.get('volume', 0.0)
                    
                    profit_lock = ProfitManager(
                        lock_trigger=lock_trigger,
                        lock_value=lock_value,
                        trail_step=trail_step,
                        trail_amount=trail_amount,
                        position_type=position_type_str,
                        symbol=symbol,
                        volume=volume
                    )
                    self.active_profit_locks[ticket] = profit_lock
                    logger.info(f"Registered profit lock for position {ticket}: {position_type_str} @ {entry_price}, Trigger: {lock_trigger}, Lock: {lock_value}, Symbol: {symbol}, Volume: {volume}")
                except Exception as e:
                    logger.error(f"Failed to initialize profit lock for position {ticket}: {e}", exc_info=True)

        # Initialize Trail Wait & Trade if enabled
        if config.get('enable_wt', False):
            try:
                wt_value = config.get('wt_value', 0.0)
                wt_is_percentage = config.get('wt_is_percentage', False)
                wt = TrailWaitAndTrade(wt_value=wt_value, is_percentage=wt_is_percentage, direction=position_type_str)
                self.active_wt[ticket] = wt
                logger.info(
                    f"Registered W&T for position {ticket}: {position_type_str} @ {entry_price}, "
                    f"wt_value={wt_value}, percent={wt_is_percentage}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize W&T for position {ticket}: {e}", exc_info=True)
        
        # Store config for reference
        self.position_configs[ticket] = config.copy()
    
    def unregister_position(self, ticket: int):
        """Unregister a position from advanced risk management (when closed)"""
        if ticket in self.active_trailing_sl:
            del self.active_trailing_sl[ticket]
            logger.debug(f"Unregistered trailing SL for position {ticket}")
        if ticket in self.active_profit_locks:
            del self.active_profit_locks[ticket]
            logger.debug(f"Unregistered profit lock for position {ticket}")
        if ticket in self.active_wt:
            del self.active_wt[ticket]
            logger.debug(f"Unregistered W&T for position {ticket}")
        if ticket in self.position_configs:
            del self.position_configs[ticket]
    
    def update_advanced_risk_management(self, position: Dict, current_price: float, 
                                        current_profit: float, order_manager) -> Dict[str, Optional[float]]:
        """
        Update trailing stop-loss and profit lock for a position
        
        Args:
            position: Position dictionary from MT5
            current_price: Current market price
            current_profit: Current profit amount (in account currency)
            order_manager: OrderManager instance for modifying positions
            
        Returns:
            Dict with 'new_sl' and 'new_tp' if updates needed, None values otherwise
        """
        ticket = position.get('ticket')
        if not ticket:
            return {'new_sl': None, 'new_tp': None}
        updates = {'new_sl': None, 'new_tp': None}
        entry_price = position.get('price_open', 0.0)
        current_sl = position.get('sl', 0.0)
        current_tp = position.get('tp', 0.0)
        pos_type = position.get('type', 0)  # 0 = BUY, 1 = SELL
        
        # Update trailing stop-loss
        if ticket in self.active_trailing_sl:
            trailing_sl = self.active_trailing_sl[ticket]
            
            # Check if SL should trigger close
            if trailing_sl.should_trigger_close(current_price):
                logger.info(f"Trailing SL triggered for position {ticket}: Price {current_price:.5f} <= SL {trailing_sl.stop_loss:.5f}")
                return {'new_sl': None, 'new_tp': None, 'should_close': True, 'reason': 'TrailingSL'}
            
            # Update trailing SL
            new_sl = trailing_sl.update_price(current_price)
            
            # Only update if SL has changed significantly (avoid too frequent updates)
            # Use 0.01% change threshold or minimum 0.1 points
            if new_sl != current_sl:
                min_change = max(new_sl * 0.0001, 0.1)  # 0.01% or 0.1 points, whichever is larger
                if abs(new_sl - current_sl) >= min_change:
                    updates['new_sl'] = new_sl
                    logger.debug(f"Trailing SL update for position {ticket}: {current_sl:.5f} → {new_sl:.5f}")

        # Update Trail Wait & Trade (close-only; does not modify SL/TP)
        if ticket in self.active_wt:
            try:
                wt = self.active_wt[ticket]
                wt_price, executed = wt.update(current_price)
                if executed:
                    logger.info(
                        f"W&T triggered for position {ticket}: Price={current_price:.5f} hit WT={wt_price:.5f}"
                    )
                    return {
                        'new_sl': None,
                        'new_tp': None,
                        'should_close': True,
                        'reason': 'TrailWaitTrade',
                        'wt_price': wt_price,
                    }
            except Exception as e:
                logger.error(f"Error updating W&T for position {ticket}: {e}", exc_info=True)
        
        # Update profit lock
        if ticket in self.active_profit_locks:
            profit_lock = self.active_profit_locks[ticket]
            
            # Update locked profit based on current profit
            locked_profit = profit_lock.update_profit(current_profit)
            
            # Calculate new TP price (pass mt5_connector for symbol info)
            if locked_profit > 0:
                new_tp = profit_lock.calculate_take_profit_price(entry_price, self.mt5)
                
                if new_tp and new_tp != current_tp:
                    # Only update if TP has changed significantly
                    min_change = max(new_tp * 0.0001, 0.1)  # 0.01% or 0.1 points
                    if abs(new_tp - current_tp) >= min_change:
                        updates['new_tp'] = new_tp
                        logger.info(f"Profit lock TP update for position {ticket}: {current_tp:.5f} → {new_tp:.5f} (Locked profit: ${locked_profit:.2f})")
        
        return updates

