"""
Base Indicator Class
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import numpy as np
import pandas as pd


class BaseIndicator(ABC):
    """Base class for all technical indicators"""
    
    def __init__(self, name: str, period: int = 14):
        self.name = name
        self.period = period
        self.values: List[float] = []
        self.times: List = []
    
    @abstractmethod
    def calculate(self, data: List[Dict]) -> List[float]:
        """
        Calculate indicator values from OHLCV data
        
        Args:
            data: List of dictionaries with 'open', 'high', 'low', 'close', 'time' keys
            
        Returns:
            List of indicator values
        """
        pass
    
    def update(self, data: List[Dict]) -> None:
        """Update indicator with new data"""
        self.values = self.calculate(data)
        if data:
            self.times = [d.get('time') for d in data]
    
    def get_value(self, index: int = -1) -> Optional[float]:
        """Get indicator value at index (default: latest)"""
        if not self.values or abs(index) > len(self.values):
            return None
        return self.values[index]
    
    def get_values(self) -> List[float]:
        """Get all indicator values"""
        return self.values
    
    def _to_dataframe(self, data: List[Dict]) -> pd.DataFrame:
        """Convert data list to pandas DataFrame"""
        return pd.DataFrame(data)
    
    def _get_close_prices(self, data: List[Dict]) -> np.ndarray:
        """Extract close prices from data"""
        return np.array([d['close'] for d in data])
    
    def _get_high_prices(self, data: List[Dict]) -> np.ndarray:
        """Extract high prices from data"""
        return np.array([d['high'] for d in data])
    
    def _get_low_prices(self, data: List[Dict]) -> np.ndarray:
        """Extract low prices from data"""
        return np.array([d['low'] for d in data])

