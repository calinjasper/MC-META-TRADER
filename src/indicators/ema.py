"""
Exponential Moving Average (EMA) Indicator
"""

from typing import List, Dict
import numpy as np
from .base_indicator import BaseIndicator


class EMA(BaseIndicator):
    """Exponential Moving Average"""
    
    def __init__(self, period: int = 14):
        super().__init__("EMA", period)
        self.multiplier = 2.0 / (period + 1.0)
    
    def calculate(self, data: List[Dict]) -> List[float]:
        """Calculate EMA values"""
        if len(data) < self.period:
            return []
        
        closes = self._get_close_prices(data)
        ema_values = []
        
        # Start with SMA
        sma = np.mean(closes[:self.period])
        ema_values.append(float(sma))
        
        # Calculate EMA for remaining values
        for i in range(self.period, len(closes)):
            ema = (closes[i] - ema_values[-1]) * self.multiplier + ema_values[-1]
            ema_values.append(float(ema))
        
        # Pad beginning with None values
        return [None] * (self.period - 1) + ema_values

