"""
Candle Pattern Detection
Detects reversal patterns in candlestick data
"""

from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class PatternDetector:
    """
    Detects candlestick reversal patterns
    """
    
    # Minimum wick-to-body ratio for pin bars
    PIN_BAR_WICK_RATIO = 2.0
    
    # Minimum body size for engulfing patterns (as ratio of previous body)
    ENGULFING_BODY_RATIO = 1.2
    
    @staticmethod
    def detect_pattern(candle: Dict, previous_candle: Optional[Dict] = None) -> Optional[str]:
        """
        Detect candlestick pattern
        
        Args:
            candle: Current candle dict with 'open', 'high', 'low', 'close'
            previous_candle: Previous candle for patterns requiring two candles
            
        Returns:
            Pattern name or None
        """
        if not candle:
            return None
        
        open_price = candle.get('open', 0)
        high = candle.get('high', 0)
        low = candle.get('low', 0)
        close = candle.get('close', 0)
        
        if open_price == 0 or high == 0 or low == 0 or close == 0:
            return None
        
        # Calculate body and wicks
        body_size = abs(close - open_price)
        upper_wick = high - max(open_price, close)
        lower_wick = min(open_price, close) - low
        total_range = high - low
        
        if total_range == 0:
            return None
        
        # Doji pattern (very small body)
        if body_size / total_range < 0.1:
            return 'Doji'
        
        # Pin Bar (Bullish) - long lower wick, small upper wick
        if lower_wick > 0 and body_size > 0:
            lower_wick_ratio = lower_wick / body_size
            upper_wick_ratio = upper_wick / body_size if body_size > 0 else 0
            if lower_wick_ratio >= PatternDetector.PIN_BAR_WICK_RATIO and upper_wick_ratio < 1.0:
                return 'Pin Bar (Bullish)'
        
        # Pin Bar (Bearish) - long upper wick, small lower wick
        if upper_wick > 0 and body_size > 0:
            upper_wick_ratio = upper_wick / body_size
            lower_wick_ratio = lower_wick / body_size if body_size > 0 else 0
            if upper_wick_ratio >= PatternDetector.PIN_BAR_WICK_RATIO and lower_wick_ratio < 1.0:
                return 'Pin Bar (Bearish)'
        
        # Hammer (Bullish) - long lower wick, small body at top
        if lower_wick > 0 and body_size > 0:
            lower_wick_ratio = lower_wick / body_size
            body_position = (min(open_price, close) - low) / total_range if total_range > 0 else 0
            if lower_wick_ratio >= 2.0 and body_position < 0.3 and close > open_price:
                return 'Hammer'
        
        # Shooting Star (Bearish) - long upper wick, small body at bottom
        if upper_wick > 0 and body_size > 0:
            upper_wick_ratio = upper_wick / body_size
            body_position = (high - max(open_price, close)) / total_range if total_range > 0 else 0
            if upper_wick_ratio >= 2.0 and body_position < 0.3 and close < open_price:
                return 'Shooting Star'
        
        # Engulfing patterns (require previous candle)
        if previous_candle:
            prev_open = previous_candle.get('open', 0)
            prev_close = previous_candle.get('close', 0)
            prev_body_size = abs(prev_close - prev_open)
            
            if prev_body_size > 0:
                # Bullish Engulfing
                if (prev_close < prev_open and  # Previous was bearish
                    close > open_price and  # Current is bullish
                    open_price < prev_close and  # Current opens below previous close
                    close > prev_open):  # Current closes above previous open
                    if body_size >= prev_body_size * PatternDetector.ENGULFING_BODY_RATIO:
                        return 'Bullish Engulfing'
                
                # Bearish Engulfing
                if (prev_close > prev_open and  # Previous was bullish
                    close < open_price and  # Current is bearish
                    open_price > prev_close and  # Current opens above previous close
                    close < prev_open):  # Current closes below previous open
                    if body_size >= prev_body_size * PatternDetector.ENGULFING_BODY_RATIO:
                        return 'Bearish Engulfing'
        
        return None
    
    @staticmethod
    def detect_patterns(candles: List[Dict], lookback: int = 2) -> List[Optional[str]]:
        """
        Detect patterns for multiple candles
        
        Args:
            candles: List of candle dictionaries
            lookback: Number of previous candles to consider
            
        Returns:
            List of pattern names (None if no pattern)
        """
        if not candles:
            return []
        
        patterns = []
        for i in range(len(candles)):
            current_candle = candles[i]
            previous_candle = None
            
            # Get previous candle if available
            if i > 0:
                previous_candle = candles[i - 1]
            
            pattern = PatternDetector.detect_pattern(current_candle, previous_candle)
            patterns.append(pattern)
        
        return patterns
    
    @staticmethod
    def is_bullish_pattern(pattern: Optional[str]) -> bool:
        """Check if pattern is bullish"""
        if not pattern:
            return False
        bullish_patterns = [
            'Pin Bar (Bullish)',
            'Hammer',
            'Bullish Engulfing',
            'Doji'  # Doji can be bullish in context
        ]
        return pattern in bullish_patterns
    
    @staticmethod
    def is_bearish_pattern(pattern: Optional[str]) -> bool:
        """Check if pattern is bearish"""
        if not pattern:
            return False
        bearish_patterns = [
            'Pin Bar (Bearish)',
            'Shooting Star',
            'Bearish Engulfing',
            'Doji'  # Doji can be bearish in context
        ]
        return pattern in bearish_patterns
    
    @staticmethod
    def matches_pattern(current_pattern: Optional[str], required_pattern: str) -> bool:
        """
        Check if current pattern matches required pattern
        
        Args:
            current_pattern: Detected pattern name
            required_pattern: Required pattern name (can be 'Any' or specific pattern)
            
        Returns:
            True if matches
        """
        if not required_pattern or required_pattern == 'Any':
            return current_pattern is not None
        
        if not current_pattern:
            return False
        
        # Exact match
        if current_pattern == required_pattern:
            return True
        
        # Category matches
        if required_pattern == 'Bullish Reversal' and PatternDetector.is_bullish_pattern(current_pattern):
            return True
        
        if required_pattern == 'Bearish Reversal' and PatternDetector.is_bearish_pattern(current_pattern):
            return True
        
        return False

