"""
Relative Strength Index (RSI) Indicator
"""

from typing import List, Dict
import numpy as np
from .base_indicator import BaseIndicator


class RSI(BaseIndicator):
    """Relative Strength Index"""
    
    def __init__(self, period: int = 14):
        super().__init__("RSI", period)
    
    def calculate(self, data: List[Dict]) -> List[float]:
        """Calculate RSI values"""
        if len(data) < self.period + 1:
            return []
        
        closes = self._get_close_prices(data)
        
        # Calculate price changes
        deltas = np.diff(closes)
        
        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        rsi_values = []
        
        # Calculate initial average gain and loss
        avg_gain = np.mean(gains[:self.period])
        avg_loss = np.mean(losses[:self.period])
        
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
        
        rsi_values.append(float(rsi))
        
        # Calculate RSI for remaining values using Wilder's smoothing
        for i in range(self.period, len(deltas)):
            avg_gain = (avg_gain * (self.period - 1) + gains[i]) / self.period
            avg_loss = (avg_loss * (self.period - 1) + losses[i]) / self.period
            
            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100.0 - (100.0 / (1.0 + rs))
            
            rsi_values.append(float(rsi))
        
        # Pad beginning with None values
        return [None] * self.period + rsi_values

