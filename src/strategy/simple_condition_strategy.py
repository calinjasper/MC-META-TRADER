"""
Simple Condition Strategy
A strategy that evaluates buy/sell conditions directly without strategy-specific logic
"""

from typing import Dict, List, Optional
from datetime import datetime
import logging
import MetaTrader5 as mt5

from .base_strategy import BaseStrategy
from .ohlc_price_strategy import OHLCPriceCondition

logger = logging.getLogger(__name__)


class SimpleConditionStrategy(BaseStrategy):
    """
    Simple strategy that trades based on buy/sell conditions only.
    No strategy-specific indicators or logic - just direct condition evaluation.
    Uses current price and current candle OHLC data.
    """
    
    def __init__(self, name: str, symbol: str, timeframe: Optional[int] = None):
        super().__init__(name, symbol)
        self.timeframe = timeframe or mt5.TIMEFRAME_M1
        self.buy_conditions: List[OHLCPriceCondition] = []
        self.sell_conditions: List[OHLCPriceCondition] = []
        self.previous_price: Optional[float] = None
        self.mt5_connector = None
    
    def set_mt5_connector(self, mt5_connector):
        """Set MT5 connector for data retrieval"""
        self.mt5_connector = mt5_connector
    
    def add_buy_condition(self, condition: OHLCPriceCondition):
        """Add a buy condition"""
        self.buy_conditions.append(condition)
    
    def add_sell_condition(self, condition: OHLCPriceCondition):
        """Add a sell condition"""
        self.sell_conditions.append(condition)
    
    def _get_current_candle(self) -> Optional[Dict]:
        """Get current candle OHLC data"""
        if not self.mt5_connector or not self.mt5_connector.is_connected():
            return None
        
        try:
            rates = self.mt5_connector.get_rates(self.symbol, self.timeframe, 1, 0)
            if rates is not None and len(rates) > 0:
                rate = rates[0]
                return {
                    'open': float(rate['open']),   # OPEN
                    'high': float(rate['high']),   # HIGH
                    'low': float(rate['low']),     # LOW
                    'close': float(rate['close']), # CLOSE
                }
        except Exception as e:
            logger.error(f"Error getting current candle for {self.symbol}: {e}")
        
        return None
    
    def _evaluate_condition_chain(self, conditions: List[OHLCPriceCondition], 
                                  current_price: float, ohlc_data: Dict) -> bool:
        """
        Evaluate a chain of conditions with AND/OR connectors
        
        Args:
            conditions: List of conditions to evaluate
            current_price: Current market price
            ohlc_data: Dictionary with OHLC data
            
        Returns:
            True if conditions are met, False otherwise
        """
        if not conditions:
            return False
        
        cumulative = None
        prev_connector = None
        
        for cond in conditions:
            try:
                result = cond.evaluate(current_price, ohlc_data, self.previous_price)
                
                if cumulative is None:
                    cumulative = result
                else:
                    if prev_connector == "AND":
                        cumulative = cumulative and result
                    else:  # OR
                        cumulative = cumulative or result
                
                prev_connector = cond.connector or "OR"
            except Exception as e:
                logger.error(f"Error evaluating condition in {self.name}: {e}")
                continue
        
        return bool(cumulative)
    
    def generate_signal(self, market_data: Dict) -> Optional[str]:
        """
        Generate signal based on buy/sell conditions only, or direct execution if no conditions.
        Respects time restrictions and other entry conditions from BaseStrategy.
        
        Args:
            market_data: Dictionary with market data
            
        Returns:
            'BUY', 'SELL', or None
        """
        # Check time restrictions first (from BaseStrategy)
        if not self.is_trading_time():
            return None
        
        # Get current price from market data
        tick = market_data.get("tick")
        if not tick:
            return None
        
        current_price = (tick.get("bid", 0) + tick.get("ask", 0)) / 2.0
        if current_price == 0:
            current_price = tick.get("bid", tick.get("ask", 0))
        if current_price == 0:
            return None
        
        # If no conditions are set, execute directly based on trade direction (No Strategy mode)
        # This allows trading with only SL, TP, time restrictions, and risk management settings
        if len(self.buy_conditions) == 0 and len(self.sell_conditions) == 0:
            # Direct execution mode - no conditions to check, only respects:
            # - Time restrictions (already checked above)
            # - Trade direction
            # - SL/TP and risk management (handled by order execution)
            self.previous_price = current_price
            trade_dir = getattr(self, "trade_direction", "both")
            if trade_dir == "long":
                signal = 'BUY'
                logger.info(f"SimpleConditionStrategy {self.name}: Direct execution - BUY (Long-only, No Strategy mode)")
                return signal
            elif trade_dir == "short":
                signal = 'SELL'
                logger.info(f"SimpleConditionStrategy {self.name}: Direct execution - SELL (Short-only, No Strategy mode)")
                return signal
            else:  # both
                signal = 'BUY'
                # Default to BUY for both direction when no conditions
                logger.info(f"SimpleConditionStrategy {self.name}: Direct execution - BUY (Both direction, default, No Strategy mode)")
                return signal
        
        # Get current candle OHLC data for condition evaluation
        ohlc_data = self._get_current_candle()
        if not ohlc_data:
            # Fallback: use current price for all OHLC values
            ohlc_data = {
                'open': current_price,
                'high': current_price,
                'low': current_price,
                'close': current_price,
            }
        
        # Check buy conditions first (BUY takes priority)
        try:
            if self._evaluate_condition_chain(self.buy_conditions, current_price, ohlc_data):
                logger.info(f"SimpleConditionStrategy {self.name}: ✅ Buy conditions met")
                self.previous_price = current_price
                return 'BUY'
        except Exception as e:
            logger.error(f"Error evaluating buy conditions in {self.name}: {e}", exc_info=True)
        
        # Check sell conditions
        try:
            if self._evaluate_condition_chain(self.sell_conditions, current_price, ohlc_data):
                logger.info(f"SimpleConditionStrategy {self.name}: ✅ Sell conditions met")
                self.previous_price = current_price
                return 'SELL'
        except Exception as e:
            logger.error(f"Error evaluating sell conditions in {self.name}: {e}", exc_info=True)
        
        self.previous_price = current_price
        return None
    
    def to_dict(self) -> Dict:
        """Convert strategy to dictionary for serialization"""
        base_dict = super().to_dict()
        base_dict.update({
            'strategy_type': 'simple_condition',
            'timeframe': self.timeframe,
            'buy_conditions': [c.to_dict() for c in self.buy_conditions],
            'sell_conditions': [c.to_dict() for c in self.sell_conditions]
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict, mt5_connector=None) -> 'SimpleConditionStrategy':
        """Create strategy from dictionary"""
        strategy = cls(
            name=data['name'],
            symbol=data['symbol'],
            timeframe=data.get('timeframe', mt5.TIMEFRAME_M1)
        )
        strategy.set_mt5_connector(mt5_connector)
        strategy.enabled = data.get('enabled', False)
        
        # Load buy conditions
        for cond_data in data.get('buy_conditions', []):
            condition = OHLCPriceCondition.from_dict(cond_data)
            strategy.add_buy_condition(condition)
        
        # Load sell conditions
        for cond_data in data.get('sell_conditions', []):
            condition = OHLCPriceCondition.from_dict(cond_data)
            strategy.add_sell_condition(condition)
        
        # Load common configuration
        strategy.trade_monitoring_mode = data.get('trade_monitoring_mode', 'LTP')
        strategy.lot_size = data.get('lot_size', None)
        strategy.sl_type = data.get('sl_type')
        strategy.sl_value = data.get('sl_value', 20.0)
        strategy.tp_value = data.get('tp_value', 40.0)
        strategy.use_ratio = data.get('use_ratio', False)
        strategy.trade_direction = data.get('trade_direction', 'both')
        strategy.preserve_position = data.get('preserve_position', False)
        
        # Advanced Risk Management
        strategy.enable_trailing_sl = data.get('enable_trailing_sl', False)
        strategy.trailing_sl_gap = data.get('trailing_sl_gap', 0.0)
        strategy.enable_profit_lock = data.get('enable_profit_lock', False)
        strategy.profit_lock_trigger = data.get('profit_lock_trigger', 0.0)
        strategy.profit_lock_value = data.get('profit_lock_value', 0.0)
        strategy.profit_trail_step = data.get('profit_trail_step', 0.0)
        strategy.profit_trail_amount = data.get('profit_trail_amount', 0.0)
        
        # Trail Wait & Trade (W&T)
        strategy.enable_wt = data.get('enable_wt', False)
        strategy.wt_value = data.get('wt_value', 0.0)
        strategy.wt_is_percentage = data.get('wt_is_percentage', False)
        
        # Re-Entry configuration
        strategy.reentry_on_sl_enabled = data.get('reentry_on_sl_enabled', False)
        strategy.reentry_on_sl_mode = data.get('reentry_on_sl_mode')
        strategy.reentry_on_sl_count = data.get('reentry_on_sl_count', 0)
        strategy.reentry_on_sl_used = data.get('reentry_on_sl_used', 0)
        strategy.reentry_on_tp_enabled = data.get('reentry_on_tp_enabled', False)
        strategy.reentry_on_tp_mode = data.get('reentry_on_tp_mode')
        strategy.reentry_on_tp_count = data.get('reentry_on_tp_count', 0)
        strategy.reentry_on_tp_used = data.get('reentry_on_tp_used', 0)
        
        # Time rules
        strategy.time_rules = data.get('time_rules', [])
        
        return strategy

