"""
Strategy Manager
Manages multiple strategies running simultaneously
"""

import logging
from typing import Dict, List, Optional, Tuple
from threading import Lock
from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

# Import system log service for UI logging
try:
    from ..gui.system_log_service import system_log_service
except ImportError:
    system_log_service = None


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
    
    def process_alert(self, alert: Dict) -> Dict[str, Optional[str]]:
        """
        Process MT5 alert and trigger matching strategies
        
        Args:
            alert: Alert dictionary with keys: symbol, action, price, timeframe, etc.
            
        Returns:
            Dictionary mapping strategy name to signal ('BUY', 'SELL', or None)
        """
        signals = {}
        alert_symbol = alert.get('symbol', '').upper()
        alert_action = alert.get('action', '').upper()
        alert_timeframe = alert.get('timeframe')
        alert_price = alert.get('price', 0.0)
        
        if not alert_symbol or alert_action not in ['BUY', 'SELL']:
            logger.warning(f"StrategyManager: Invalid alert format: {alert}")
            return signals
        
        logger.info(f"StrategyManager: Processing alert - {alert_action} {alert_symbol} @ {alert_price:.5f} (TF: {alert_timeframe})")
        
        # Log to system logs
        if system_log_service:
            system_log_service.log(
                log_type="ALERTS",
                message=f"Processing alert: {alert_action} {alert_symbol} @ {alert_price:.5f} (TF: {alert_timeframe})",
                strategy=""
            )
        
        with self.lock:
            for name, strategy in self.strategies.items():
                if not strategy.enabled:
                    logger.debug(f"StrategyManager: Strategy {name} skipped (disabled)")
                    continue
                
                # Check if strategy matches alert
                match_result, match_reason = self._alert_matches_strategy(alert, strategy)
                if not match_result:
                    logger.debug(f"StrategyManager: Strategy {name} does not match alert - {match_reason}")
                    continue
                
                # Check if strategy is alert-driven
                if hasattr(strategy, 'alert_driven') and strategy.alert_driven:
                    # Trigger strategy from alert
                    if hasattr(strategy, 'trigger_from_alert'):
                        signal = strategy.trigger_from_alert(alert_action, alert_price)
                        if signal:
                            signals[name] = signal
                            logger.info(f"StrategyManager: Strategy {name} triggered {signal} signal from alert")
                            # Log to system logs
                            if system_log_service:
                                system_log_service.log(
                                    log_type="ALERTS",
                                    message=f"Strategy {name} triggered {signal} signal from alert",
                                    strategy=name
                                )
                        else:
                            logger.debug(f"StrategyManager: Strategy {name} trigger_from_alert returned None")
                            # Log to system logs why signal was not generated
                            if system_log_service:
                                system_log_service.log(
                                    log_type="ALERTS",
                                    message=f"Strategy {name} did not generate signal from alert (direction mismatch or duplicate)",
                                    strategy=name
                                )
                    else:
                        logger.warning(f"StrategyManager: Strategy {name} is alert-driven but missing trigger_from_alert method")
                else:
                    logger.debug(f"StrategyManager: Strategy {name} is not alert-driven (alert_driven={getattr(strategy, 'alert_driven', False)})")
        
        return signals
    
    def _alert_matches_strategy(self, alert: Dict, strategy: BaseStrategy) -> Tuple[bool, str]:
        """
        Check if alert matches strategy criteria
        
        Args:
            alert: Alert dictionary
            strategy: Strategy to check
            
        Returns:
            Tuple of (bool, reason_string) - True if matches, False with reason if not
        """
        # Symbol must match
        alert_symbol = alert.get('symbol', '').upper()
        strategy_symbol = strategy.symbol.upper()
        if alert_symbol != strategy_symbol:
            return (False, f"symbol mismatch: alert={alert_symbol}, strategy={strategy_symbol}")
        
        # Timeframe must match (if strategy has timeframe)
        if hasattr(strategy, 'timeframe'):
            alert_timeframe = alert.get('timeframe')
            strategy_timeframe = strategy.timeframe
            if alert_timeframe and strategy_timeframe and alert_timeframe != strategy_timeframe:
                return (False, f"timeframe mismatch: alert={alert_timeframe}, strategy={strategy_timeframe}")
        
        # Action must match strategy direction
        alert_action = alert.get('action', '').upper()
        trade_direction = getattr(strategy, 'trade_direction', 'both')
        
        if trade_direction == 'long' and alert_action != 'BUY':
            return (False, f"direction mismatch: alert={alert_action}, strategy direction=long (needs BUY)")
        if trade_direction == 'short' and alert_action != 'SELL':
            return (False, f"direction mismatch: alert={alert_action}, strategy direction=short (needs SELL)")
        
        return (True, "match")
    
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
    
    def reload_strategy(self, name: str, mt5_connector=None) -> bool:
        """
        Reload a strategy from JSON file to ensure in-memory object matches disk
        
        Args:
            name: Strategy name to reload
            mt5_connector: Optional MT5 connector to pass to strategy
            
        Returns:
            True if reloaded successfully, False otherwise
        """
        from .strategy_persistence import StrategyPersistence
        from pathlib import Path
        
        persistence = StrategyPersistence()
        strategy_file = persistence.strategies_dir / f"{name}.json"
        
        if not strategy_file.exists():
            logger.warning(f"Cannot reload strategy {name}: JSON file not found at {strategy_file}")
            return False
        
        try:
            strategy = persistence.load_strategy(str(strategy_file))
            if not strategy:
                logger.error(f"Failed to load strategy {name} from {strategy_file}")
                return False
            
            # Set MT5 connector if provided
            if mt5_connector and hasattr(strategy, 'set_mt5_connector'):
                strategy.set_mt5_connector(mt5_connector)
            
            # Preserve enabled state and other runtime state
            with self.lock:
                old_strategy = self.strategies.get(name)
                if old_strategy:
                    strategy.enabled = old_strategy.enabled
                    # Preserve market data panel reference if it exists
                    if hasattr(old_strategy, 'market_data_panel'):
                        strategy.market_data_panel = old_strategy.market_data_panel
                    if hasattr(old_strategy, 'set_market_data_panel') and hasattr(old_strategy, 'market_data_panel'):
                        strategy.set_market_data_panel(old_strategy.market_data_panel)
                
                self.strategies[name] = strategy
                logger.info(f"Reloaded strategy {name} from JSON (sl_value={getattr(strategy, 'sl_value', 'N/A')}, "
                           f"sl_type={getattr(strategy, 'sl_type', 'N/A')})")
                return True
        except Exception as e:
            logger.error(f"Error reloading strategy {name}: {e}", exc_info=True)
            return False
    
    def reload_all_strategies(self, mt5_connector=None) -> int:
        """
        Reload all strategies from JSON files
        
        Args:
            mt5_connector: Optional MT5 connector to pass to strategies
            
        Returns:
            Number of strategies successfully reloaded
        """
        reloaded_count = 0
        with self.lock:
            strategy_names = list(self.strategies.keys())
        
        for name in strategy_names:
            if self.reload_strategy(name, mt5_connector=mt5_connector):
                reloaded_count += 1
        
        logger.info(f"Reloaded {reloaded_count} out of {len(strategy_names)} strategies from JSON")
        return reloaded_count

