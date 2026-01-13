"""
Smoothed Moving Average (SMMA) Indicator
Also known as RMA (Running Moving Average) or Modified Moving Average
"""

from typing import List, Dict, Optional
import numpy as np
from .base_indicator import BaseIndicator


class SMMA(BaseIndicator):
    """Smoothed Moving Average - SMMA/RMA/Modified MA"""
    
    def __init__(self, period: int = 7, source_price: str = "close"):
        """
        Initialize SMMA indicator
        
        Args:
            period: Period for SMMA calculation (default: 7)
            source_price: Source price type - "close", "open", "high", "low", 
                         "median", "typical", "weighted"
        """
        super().__init__("SMMA", period)
        self.source_price = source_price.lower()
    
    def _get_source_prices(self, data: List[Dict]) -> np.ndarray:
        """Extract source prices based on source_price setting"""
        if self.source_price == "close":
            return self._get_close_prices(data)
        elif self.source_price == "open":
            return np.array([d['open'] for d in data])
        elif self.source_price == "high":
            return self._get_high_prices(data)
        elif self.source_price == "low":
            return self._get_low_prices(data)
        elif self.source_price == "median":
            return np.array([(d['high'] + d['low']) / 2.0 for d in data])
        elif self.source_price == "typical":
            return np.array([(d['high'] + d['low'] + d['close']) / 3.0 for d in data])
        elif self.source_price == "weighted":
            return np.array([(d['high'] + d['low'] + d['close'] + d['close']) / 4.0 for d in data])
        else:
            # Default to close
            return self._get_close_prices(data)
    
    def calculate(self, data: List[Dict]) -> List[float]:
        """
        Calculate SMMA values
        
        Formula:
        - First value: SMA (Simple Moving Average) of first 'period' values
        - Subsequent: SMMA[i] = (SMMA[i-1] * (period - 1) + source[i]) / period
        
        This matches the MT5 implementation where:
        SMMA[i] = (prevSMMA * (Length - 1) + source[i]) / Length
        """
        if len(data) < self.period:
            return []
        
        source_prices = self._get_source_prices(data)
        smma_values = []
        
        # Initialize with SMA (first value)
        sma = np.mean(source_prices[:self.period])
        smma_values.append(float(sma))
        
        # Calculate SMMA for remaining values
        # SMMA[i] = (SMMA[i-1] * (period - 1) + source[i]) / period
        for i in range(self.period, len(source_prices)):
            prev_smma = smma_values[-1]
            smma = (prev_smma * (self.period - 1) + source_prices[i]) / self.period
            smma_values.append(float(smma))
        
        # Pad beginning with None values
        return [None] * (self.period - 1) + smma_values
