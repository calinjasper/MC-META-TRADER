"""
Base Strategy Class
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, name: str, symbol: str):
        self.name = name
        self.symbol = symbol
        self.enabled = False
        self.indicators: Dict[str, any] = {}
        self.entry_conditions: List[Callable] = []
        self.exit_conditions: List[Callable] = []
        self.time_rules: List[Dict] = []  # List of time-based rules
        self.last_signal = None
        self.signal_history: List[Dict] = []
        self.last_trade_time: Optional[datetime] = None  # Track last trade execution time
        self.trade_cooldown_seconds = 60  # Cooldown between trades (default 60 seconds)
        
        # Trade monitoring mode (AlgoTest architecture)
        self.trade_monitoring_mode: Optional[str] = "LTP"  # "LTP" or "CANDLE_CLOSE"
        
        # SL/TP configuration
        self.sl_type: Optional[str] = None  # "Price (Pips)", "Price (Points)", "Percentage"
        self.sl_value: float = 20.0  # SL value
        self.use_ratio: bool = True  # Use 1:2 ratio
        self.tp_value: float = 40.0  # TP value (or calculated if use_ratio)
        
        # Re-Entry configuration (AlgoTest architecture)
        self.reentry_on_sl_enabled: bool = False
        self.reentry_on_sl_mode: Optional[str] = None  # "RE_ASAP", "RE_ASAP_REVERSE", "RE_COST", "RE_COST_REVERSE"
        self.reentry_on_sl_count: int = 0  # Max re-entries (0-20)
        self.reentry_on_sl_used: int = 0  # Track how many re-entries have been used
        
        self.reentry_on_tp_enabled: bool = False
        self.reentry_on_tp_mode: Optional[str] = None
        self.reentry_on_tp_count: int = 0
        self.reentry_on_tp_used: int = 0
        
        # Track original entry details for RE-COST mode
        self.original_entry_price: Optional[float] = None
        self.original_entry_type: Optional[str] = None  # "BUY" or "SELL"
        self.original_entry_symbol: Optional[str] = None
        
        # Advanced Risk Management Configuration
        # Trailing Stop-Loss
        self.enable_trailing_sl: bool = False
        self.trailing_sl_gap: float = 0.0  # Gap in price points
        
        # Profit Lock + Trailing
        self.enable_profit_lock: bool = False
        self.profit_lock_trigger: float = 0.0  # Profit amount to trigger lock
        self.profit_lock_value: float = 0.0  # Minimum profit to lock
        self.profit_trail_step: float = 0.0  # Profit increase to trigger trail
        self.profit_trail_amount: float = 0.0  # Amount to trail profit by
        
        # Position Preservation
        self.preserve_position: bool = False  # If True, prevents duplicate positions per strategy per symbol

        # Trail Wait & Trade (W&T)
        # Tracks a dynamic trailing trigger line and closes the position when hit.
        # Note: This is applied at the position-monitoring layer (see TradeMonitor),
        # not inside strategy signal generation.
        self.enable_wt: bool = False
        self.wt_value: float = 0.0  # gap in price points (or % if wt_is_percentage=True)
        self.wt_is_percentage: bool = False

        # Trade direction
        self.trade_direction: str = "both"  # "both" | "long" | "short"
        
        # Lot size for this strategy (None = use default from config)
        self.lot_size: Optional[float] = None
    
    def add_indicator(self, name: str, indicator: any) -> None:
        """Add an indicator to the strategy"""
        self.indicators[name] = indicator
    
    def add_entry_condition(self, condition: Callable) -> None:
        """Add an entry condition function"""
        self.entry_conditions.append(condition)
    
    def add_exit_condition(self, condition: Callable) -> None:
        """Add an exit condition function"""
        self.exit_conditions.append(condition)
    
    def add_time_rule(self, start_time: time, end_time: time, 
                     days: List[int] = None) -> None:
        """
        Add a time-based trading rule
        
        Args:
            start_time: Start time (e.g., time(9, 0) for 9 AM)
            end_time: End time (e.g., time(17, 0) for 5 PM)
            days: List of weekday numbers (0=Monday, 6=Sunday), None for all days
        """
        self.time_rules.append({
            'start_time': start_time,
            'end_time': end_time,
            'days': days
        })
    
    def is_trading_time(self) -> bool:
        """Check if current time is within trading hours"""
        if not self.time_rules:
            return True  # No time restrictions
        
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()
        
        for rule in self.time_rules:
            start = rule['start_time']
            end = rule['end_time']
            days = rule['days']
            
            # Check if current day is allowed
            if days is not None and current_weekday not in days:
                continue
            
            # Check if current time is within range
            if start <= end:  # Same day range
                if start <= current_time <= end:
                    return True
            else:  # Overnight range
                if current_time >= start or current_time <= end:
                    return True
        
        return False
    
    def check_entry_conditions(self, data: Dict) -> Optional[str]:
        """
        Check entry conditions and return signal ('BUY', 'SELL', or None)
        
        Args:
            data: Dictionary with current market data and indicator values
            
        Returns:
            'BUY', 'SELL', or None
        """
        if not self.is_trading_time():
            return None
        
        if not self.entry_conditions:
            return None
        
        # Check all entry conditions (OR logic - any condition can trigger)
        # If multiple conditions, any one that evaluates to BUY/SELL will trigger
        for i, condition in enumerate(self.entry_conditions):
            try:
                result = condition(data)
                if result is None:
                    logger.debug(f"Strategy {self.name}: Condition {i+1} evaluated to None")
                    continue
                elif result in ['BUY', 'SELL']:
                    logger.info(f"Strategy {self.name}: Condition {i+1} triggered {result} signal")
                    return result
            except Exception as e:
                logger.error(f"Error in entry condition {i+1} for {self.name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        return None
    
    def check_exit_conditions(self, position: Dict, data: Dict) -> bool:
        """
        Check exit conditions for a position
        
        Args:
            position: Position dictionary
            data: Dictionary with current market data and indicator values
            
        Returns:
            True if position should be closed
        """
        if not self.exit_conditions:
            return False
        
        # Check all exit conditions (OR logic - any condition can trigger exit)
        for condition in self.exit_conditions:
            try:
                if condition(position, data):
                    return True
            except Exception as e:
                logger.error(f"Error in exit condition: {e}")
        
        return False
    
    def is_buy_only(self) -> bool:
        """
        Check if strategy has only buy conditions (no sell conditions)
        
        Returns:
            True if strategy has buy conditions but no sell conditions
        """
        # Check for strategies with buy_conditions and sell_conditions attributes (OHLC, VWAP)
        if hasattr(self, 'buy_conditions') and hasattr(self, 'sell_conditions'):
            has_buy = len(self.buy_conditions) > 0
            has_sell = len(self.sell_conditions) > 0
            return has_buy and not has_sell
        
        # For other strategy types, check entry_conditions
        # This is a heuristic - strategies that only generate BUY signals
        # Note: This may not be perfect for all strategy types
        return False
    
    def is_sell_only(self) -> bool:
        """
        Check if strategy has only sell conditions (no buy conditions)
        
        Returns:
            True if strategy has sell conditions but no buy conditions
        """
        # Check for strategies with buy_conditions and sell_conditions attributes (OHLC, VWAP)
        if hasattr(self, 'buy_conditions') and hasattr(self, 'sell_conditions'):
            has_buy = len(self.buy_conditions) > 0
            has_sell = len(self.sell_conditions) > 0
            return has_sell and not has_buy
        
        # For other strategy types, check entry_conditions
        # This is a heuristic - strategies that only generate SELL signals
        # Note: This may not be perfect for all strategy types
        return False
    
    def has_both_directions(self) -> bool:
        """
        Check if strategy has both buy and sell conditions
        
        Returns:
            True if strategy has both buy and sell conditions
        """
        # Check for strategies with buy_conditions and sell_conditions attributes (OHLC, VWAP)
        if hasattr(self, 'buy_conditions') and hasattr(self, 'sell_conditions'):
            has_buy = len(self.buy_conditions) > 0
            has_sell = len(self.sell_conditions) > 0
            return has_buy and has_sell
        
        return False
    
    @abstractmethod
    def generate_signal(self, market_data: Dict) -> Optional[str]:
        """
        Generate trading signal based on market data
        
        Args:
            market_data: Dictionary with current prices, indicators, etc.
            
        Returns:
            'BUY', 'SELL', or None
        """
        pass
    
    def update(self, market_data: Dict) -> Optional[str]:
        """
        Update strategy with new market data and generate signal
        
        Args:
            market_data: Dictionary with current market data
            
        Returns:
            'BUY', 'SELL', or None
        """
        if not self.enabled:
            return None
        
        signal = self.generate_signal(market_data)
        
        # Always return signal if condition is met (not just on change)
        # This allows strategies to trigger even if condition was already met
        if signal:
            current_time = datetime.now()
            
            # Log signal change or continuation
            if signal != self.last_signal:
                logger.info(f"Strategy {self.name} generated NEW {signal} signal for {self.symbol} (was {self.last_signal})")
            else:
                logger.debug(f"Strategy {self.name}: Condition still met - {signal} signal")
            
            self.last_signal = signal
            self.signal_history.append({
                'time': current_time,
                'signal': signal,
                'symbol': self.symbol,
                'data': market_data.copy()
            })
        
        return signal
    
    def enable(self) -> None:
        """Enable the strategy"""
        self.enabled = True
        logger.info(f"Strategy {self.name} enabled")
    
    def disable(self) -> None:
        """Disable the strategy"""
        self.enabled = False
        logger.info(f"Strategy {self.name} disabled")
    
    def get_signal_history(self) -> List[Dict]:
        """Get signal history"""
        return self.signal_history.copy()
    
    def to_dict(self) -> Dict:
        """Convert strategy to dictionary for serialization"""
        return {
            'name': self.name,
            'symbol': self.symbol,
            'enabled': self.enabled,
            'indicators': {k: str(type(v).__name__) for k, v in self.indicators.items()},
            'time_rules': [
                {
                    'start_time': str(r['start_time']),
                    'end_time': str(r['end_time']),
                    'days': r['days']
                }
                for r in self.time_rules
            ],

            # Common configuration (persisted for all strategy types)
            'trade_monitoring_mode': getattr(self, 'trade_monitoring_mode', 'LTP'),

            # SL/TP configuration
            'sl_type': getattr(self, 'sl_type', None),
            'sl_value': getattr(self, 'sl_value', 20.0),
            'use_ratio': getattr(self, 'use_ratio', True),
            'tp_value': getattr(self, 'tp_value', 40.0),

            # Advanced Risk Management
            'enable_trailing_sl': getattr(self, 'enable_trailing_sl', False),
            'trailing_sl_gap': getattr(self, 'trailing_sl_gap', 0.0),
            'enable_profit_lock': getattr(self, 'enable_profit_lock', False),
            'profit_lock_trigger': getattr(self, 'profit_lock_trigger', 0.0),
            'profit_lock_value': getattr(self, 'profit_lock_value', 0.0),
            'profit_trail_step': getattr(self, 'profit_trail_step', 0.0),
            'profit_trail_amount': getattr(self, 'profit_trail_amount', 0.0),

            # Trail Wait & Trade (W&T)
            'enable_wt': getattr(self, 'enable_wt', False),
            'wt_value': getattr(self, 'wt_value', 0.0),
            'wt_is_percentage': getattr(self, 'wt_is_percentage', False),

            # Position preservation
            'preserve_position': getattr(self, 'preserve_position', False),

            # Re-Entry configuration
            'reentry_on_sl_enabled': getattr(self, 'reentry_on_sl_enabled', False),
            'reentry_on_sl_mode': getattr(self, 'reentry_on_sl_mode', None),
            'reentry_on_sl_count': getattr(self, 'reentry_on_sl_count', 0),
            'reentry_on_sl_used': getattr(self, 'reentry_on_sl_used', 0),
            'reentry_on_tp_enabled': getattr(self, 'reentry_on_tp_enabled', False),
            'reentry_on_tp_mode': getattr(self, 'reentry_on_tp_mode', None),
            'reentry_on_tp_count': getattr(self, 'reentry_on_tp_count', 0),
            'reentry_on_tp_used': getattr(self, 'reentry_on_tp_used', 0),

            # Trade direction
            'trade_direction': getattr(self, 'trade_direction', 'both'),
            
            # Lot size
            'lot_size': getattr(self, 'lot_size', None),
        }

