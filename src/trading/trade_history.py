"""
Trade History Tracker
Tracks all trades (open and closed) for orderbook display
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TradeHistory:
    """Tracks all trades for orderbook display"""
    
    def __init__(self, persistence_file: Optional[str] = None):
        """
        Initialize trade history
        
        Args:
            persistence_file: Optional path to JSON file for persistence
        """
        # Store all trades by ticket
        # Structure: {ticket: trade_dict}
        self.trades: Dict[int, Dict] = {}
        self.persistence_file = persistence_file
        
        # Load existing trades from file if it exists
        if self.persistence_file:
            self.load_from_file(self.persistence_file)
            # Clean up trades older than 24 hours
            self.cleanup_old_trades(hours=24)
    
    def add_trade(self, ticket: int, strategy_name: str, symbol: str, 
                  entry_price: float, entry_time: datetime, entry_condition: str,
                  sl: float = 0.0, tp: float = 0.0, volume: float = 0.01,
                  direction: str = 'BUY'):
        """
        Add a new trade to history
        
        Args:
            ticket: Position/order ticket
            strategy_name: Strategy name
            symbol: Trading symbol
            entry_price: Entry price
            entry_time: Entry time
            entry_condition: Entry condition text
            sl: Stop loss price
            tp: Take profit price
            volume: Trade volume
            direction: BUY or SELL
        """
        self.trades[ticket] = {
            'ticket': ticket,
            'strategy_name': strategy_name,
            'symbol': symbol,
            'entry_price': entry_price,
            'entry_time': entry_time,
            'entry_condition': entry_condition,
            'sl': sl,
            'tp': tp,
            'volume': volume,
            'direction': direction,
            'exit_time': None,
            'exit_price': None,
            'exit_reason': None,
            'exit_condition': None,
            'status': 'Open',
            'profit': 0.0
        }
        logger.info(f"Added trade to history: {ticket} - {strategy_name} - {symbol} - {direction}")
        
        # Auto-save to file
        if self.persistence_file:
            self.save_to_file(self.persistence_file)
    
    def close_trade(self, ticket: int, exit_price: float, exit_time: datetime, 
                   exit_condition: str, profit: float = 0.0):
        """
        Close a trade in history
        
        Args:
            ticket: Position/order ticket
            exit_price: Exit price
            exit_time: Exit time
            exit_condition: Exit condition from MT5 (SL/TP/Manual/etc)
            profit: Trade profit
        """
        if ticket in self.trades:
            self.trades[ticket]['exit_price'] = exit_price
            self.trades[ticket]['exit_time'] = exit_time
            self.trades[ticket]['exit_condition'] = exit_condition
            self.trades[ticket]['exit_reason'] = exit_condition  # Also set exit_reason for backward compatibility
            self.trades[ticket]['status'] = 'Closed'
            self.trades[ticket]['profit'] = profit
            logger.info(f"Closed trade in history: {ticket} - Exit Condition: {exit_condition}, Exit Price: {exit_price}, Exit Time: {exit_time}")
            
            # Auto-save to file
            if self.persistence_file:
                self.save_to_file(self.persistence_file)
        else:
            logger.warning(f"Attempted to close trade {ticket} that doesn't exist in history")
    
    def update_trade_profit(self, ticket: int, profit: float):
        """Update profit for an open trade"""
        if ticket in self.trades and self.trades[ticket]['status'] == 'Open':
            self.trades[ticket]['profit'] = profit
    
    def get_all_trades(self) -> List[Dict]:
        """Get all trades (open and closed)"""
        return list(self.trades.values())
    
    def get_open_trades(self) -> List[Dict]:
        """Get only open trades"""
        return [t for t in self.trades.values() if t['status'] == 'Open']
    
    def get_closed_trades(self) -> List[Dict]:
        """Get only closed trades"""
        return [t for t in self.trades.values() if t['status'] == 'Closed']
    
    def get_trade(self, ticket: int) -> Optional[Dict]:
        """Get a specific trade by ticket"""
        return self.trades.get(ticket)
    
    def clear(self):
        """Clear all trade history"""
        self.trades.clear()
        logger.info("Cleared trade history")
        # Save empty state to file
        if self.persistence_file:
            self.save_to_file(self.persistence_file)
    
    def save_to_file(self, file_path: str):
        """
        Save trade history to JSON file
        
        Args:
            file_path: Path to JSON file
        """
        try:
            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert datetime objects to ISO format strings for JSON serialization
            trades_data = []
            for trade in self.trades.values():
                trade_copy = trade.copy()
                # Convert datetime objects to strings
                if isinstance(trade_copy.get('entry_time'), datetime):
                    trade_copy['entry_time'] = trade_copy['entry_time'].isoformat()
                if isinstance(trade_copy.get('exit_time'), datetime):
                    trade_copy['exit_time'] = trade_copy['exit_time'].isoformat()
                trades_data.append(trade_copy)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(trades_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Saved {len(trades_data)} trades to {file_path}")
        except Exception as e:
            logger.error(f"Error saving trade history to {file_path}: {e}", exc_info=True)
    
    def load_from_file(self, file_path: str):
        """
        Load trade history from JSON file
        
        Args:
            file_path: Path to JSON file
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.info(f"Trade history file {file_path} does not exist, starting fresh")
                return
            
            with open(file_path, 'r', encoding='utf-8') as f:
                trades_data = json.load(f)
            
            # Convert ISO format strings back to datetime objects
            for trade_data in trades_data:
                ticket = trade_data.get('ticket')
                if not ticket:
                    continue
                
                # Convert string dates back to datetime
                if isinstance(trade_data.get('entry_time'), str):
                    try:
                        trade_data['entry_time'] = datetime.fromisoformat(trade_data['entry_time'])
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse entry_time for trade {ticket}")
                        trade_data['entry_time'] = datetime.now()
                
                if isinstance(trade_data.get('exit_time'), str) and trade_data.get('exit_time'):
                    try:
                        trade_data['exit_time'] = datetime.fromisoformat(trade_data['exit_time'])
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse exit_time for trade {ticket}")
                        trade_data['exit_time'] = None
                
                self.trades[ticket] = trade_data
            
            logger.info(f"Loaded {len(self.trades)} trades from {file_path}")
        except Exception as e:
            logger.error(f"Error loading trade history from {file_path}: {e}", exc_info=True)
    
    def cleanup_old_trades(self, hours: int = 24):
        """
        Remove trades older than specified hours
        
        Args:
            hours: Number of hours to keep (default: 24)
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        trades_to_remove = []
        
        for ticket, trade in self.trades.items():
            entry_time = trade.get('entry_time')
            if isinstance(entry_time, datetime) and entry_time < cutoff_time:
                trades_to_remove.append(ticket)
        
        for ticket in trades_to_remove:
            del self.trades[ticket]
        
        if trades_to_remove:
            logger.info(f"Cleaned up {len(trades_to_remove)} trades older than {hours} hours")
            # Save after cleanup
            if self.persistence_file:
                self.save_to_file(self.persistence_file)

