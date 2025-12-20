"""
Position Tracker
Tracks open positions per strategy per symbol to prevent duplicate positions
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

from ..gui.system_log_service import system_log_service


class PositionTracker:
    """Tracks positions per strategy per symbol"""
    
    def __init__(self):
        """
        Initialize position tracker
        
        Structure:
        {
            "strategy_name": {
                "symbol": {
                    "BUY": {"ticket": int, "entry_time": datetime, ...},
                    "SELL": {"ticket": int, "entry_time": datetime, ...}
                }
            }
        }
        """
        self.positions: Dict[str, Dict[str, Dict[str, Dict]]] = {}
        # Store closed positions history for orderbook exit reason detection
        self.closed_positions_history: Dict[int, Dict] = {}  # ticket -> position data
    
    def has_position(self, strategy_name: str, symbol: str, direction: str) -> bool:
        """
        Check if strategy has an open position for symbol and direction
        
        Args:
            strategy_name: Name of the strategy
            symbol: Trading symbol
            direction: "BUY" or "SELL"
            
        Returns:
            True if position exists, False otherwise
        """
        if strategy_name not in self.positions:
            return False
        
        if symbol not in self.positions[strategy_name]:
            return False
        
        return direction in self.positions[strategy_name][symbol]
    
    def add_position(self, strategy_name: str, symbol: str, direction: str, ticket: int, 
                    entry_price: float = None, entry_time: datetime = None, volume: float = None,
                    entry_condition: str = None, sl: float = None, tp: float = None):
        """
        Add a position to tracker
        
        Args:
            strategy_name: Name of the strategy
            symbol: Trading symbol
            direction: "BUY" or "SELL"
            ticket: Position ticket number
            entry_price: Entry price (optional)
            entry_time: Entry time (optional, defaults to now)
            volume: Position volume (optional)
            entry_condition: Entry condition text (optional)
            sl: Stop loss price (optional)
            tp: Take profit price (optional)
        """
        if strategy_name not in self.positions:
            self.positions[strategy_name] = {}
        
        if symbol not in self.positions[strategy_name]:
            self.positions[strategy_name][symbol] = {}
        
        self.positions[strategy_name][symbol][direction] = {
            "ticket": ticket,
            "entry_price": entry_price,
            "entry_time": entry_time or datetime.now(),
            "volume": volume,
            "entry_condition": entry_condition,
            "sl": sl,
            "tp": tp
        }
        
        logger.debug(f"Added position to tracker: {strategy_name} - {symbol} - {direction} - Ticket: {ticket}")
        system_log_service.log(
            "TRADING",
            f"Position opened for {symbol} ({direction}) ticket {ticket}",
            strategy=strategy_name,
        )
    
    def remove_position(self, strategy_name: str, symbol: str, direction: str, ticket: int = None):
        """
        Remove a position from tracker
        
        Args:
            strategy_name: Name of the strategy
            symbol: Trading symbol
            direction: "BUY" or "SELL"
            ticket: Position ticket (optional, for verification)
        """
        if strategy_name not in self.positions:
            return
        
        if symbol not in self.positions[strategy_name]:
            return
        
        if direction not in self.positions[strategy_name][symbol]:
            return
        
        # Verify ticket if provided
        if ticket is not None:
            tracked_ticket = self.positions[strategy_name][symbol][direction].get("ticket")
            if tracked_ticket != ticket:
                logger.warning(f"Ticket mismatch when removing position: expected {tracked_ticket}, got {ticket}")
                return
        
        # Store in closed positions history before removing
        pos_data = self.positions[strategy_name][symbol][direction].copy()
        stored_ticket = pos_data.get('ticket')
        if stored_ticket:
            self.closed_positions_history[stored_ticket] = {
                'strategy_name': strategy_name,
                'symbol': symbol,
                'direction': direction,
                **pos_data
            }
            # Keep only last 1000 closed positions to avoid memory issues
            if len(self.closed_positions_history) > 1000:
                # Remove oldest entries
                oldest_tickets = sorted(self.closed_positions_history.keys())[:-1000]
                for old_ticket in oldest_tickets:
                    del self.closed_positions_history[old_ticket]
        
        del self.positions[strategy_name][symbol][direction]
        
        # Clean up empty dictionaries
        if not self.positions[strategy_name][symbol]:
            del self.positions[strategy_name][symbol]
        
        if not self.positions[strategy_name]:
            del self.positions[strategy_name]
        
        logger.debug(f"Removed position from tracker: {strategy_name} - {symbol} - {direction}")
        system_log_service.log(
            "TRADING",
            f"Position closed for {symbol} ({direction})",
            strategy=strategy_name,
        )
    
    def get_closed_position(self, ticket: int) -> Optional[Dict]:
        """
        Get closed position data from history
        
        Args:
            ticket: Position ticket number
            
        Returns:
            Position data dictionary with SL/TP, or None if not found
        """
        return self.closed_positions_history.get(ticket)
    
    def get_positions_for_strategy(self, strategy_name: str, symbol: str = None) -> List[Dict]:
        """
        Get all positions for a strategy (optionally filtered by symbol)
        
        Args:
            strategy_name: Name of the strategy
            symbol: Trading symbol (optional, if None returns all symbols)
            
        Returns:
            List of position dictionaries
        """
        if strategy_name not in self.positions:
            return []
        
        positions = []
        
        if symbol:
            if symbol in self.positions[strategy_name]:
                for direction, pos_data in self.positions[strategy_name][symbol].items():
                    positions.append({
                        "direction": direction,
                        "symbol": symbol,
                        **pos_data
                    })
        else:
            for sym, directions in self.positions[strategy_name].items():
                for direction, pos_data in directions.items():
                    positions.append({
                        "direction": direction,
                        "symbol": sym,
                        **pos_data
                    })
        
        return positions
    
    def sync_with_mt5_positions(self, mt5_positions: List[Dict], strategy_name_from_comment: callable):
        """
        Sync tracker with actual MT5 positions
        
        Args:
            mt5_positions: List of position dictionaries from MT5
            strategy_name_from_comment: Function to extract strategy name from position comment
        """
        # Build set of current MT5 positions
        current_positions = {}
        for pos in mt5_positions:
            comment = pos.get('comment', '')
            strategy_name = strategy_name_from_comment(comment)
            if not strategy_name:
                continue
            
            symbol = pos.get('symbol', '')
            direction = "BUY" if pos.get('type', 0) == 0 else "SELL"
            ticket = pos.get('ticket', 0)
            
            key = (strategy_name, symbol, direction)
            current_positions[key] = {
                "ticket": ticket,
                "entry_price": pos.get('price_open'),
                "entry_time": pos.get('time'),
                "volume": pos.get('volume')
            }
        
        # Update tracker
        for (strategy_name, symbol, direction), pos_data in current_positions.items():
            if not self.has_position(strategy_name, symbol, direction):
                self.add_position(
                    strategy_name, symbol, direction,
                    pos_data["ticket"],
                    pos_data.get("entry_price"),
                    pos_data.get("entry_time"),
                    pos_data.get("volume")
                )
        
        # Remove positions that no longer exist in MT5
        for strategy_name in list(self.positions.keys()):
            for symbol in list(self.positions[strategy_name].keys()):
                for direction in list(self.positions[strategy_name][symbol].keys()):
                    key = (strategy_name, symbol, direction)
                    if key not in current_positions:
                        self.remove_position(strategy_name, symbol, direction)
    
    def get_all_positions_for_symbol(self, symbol: str) -> List[Dict]:
        """
        Get all positions for a symbol across all strategies
        
        Args:
            symbol: Trading symbol
            
        Returns:
            List of position dictionaries with strategy_name, direction, and position data
        """
        positions = []
        for strategy_name, symbols in self.positions.items():
            if symbol in symbols:
                for direction, pos_data in symbols[symbol].items():
                    positions.append({
                        "strategy_name": strategy_name,
                        "direction": direction,
                        "symbol": symbol,
                        **pos_data
                    })
        return positions
    
    def get_positions_by_direction(self, symbol: str, direction: str) -> List[Dict]:
        """
        Get all positions for a symbol with specific direction across all strategies
        
        Args:
            symbol: Trading symbol
            direction: "BUY" or "SELL"
            
        Returns:
            List of position dictionaries with strategy_name and position data
        """
        return [pos for pos in self.get_all_positions_for_symbol(symbol) 
                if pos["direction"] == direction]
    
    def find_position_by_strategy_and_direction(self, symbol: str, strategy_name: str, direction: str) -> Optional[Dict]:
        """
        Find a specific position by strategy, symbol, and direction
        
        Args:
            symbol: Trading symbol
            strategy_name: Name of the strategy
            direction: "BUY" or "SELL"
            
        Returns:
            Position dictionary if found, None otherwise
        """
        if not self.has_position(strategy_name, symbol, direction):
            return None
        
        pos_data = self.positions[strategy_name][symbol][direction].copy()
        return {
            "strategy_name": strategy_name,
            "direction": direction,
            "symbol": symbol,
            **pos_data
        }
    
    def clear(self):
        """Clear all tracked positions"""
        self.positions.clear()
        logger.debug("Position tracker cleared")

