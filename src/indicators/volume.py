"""
Volume Indicator
Calculates tick volume and detects volume momentum
"""

from typing import List, Dict, Optional
import numpy as np
import logging
from .base_indicator import BaseIndicator

logger = logging.getLogger(__name__)


class Volume(BaseIndicator):
    """
    Volume Indicator
    Tracks tick volume and detects volume momentum patterns
    """
    
    def __init__(self, period: int = 20):
        """
        Initialize Volume indicator
        
        Args:
            period: Period for volume moving average and momentum calculation
        """
        super().__init__("Volume", period)
        self.volume_values: List[float] = []
        self.volume_ma: Optional[float] = None
    
    def calculate(self, data: List[Dict]) -> List[float]:
        """
        Calculate volume values from OHLCV data
        
        Args:
            data: List of dictionaries with 'tick_volume' or 'volume' keys
            
        Returns:
            List of volume values
        """
        if not data:
            return []
        
        volumes = []
        for candle in data:
            # Get tick volume (preferred) or real volume
            volume = float(candle.get('tick_volume', candle.get('volume', 0.0)))
            volumes.append(volume)
        
        self.volume_values = volumes
        
        # Calculate volume moving average if we have enough data
        if len(volumes) >= self.period:
            self.volume_ma = np.mean(volumes[-self.period:])
        elif len(volumes) > 0:
            self.volume_ma = np.mean(volumes)
        else:
            self.volume_ma = None
        
        return volumes
    
    def get_current_volume(self) -> Optional[float]:
        """Get current volume value"""
        if not self.volume_values:
            return None
        return self.volume_values[-1]
    
    def get_volume_ma(self) -> Optional[float]:
        """Get volume moving average"""
        return self.volume_ma
    
    def get_volume_ratio(self) -> Optional[float]:
        """
        Get ratio of current volume to moving average
        
        Returns:
            Volume ratio (current_volume / ma_volume) or None
        """
        current_volume = self.get_current_volume()
        if current_volume is None or self.volume_ma is None or self.volume_ma == 0:
            return None
        return current_volume / self.volume_ma
    
    def is_volume_increasing(self, lookback: int = 3) -> bool:
        """
        Check if volume is increasing over recent periods
        
        Args:
            lookback: Number of recent periods to check
            
        Returns:
            True if volume is increasing, False otherwise
        """
        if len(self.volume_values) < lookback + 1:
            return False
        
        recent_volumes = self.volume_values[-lookback:]
        # Check if volumes are generally increasing
        increasing_count = 0
        for i in range(1, len(recent_volumes)):
            if recent_volumes[i] > recent_volumes[i-1]:
                increasing_count += 1
        
        # Consider increasing if majority of comparisons show increase
        return increasing_count >= (len(recent_volumes) - 1) * 0.6
    
    def is_volume_declining(self, lookback: int = 3) -> bool:
        """
        Check if volume is declining over recent periods
        
        Args:
            lookback: Number of recent periods to check
            
        Returns:
            True if volume is declining, False otherwise
        """
        if len(self.volume_values) < lookback + 1:
            return False
        
        recent_volumes = self.volume_values[-lookback:]
        # Check if volumes are generally declining
        declining_count = 0
        for i in range(1, len(recent_volumes)):
            if recent_volumes[i] < recent_volumes[i-1]:
                declining_count += 1
        
        # Consider declining if majority of comparisons show decline
        return declining_count >= (len(recent_volumes) - 1) * 0.6
    
    def is_volume_above_average(self, threshold: float = 1.0) -> bool:
        """
        Check if current volume is above average
        
        Args:
            threshold: Multiplier for average (1.0 = exactly average, >1.0 = above average)
            
        Returns:
            True if volume is above threshold * average
        """
        ratio = self.get_volume_ratio()
        if ratio is None:
            return False
        return ratio > threshold
    
    def is_volume_below_average(self, threshold: float = 1.0) -> bool:
        """
        Check if current volume is below average
        
        Args:
            threshold: Multiplier for average (1.0 = exactly average, <1.0 = below average)
            
        Returns:
            True if volume is below threshold * average
        """
        ratio = self.get_volume_ratio()
        if ratio is None:
            return False
        return ratio < threshold
    
    def get_volume_momentum(self, lookback: int = 3) -> str:
        """
        Get volume momentum description
        
        Args:
            lookback: Number of recent periods to analyze
            
        Returns:
            'increasing', 'declining', or 'neutral'
        """
        if self.is_volume_increasing(lookback):
            return 'increasing'
        elif self.is_volume_declining(lookback):
            return 'declining'
        else:
            return 'neutral'

