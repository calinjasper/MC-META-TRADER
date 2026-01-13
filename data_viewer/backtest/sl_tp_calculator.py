"""
SL/TP Calculator
Calculates stop loss and take profit prices based on strategy configuration
"""

import logging
from typing import Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class SLTPCalculator:
    """Calculates SL and TP prices based on strategy configuration"""
    
    def __init__(self):
        """Initialize SL/TP calculator"""
        pass
    
    def calculate_sl_tp(
        self,
        strategy: Any,
        symbol: str,
        entry_price: float,
        signal: str,
        symbol_info: Optional[Dict] = None
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate stop loss and take profit prices from strategy configuration
        
        Args:
            strategy: Strategy instance with SL/TP configuration
            symbol: Trading symbol
            entry_price: Entry price for the position
            signal: 'BUY' or 'SELL'
            symbol_info: Optional symbol info dict with 'point' and 'digits' keys
            
        Returns:
            Tuple of (sl_price, tp_price). Either can be None if disabled.
        """
        # Check if strategy has SL/TP configuration
        if not hasattr(strategy, 'sl_type') or strategy.sl_type is None:
            # No SL/TP configuration - return None
            logger.debug(f"Strategy {strategy.name} has no SL/TP configuration")
            return None, None
        
        # Check if SL/TP are enabled
        sl_enabled = getattr(strategy, 'sl_enabled', True)
        tp_enabled = getattr(strategy, 'tp_enabled', True)
        
        if not sl_enabled and not tp_enabled:
            return None, None
        
        # Get symbol info for point/pip calculations
        if symbol_info is None:
            symbol_info = self._get_default_symbol_info(symbol)
        
        point = symbol_info.get('point', 0.0001)
        digits = symbol_info.get('digits', 5)
        
        # Calculate SL
        sl_price = None
        if sl_enabled:
            sl_price = self._calculate_sl(
                strategy, entry_price, signal, point, digits
            )
        
        # Calculate TP
        tp_price = None
        if tp_enabled:
            tp_price = self._calculate_tp(
                strategy, entry_price, signal, point, digits, sl_price
            )
        
        return sl_price, tp_price
    
    def _calculate_sl(
        self,
        strategy: Any,
        entry_price: float,
        signal: str,
        point: float,
        digits: int
    ) -> Optional[float]:
        """Calculate stop loss price"""
        sl_value = getattr(strategy, 'sl_value', 20.0)
        sl_type = strategy.sl_type
        
        if "Pips" in sl_type:
            # Convert pips to price points (1 pip = 10 points for 5-digit, 1 point for 4-digit)
            pip_size = point * (10 if digits == 5 else 1)
            sl_distance = sl_value * pip_size
        elif "Points" in sl_type:
            # Direct points
            sl_distance = sl_value * point
        else:  # Percentage
            # Percentage-based
            sl_distance = entry_price * (sl_value / 100.0)
        
        # Calculate SL price
        if signal == 'BUY':
            sl_price = entry_price - sl_distance
        else:  # SELL
            sl_price = entry_price + sl_distance
        
        return sl_price
    
    def _calculate_tp(
        self,
        strategy: Any,
        entry_price: float,
        signal: str,
        point: float,
        digits: int,
        sl_price: Optional[float]
    ) -> Optional[float]:
        """Calculate take profit price"""
        use_ratio = getattr(strategy, 'use_ratio', True)
        tp_value = getattr(strategy, 'tp_value', 40.0)
        
        if use_ratio and sl_price is not None:
            # Use 1:2 ratio (TP = 2x SL distance)
            if signal == 'BUY':
                sl_distance = entry_price - sl_price
            else:  # SELL
                sl_distance = sl_price - entry_price
            
            tp_distance = sl_distance * 2.0
            
            if signal == 'BUY':
                tp_price = entry_price + tp_distance
            else:  # SELL
                tp_price = entry_price - tp_distance
        else:
            # Use fixed TP value
            sl_type = getattr(strategy, 'sl_type', 'Price (Pips)')
            
            if "Pips" in sl_type:
                pip_size = point * (10 if digits == 5 else 1)
                tp_distance = tp_value * pip_size
            elif "Points" in sl_type:
                tp_distance = tp_value * point
            else:  # Percentage
                tp_distance = entry_price * (tp_value / 100.0)
            
            if signal == 'BUY':
                tp_price = entry_price + tp_distance
            else:  # SELL
                tp_price = entry_price - tp_distance
        
        return tp_price
    
    def _get_default_symbol_info(self, symbol: str) -> Dict:
        """
        Get default symbol info when not provided
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with default point and digits values
        """
        # Default values for common forex pairs
        # Most forex pairs use 5 digits (0.00001) or 4 digits (0.0001)
        return {
            'point': 0.0001,
            'digits': 5
        }

