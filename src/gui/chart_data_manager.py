"""
Chart Data Manager
Handles data optimization, caching, and decimation for performance
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ChartDataManager:
    """Manages chart data with performance optimizations"""
    
    def __init__(self, max_visible_bars: int = 1000):
        """
        Initialize the data manager
        
        Args:
            max_visible_bars: Maximum number of bars to render at once
        """
        self.max_visible_bars = max_visible_bars
        self.cache = {}
        self.last_view_range = None
    
    def decimate_data(self, times: List[datetime], rates: List[Dict],
                     view_range: Optional[Tuple] = None) -> Tuple[List[datetime], List[Dict]]:
        """
        Decimate data based on view range for better performance
        
        Args:
            times: List of datetime objects
            rates: List of rate dictionaries
            view_range: Current view range (x_min, x_max, y_min, y_max)
        
        Returns:
            Decimated (times, rates) tuple
        """
        if not times or not rates:
            return times, rates
        
        # Ensure times and rates have same length
        min_len = min(len(times), len(rates))
        times = times[:min_len]
        rates = rates[:min_len]
        
        # If view range is provided, only show visible data
        if view_range and len(view_range) >= 2:
            x_min, x_max = view_range[0]
            
            # Convert times to timestamps for comparison
            times_ts = []
            for t in times:
                if isinstance(t, datetime):
                    times_ts.append(t.timestamp())
                else:
                    try:
                        times_ts.append(float(t))
                    except Exception:
                        times_ts.append(None)
            
            # Find visible range
            visible_indices = []
            for i, ts in enumerate(times_ts):
                if ts is not None and x_min <= ts <= x_max:
                    visible_indices.append(i)
            
            if visible_indices:
                # Add some padding for smooth scrolling (50 bars on each side)
                start_idx = max(0, visible_indices[0] - 50)
                end_idx = min(len(times), visible_indices[-1] + 50)
                return times[start_idx:end_idx], rates[start_idx:end_idx]
        
        # If too many bars, decimate
        if len(times) > self.max_visible_bars:
            step = max(1, len(times) // self.max_visible_bars)
            return times[::step], rates[::step]
        
        return times, rates
    
    def get_cached_indicator(self, cache_key: str) -> Optional[any]:
        """
        Get cached indicator calculation
        
        Args:
            cache_key: Cache key for the indicator
        
        Returns:
            Cached value or None if not found
        """
        return self.cache.get(cache_key)
    
    def set_cached_indicator(self, cache_key: str, value: any):
        """
        Cache indicator calculation
        
        Args:
            cache_key: Cache key for the indicator
            value: Value to cache
        """
        # Limit cache size (max 100 entries, FIFO eviction)
        if len(self.cache) >= 100:
            # Remove oldest entries (simple FIFO - remove first 20)
            keys_to_remove = list(self.cache.keys())[:20]
            for key in keys_to_remove:
                del self.cache[key]
        
        self.cache[cache_key] = value
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
    
    def create_cache_key(self, symbol: str, timeframe: int, 
                        indicator_type: str, **params) -> str:
        """
        Create a cache key for indicator calculations
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe constant
            indicator_type: Type of indicator (e.g., 'vwap', 'ema')
            **params: Additional parameters for the indicator
        
        Returns:
            Cache key string
        """
        params_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{symbol}_{timeframe}_{indicator_type}_{params_str}"

