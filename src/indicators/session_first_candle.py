"""
Session First Candle Indicator
Calculates High and Low of first candle of each trading session
"""

from typing import List, Dict, Optional
from datetime import datetime, time as dt_time
import logging
from .base_indicator import BaseIndicator

logger = logging.getLogger(__name__)


class SessionFirstCandle(BaseIndicator):
    """
    Session First Candle Indicator
    Tracks High and Low of the first candle of each configured trading session
    """
    
    def __init__(
        self,
        session1_start_hour: int = 0,
        session1_end_hour: int = 9,
        session2_start_hour: int = 8,
        session2_end_hour: int = 17,
        session3_start_hour: int = 13,
        session3_end_hour: int = 22,
    ):
        """
        Initialize Session First Candle indicator
        
        Args:
            session1_start_hour: Session 1 start hour (0-23)
            session1_end_hour: Session 1 end hour (0-23)
            session2_start_hour: Session 2 start hour (-1 to disable)
            session2_end_hour: Session 2 end hour (0-23)
            session3_start_hour: Session 3 start hour (-1 to disable)
            session3_end_hour: Session 3 end hour (0-23)
        """
        super().__init__("SessionFirstCandle", period=1)
        self.session1_start_hour = session1_start_hour
        self.session1_end_hour = session1_end_hour
        self.session2_start_hour = session2_start_hour
        self.session2_end_hour = session2_end_hour
        self.session3_start_hour = session3_start_hour
        self.session3_end_hour = session3_end_hour
        
        # Current session tracking
        self.current_session = 0  # 0 = no session, 1/2/3 = active session
        self.session_high: Optional[float] = None
        self.session_low: Optional[float] = None
        self.last_session = 0
        self.last_bar_time: Optional[datetime] = None
        
    def _get_session_number(self, hour: int) -> int:
        """
        Get session number for a given hour
        
        Args:
            hour: Hour of day (0-23)
            
        Returns:
            Session number (1, 2, 3) or 0 if no session
        """
        # Check Session 1
        if self.session1_start_hour <= self.session1_end_hour:
            # Normal session (doesn't cross midnight)
            if self.session1_start_hour <= hour < self.session1_end_hour:
                return 1
        else:
            # Session crosses midnight (e.g., 22:00-06:00)
            if hour >= self.session1_start_hour or hour < self.session1_end_hour:
                return 1
        
        # Check Session 2 (if enabled)
        if self.session2_start_hour >= 0:
            if self.session2_start_hour <= self.session2_end_hour:
                # Normal session
                if self.session2_start_hour <= hour < self.session2_end_hour:
                    return 2
            else:
                # Session crosses midnight
                if hour >= self.session2_start_hour or hour < self.session2_end_hour:
                    return 2
        
        # Check Session 3 (if enabled)
        if self.session3_start_hour >= 0:
            if self.session3_start_hour <= self.session3_end_hour:
                # Normal session
                if self.session3_start_hour <= hour < self.session3_end_hour:
                    return 3
            else:
                # Session crosses midnight
                if hour >= self.session3_start_hour or hour < self.session3_end_hour:
                    return 3
        
        return 0  # No session
    
    def calculate(self, data: List[Dict]) -> List[float]:
        """
        Calculate session first candle high/low values
        
        Args:
            data: List of dictionaries with 'open', 'high', 'low', 'close', 'time' keys
            
        Returns:
            List of high values (we'll track low separately)
        """
        if not data:
            return []
        
        # Process data from oldest to newest
        # Track session values as we process, but at the end, keep the MOST RECENT session's values
        # This matches MT5 behavior where the indicator shows the current session's first candle high/low
        highs = []
        current_session_values = {}  # Track first candle high/low for each session we encounter
        
        # Determine if data needs to be reversed for chronological processing
        # Check first and last bar timestamps to determine order
        needs_reverse = False
        if len(data) >= 2:
            first_time = data[0].get('time')
            last_time = data[-1].get('time')
            if isinstance(first_time, str):
                try:
                    first_time = datetime.fromisoformat(first_time)
                except:
                    first_time = None
            if isinstance(last_time, str):
                try:
                    last_time = datetime.fromisoformat(last_time)
                except:
                    last_time = None
            if isinstance(first_time, datetime) and isinstance(last_time, datetime):
                # If first bar is newer than last bar, data is in reverse chronological order
                # We need to reverse it to process oldest to newest
                if first_time > last_time:
                    needs_reverse = True
                    data = list(reversed(data))
        
        for i, bar in enumerate(data):
            bar_time = bar.get('time')
            if not bar_time:
                highs.append(self.session_high if self.session_high is not None else 0.0)
                continue
            
            # Convert to datetime if needed
            if isinstance(bar_time, str):
                try:
                    bar_time = datetime.fromisoformat(bar_time)
                except:
                    highs.append(self.session_high if self.session_high is not None else 0.0)
                    continue
            
            # Get hour from bar time (MT5 uses server time, we're using UTC here - potential mismatch!)
            # MT5's TimeToStruct converts UTC timestamp to server local time, then extracts hour
            # We're extracting UTC hour directly, which may cause session detection mismatch
            hour = bar_time.hour
            
            # Determine which session this bar belongs to
            bar_session = self._get_session_number(hour)
            
            # Check if this is the first candle of a new session
            is_new_session = False
            prev_session = 0
            
            if i > 0:
                # Get previous bar's session
                prev_bar = data[i - 1]
                prev_time = prev_bar.get('time')
                if prev_time:
                    if isinstance(prev_time, str):
                        try:
                            prev_time = datetime.fromisoformat(prev_time)
                        except:
                            pass
                    if isinstance(prev_time, datetime):
                        prev_hour = prev_time.hour
                        prev_session = self._get_session_number(prev_hour)
                        
                        # Session changed if current bar's session differs from previous bar's session
                        if bar_session != prev_session and bar_session > 0:
                            is_new_session = True
            else:
                # First bar in data
                if bar_session > 0:
                    is_new_session = True
            
            
            # Update session tracking
            # Always update instance variables as we process (these will contain the most recent session's values)
            # When we encounter a new session, store its first candle's High/Low
            if is_new_session:
                # New session - store first candle's High/Low for this session
                # If this session already exists in our tracking, we update it (this handles session reappearing later in time)
                current_session_values[bar_session] = {
                    'high': bar.get('high'),
                    'low': bar.get('low')
                }
                # Update instance variables - these will be overwritten as we process, but final values will be from newest bar
                self.session_high = bar.get('high')
                self.session_low = bar.get('low')
                self.current_session = bar_session
                self.last_session = bar_session
            else:
                # Same session - keep existing values, but ensure instance variables are set
                if bar_session > 0 and bar_session in current_session_values:
                    self.session_high = current_session_values[bar_session]['high']
                    self.session_low = current_session_values[bar_session]['low']
                    self.current_session = bar_session
            
            # Use the current bar's session values from our tracking
            if bar_session > 0 and bar_session in current_session_values:
                session_high_val = current_session_values[bar_session]['high']
                session_low_val = current_session_values[bar_session]['low']
            else:
                session_high_val = self.session_high if self.session_high is not None else None
                session_low_val = self.session_low if self.session_low is not None else None
            
            # Store high value for this bar
            highs.append(session_high_val if session_high_val is not None else 0.0)
            self.last_bar_time = bar_time
        
        # After processing all bars, we need to get values from the MOST RECENT bar's session
        # Since we've ensured data is in chronological order (oldest to newest) above,
        # data[-1] should now be the newest bar. But we'll verify with timestamp comparison as a safety check.
        if data:
            # Get first and last bar for timestamp comparison (safety check)
            first_bar = data[0] if len(data) > 0 else None
            last_bar = data[-1] if len(data) > 0 else None
            
            # Determine which is actually newer by comparing timestamps
            actual_newest_bar = last_bar  # Default to last bar (should be newest after chronological ordering)
            actual_newest_bar_time = last_bar.get('time') if last_bar else None
            
            if first_bar and last_bar:
                first_bar_time = first_bar.get('time')
                last_bar_time = last_bar.get('time')
                
                # Convert to datetime if needed
                if isinstance(first_bar_time, str):
                    try:
                        first_bar_time = datetime.fromisoformat(first_bar_time)
                    except:
                        first_bar_time = None
                if isinstance(last_bar_time, str):
                    try:
                        last_bar_time = datetime.fromisoformat(last_bar_time)
                    except:
                        last_bar_time = None
                
                # Safety check: use whichever is actually newer
                if isinstance(first_bar_time, datetime) and isinstance(last_bar_time, datetime):
                    if first_bar_time > last_bar_time:
                        actual_newest_bar = first_bar
                        actual_newest_bar_time = first_bar_time
                    else:
                        actual_newest_bar_time = last_bar_time
                elif isinstance(first_bar_time, datetime):
                    actual_newest_bar_time = first_bar_time
            elif actual_newest_bar_time and isinstance(actual_newest_bar_time, str):
                try:
                    actual_newest_bar_time = datetime.fromisoformat(actual_newest_bar_time)
                except:
                    actual_newest_bar_time = None
            
            if actual_newest_bar and actual_newest_bar_time and isinstance(actual_newest_bar_time, datetime):
                last_hour = actual_newest_bar_time.hour
                last_session = self._get_session_number(last_hour)
                if last_session > 0 and last_session in current_session_values:
                    # Ensure we have the correct values for the most recent bar's session
                    self.session_high = current_session_values[last_session]['high']
                    self.session_low = current_session_values[last_session]['low']
                    self.current_session = last_session
        
        return highs
    
    def get_session_high(self) -> Optional[float]:
        """Get current session high line value"""
        return self.session_high
    
    def get_session_low(self) -> Optional[float]:
        """Get current session low line value"""
        return self.session_low
    
    def get_current_session(self) -> int:
        """Get current session number (0, 1, 2, or 3)"""
        return self.current_session
    
    def update(self, data: List[Dict]) -> None:
        """Update indicator with new data"""
        self.values = self.calculate(data)
        if data:
            self.times = [d.get('time') for d in data]
