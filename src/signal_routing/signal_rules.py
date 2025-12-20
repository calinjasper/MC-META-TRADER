"""
Signal Rules Processing
Handles signal rules like Cancel Previous, Stop & Reverse
"""

import logging
from typing import Dict, Optional, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SignalRules:
    """Process signal rules and apply them"""
    
    def __init__(self):
        self.cancel_previous_enabled = True  # Default: cancel previous open signal
        self.stop_reverse_enabled = False  # Default: disabled
        self.open_signals: Dict[str, Dict] = {}  # Track open signals by symbol
        self.signal_history: List[Dict] = []  # Track all signals
    
    def process_signal(self, signal: Dict[str, Any], current_positions: List[Dict]) -> Dict[str, Any]:
        """
        Process signal according to rules
        
        Args:
            signal: Incoming signal
            current_positions: List of current open positions
            
        Returns:
            Processed signal with rules applied
        """
        symbol = signal.get('symbol')
        action = signal.get('action')
        
        # Track signal
        self.signal_history.append({
            'time': datetime.now(),
            'signal': signal.copy(),
            'original_action': action
        })
        
        # Apply Cancel Previous Open Signal rule
        if self.cancel_previous_enabled:
            signal = self._apply_cancel_previous(signal, current_positions)
        
        # Apply Stop & Reverse rule
        if self.stop_reverse_enabled:
            signal = self._apply_stop_reverse(signal, current_positions)
        
        # Update open signals tracking
        if action in ['BUY', 'SELL']:
            self.open_signals[symbol] = signal.copy()
        elif action in ['EXIT', 'CLOSE']:
            if symbol in self.open_signals:
                del self.open_signals[symbol]
        
        return signal
    
    def _apply_cancel_previous(self, signal: Dict[str, Any], positions: List[Dict]) -> Dict[str, Any]:
        """
        Cancel Previous Open Signal rule:
        - If there's an open position for the symbol, close it before opening new one
        """
        symbol = signal.get('symbol')
        action = signal.get('action')
        
        # Only apply to BUY/SELL signals
        if action not in ['BUY', 'SELL']:
            return signal
        
        # Find open positions for this symbol
        symbol_positions = [p for p in positions if p.get('symbol', '').upper() == symbol.upper()]
        
        if symbol_positions:
            logger.info(f"Cancel Previous: Found {len(symbol_positions)} open position(s) for {symbol}, will close before {action}")
            # Mark signal to close existing positions first
            signal['close_existing'] = True
            signal['existing_positions'] = symbol_positions
        
        return signal
    
    def _apply_stop_reverse(self, signal: Dict[str, Any], positions: List[Dict]) -> Dict[str, Any]:
        """
        Stop & Reverse rule:
        - If there's an open position in opposite direction, close it and reverse
        """
        symbol = signal.get('symbol')
        action = signal.get('action')
        
        # Only apply to BUY/SELL signals
        if action not in ['BUY', 'SELL']:
            return signal
        
        # Find open positions for this symbol
        symbol_positions = [p for p in positions if p.get('symbol', '').upper() == symbol.upper()]
        
        if not symbol_positions:
            return signal
        
        # Check if any position is in opposite direction
        opposite_positions = []
        for pos in symbol_positions:
            pos_type = pos.get('type', 0)  # 0 = BUY, 1 = SELL
            if action == 'BUY' and pos_type == 1:  # Have SELL, want BUY
                opposite_positions.append(pos)
            elif action == 'SELL' and pos_type == 0:  # Have BUY, want SELL
                opposite_positions.append(pos)
        
        if opposite_positions:
            logger.info(f"Stop & Reverse: Found {len(opposite_positions)} opposite position(s) for {symbol}, will reverse")
            signal['stop_reverse'] = True
            signal['reverse_positions'] = opposite_positions
        
        return signal
    
    def get_open_signal(self, symbol: str) -> Optional[Dict]:
        """Get current open signal for a symbol"""
        return self.open_signals.get(symbol.upper())
    
    def clear_open_signal(self, symbol: str) -> None:
        """Clear open signal for a symbol"""
        if symbol.upper() in self.open_signals:
            del self.open_signals[symbol.upper()]
    
    def get_signal_history(self, limit: int = 100) -> List[Dict]:
        """Get recent signal history"""
        return self.signal_history[-limit:] if limit > 0 else self.signal_history

