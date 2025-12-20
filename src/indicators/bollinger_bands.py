"""
Bollinger Bands Indicator
"""

from typing import List, Dict
import numpy as np
from .base_indicator import BaseIndicator
from .sma import SMA


class BollingerBands(BaseIndicator):
    """Bollinger Bands"""
    
    def __init__(self, period: int = 20, num_std: float = 2.0):
        super().__init__("BollingerBands", period)
        self.num_std = num_std
        self.upper_band: List[float] = []
        self.lower_band: List[float] = []
        self.middle_band: List[float] = []
    
    def calculate(self, data: List[Dict]) -> List[float]:
        """Calculate Bollinger Bands (returns middle band/SMA)"""
        if len(data) < self.period:
            return []
        
        closes = self._get_close_prices(data)
        
        # Calculate SMA (middle band)
        sma = SMA(self.period)
        middle_band = sma.calculate(data)
        
        # Calculate standard deviation and bands
        upper_band = []
        lower_band = []
        
        for i in range(self.period - 1, len(closes)):
            period_data = closes[i - self.period + 1:i + 1]
            std = np.std(period_data)
            sma_value = middle_band[i]
            
            if sma_value is not None:
                upper_band.append(sma_value + (self.num_std * std))
                lower_band.append(sma_value - (self.num_std * std))
            else:
                upper_band.append(None)
                lower_band.append(None)
        
        # Pad beginning
        upper_band = [None] * (self.period - 1) + upper_band
        lower_band = [None] * (self.period - 1) + lower_band
        
        self.upper_band = upper_band
        self.lower_band = lower_band
        self.middle_band = middle_band
        
        return middle_band
    
    def get_upper_band(self) -> List[float]:
        """Get upper band values"""
        return self.upper_band
    
    def get_lower_band(self) -> List[float]:
        """Get lower band values"""
        return self.lower_band
    
    def get_middle_band(self) -> List[float]:
        """Get middle band (SMA) values"""
        return self.middle_band

