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
        
        self.entry_price = entry_price
        self.sl_gap = sl_gap
        self.position_type = position_type.upper()
        
        if self.position_type == 'BUY':
            self.stop_loss = entry_price - sl_gap  # Initial SL below entry
            self.highest_price = entry_price  # Track highest price
            logger.info(f"TrailingStopLoss initialized: BUY @ {entry_price}, SL Gap: {sl_gap}, Initial SL: {self.stop_loss}")
        elif self.position_type == 'SELL':
            self.stop_loss = entry_price + sl_gap  # Initial SL above entry
            self.lowest_price = entry_price  # Track lowest price
            logger.info(f"TrailingStopLoss initialized: SELL @ {entry_price}, SL Gap: {sl_gap}, Initial SL: {self.stop_loss}")
        else:
            raise ValueError(f"Invalid position_type: {position_type}. Must be 'BUY' or 'SELL'")
    
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
        Check if trailing stop-loss should trigger position close
        
        Args:
            current_price: Current market price
            
        Returns:
            True if SL should trigger close, False otherwise
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
                 trail_step: float, trail_amount: float, position_type: str,
                 symbol: str = None, volume: float = None):
        """
        Initialize profit lock manager
        
        Args:
            lock_trigger: Profit amount to trigger lock
            lock_value: Minimum profit to lock
            trail_step: Profit increase to trigger trail
            trail_amount: Amount to trail profit by
            position_type: 'BUY' or 'SELL'
            symbol: Trading symbol (e.g., 'BTCUSDm') - required for TP calculation
            volume: Lot size (e.g., 0.01) - required for TP calculation
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
        self.symbol = symbol
        self.volume = volume
        
        self.lock_enabled = False
        self.current_locked_profit = 0
        self.last_trail_base = lock_trigger  # Will trail only after reaching trigger
        
        logger.info(f"ProfitManager initialized: {position_type}, Lock Trigger: {lock_trigger}, Lock Value: {lock_value}, Trail Step: {trail_step}, Trail Amount: {trail_amount}, Symbol: {symbol}, Volume: {volume}")
    
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
    
    def calculate_take_profit_price(self, entry_price: float, mt5_connector=None) -> Optional[float]:
        """
        Calculate the take-profit price based on locked profit
        
        Args:
            entry_price: Entry price of the position
            mt5_connector: MT5Connector instance to get symbol info (required for conversion)
            
        Returns:
            Take-profit price to maintain locked profit, or None if lock not enabled
        """
        if not self.lock_enabled or self.current_locked_profit == 0:
            return None  # No TP adjustment needed
        
        # If symbol and volume are available, convert profit to price points
        if self.symbol and self.volume and mt5_connector:
            try:
                symbol_info = mt5_connector.get_symbol_info(self.symbol)
                if symbol_info:
                    # Get contract size and point value
                    contract_size = symbol_info.get('trade_contract_size', symbol_info.get('contract_size', 100000))
                    point = symbol_info.get('point', 0.00001)
                    tick_size = symbol_info.get('trade_tick_size', symbol_info.get('tick_size', point))
                    tick_value = symbol_info.get('trade_tick_value', symbol_info.get('tick_value', 0.0))
                    
                    # Convert locked profit (in account currency) to price difference
                    # MT5 profit calculation varies by symbol type:
                    # For forex: profit = (price_diff / point) * volume * (contract_size / 100000)
                    # For crypto/CFD: profit = (price_diff / tick_size) * volume * contract_size * tick_value
                    # General formula: profit = (price_diff / tick_size) * volume * contract_size * tick_value
                    
                    if contract_size > 0 and volume > 0 and tick_size > 0:
                        # Calculate price difference in price units
                        if tick_value > 0:
                            # Use tick_value for accurate calculation
                            # profit = (price_diff / tick_size) * volume * contract_size * tick_value
                            # Solving: price_diff = (profit * tick_size) / (volume * contract_size * tick_value)
                            price_diff = (self.current_locked_profit * tick_size) / (volume * contract_size * tick_value)
                        else:
                            # Fallback: assume profit per point calculation
                            # For most symbols: profit = (price_diff / point) * volume * contract_size
                            # Solving: price_diff = (profit * point) / (volume * contract_size)
                            price_diff = (self.current_locked_profit * point) / (volume * contract_size)
                        
                        if self.position_type == 'BUY':
                            tp_price = entry_price + price_diff
                        else:  # SELL
                            tp_price = entry_price - price_diff
                        
                        logger.info(f"ProfitManager: Converted locked profit ${self.current_locked_profit:.2f} to {price_diff:.5f} price units for {self.symbol} "
                                   f"(entry={entry_price:.5f}, new_tp={tp_price:.5f}, contract_size={contract_size}, volume={volume}, point={point}, tick_value={tick_value})")
                        return tp_price
                    else:
                        logger.warning(f"ProfitManager: Invalid contract_size ({contract_size}) or volume ({volume}) for {self.symbol}")
                else:
                    logger.warning(f"ProfitManager: Could not get symbol info for {self.symbol}")
            except Exception as e:
                logger.error(f"ProfitManager: Error calculating TP price: {e}", exc_info=True)
        
        # Fallback: treat locked_profit as price points (old incorrect behavior)
        # This should not happen if symbol/volume are provided, but kept for backward compatibility
        logger.warning(f"ProfitManager: Using fallback calculation (treating profit as price points). Symbol: {self.symbol}, Volume: {self.volume}")
        if self.position_type == 'BUY':
            tp_price = entry_price + self.current_locked_profit
        else:  # SELL
            tp_price = entry_price - self.current_locked_profit
        
        return tp_price


class TrailWaitAndTrade:
    """
    Trail Wait & Trade (W&T)

    This implements the same core logic as the user's provided reference:
    - Initialize a trigger line (wt_price) from the first observed LTP
    - Trail the trigger line only in the favorable direction
    - "Execute" (trigger) once price crosses back to the trigger line

    Notes:
    - For BUY: tracks max_ltp, trails upward, triggers when ltp <= wt_price
    - For SELL: tracks min_ltp, trails downward, triggers when ltp >= wt_price
    """

    def __init__(self, wt_value: float, is_percentage: bool = False, direction: str = "BUY"):
        self.wt_value = wt_value
        self.is_percentage = is_percentage
        self.direction = direction.upper()

        self.wt_price: Optional[float] = None
        self.max_ltp: Optional[float] = None
        self.min_ltp: Optional[float] = None

    def compute_wt(self, ltp: float) -> float:
        """Compute W&T line from a reference price."""
        if self.is_percentage:
            return ltp * (1 + self.wt_value / 100.0)
        return ltp + self.wt_value

    def update(self, ltp: float) -> tuple[float, bool]:
        """
        Update trailing W&T.
        Returns: (wt_price, executed)
        """
        # First tick – initialize
        if self.wt_price is None:
            self.wt_price = self.compute_wt(ltp)
            self.max_ltp = ltp
            self.min_ltp = ltp
            return self.wt_price, False

        if self.direction == "BUY":
            # Update max LTP seen + trail upward
            if self.max_ltp is None or ltp > self.max_ltp:
                self.max_ltp = ltp
                self.wt_price = self.compute_wt(self.max_ltp)

            executed = ltp <= self.wt_price
            return self.wt_price, executed

        # SELL: update min LTP seen + trail downward
        if self.min_ltp is None or ltp < self.min_ltp:
            self.min_ltp = ltp
            self.wt_price = self.compute_wt(self.min_ltp)

        executed = ltp >= self.wt_price
        return self.wt_price, executed
