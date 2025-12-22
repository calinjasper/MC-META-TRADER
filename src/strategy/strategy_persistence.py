"""
Strategy Persistence
Save and load strategies to/from disk
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import time

from .base_strategy import BaseStrategy
from ..indicators import SMA, EMA, RSI, MACD, BollingerBands, Stochastic

logger = logging.getLogger(__name__)


class StrategyPersistence:
    """Handles saving and loading strategies to/from disk"""
    
    def __init__(self, strategies_dir: str = None):
        if strategies_dir is None:
            project_root = Path(__file__).parent.parent.parent
            strategies_dir = project_root / "strategies"
        
        self.strategies_dir = Path(strategies_dir)
        self.strategies_dir.mkdir(parents=True, exist_ok=True)
    
    def save_strategy(self, strategy: BaseStrategy) -> bool:
        """Save a strategy to disk"""
        try:
            strategy_dict = self._strategy_to_dict(strategy)
            file_path = self.strategies_dir / f"{strategy.name}.json"
            
            with open(file_path, 'w') as f:
                json.dump(strategy_dict, f, indent=2)
            
            logger.info(f"Saved strategy '{strategy.name}' to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving strategy '{strategy.name}': {e}")
            return False
    
    def load_strategy(self, file_path: str) -> Optional[BaseStrategy]:
        """Load a strategy from disk"""
        try:
            with open(file_path, 'r') as f:
                strategy_dict = json.load(f)
            
            strategy = self._dict_to_strategy(strategy_dict)
            logger.info(f"Loaded strategy '{strategy.name}' from {file_path}")
            return strategy
        except Exception as e:
            logger.error(f"Error loading strategy from {file_path}: {e}")
            return None
    
    def load_all_strategies(self) -> List[BaseStrategy]:
        """Load all strategies from the strategies directory"""
        strategies = []
        
        for file_path in self.strategies_dir.glob("*.json"):
            strategy = self.load_strategy(str(file_path))
            if strategy:
                strategies.append(strategy)
        
        logger.info(f"Loaded {len(strategies)} strategies from disk")
        return strategies
    
    def delete_strategy(self, strategy_name: str) -> bool:
        """Delete a strategy file from disk"""
        try:
            file_path = self.strategies_dir / f"{strategy_name}.json"
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted strategy file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting strategy '{strategy_name}': {e}")
            return False
    
    def _strategy_to_dict(self, strategy: BaseStrategy) -> Dict:
        """Convert strategy to dictionary for serialization"""
        # Get base dict
        strategy_dict = strategy.to_dict()
        
        # Add additional info for custom strategies
        if hasattr(strategy, 'builder'):
            # This is a CustomStrategy - save its configuration
            strategy_dict['type'] = 'CustomStrategy'
            strategy_dict['indicators_config'] = {}
            strategy_dict['entry_conditions'] = []
            
            # Save indicator configurations
            for ind_name, indicator in strategy.indicators.items():
                if hasattr(indicator, 'period'):
                    strategy_dict['indicators_config'][ind_name] = {
                        'type': type(indicator).__name__,
                        'period': indicator.period
                    }
                elif hasattr(indicator, 'fast_period'):  # MACD
                    strategy_dict['indicators_config'][ind_name] = {
                        'type': type(indicator).__name__,
                        'fast_period': indicator.fast_period,
                        'slow_period': indicator.slow_period,
                        'signal_period': indicator.signal_period
                    }
            
            # Save entry condition texts for recreation
            if hasattr(strategy, 'entry_conditions_text'):
                strategy_dict['entry_conditions_text'] = strategy.entry_conditions_text
            else:
                strategy_dict['entry_conditions_text'] = []

            # Save buy/sell condition texts if present
            if hasattr(strategy, 'buy_conditions_text'):
                strategy_dict['buy_conditions_text'] = getattr(strategy, 'buy_conditions_text', [])
            if hasattr(strategy, 'sell_conditions_text'):
                strategy_dict['sell_conditions_text'] = getattr(strategy, 'sell_conditions_text', [])
            
            # Save trade monitoring mode
            strategy_dict['trade_monitoring_mode'] = getattr(strategy, 'trade_monitoring_mode', 'LTP')
            
            # Save SL/TP configuration
            strategy_dict['sl_type'] = getattr(strategy, 'sl_type', None)
            strategy_dict['sl_value'] = getattr(strategy, 'sl_value', 20.0)
            strategy_dict['use_ratio'] = getattr(strategy, 'use_ratio', True)
            strategy_dict['tp_value'] = getattr(strategy, 'tp_value', 40.0)
            
            # Advanced Risk Management
            strategy_dict['enable_trailing_sl'] = getattr(strategy, 'enable_trailing_sl', False)
            strategy_dict['trailing_sl_gap'] = getattr(strategy, 'trailing_sl_gap', 0.0)
            strategy_dict['enable_profit_lock'] = getattr(strategy, 'enable_profit_lock', False)
            strategy_dict['profit_lock_trigger'] = getattr(strategy, 'profit_lock_trigger', 0.0)
            strategy_dict['profit_lock_value'] = getattr(strategy, 'profit_lock_value', 0.0)
            strategy_dict['profit_trail_step'] = getattr(strategy, 'profit_trail_step', 0.0)
            strategy_dict['profit_trail_amount'] = getattr(strategy, 'profit_trail_amount', 0.0)

            # Trail Wait & Trade (W&T)
            strategy_dict['enable_wt'] = getattr(strategy, 'enable_wt', False)
            strategy_dict['wt_value'] = getattr(strategy, 'wt_value', 0.0)
            strategy_dict['wt_is_percentage'] = getattr(strategy, 'wt_is_percentage', False)
            
            # Position Preservation
            strategy_dict['preserve_position'] = getattr(strategy, 'preserve_position', False)
            
            # Save timeframe
            if hasattr(strategy, 'timeframe'):
                strategy_dict['timeframe'] = strategy.timeframe
        
        return strategy_dict
    
    def _dict_to_strategy(self, strategy_dict: Dict) -> Optional[BaseStrategy]:
        """Convert dictionary to strategy object"""
        from .base_strategy import BaseStrategy as Base
        from ..gui.strategy_builder import CustomStrategy
        
        name = strategy_dict.get('name')
        symbol = strategy_dict.get('symbol')
        enabled = strategy_dict.get('enabled', False)
        
        if not name or not symbol:
            return None
        
        # Create strategy based on type
        if strategy_dict.get('strategy_type') == 'ohlc_price':
            # Create OHLCPriceStrategy instance
            from .ohlc_price_strategy import OHLCPriceStrategy, OHLCPriceCondition
            strategy = OHLCPriceStrategy.from_dict(strategy_dict, market_data_panel=None)
            strategy.enabled = enabled
            return strategy
        elif strategy_dict.get('strategy_type') == 'vwap':
            # Create VWAPStrategy instance
            from .vwap_strategy import VWAPStrategy, VWAPCondition
            # Get MT5 connector from context if available
            mt5_connector = strategy_dict.get('_mt5_connector')  # Passed separately
            strategy = VWAPStrategy.from_dict(strategy_dict, mt5_connector=mt5_connector)
            strategy.enabled = enabled
            return strategy
        elif strategy_dict.get('strategy_type') == 'smc':
            # Create SMCStrategy instance
            from .smc_strategy import SMCStrategy
            mt5_connector = strategy_dict.get('_mt5_connector')  # Passed separately (optional)
            strategy = SMCStrategy.from_dict(strategy_dict, mt5_connector=mt5_connector)
            strategy.enabled = enabled
            return strategy
        elif strategy_dict.get('strategy_type') == 'ema':
            # Create EMAStrategy instance
            from .ema_strategy import EMAStrategy
            mt5_connector = strategy_dict.get('_mt5_connector')  # Passed separately (optional)
            strategy = EMAStrategy.from_dict(strategy_dict, mt5_connector=mt5_connector)
            strategy.enabled = enabled
            return strategy
        elif strategy_dict.get('strategy_type') == 'supertrend':
            # Create SuperTrendStrategy instance
            from .supertrend_strategy import SuperTrendStrategy
            mt5_connector = strategy_dict.get('_mt5_connector')  # Passed separately (optional)
            strategy = SuperTrendStrategy.from_dict(strategy_dict, mt5_connector=mt5_connector)
            strategy.enabled = enabled
            return strategy
        elif strategy_dict.get('type') == 'CustomStrategy':
            # Create a CustomStrategy instance
            from ..gui.strategy_builder import CustomStrategy
            import MetaTrader5 as mt5
            timeframe = strategy_dict.get('timeframe', mt5.TIMEFRAME_M1)  # Default to M1
            strategy = CustomStrategy(name, symbol, builder=None, timeframe=timeframe)
            strategy.enabled = enabled
            
            # Recreate indicators
            indicators_config = strategy_dict.get('indicators_config', {})
            for ind_name, ind_config in indicators_config.items():
                ind_type = ind_config.get('type')
                if ind_type == 'SMA':
                    period = ind_config.get('period', 14)
                    strategy.add_indicator(ind_name, SMA(period))
                elif ind_type == 'EMA':
                    period = ind_config.get('period', 14)
                    strategy.add_indicator(ind_name, EMA(period))
                elif ind_type == 'RSI':
                    period = ind_config.get('period', 14)
                    strategy.add_indicator(ind_name, RSI(period))
                elif ind_type == 'MACD':
                    fast = ind_config.get('fast_period', 12)
                    slow = ind_config.get('slow_period', 26)
                    signal = ind_config.get('signal_period', 9)
                    strategy.add_indicator(ind_name, MACD(fast, slow, signal))
            
            # Recreate time rules
            time_rules = strategy_dict.get('time_rules', [])
            for rule in time_rules:
                start_time = time.fromisoformat(rule['start_time'])
                end_time = time.fromisoformat(rule['end_time'])
                days = rule.get('days')
                strategy.add_time_rule(start_time, end_time, days)
            
            # Recreate entry conditions from saved text
            entry_conditions_text = strategy_dict.get('entry_conditions_text', [])
            strategy.entry_conditions_text = entry_conditions_text
            
            logger.info(f"Loading strategy {name}: {len(entry_conditions_text)} entry conditions")

            # Restore buy/sell text
            strategy.buy_conditions_text = strategy_dict.get('buy_conditions_text', [])
            strategy.sell_conditions_text = strategy_dict.get('sell_conditions_text', [])
            
            # Load trade monitoring mode
            strategy.trade_monitoring_mode = strategy_dict.get('trade_monitoring_mode', 'LTP')
            
            # Load SL/TP configuration
            strategy.sl_type = strategy_dict.get('sl_type', None)
            strategy.sl_value = strategy_dict.get('sl_value', 20.0)
            strategy.use_ratio = strategy_dict.get('use_ratio', True)
            strategy.tp_value = strategy_dict.get('tp_value', 40.0)
            
            # Advanced Risk Management (with defaults for backward compatibility)
            strategy.enable_trailing_sl = strategy_dict.get('enable_trailing_sl', False)
            strategy.trailing_sl_gap = strategy_dict.get('trailing_sl_gap', 0.0)
            strategy.enable_profit_lock = strategy_dict.get('enable_profit_lock', False)
            strategy.profit_lock_trigger = strategy_dict.get('profit_lock_trigger', 0.0)
            strategy.profit_lock_value = strategy_dict.get('profit_lock_value', 0.0)
            strategy.profit_trail_step = strategy_dict.get('profit_trail_step', 0.0)
            strategy.profit_trail_amount = strategy_dict.get('profit_trail_amount', 0.0)

            # Trail Wait & Trade (W&T)
            strategy.enable_wt = strategy_dict.get('enable_wt', False)
            strategy.wt_value = strategy_dict.get('wt_value', 0.0)
            strategy.wt_is_percentage = strategy_dict.get('wt_is_percentage', False)
            
            # Position Preservation
            strategy.preserve_position = strategy_dict.get('preserve_position', False)
            
            # Load Re-Entry configuration
            strategy.reentry_on_sl_enabled = strategy_dict.get('reentry_on_sl_enabled', False)
            strategy.reentry_on_sl_mode = strategy_dict.get('reentry_on_sl_mode', None)
            strategy.reentry_on_sl_count = strategy_dict.get('reentry_on_sl_count', 0)
            strategy.reentry_on_sl_used = 0  # Reset on load
            strategy.reentry_on_tp_enabled = strategy_dict.get('reentry_on_tp_enabled', False)
            strategy.reentry_on_tp_mode = strategy_dict.get('reentry_on_tp_mode', None)
            strategy.reentry_on_tp_count = strategy_dict.get('reentry_on_tp_count', 0)
            strategy.reentry_on_tp_used = 0  # Reset on load
            
            # Recreate entry condition functions
            for i, condition_text in enumerate(entry_conditions_text):
                logger.debug(f"Parsing condition {i+1}: {condition_text}")
                condition_func = self._parse_condition_text(condition_text)
                if condition_func:
                    strategy.add_entry_condition(condition_func)
                    logger.info(f"Successfully added condition {i+1}: {condition_text}")
                else:
                    logger.error(f"Failed to parse condition {i+1}: {condition_text}")
            
            # Recreate buy/sell condition functions
            def create_side_condition(condition_text: str, signal: str):
                try:
                    operators = ['>=', '<=', '==', '>', '<']
                    operator = None
                    operator_pos = -1
                    for op in operators:
                        pos = condition_text.find(op)
                        if pos >= 0:
                            operator = op
                            operator_pos = pos
                            break
                    if operator is None:
                        return None
                    indicator_part = condition_text[:operator_pos].strip()
                    value_str = condition_text[operator_pos + len(operator):].strip()
                    value = float(value_str)

                    def condition(data: Dict):
                        indicators = data.get('indicators', {})
                        indicator_value = indicators.get(indicator_part)
                        if indicator_value is None:
                            return None
                        if operator == '>':
                            ok = indicator_value > value
                        elif operator == '<':
                            ok = indicator_value < value
                        elif operator == '>=':
                            ok = indicator_value >= value
                        elif operator == '<=':
                            ok = indicator_value <= value
                        elif operator == '==':
                            ok = abs(indicator_value - value) < 0.0001
                        else:
                            ok = False
                        return signal if ok else None

                    return condition
                except Exception as e:
                    logger.error(f"Error parsing side condition '{condition_text}': {e}")
                    return None

            strategy.buy_condition_funcs = []
            for ctext in strategy.buy_conditions_text:
                cond = create_side_condition(ctext, "BUY")
                if cond:
                    strategy.buy_condition_funcs.append(cond)

            strategy.sell_condition_funcs = []
            for ctext in strategy.sell_conditions_text:
                cond = create_side_condition(ctext, "SELL")
                if cond:
                    strategy.sell_condition_funcs.append(cond)

            logger.info(f"Strategy {name} loaded with {len(strategy.entry_conditions)} entry conditions")
            
            return strategy
        
        return None
    
    def _parse_condition_text(self, condition_text: str):
        """Parse condition text and create evaluable condition function"""
        try:
            if "->" not in condition_text:
                logger.warning(f"Condition missing '->': {condition_text}")
                return None
            
            condition_part, signal_part = condition_text.split("->", 1)
            signal = signal_part.strip().upper()
            
            if signal not in ['BUY', 'SELL']:
                logger.warning(f"Invalid signal '{signal}' in condition: {condition_text}")
                return None
            
            condition_part = condition_part.strip()
            operators = ['>=', '<=', '==', '>', '<']
            operator = None
            operator_pos = -1
            
            for op in operators:
                pos = condition_part.find(op)
                if pos >= 0:
                    operator = op
                    operator_pos = pos
                    break
            
            if operator is None:
                logger.warning(f"No operator found in condition: {condition_text}")
                return None
            
            indicator_part = condition_part[:operator_pos].strip()
            value_str = condition_part[operator_pos + len(operator):].strip()
            
            try:
                value = float(value_str)
            except ValueError:
                logger.warning(f"Invalid value '{value_str}' in condition: {condition_text}")
                return None
            
            indicator_name = indicator_part
            if '(' in indicator_part:
                indicator_name = indicator_part.split('(')[0].strip()
            
            indicator_name_upper = indicator_name.upper()
            
            logger.debug(f"Parsed condition: indicator={indicator_name}, operator={operator}, value={value}, signal={signal}")
            
            def condition(data: Dict):
                import logging
                cond_logger = logging.getLogger(__name__)
                
                indicators = data.get('indicators', {})
                cond_logger.debug(f"Evaluating condition: {indicator_name} {operator} {value} -> {signal}")
                cond_logger.debug(f"Available indicators: {list(indicators.keys())}")
                
                indicator_value = indicators.get(indicator_name)
                
                if indicator_value is None:
                    for key, val in indicators.items():
                        if key.upper() == indicator_name_upper:
                            indicator_value = val
                            cond_logger.debug(f"Found indicator {key} (case-insensitive) = {val}")
                            break
                
                if indicator_value is None:
                    cond_logger.warning(f"Indicator '{indicator_name}' not found in {list(indicators.keys())}")
                    return None
                
                cond_logger.debug(f"Comparing: {indicator_value} {operator} {value}")
                
                result = False
                if operator == '>':
                    result = indicator_value > value
                elif operator == '<':
                    result = indicator_value < value
                elif operator == '>=':
                    result = indicator_value >= value
                elif operator == '<=':
                    result = indicator_value <= value
                elif operator == '==':
                    result = abs(indicator_value - value) < 0.0001
                
                cond_logger.debug(f"Condition result: {result}")
                
                if result:
                    cond_logger.info(f"Condition met! {indicator_name}={indicator_value} {operator} {value} -> {signal}")
                    return signal
                return None
            
            return condition
        except Exception as e:
            logger.error(f"Error parsing condition '{condition_text}': {e}", exc_info=True)
            return None

