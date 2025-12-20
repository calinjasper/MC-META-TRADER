"""
Re-Entry Manager
Handles re-entry logic after SL or TP is hit
Based on AlgoTest architecture
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ReEntryMode(Enum):
    """Re-entry modes"""
    RE_ASAP = "RE_ASAP"  # Immediate re-entry
    RE_ASAP_REVERSE = "RE_ASAP_REVERSE"  # Immediate reverse re-entry
    RE_COST = "RE_COST"  # Re-entry at original entry price
    RE_COST_REVERSE = "RE_COST_REVERSE"  # Reverse re-entry at original entry price


class ReEntryManager:
    """
    Manages re-entry logic for strategies
    
    Based on AlgoTest documentation:
    - RE-ASAP: Re-enter immediately after SL/TP hit
    - RE-ASAP Reverse: Re-enter immediately in reverse position
    - RE-COST: Re-enter at original entry price
    - RE-COST Reverse: Re-enter in reverse at original entry price
    """
    
    def __init__(self):
        # Track closed positions with their entry details for RE-COST mode
        self.closed_positions: Dict[int, Dict] = {}  # ticket -> position details
        
    def record_closed_position(self, position: Dict, entry_price: float, 
                              entry_type: str, entry_symbol: str):
        """
        Record a closed position for potential RE-COST re-entry
        
        Args:
            position: Closed position dictionary
            entry_price: Original entry price
            entry_type: Original entry type ("BUY" or "SELL")
            entry_symbol: Trading symbol
        """
        ticket = position.get('ticket')
        if ticket:
            self.closed_positions[ticket] = {
                'entry_price': entry_price,
                'entry_type': entry_type,
                'entry_symbol': entry_symbol,
                'closed_time': datetime.now(),
                'closed_price': position.get('price_current', entry_price),
                'action': position.get('action', 'SL')  # 'SL' or 'TP'
            }
            logger.debug(f"Recorded closed position {ticket} for RE-COST tracking")
    
    def should_reenter(self, strategy, action: str) -> Tuple[bool, Optional[str]]:
        """
        Check if strategy should re-enter after SL/TP hit
        
        Args:
            strategy: Strategy object
            action: 'SL' or 'TP'
            
        Returns:
            Tuple of (should_reenter, reentry_mode)
        """
        if action == 'SL':
            if not getattr(strategy, 'reentry_on_sl_enabled', False):
                return False, None
            if getattr(strategy, 'reentry_on_sl_used', 0) >= getattr(strategy, 'reentry_on_sl_count', 0):
                logger.debug(f"Strategy {strategy.name}: Max SL re-entries reached")
                return False, None
            mode = getattr(strategy, 'reentry_on_sl_mode', None)
            return True, mode
        
        elif action == 'TP':
            if not getattr(strategy, 'reentry_on_tp_enabled', False):
                return False, None
            if getattr(strategy, 'reentry_on_tp_used', 0) >= getattr(strategy, 'reentry_on_tp_count', 0):
                logger.debug(f"Strategy {strategy.name}: Max TP re-entries reached")
                return False, None
            mode = getattr(strategy, 'reentry_on_tp_mode', None)
            return True, mode
        
        return False, None
    
    def get_reentry_signal(self, strategy, action: str, current_price: float) -> Optional[str]:
        """
        Get re-entry signal based on mode
        
        Args:
            strategy: Strategy object
            action: 'SL' or 'TP'
            current_price: Current market price
            
        Returns:
            'BUY', 'SELL', or None
        """
        should_reenter, mode = self.should_reenter(strategy, action)
        if not should_reenter or not mode:
            return None
        
        original_type = getattr(strategy, 'original_entry_type', None)
        if not original_type:
            # Use last signal if original entry type not set
            original_type = strategy.last_signal
        
        if not original_type:
            logger.warning(f"Strategy {strategy.name}: Cannot determine re-entry signal - no original entry type")
            return None
        
        # Determine re-entry signal based on mode
        if mode == "RE_ASAP":
            # Re-enter with same direction
            return original_type
        
        elif mode == "RE_ASAP_REVERSE":
            # Re-enter in reverse direction
            return "SELL" if original_type == "BUY" else "BUY"
        
        elif mode == "RE_COST":
            # Re-enter at original entry price (same direction)
            original_price = getattr(strategy, 'original_entry_price', None)
            if original_price:
                # Check if price is at or near original entry price
                price_diff = abs(current_price - original_price)
                # Allow small tolerance (0.1% or 10 pips)
                tolerance = max(original_price * 0.001, 0.0001)
                if price_diff <= tolerance:
                    logger.info(f"Strategy {strategy.name}: Price reached original entry {original_price}, re-entering")
                    return original_type
                else:
                    logger.debug(f"Strategy {strategy.name}: Waiting for price {current_price} to reach {original_price} (diff: {price_diff:.5f})")
            return None
        
        elif mode == "RE_COST_REVERSE":
            # Re-enter in reverse at original entry price
            original_price = getattr(strategy, 'original_entry_price', None)
            if original_price:
                price_diff = abs(current_price - original_price)
                tolerance = max(original_price * 0.001, 0.0001)
                if price_diff <= tolerance:
                    reverse_type = "SELL" if original_type == "BUY" else "BUY"
                    logger.info(f"Strategy {strategy.name}: Price reached original entry {original_price}, re-entering in reverse")
                    return reverse_type
                else:
                    logger.debug(f"Strategy {strategy.name}: Waiting for price {current_price} to reach {original_price} for reverse re-entry")
            return None
        
        return None
    
    def increment_reentry_count(self, strategy, action: str):
        """Increment re-entry count for strategy"""
        if action == 'SL':
            current_count = getattr(strategy, 'reentry_on_sl_used', 0)
            strategy.reentry_on_sl_used = current_count + 1
            logger.info(f"Strategy {strategy.name}: SL re-entry count = {strategy.reentry_on_sl_used}/{getattr(strategy, 'reentry_on_sl_count', 0)}")
        elif action == 'TP':
            current_count = getattr(strategy, 'reentry_on_tp_used', 0)
            strategy.reentry_on_tp_used = current_count + 1
            logger.info(f"Strategy {strategy.name}: TP re-entry count = {strategy.reentry_on_tp_used}/{getattr(strategy, 'reentry_on_tp_count', 0)}")
    
    def record_original_entry(self, strategy, entry_price: float, entry_type: str, entry_symbol: str):
        """Record original entry details for RE-COST mode"""
        strategy.original_entry_price = entry_price
        strategy.original_entry_type = entry_type
        strategy.original_entry_symbol = entry_symbol
        logger.debug(f"Strategy {strategy.name}: Recorded original entry - {entry_type} @ {entry_price} for {entry_symbol}")

