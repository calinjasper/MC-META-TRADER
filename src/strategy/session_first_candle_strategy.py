"""
Session First Candle Strategy
Trading strategy based on Session First Candle High/Low lines
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging
import MetaTrader5 as mt5

from .base_strategy import BaseStrategy
from ..indicators.session_first_candle import SessionFirstCandle

logger = logging.getLogger(__name__)


class SessionFirstCandleCondition:
    """Represents a single Session First Candle condition"""
    
    def __init__(
        self,
        price_reference: str,
        operator: str,
        left_field: str = None,
        right_field: str = None,
        connector: str = "OR",
    ):
        """
        Initialize a Session First Candle condition
        
        Args:
            price_reference: "Current Price", "High Line", or "Low Line"
            operator: ">", "<", ">=", "<=", "==", "Crosses Above", "Crosses Under"
            left_field: Left operand field (e.g., "price", "session_high_line", "session_low_line")
            right_field: Right operand field (e.g., "price", "session_high_line", "session_low_line")
            connector: logical connector to next condition ("AND" | "OR")
        """
        self.price_reference = price_reference
        self.operator = operator
        self.left_field = left_field or "price"
        self.right_field = right_field or "session_high_line"
        self.connector = connector or "OR"
        self.previous_state = None  # For cross detection: True if was above, False if was below
    
    def _resolve_operand(self, field: str, current_price: float, ohlc_data: Dict, market_data: Dict = None) -> Optional[float]:
        """
        Resolve operand using unified indicator resolver.
        """
        # Build context for unified resolver
        context = {
            "price": current_price,
            "ohlc": ohlc_data if ohlc_data else {},
        }
        
        # Add market_data context if available
        if market_data:
            context["smc_pivots"] = market_data.get("smc_pivots", {})
            context["vwap"] = market_data.get("vwap")
            context["ema"] = market_data.get("ema")
            context["indicators"] = market_data.get("indicators", {})
            context["session_first_candle"] = market_data.get("session_first_candle", {})
        
        # Try unified resolver first
        from .unified_indicator_resolver import resolve_operand
        result = resolve_operand(field, context)
        if result is not None:
            return result
        
        return None
    
    def evaluate(self, current_price: float, ohlc_data: Dict, previous_price: Optional[float] = None, market_data: Dict = None) -> bool:
        """
        Evaluate the condition
        
        Args:
            current_price: Current market price
            ohlc_data: Dictionary with 'open', 'high', 'low', 'close' keys
            previous_price: Previous price for cross detection
            market_data: Full market data dict for unified indicator resolution
        """
        left_val = self._resolve_operand(self.left_field, current_price, ohlc_data, market_data)
        right_val = self._resolve_operand(self.right_field, current_price, ohlc_data, market_data)
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
            'left_field': self.left_field,
            'right_field': self.right_field,
            'connector': self.connector
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionFirstCandleCondition':
        """Create condition from dictionary"""
        return cls(
            price_reference=data.get('price_reference', 'Current Price'),
            operator=data.get('operator', '>'),
            left_field=data.get('left_field'),
            right_field=data.get('right_field'),
            connector=data.get('connector', data.get('logical_connector', 'OR'))
        )


class SessionFirstCandleStrategy(BaseStrategy):
    """Trading strategy based on Session First Candle High/Low lines"""
    
    def __init__(
        self,
        name: str,
        symbol: str,
        timeframe: int = None,
        session1_start_hour: int = 0,
        session1_end_hour: int = 9,
        session2_start_hour: int = 8,
        session2_end_hour: int = 17,
        session3_start_hour: int = 13,
        session3_end_hour: int = 22,
    ):
        """
        Initialize Session First Candle strategy
        
        Args:
            name: Strategy name
            symbol: Trading symbol
            timeframe: MT5 timeframe (default: M1)
            session1_start_hour: Session 1 start hour (0-23)
            session1_end_hour: Session 1 end hour (0-23)
            session2_start_hour: Session 2 start hour (-1 to disable)
            session2_end_hour: Session 2 end hour (0-23)
            session3_start_hour: Session 3 start hour (-1 to disable)
            session3_end_hour: Session 3 end hour (0-23)
        """
        super().__init__(name, symbol)
        self.timeframe = timeframe or mt5.TIMEFRAME_M1
        
        # Session configuration
        self.session1_start_hour = session1_start_hour
        self.session1_end_hour = session1_end_hour
        self.session2_start_hour = session2_start_hour
        self.session2_end_hour = session2_end_hour
        self.session3_start_hour = session3_start_hour
        self.session3_end_hour = session3_end_hour
        
        # Initialize Session First Candle indicator
        self.session_first_candle = SessionFirstCandle(
            session1_start_hour=session1_start_hour,
            session1_end_hour=session1_end_hour,
            session2_start_hour=session2_start_hour,
            session2_end_hour=session2_end_hour,
            session3_start_hour=session3_start_hour,
            session3_end_hour=session3_end_hour,
        )
        self.add_indicator("SessionFirstCandle", self.session_first_candle)
        
        # Buy and sell conditions
        self.buy_conditions: List[SessionFirstCandleCondition] = []
        self.sell_conditions: List[SessionFirstCandleCondition] = []
        
        # Track previous price for cross detection
        self.previous_price: Optional[float] = None
        
        self.mt5_connector = None
    
    def set_mt5_connector(self, mt5_connector):
        """Set MT5 connector for data access"""
        self.mt5_connector = mt5_connector
    
    def add_buy_condition(self, condition: SessionFirstCandleCondition) -> None:
        """Add a buy condition"""
        if len(self.sell_conditions) > 0:
            logger.warning(f"Strategy {self.name} already has sell conditions. For separate buy/sell legs, strategies should have only buy OR only sell conditions.")
        self.buy_conditions.append(condition)
        logger.info(f"Added buy condition to {self.name}: {condition.operator} {condition.left_field} vs {condition.right_field}")
    
    def add_sell_condition(self, condition: SessionFirstCandleCondition) -> None:
        """Add a sell condition"""
        if len(self.buy_conditions) > 0:
            logger.warning(f"Strategy {self.name} already has buy conditions. For separate buy/sell legs, strategies should have only buy OR only sell conditions.")
        self.sell_conditions.append(condition)
        logger.info(f"Added sell condition to {self.name}: {condition.operator} {condition.left_field} vs {condition.right_field}")
    
    def remove_buy_condition(self, index: int) -> None:
        """Remove a buy condition by index"""
        if 0 <= index < len(self.buy_conditions):
            self.buy_conditions.pop(index)
    
    def remove_sell_condition(self, index: int) -> None:
        """Remove a sell condition by index"""
        if 0 <= index < len(self.sell_conditions):
            self.sell_conditions.pop(index)
    
    def _evaluate_condition_chain(self, conditions: List[SessionFirstCandleCondition], current_price: float, ohlc_data: Dict, market_data: Dict = None) -> bool:
        """Evaluate conditions honoring AND/OR connectors."""
        if not conditions:
            return False
        cumulative = None
        prev_connector = None
        for cond in conditions:
            result = cond.evaluate(current_price, ohlc_data, self.previous_price, market_data)
            if cumulative is None:
                cumulative = result
            else:
                if prev_connector == "AND":
                    cumulative = cumulative and result
                else:  # OR
                    cumulative = cumulative or result
            prev_connector = cond.connector
        return cumulative
    
    def generate_signal(self, market_data: Dict) -> Optional[str]:
        """
        Generate trading signal based on conditions
        
        Args:
            market_data: Dictionary containing price data, indicators, etc.
            
        Returns:
            "BUY", "SELL", or None
        """
        if not self.enabled:
            return None
        
        # Get symbol data
        symbol_data = market_data.get(self.symbol.upper())
        if not symbol_data:
            # Try case-insensitive match
            for key in market_data.keys():
                if key.upper() == self.symbol.upper():
                    symbol_data = market_data[key]
                    break
        
        if not symbol_data:
            logger.warning(f"Strategy {self.name}: No data for symbol {self.symbol}")
            return None
        
        # Get current price
        current_price = symbol_data.get('close')
        if current_price is None:
            current_price = symbol_data.get('price')
        if current_price is None:
            logger.warning(f"Strategy {self.name}: No price data for {self.symbol}")
            return None
        
        # Get OHLC data
        ohlc_data = {
            'open': symbol_data.get('open'),
            'high': symbol_data.get('high'),
            'low': symbol_data.get('low'),
            'close': current_price,
        }
        
        # Update Session First Candle indicator
        if self.mt5_connector and self.mt5_connector.is_connected():
            try:
                # Get rates for indicator calculation
                rates = self.mt5_connector.get_rates(self.symbol, self.timeframe, 500)
                if rates:
                    # Convert to list of dicts
                    rates_list = []
                    for i in range(len(rates)):
                        rates_list.append({
                            'time': datetime.fromtimestamp(rates[i][0]),
                            'open': rates[i][1],
                            'high': rates[i][2],
                            'low': rates[i][3],
                            'close': rates[i][4],
                            'tick_volume': rates[i][5],
                        })
                    
                    # Update indicator
                    self.session_first_candle.update(rates_list)
                    
                    # Get session high/low values
                    session_high = self.session_first_candle.get_session_high()
                    session_low = self.session_first_candle.get_session_low()
                    active_session = self.session_first_candle.get_current_session()
                    
                    # Add to market_data for condition evaluation
                    if 'session_first_candle' not in market_data:
                        market_data['session_first_candle'] = {}
                    market_data['session_first_candle'] = {
                        'session_high': session_high,
                        'session_low': session_low,
                        'active_session': active_session,
                    }
            except Exception as e:
                logger.error(f"Error updating Session First Candle indicator: {e}", exc_info=True)
        
        # Evaluate buy conditions
        if self.buy_conditions:
            buy_result = self._evaluate_condition_chain(self.buy_conditions, current_price, ohlc_data, market_data)
            if buy_result:
                self.previous_price = current_price
                return "BUY"
        
        # Evaluate sell conditions
        if self.sell_conditions:
            sell_result = self._evaluate_condition_chain(self.sell_conditions, current_price, ohlc_data, market_data)
            if sell_result:
                self.previous_price = current_price
                return "SELL"
        
        self.previous_price = current_price
        return None
    
    def to_dict(self) -> Dict:
        """Convert strategy to dictionary for serialization"""
        strategy_dict = {
            'name': self.name,
            'symbol': self.symbol,
            'strategy_type': 'session_first_candle',
            'timeframe': self.timeframe,
            'enabled': self.enabled,
            'session1_start_hour': self.session1_start_hour,
            'session1_end_hour': self.session1_end_hour,
            'session2_start_hour': self.session2_start_hour,
            'session2_end_hour': self.session2_end_hour,
            'session3_start_hour': self.session3_start_hour,
            'session3_end_hour': self.session3_end_hour,
            'buy_conditions': [cond.to_dict() for cond in self.buy_conditions],
            'sell_conditions': [cond.to_dict() for cond in self.sell_conditions],
        }
        return strategy_dict
    
    @classmethod
    def from_dict(cls, data: Dict, mt5_connector=None) -> 'SessionFirstCandleStrategy':
        """Create strategy from dictionary"""
        strategy = cls(
            name=data['name'],
            symbol=data['symbol'],
            timeframe=data.get('timeframe'),
            session1_start_hour=data.get('session1_start_hour', 0),
            session1_end_hour=data.get('session1_end_hour', 9),
            session2_start_hour=data.get('session2_start_hour', 8),
            session2_end_hour=data.get('session2_end_hour', 17),
            session3_start_hour=data.get('session3_start_hour', 13),
            session3_end_hour=data.get('session3_end_hour', 22),
        )
        strategy.enabled = data.get('enabled', False)
        strategy.set_mt5_connector(mt5_connector)
        
        # Load conditions
        for cond_data in data.get('buy_conditions', []):
            condition = SessionFirstCandleCondition.from_dict(cond_data)
            strategy.add_buy_condition(condition)
        
        for cond_data in data.get('sell_conditions', []):
            condition = SessionFirstCandleCondition.from_dict(cond_data)
            strategy.add_sell_condition(condition)
        
        return strategy
