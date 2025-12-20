"""
Simple Moving Average (SMA) Indicator
"""

from typing import List, Dict
import numpy as np
from .base_indicator import BaseIndicator


class SMA(BaseIndicator):
    """Simple Moving Average"""
    
    def __init__(self, period: int = 14):
        super().__init__("SMA", period)
    
    def calculate(self, data: List[Dict]) -> List[float]:
        """Calculate SMA values"""
        if len(data) < self.period:
            return []
        
        closes = self._get_close_prices(data)
        sma_values = []
        
        for i in range(self.period - 1, len(closes)):
            sma = np.mean(closes[i - self.period + 1:i + 1])
            sma_values.append(float(sma))
        
        # Pad beginning with None values
        return [None] * (self.period - 1) + sma_values

