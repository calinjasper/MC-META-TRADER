"""
SMC Utility Functions
Helper functions for SMC pivot detection used by indicators and visualizations.
"""

from typing import List, Tuple, Dict


def extract_ohlc_arrays(rates: List[Dict]) -> Tuple[List[float], List[float], List[float], List[float]]:
    """
    Extract OHLC arrays from rate dictionaries.
    
    Args:
        rates: List of dictionaries with 'open', 'high', 'low', 'close' keys
        
    Returns:
        Tuple of (opens, highs, lows, closes) lists
    """
    opens, highs, lows, closes = [], [], [], []
    for r in rates:
        # supports both dicts from MT5Connector and data_feed.get_rates()
        opens.append(float(r.get("open")))
        highs.append(float(r.get("high")))
        lows.append(float(r.get("low")))
        closes.append(float(r.get("close")))
    return opens, highs, lows, closes


def fractal_pivot_high(highs: List[float], i: int, left: int, right: int) -> bool:
    """
    Check if index i is a fractal pivot high.
    
    Args:
        highs: List of high prices
        i: Index to check
        left: Number of bars to the left required
        right: Number of bars to the right required
        
    Returns:
        True if index i is a pivot high
    """
    if i - left < 0 or i + right >= len(highs):
        return False
    h = highs[i]
    return all(h > highs[j] for j in range(i - left, i)) and all(h >= highs[j] for j in range(i + 1, i + right + 1))


def fractal_pivot_low(lows: List[float], i: int, left: int, right: int) -> bool:
    """
    Check if index i is a fractal pivot low.
    
    Args:
        lows: List of low prices
        i: Index to check
        left: Number of bars to the left required
        right: Number of bars to the right required
        
    Returns:
        True if index i is a pivot low
    """
    if i - left < 0 or i + right >= len(lows):
        return False
    l = lows[i]
    return all(l < lows[j] for j in range(i - left, i)) and all(l <= lows[j] for j in range(i + 1, i + right + 1))
