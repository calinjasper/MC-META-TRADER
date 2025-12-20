"""
Stochastic Oscillator Indicator
"""

from typing import List, Dict
import numpy as np
from .base_indicator import BaseIndicator


class Stochastic(BaseIndicator):
    """Stochastic Oscillator (%K and %D)"""
    
    def __init__(self, k_period: int = 14, d_period: int = 3, slowing: int = 3):
        super().__init__("Stochastic", k_period)
        self.k_period = k_period
        self.d_period = d_period
        self.slowing = slowing
        self.percent_k: List[float] = []
        self.percent_d: List[float] = []
    
    def calculate(self, data: List[Dict]) -> List[float]:
        """Calculate Stochastic values (returns %K)"""
        if len(data) < self.k_period + self.slowing:
            return []
        
        highs = self._get_high_prices(data)
        lows = self._get_low_prices(data)
        closes = self._get_close_prices(data)
        
        # Calculate %K
        percent_k = []
        
        for i in range(self.k_period - 1, len(data)):
            period_highs = highs[i - self.k_period + 1:i + 1]
            period_lows = lows[i - self.k_period + 1:i + 1]
            
            highest_high = np.max(period_highs)
            lowest_low = np.min(period_lows)
            
            if highest_high == lowest_low:
                k_value = 50.0  # Neutral value when range is zero
            else:
                k_value = ((closes[i] - lowest_low) / (highest_high - lowest_low)) * 100.0
            
            percent_k.append(float(k_value))
        
        # Apply slowing (SMA of %K)
        if self.slowing > 1:
            smoothed_k = []
            for i in range(self.slowing - 1, len(percent_k)):
                smoothed = np.mean(percent_k[i - self.slowing + 1:i + 1])
                smoothed_k.append(float(smoothed))
            percent_k = [None] * (self.slowing - 1) + smoothed_k
        
        # Pad beginning
        percent_k = [None] * (self.k_period - 1) + percent_k
        
        # Calculate %D (SMA of %K)
        percent_d = []
        for i in range(self.d_period - 1, len(percent_k)):
            if all(v is not None for v in percent_k[i - self.d_period + 1:i + 1]):
                d_value = np.mean([v for v in percent_k[i - self.d_period + 1:i + 1]])
                percent_d.append(float(d_value))
            else:
                percent_d.append(None)
        
        # Pad beginning
        percent_d = [None] * (len(percent_k) - len(percent_d)) + percent_d
        
        self.percent_k = percent_k
        self.percent_d = percent_d
        
        return percent_k
    
    def get_percent_d(self) -> List[float]:
        """Get %D values"""
        return self.percent_d

