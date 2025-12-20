"""
MACD (Moving Average Convergence Divergence) Indicator
"""

from typing import List, Dict, Tuple
import numpy as np
from .base_indicator import BaseIndicator
from .ema import EMA


class MACD(BaseIndicator):
    """MACD Indicator"""
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__("MACD", slow_period)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.macd_line: List[float] = []
        self.signal_line: List[float] = []
        self.histogram: List[float] = []
    
    def calculate(self, data: List[Dict]) -> List[float]:
        """Calculate MACD values (returns MACD line)"""
        if len(data) < self.slow_period + self.signal_period:
            return []
        
        closes = self._get_close_prices(data)
        
        # Calculate fast and slow EMAs
        fast_ema = EMA(self.fast_period)
        slow_ema = EMA(self.slow_period)
        
        fast_values = fast_ema.calculate(data)
        slow_values = slow_ema.calculate(data)
        
        # Calculate MACD line
        macd_line = []
        min_len = min(len(fast_values), len(slow_values))
        
        for i in range(min_len):
            if fast_values[i] is not None and slow_values[i] is not None:
                macd_line.append(fast_values[i] - slow_values[i])
            else:
                macd_line.append(None)
        
        # Calculate signal line (EMA of MACD line)
        # Filter out None values for signal calculation
        valid_macd = [v for v in macd_line if v is not None]
        if len(valid_macd) < self.signal_period:
            return []
        
        # Create data structure for signal EMA
        signal_data = [{'close': v, 'time': data[i].get('time')} 
                      for i, v in enumerate(macd_line) if v is not None]
        
        signal_ema = EMA(self.signal_period)
        signal_values = signal_ema.calculate(signal_data)
        
        # Align signal line with MACD line
        signal_line = [None] * (len(macd_line) - len(signal_values)) + signal_values
        
        # Calculate histogram
        histogram = []
        for i in range(len(macd_line)):
            if macd_line[i] is not None and signal_line[i] is not None:
                histogram.append(macd_line[i] - signal_line[i])
            else:
                histogram.append(None)
        
        self.macd_line = macd_line
        self.signal_line = signal_line
        self.histogram = histogram
        
        return macd_line
    
    def get_signal_line(self) -> List[float]:
        """Get signal line values"""
        return self.signal_line
    
    def get_histogram(self) -> List[float]:
        """Get histogram values"""
        return self.histogram

