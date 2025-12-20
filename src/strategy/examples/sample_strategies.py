"""
Sample Strategy Implementations
"""

from typing import Dict, Optional
from ..base_strategy import BaseStrategy
from ...indicators import RSI, SMA, EMA


class RSIStrategy(BaseStrategy):
    """Simple RSI-based strategy"""
    
    def __init__(self, symbol: str, period: int = 14, 
                 oversold: float = 30.0, overbought: float = 70.0):
        super().__init__(f"RSI_{symbol}", symbol)
        self.oversold = oversold
        self.overbought = overbought
        
        # Add RSI indicator
        rsi = RSI(period)
        self.add_indicator('RSI', rsi)
        
        # Define entry conditions
        def buy_condition(data: Dict) -> Optional[str]:
            rsi_value = data.get('indicators', {}).get('RSI')
            if rsi_value is not None and rsi_value < self.oversold:
                return 'BUY'
            return None
        
        def sell_condition(data: Dict) -> Optional[str]:
            rsi_value = data.get('indicators', {}).get('RSI')
            if rsi_value is not None and rsi_value > self.overbought:
                return 'SELL'
            return None
        
        self.add_entry_condition(buy_condition)
        self.add_entry_condition(sell_condition)
    
    def generate_signal(self, market_data: Dict) -> Optional[str]:
        """Generate signal based on RSI"""
        return self.check_entry_conditions(market_data)


class MovingAverageCrossoverStrategy(BaseStrategy):
    """Moving average crossover strategy"""
    
    def __init__(self, symbol: str, fast_period: int = 10, slow_period: int = 30):
        super().__init__(f"MA_Cross_{symbol}", symbol)
        
        # Add indicators
        fast_ma = EMA(fast_period)
        slow_ma = EMA(slow_period)
        self.add_indicator('FastMA', fast_ma)
        self.add_indicator('SlowMA', slow_ma)
        
        # Define entry conditions
        def buy_condition(data: Dict) -> Optional[str]:
            indicators = data.get('indicators', {})
            fast = indicators.get('FastMA')
            slow = indicators.get('SlowMA')
            
            if fast is not None and slow is not None:
                # Golden cross: fast MA crosses above slow MA
                if fast > slow:
                    # Check previous values to confirm crossover
                    prev_data = data.get('previous_data')
                    if prev_data:
                        prev_fast = prev_data.get('indicators', {}).get('FastMA')
                        prev_slow = prev_data.get('indicators', {}).get('SlowMA')
                        if prev_fast is not None and prev_slow is not None:
                            if prev_fast <= prev_slow:  # Crossover occurred
                                return 'BUY'
            return None
        
        def sell_condition(data: Dict) -> Optional[str]:
            indicators = data.get('indicators', {})
            fast = indicators.get('FastMA')
            slow = indicators.get('SlowMA')
            
            if fast is not None and slow is not None:
                # Death cross: fast MA crosses below slow MA
                if fast < slow:
                    # Check previous values to confirm crossover
                    prev_data = data.get('previous_data')
                    if prev_data:
                        prev_fast = prev_data.get('indicators', {}).get('FastMA')
                        prev_slow = prev_data.get('indicators', {}).get('SlowMA')
                        if prev_fast is not None and prev_slow is not None:
                            if prev_fast >= prev_slow:  # Crossover occurred
                                return 'SELL'
            return None
        
        self.add_entry_condition(buy_condition)
        self.add_entry_condition(sell_condition)
    
    def generate_signal(self, market_data: Dict) -> Optional[str]:
        """Generate signal based on MA crossover"""
        return self.check_entry_conditions(market_data)

