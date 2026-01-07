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
        """
        Calculate EMA values matching MT5 EMA indicator logic exactly.
        
        MT5 logic (with series indexing where index 0 = most recent):
        - First EMA value at rates_total - period = SMA of oldest 'period' bars
        - Then calculates backwards from rates_total - period - 1 to 0
        - Formula: buffer[i] = (close[i] - prevEMA) * multiplier + prevEMA
        
        Python equivalent (with forward indexing where index 0 = oldest):
        - First EMA value at index period - 1 = SMA of first 'period' bars
        - Then calculates forward from index period to len(closes) - 1
        - Formula: ema[i] = (closes[i] - prevEMA) * multiplier + prevEMA
        """
        if len(data) < self.period:
            return []
        
        closes = self._get_close_prices(data)
        rates_total = len(closes)
        
        # Initialize result array with None values (equivalent to MT5's EMPTY_VALUE)
        ema_values = [None] * rates_total
        
        # Calculate first EMA value as SMA of first 'period' bars
        # In MT5: buffer[rates_total - period] = SMA of close[rates_total - period] to close[rates_total - 1]
        # In Python: ema_values[period - 1] = SMA of closes[0] to closes[period - 1]
        sum_close = 0.0
        for j in range(self.period):
            sum_close += closes[j]
        first_ema = sum_close / self.period
        ema_values[self.period - 1] = float(first_ema)
        
        # Calculate EMA for remaining values (going forward in time)
        # In MT5: for i from rates_total - period - 1 down to 0
        # In Python: for i from period to rates_total - 1
        for i in range(self.period, rates_total):
            prev_ema = ema_values[i - 1]
            if prev_ema is not None:
                # Exact MT5 formula: buffer[i] = (close[i] - prevEMA) * multiplier + prevEMA
                ema = (closes[i] - prev_ema) * self.multiplier + prev_ema
                ema_values[i] = float(ema)
        
        return ema_values

