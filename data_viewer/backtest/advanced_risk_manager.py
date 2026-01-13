"""
Advanced Risk Management
Trailing Stop-Loss and Profit Lock + Trailing Logic
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TrailingStopLoss:
    """
    Trailing Stop-Loss System - tracks highest/lowest price and moves SL by gap
    
    Purpose: Automatically move stop-loss in favorable direction to lock in profits
    while allowing trades to run.
    
    How it works:
    - For BUY positions: Tracks highest price reached, moves SL upward as price increases
    - For SELL positions: Tracks lowest price reached, moves SL downward as price decreases
    - Key feature: SL only moves in favorable direction (never widens the loss)
    - Gap parameter: Fixed distance (in price points) between current best price and SL
    """
    
    def __init__(self, entry_price: float, sl_gap: float, position_type: str):
        """
        Initialize trailing stop-loss
        
        Args:
            entry_price: Entry price of the position
            sl_gap: Gap for trailing stop (in price points)
            position_type: 'BUY' or 'SELL'
        """
        if sl_gap <= 0:
            raise ValueError(f"SL gap must be positive, got {sl_gap}")
        
        if position_type.upper() not in ['BUY', 'SELL']:
            raise ValueError(f"Invalid position_type: {position_type}. Must be 'BUY' or 'SELL'")
        
        self.entry_price = entry_price
        self.sl_gap = sl_gap
        self.position_type = position_type.upper()
        
        if self.position_type == 'BUY':
            # For BUY: SL starts below entry, tracks highest price
            self.stop_loss = entry_price - sl_gap
            self.highest_price = entry_price
            self.lowest_price = None
        else:  # SELL
            # For SELL: SL starts above entry, tracks lowest price
            self.stop_loss = entry_price + sl_gap
            self.lowest_price = entry_price
            self.highest_price = None
    
    def update_price(self, current_price: float) -> float:
        """
        Update trailing stop-loss based on current price
        
        Args:
            current_price: Current market price
            
        Returns:
            Updated stop-loss price
        """
        if self.position_type == 'BUY':
            # Update highest seen price
            if current_price > self.highest_price:
                self.highest_price = current_price
                # Calculate new SL
                new_sl = self.highest_price - self.sl_gap
                # Trailing SL only moves upward (for BUY)
                if new_sl > self.stop_loss:
                    old_sl = self.stop_loss
                    self.stop_loss = new_sl
                    logger.debug(f"TrailingStopLoss BUY: Price {current_price:.5f} > Highest {self.highest_price:.5f}, SL moved {old_sl:.5f} → {new_sl:.5f}")
        else:  # SELL
            # Update lowest seen price
            if current_price < self.lowest_price:
                self.lowest_price = current_price
                # Calculate new SL
                new_sl = self.lowest_price + self.sl_gap
                # Trailing SL only moves downward (for SELL)
                if new_sl < self.stop_loss:
                    old_sl = self.stop_loss
                    self.stop_loss = new_sl
                    logger.debug(f"TrailingStopLoss SELL: Price {current_price:.5f} < Lowest {self.lowest_price:.5f}, SL moved {old_sl:.5f} → {new_sl:.5f}")
        
        return self.stop_loss
    
    def should_trigger_close(self, current_price: float) -> bool:
        """
        Check if current price should trigger position close
        
        Args:
            current_price: Current market price
            
        Returns:
            True if position should be closed
        """
        if self.position_type == 'BUY':
            return current_price <= self.stop_loss
        else:  # SELL
            return current_price >= self.stop_loss


class ProfitManager:
    """
    Profit Lock + Trailing Logic - locks minimum profit and trails it
    
    Purpose: Lock minimum profit once target is reached, then trail TP upward as profit increases.
    
    How it works:
    - Lock Trigger: When profit reaches this amount, lock minimum profit
    - Lock Value: Minimum profit to lock (becomes new TP)
    - Trail Step: Every time profit increases by this amount...
    - Trail Amount: ...increase locked profit by this amount
    """
    
    def __init__(self, lock_trigger: float, lock_value: float, 
                 trail_step: float, trail_amount: float, position_type: str):
        """
        Initialize profit lock manager
        
        Args:
            lock_trigger: Profit amount to trigger lock
            lock_value: Minimum profit to lock
            trail_step: Profit increase to trigger trail
            trail_amount: Amount to trail profit by
            position_type: 'BUY' or 'SELL'
        """
        if lock_trigger <= 0:
            raise ValueError(f"Lock trigger must be positive, got {lock_trigger}")
        if lock_value <= 0:
            raise ValueError(f"Lock value must be positive, got {lock_value}")
        if trail_step < 0:
            raise ValueError(f"Trail step must be non-negative, got {trail_step}")
        if trail_amount < 0:
            raise ValueError(f"Trail amount must be non-negative, got {trail_amount}")
        
        self.lock_trigger = lock_trigger
        self.lock_value = lock_value
        self.trail_step = trail_step
        self.trail_amount = trail_amount
        self.position_type = position_type.upper()
        
        self.lock_enabled = False
        self.current_locked_profit = 0
        self.last_trail_base = lock_trigger  # Will trail only after reaching trigger
        
        logger.info(f"ProfitManager initialized: {position_type}, Lock Trigger: {lock_trigger}, Lock Value: {lock_value}, Trail Step: {trail_step}, Trail Amount: {trail_amount}")
    
    def update_profit(self, profit: float) -> float:
        """
        Update profit lock based on current profit
        
        Args:
            profit: Current profit amount (in account currency)
            
        Returns:
            Updated locked profit (minimum TP to maintain)
        """
        # Enable locking when profit reaches trigger
        if profit >= self.lock_trigger and not self.lock_enabled:
            self.lock_enabled = True
            self.current_locked_profit = self.lock_value
            logger.info(f"ProfitManager: Lock enabled! Profit {profit:.2f} >= Trigger {self.lock_trigger:.2f}, Locked profit: {self.current_locked_profit:.2f}")
        
        # Apply trailing only after lock trigger is hit
        if self.lock_enabled and self.trail_step > 0:
            # Check if profit increased enough to trail more
            while profit >= self.last_trail_base + self.trail_step:
                old_locked = self.current_locked_profit
                self.last_trail_base += self.trail_step
                self.current_locked_profit += self.trail_amount
                logger.info(f"ProfitManager: Trailing! Profit {profit:.2f} >= Base {self.last_trail_base:.2f}, Locked profit: {old_locked:.2f} → {self.current_locked_profit:.2f}")
        
        return self.current_locked_profit
    
    def calculate_take_profit_price(self, entry_price: float, lot_size: float = 0.01) -> Optional[float]:
        """
        Calculate take profit price based on locked profit
        
        Args:
            entry_price: Entry price of the position
            lot_size: Lot size for converting profit to price difference
            
        Returns:
            Take profit price or None if lock not enabled
        """
        if not self.lock_enabled or self.current_locked_profit == 0:
            return None
        
        # Convert locked profit (currency) to price difference
        # For standard lot (100000 units): 1 point = $1 per lot
        # For 0.01 lot: 1 point = $0.01 per 0.01 lot
        # So: profit (in $) = price_diff * lot_size * 100000
        # Therefore: price_diff = profit / (lot_size * 100000)
        if lot_size > 0:
            price_diff = self.current_locked_profit / (lot_size * 100000)
        else:
            # Fallback: assume 0.01 lot
            price_diff = self.current_locked_profit / 1000
        
        if self.position_type == 'BUY':
            # For BUY: TP = entry + price_diff
            return entry_price + price_diff
        else:  # SELL
            # For SELL: TP = entry - price_diff
            return entry_price - price_diff
    
    def should_trigger_close(self, entry_price: float, current_price: float, lot_size: float = 0.01) -> bool:
        """
        Check if profit lock should trigger position close
        
        Args:
            entry_price: Entry price of the position
            current_price: Current market price
            lot_size: Lot size for profit calculation
            
        Returns:
            True if position should be closed based on profit lock
        """
        if not self.lock_enabled:
            return False
        
        # Calculate current profit
        if self.position_type == 'BUY':
            price_diff = current_price - entry_price
        else:  # SELL
            price_diff = entry_price - current_price
        
        # Convert price difference to profit (simplified: 1 point = $1 per lot)
        # For standard lot (100000 units), 1 point = $1
        # For 0.01 lot, 1 point = $0.01
        profit = price_diff * lot_size * 100000
        
        # Check if profit has dropped below locked profit
        return profit < self.current_locked_profit

