"""
OHLC Price Strategy
Trading strategy based on price comparisons with previous session OHLC values
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging

from .base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class OHLCPriceCondition:
    """Represents a single price condition"""
    
    def __init__(
        self,
        price_reference: str,
        operator: str,
        ohlc_field: str = None,
        value: float = None,
        left_field: str = None,
        right_field: str = None,
        connector: str = "OR",
    ):
        """
        Initialize a price condition
        
        Args:
            price_reference: "Current Price" or "Previous OHLC"
            operator: ">", "<", ">=", "<=", "==", "Crosses Above", "Crosses Under"
            ohlc_field: "open", "high", "low", "close" (legacy field)
            value: Comparison value (optional, used for direct comparisons)
            left_field/right_field: operands selected in the UI
            connector: logical connector to next condition ("AND" | "OR")
        """
        self.price_reference = price_reference
        self.operator = operator
        self.ohlc_field = ohlc_field
        self.value = value
        self.left_field = left_field or "price"
        self.right_field = right_field or ohlc_field
        self.connector = connector or "OR"
        self.previous_state = None  # For cross detection: True if was above, False if was below
    
    def _resolve_operand(self, field: str, current_price: float, ohlc_data: Dict) -> Optional[float]:
        if field == "price":
            return current_price
        if not ohlc_data:
            return None
        if field == "open":
            return ohlc_data.get('open')
        if field == "high":
            return ohlc_data.get('high')
        if field == "low":
            return ohlc_data.get('low')
        if field == "close":
            return ohlc_data.get('close')
        if field == "hl2":
            h = ohlc_data.get('high')
            l = ohlc_data.get('low')
            return (h + l) / 2.0 if h is not None and l is not None else None
        if field == "hlc3":
            h = ohlc_data.get('high')
            l = ohlc_data.get('low')
            c = ohlc_data.get('close')
            return (h + l + c) / 3.0 if None not in (h, l, c) else None
        if field == "ohlc4":
            o = ohlc_data.get('open')
            h = ohlc_data.get('high')
            l = ohlc_data.get('low')
            c = ohlc_data.get('close')
            return (o + h + l + c) / 4.0 if None not in (o, h, l, c) else None
        return self.value
    
    def evaluate(self, current_price: float, ohlc_data: Dict, previous_price: Optional[float] = None) -> bool:
        """
        Evaluate the condition
        
        Args:
            current_price: Current market price
            ohlc_data: Dictionary with 'open', 'high', 'low', 'close' keys
            previous_price: Previous price for cross detection
        """
        left_val = self._resolve_operand(self.left_field, current_price, ohlc_data)
        right_val = self._resolve_operand(self.right_field, current_price, ohlc_data)
        if left_val is None or right_val is None:
            return False
        
        # Handle cross detection operators
        if self.operator == "Crosses Above":
            if previous_price is not None:
                was_below = previous_price < right_val
                is_above = left_val >= right_val
                if was_below and is_above:
                    self.previous_state = True
                    return True
            self.previous_state = left_val >= right_val
            return False
        
        if self.operator == "Crosses Under":
            if previous_price is not None:
                was_above = previous_price > right_val
                is_below = left_val <= right_val
                if was_above and is_below:
                    self.previous_state = False
                    return True
            self.previous_state = left_val > right_val
            return False

        if self.operator == "Any_Cross":
            if previous_price is not None:
                crossed_up = previous_price < right_val <= left_val
                crossed_down = previous_price > right_val >= left_val
                if crossed_up or crossed_down:
                    self.previous_state = left_val >= right_val
                    return True
            self.previous_state = left_val >= right_val
            return False
        
        # Handle simple comparison operators
        if self.operator == ">":
            return left_val > right_val
        if self.operator == "<":
            return left_val < right_val
        if self.operator == ">=":
            return left_val >= right_val
        if self.operator == "<=":
            return left_val <= right_val
        if self.operator == "==":
            epsilon = 0.00001
            return abs(left_val - right_val) < epsilon
        
        return False
    
    def to_dict(self) -> Dict:
        """Convert condition to dictionary for serialization"""
        return {
            'price_reference': self.price_reference,
            'operator': self.operator,
            'ohlc_field': self.ohlc_field,
            'value': self.value,
            'left_field': self.left_field,
            'right_field': self.right_field,
            'connector': self.connector
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'OHLCPriceCondition':
        """Create condition from dictionary"""
        return cls(
            price_reference=data.get('price_reference', 'Current Price'),
            operator=data.get('operator', '>'),
            ohlc_field=data.get('ohlc_field'),
            value=data.get('value'),
            left_field=data.get('left_field'),
            right_field=data.get('right_field'),
            connector=data.get('connector', data.get('logical_connector', 'OR'))
        )


class OHLCPriceStrategy(BaseStrategy):
    """Trading strategy based on OHLC price conditions"""
    
    def __init__(self, name: str, symbol: str, session_type: str = 'daily', timeframe: int = None):
        """
        Initialize OHLC price strategy
        
        Args:
            name: Strategy name
            symbol: Trading symbol
            session_type: Session type for OHLC calculation ('daily', 'asian', 'european', 'us')
            timeframe: MT5 timeframe constant
        """
        super().__init__(name, symbol)
        self.session_type = session_type
        self.timeframe = timeframe
        
        # Buy and sell conditions
        self.buy_conditions: List[OHLCPriceCondition] = []
        self.sell_conditions: List[OHLCPriceCondition] = []
        
        # Track previous price for cross detection
        self.previous_price: Optional[float] = None
        
        # Reference to market data panel for OHLC access
        self.market_data_panel = None
    
    def add_buy_condition(self, condition: OHLCPriceCondition) -> None:
        """Add a buy condition"""
        # Validation: If strategy already has sell conditions, warn but allow (for backward compatibility)
        if len(self.sell_conditions) > 0:
            logger.warning(f"Strategy {self.name} already has sell conditions. For separate buy/sell legs, strategies should have only buy OR only sell conditions.")
        self.buy_conditions.append(condition)
        logger.info(f"Added buy condition to {self.name}: {condition.operator} {condition.ohlc_field or condition.value}")
    
    def add_sell_condition(self, condition: OHLCPriceCondition) -> None:
        """Add a sell condition"""
        # Validation: If strategy already has buy conditions, warn but allow (for backward compatibility)
        if len(self.buy_conditions) > 0:
            logger.warning(f"Strategy {self.name} already has buy conditions. For separate buy/sell legs, strategies should have only buy OR only sell conditions.")
        self.sell_conditions.append(condition)
        logger.info(f"Added sell condition to {self.name}: {condition.operator} {condition.ohlc_field or condition.value}")
    
    def remove_buy_condition(self, index: int) -> None:
        """Remove a buy condition by index"""
        if 0 <= index < len(self.buy_conditions):
            self.buy_conditions.pop(index)
    
    def remove_sell_condition(self, index: int) -> None:
        """Remove a sell condition by index"""
        if 0 <= index < len(self.sell_conditions):
            self.sell_conditions.pop(index)
    
    def set_market_data_panel(self, market_data_panel) -> None:
        """Set reference to market data panel for OHLC access"""
        self.market_data_panel = market_data_panel
    
    def get_ohlc_data(self) -> Optional[Dict]:
        """Get OHLC data for this symbol"""
        if not self.market_data_panel:
            logger.warning(f"Strategy {self.name}: No market_data_panel reference set")
            return None
        
        # Get OHLC data from market data panel
        # Try case-insensitive match
        ohlc = None
        symbol_upper = self.symbol.upper()
        for symbol_key in self.market_data_panel.ohlc_data.keys():
            if symbol_key.upper() == symbol_upper:
                ohlc = self.market_data_panel.ohlc_data[symbol_key]
                break
        
        if ohlc is None:
            # Try to fetch if not available
            if hasattr(self.market_data_panel, 'fetch_ohlc_for_symbols'):
                self.market_data_panel.fetch_ohlc_for_symbols([self.symbol])
                # Try again after fetching
                for symbol_key in self.market_data_panel.ohlc_data.keys():
                    if symbol_key.upper() == symbol_upper:
                        ohlc = self.market_data_panel.ohlc_data[symbol_key]
                        break
        
        if ohlc is None:
            logger.warning(f"Strategy {self.name}: No OHLC data available for {self.symbol}. Available symbols: {list(self.market_data_panel.ohlc_data.keys())}")
        
        return ohlc

    def _evaluate_condition_chain(self, conditions: List[OHLCPriceCondition], current_price: float, ohlc_data: Dict) -> bool:
        """Evaluate conditions honoring AND/OR connectors."""
        if not conditions:
            return False
        cumulative = None
        prev_connector = None
        for cond in conditions:
            result = cond.evaluate(current_price, ohlc_data, self.previous_price)
            if cumulative is None:
                cumulative = result
            else:
                connector = prev_connector or "OR"
                if connector == "AND":
                    cumulative = cumulative and result
                else:
                    cumulative = cumulative or result
            prev_connector = cond.connector or "OR"
        return bool(cumulative)
    
    def generate_signal(self, market_data: Dict) -> Optional[str]:
        """
        Generate trading signal based on OHLC price conditions
        
        Args:
            market_data: Dictionary with current market data (must include 'tick' key)
            
        Returns:
            'BUY', 'SELL', or None
            
        Note:
            Signal Priority: BUY conditions are checked first, then SELL conditions.
            If both BUY and SELL conditions are met simultaneously, BUY signal takes priority.
            This is by design - BUY conditions are evaluated first and return immediately if met.
        """
        # Only log at INFO if this is a new call or important state change
        
        # Get current price from tick data
        tick = market_data.get('tick')
        if not tick:
            logger.warning(f"Strategy {self.name}: No tick data in market_data. Keys: {list(market_data.keys())}")
            return None
        
        # Use bid price for current price (or ask, depending on context)
        # For buy conditions, we typically check ask price
        # For sell conditions, we typically check bid price
        # Using mid price for general comparison
        current_price = (tick.get('bid', 0) + tick.get('ask', 0)) / 2.0
        if current_price == 0:
            current_price = tick.get('bid', tick.get('ask', 0))
        
        if current_price == 0:
            logger.warning(f"Strategy {self.name}: Invalid price in tick data")
            return None
        
        # Get OHLC data
        ohlc_data = self.get_ohlc_data()
        if not ohlc_data:
            logger.debug(f"Strategy {self.name}: No OHLC data available for {self.symbol}")
            return None
        
        # Check buy conditions first (OR logic - any condition triggers)
        # NOTE: BUY takes priority over SELL if both conditions are met
        try:
            if self._evaluate_condition_chain(self.buy_conditions, current_price, ohlc_data):
                logger.info(f"Strategy {self.name}: ✅ Buy conditions met")
                self.previous_price = current_price
                return 'BUY'
        except Exception as e:
            logger.error(f"Error evaluating buy conditions in {self.name}: {e}", exc_info=True)
        
        # Check sell conditions second (OR logic - any condition triggers)
        # NOTE: SELL is only returned if no BUY condition was met
        try:
            if self._evaluate_condition_chain(self.sell_conditions, current_price, ohlc_data):
                logger.info(f"Strategy {self.name}: ✅ Sell conditions met")
                self.previous_price = current_price
                return 'SELL'
        except Exception as e:
            logger.error(f"Error evaluating sell conditions in {self.name}: {e}", exc_info=True)
        
        # Update previous price for next cross detection
        self.previous_price = current_price
        
        return None
    
    def to_dict(self) -> Dict:
        """Convert strategy to dictionary for serialization"""
        base_dict = super().to_dict()
        base_dict.update({
            'strategy_type': 'ohlc_price',
            'session_type': self.session_type,
            'timeframe': self.timeframe,
            'buy_conditions': [c.to_dict() for c in self.buy_conditions],
            'sell_conditions': [c.to_dict() for c in self.sell_conditions]
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict, market_data_panel=None) -> 'OHLCPriceStrategy':
        """Create strategy from dictionary"""
        strategy = cls(
            name=data['name'],
            symbol=data['symbol'],
            session_type=data.get('session_type', 'daily'),
            timeframe=data.get('timeframe')
        )
        strategy.enabled = data.get('enabled', False)
        strategy.session_type = data.get('session_type', 'daily')
        strategy.timeframe = data.get('timeframe')
        strategy.market_data_panel = market_data_panel

        # Restore common configuration (backward compatible)
        strategy.trade_monitoring_mode = data.get('trade_monitoring_mode', getattr(strategy, 'trade_monitoring_mode', 'LTP'))
        strategy.lot_size = data.get('lot_size', getattr(strategy, 'lot_size', None))
        strategy.sl_type = data.get('sl_type', getattr(strategy, 'sl_type', None))
        strategy.sl_value = data.get('sl_value', getattr(strategy, 'sl_value', 20.0))
        strategy.use_ratio = data.get('use_ratio', getattr(strategy, 'use_ratio', True))
        strategy.tp_value = data.get('tp_value', getattr(strategy, 'tp_value', 40.0))

        # Advanced Risk Management
        strategy.enable_trailing_sl = data.get('enable_trailing_sl', getattr(strategy, 'enable_trailing_sl', False))
        strategy.trailing_sl_gap = data.get('trailing_sl_gap', getattr(strategy, 'trailing_sl_gap', 0.0))
        strategy.enable_profit_lock = data.get('enable_profit_lock', getattr(strategy, 'enable_profit_lock', False))
        strategy.profit_lock_trigger = data.get('profit_lock_trigger', getattr(strategy, 'profit_lock_trigger', 0.0))
        strategy.profit_lock_value = data.get('profit_lock_value', getattr(strategy, 'profit_lock_value', 0.0))
        strategy.profit_trail_step = data.get('profit_trail_step', getattr(strategy, 'profit_trail_step', 0.0))
        strategy.profit_trail_amount = data.get('profit_trail_amount', getattr(strategy, 'profit_trail_amount', 0.0))

        # Trail Wait & Trade (W&T)
        strategy.enable_wt = data.get('enable_wt', getattr(strategy, 'enable_wt', False))
        strategy.wt_value = data.get('wt_value', getattr(strategy, 'wt_value', 0.0))
        strategy.wt_is_percentage = data.get('wt_is_percentage', getattr(strategy, 'wt_is_percentage', False))

        # Position Preservation
        strategy.preserve_position = data.get('preserve_position', getattr(strategy, 'preserve_position', False))
        
        # Restore buy conditions
        for cond_data in data.get('buy_conditions', []):
            strategy.add_buy_condition(OHLCPriceCondition.from_dict(cond_data))
        
        # Restore sell conditions
        for cond_data in data.get('sell_conditions', []):
            strategy.add_sell_condition(OHLCPriceCondition.from_dict(cond_data))
        
        return strategy

