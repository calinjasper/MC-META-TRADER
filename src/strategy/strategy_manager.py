"""
Strategy Manager
Manages multiple strategies running simultaneously
"""

import logging
from typing import Dict, List, Optional
from threading import Lock
from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class StrategyManager:
    """Manages multiple trading strategies"""
    
    def __init__(self, position_tracker=None):
        self.strategies: Dict[str, BaseStrategy] = {}  # name -> strategy
        self.lock = Lock()
        self.position_tracker = position_tracker  # Optional position tracker for position checks
    
    def add_strategy(self, strategy: BaseStrategy) -> bool:
        """Add a strategy to the manager"""
        with self.lock:
            if strategy.name in self.strategies:
                logger.warning(f"Strategy {strategy.name} already exists")
                return False
            
            self.strategies[strategy.name] = strategy
            logger.info(f"Added strategy: {strategy.name}")
            return True
    
    def remove_strategy(self, name: str) -> bool:
        """Remove a strategy from the manager"""
        with self.lock:
            if name not in self.strategies:
                logger.warning(f"Strategy {name} not found")
                return False
            
            strategy = self.strategies[name]
            strategy.disable()
            del self.strategies[name]
            logger.info(f"Removed strategy: {name}")
            return True
    
    def get_strategy(self, name: str) -> Optional[BaseStrategy]:
        """Get a strategy by name"""
        with self.lock:
            return self.strategies.get(name)
    
    def get_all_strategies(self) -> List[BaseStrategy]:
        """Get all strategies"""
        with self.lock:
            return list(self.strategies.values())
    
    def get_enabled_strategies(self) -> List[BaseStrategy]:
        """Get all enabled strategies"""
        with self.lock:
            return [s for s in self.strategies.values() if s.enabled]
    
    def enable_strategy(self, name: str) -> bool:
        """Enable a strategy"""
        with self.lock:
            strategy = self.strategies.get(name)
            if strategy:
                strategy.enable()
                return True
            return False
    
    def disable_strategy(self, name: str) -> bool:
        """Disable a strategy"""
        with self.lock:
            strategy = self.strategies.get(name)
            if strategy:
                strategy.disable()
                return True
            return False
    
    def update_strategies(self, market_data: Dict) -> Dict[str, Optional[str]]:
        """
        Update all enabled strategies with market data
        
        Args:
            market_data: Dictionary with market data (symbol -> data dict)
            
        Returns:
            Dictionary mapping strategy name to signal ('BUY', 'SELL', or None)
        """
        signals = {}
        
        with self.lock:
            for name, strategy in self.strategies.items():
                if not strategy.enabled:
                    continue
                
                symbol = strategy.symbol
                # Find matching symbol in market_data (case-insensitive)
                matching_symbol = None
                for market_symbol in market_data.keys():
                    if market_symbol.upper() == symbol.upper():
                        matching_symbol = market_symbol
                        break
                
                if matching_symbol:
                    # Check if strategy already has position in same direction - skip condition check entirely
                    # We need to check for both BUY and SELL potential signals
                    # Since we don't know the signal yet, we'll check after generation but this prevents unnecessary checks
                    # Actually, we can't check before knowing the signal direction, so we'll let it generate and check in main_window
                    logger.debug(f"Strategy {name}: Calling update() with market_data for {matching_symbol}")
                    signal = strategy.update(market_data[matching_symbol])
                    logger.debug(f"Strategy {name}: update() returned signal={signal}")
                    signals[name] = signal
                else:
                    logger.debug(f"Strategy {name}: Symbol {symbol} not found in market_data. Available: {list(market_data.keys())}")
                    signals[name] = None
        
        return signals
    
    def get_strategy_count(self) -> int:
        """Get total number of strategies"""
        with self.lock:
            return len(self.strategies)
    
    def clear(self) -> None:
        """Clear all strategies"""
        with self.lock:
            for strategy in self.strategies.values():
                strategy.disable()
            self.strategies.clear()
            logger.info("All strategies cleared")

