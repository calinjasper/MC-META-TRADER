"""
Volume Weighted Average Price (VWAP) Indicator
Calculates session-based VWAP with standard deviation bands
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, time as dt_time
import numpy as np
import logging
from .base_indicator import BaseIndicator

logger = logging.getLogger(__name__)


class VWAP(BaseIndicator):
    """
    Volume Weighted Average Price (VWAP)
    Calculates VWAP for a trading session with standard deviation bands
    """
    
    # Session start times (in UTC)
    SESSION_TIMES = {
        'NY': dt_time(13, 0),  # 8:00 AM ET = 13:00 UTC
        'London': dt_time(8, 0),  # 8:00 AM GMT = 8:00 UTC
        'Asia': dt_time(0, 0),  # 00:00 JST = 0:00 UTC (approximate)
        'All': None  # No reset, continuous
    }
    
    def __init__(self, session_type: str = 'NY', use_typical_price: bool = True):
        """
        Initialize VWAP indicator
        
        Args:
            session_type: Trading session ('NY', 'London', 'Asia', 'All')
            use_typical_price: If True, use (H+L+C)/3, else use Close price
        """
        super().__init__("VWAP", period=1)  # VWAP doesn't use period
        self.session_type = session_type
        self.use_typical_price = use_typical_price
        
        # Cumulative values for current session
        self.cumulative_price_volume = 0.0
        self.cumulative_volume = 0.0
        self.session_start_time: Optional[datetime] = None
        self.prices: List[float] = []  # Store prices for STD calculation
        self.volumes: List[float] = []  # Store volumes
        
        # Current VWAP value
        self.current_vwap: Optional[float] = None
        
        # Standard deviation cache
        self.std_cache: Dict[float, Tuple[float, float]] = {}  # std_dev -> (upper_band, lower_band)
    
    def _get_session_start_time(self, current_time: datetime) -> datetime:
        """
        Determine session start time based on current time
        
        Args:
            current_time: Current datetime
            
        Returns:
            Session start datetime
        """
        if self.session_type == 'All':
            # For 'All', use the first data point as session start
            return current_time
        
        session_time = self.SESSION_TIMES.get(self.session_type)
        if not session_time:
            return current_time
        
        # Get today's session start
        session_start = datetime.combine(current_time.date(), session_time)
        
        # If current time is before session start today, use yesterday's session
        if current_time < session_start:
            from datetime import timedelta
            session_start = session_start - timedelta(days=1)
        
        return session_start
    
    def _should_reset_session(self, current_time: datetime) -> bool:
        """
        Check if session should be reset
        
        Args:
            current_time: Current datetime
            
        Returns:
            True if session should reset
        """
        if self.session_type == 'All':
            return False
        
        if self.session_start_time is None:
            return True
        
        new_session_start = self._get_session_start_time(current_time)
        return new_session_start > self.session_start_time
    
    def _reset_session(self, session_start: datetime):
        """Reset VWAP calculation for new session"""
        self.cumulative_price_volume = 0.0
        self.cumulative_volume = 0.0
        self.session_start_time = session_start
        self.prices.clear()
        self.volumes.clear()
        self.std_cache.clear()
        logger.debug(f"VWAP session reset for {self.session_type} at {session_start}")
    
    def _get_price(self, candle: Dict) -> float:
        """Get price for VWAP calculation (typical price or close)"""
        if self.use_typical_price:
            return (candle.get('high', 0) + candle.get('low', 0) + candle.get('close', 0)) / 3.0
        else:
            return candle.get('close', 0)
    
    def calculate(self, data: List[Dict]) -> List[float]:
        """
        Calculate VWAP values from OHLCV data
        
        Args:
            data: List of dictionaries with 'open', 'high', 'low', 'close', 'time', 'tick_volume' keys
            
        Returns:
            List of VWAP values
        """
        if not data:
            return []
        
        vwap_values = []
        
        for candle in data:
            candle_time = candle.get('time')
            if isinstance(candle_time, (int, float)):
                # Convert timestamp to datetime
                candle_time = datetime.fromtimestamp(candle_time)
            elif not isinstance(candle_time, datetime):
                # Try to parse if it's a string
                try:
                    candle_time = datetime.fromisoformat(str(candle_time))
                except:
                    logger.warning(f"Could not parse time: {candle_time}")
                    vwap_values.append(None)
                    continue
            
            # Check if session should reset
            if self._should_reset_session(candle_time):
                session_start = self._get_session_start_time(candle_time)
                self._reset_session(session_start)
            
            # Get price and volume
            price = self._get_price(candle)
            volume = float(candle.get('tick_volume', candle.get('volume', 1.0)))
            
            if volume <= 0:
                # Use previous VWAP if volume is 0
                vwap_values.append(self.current_vwap if self.current_vwap else None)
                continue
            
            # Update cumulative values
            self.cumulative_price_volume += price * volume
            self.cumulative_volume += volume
            
            # Calculate VWAP
            if self.cumulative_volume > 0:
                vwap = self.cumulative_price_volume / self.cumulative_volume
                self.current_vwap = vwap
                vwap_values.append(vwap)
                
                # Store price and volume for STD calculation
                self.prices.append(price)
                self.volumes.append(volume)
            else:
                vwap_values.append(None)
        
        return vwap_values
    
    def get_vwap(self) -> Optional[float]:
        """Get current VWAP value"""
        return self.current_vwap
    
    def get_bands(self, std_dev: float = 1.0) -> Tuple[Optional[float], Optional[float]]:
        """
        Get upper and lower standard deviation bands
        
        Args:
            std_dev: Standard deviation multiplier (1.0, 1.5, 2.0, etc.)
            
        Returns:
            Tuple of (upper_band, lower_band) or (None, None) if insufficient data
        """
        if self.current_vwap is None or len(self.prices) < 2:
            return (None, None)
        
        # Check cache
        if std_dev in self.std_cache:
            return self.std_cache[std_dev]
        
        # Calculate standard deviation of prices from VWAP
        price_array = np.array(self.prices)
        price_deviations = price_array - self.current_vwap
        std = np.std(price_deviations)
        
        # Calculate bands
        upper_band = self.current_vwap + (std_dev * std)
        lower_band = self.current_vwap - (std_dev * std)
        
        # Cache result
        self.std_cache[std_dev] = (upper_band, lower_band)
        
        return (upper_band, lower_band)
    
    def get_distance_from_vwap(self, current_price: float) -> Tuple[Optional[float], Optional[float]]:
        """
        Get distance from VWAP in points and standard deviations
        
        Args:
            current_price: Current market price
            
        Returns:
            Tuple of (distance_in_points, distance_in_std) or (None, None)
        """
        if self.current_vwap is None:
            return (None, None)
        
        distance_points = current_price - self.current_vwap
        
        # Calculate distance in standard deviations
        if len(self.prices) >= 2:
            price_array = np.array(self.prices)
            price_deviations = price_array - self.current_vwap
            std = np.std(price_deviations)
            if std > 0:
                distance_std = distance_points / std
            else:
                distance_std = 0.0
        else:
            distance_std = None
        
        return (distance_points, distance_std)
    
    def get_session_info(self) -> Dict:
        """Get current session information"""
        return {
            'session_type': self.session_type,
            'session_start_time': self.session_start_time,
            'cumulative_volume': self.cumulative_volume,
            'current_vwap': self.current_vwap
        }
    
    def reset_session(self):
        """Manually reset session (for testing or manual control)"""
        if self.session_start_time:
            self._reset_session(self.session_start_time)
        else:
            self._reset_session(datetime.now())

