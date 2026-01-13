"""
SMC Data Tracker Service
Tracks SMC pivot data (pivot_high, pivot_low, CHoCH, BOS) for multiple symbols.
Used by Market Data Panel to display real-time SMC levels.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import MetaTrader5 as mt5

from ..strategy.smc_utils import fractal_pivot_high, fractal_pivot_low, extract_ohlc_arrays

logger = logging.getLogger(__name__)


@dataclass
class SMCData:
    """SMC data for a single symbol"""
    pivot_high: Optional[float] = None
    pivot_low: Optional[float] = None
    choch_price: Optional[float] = None
    bos_price: Optional[float] = None
    bias: Optional[str] = None  # "BULLISH" | "BEARISH" | None
    last_bar_time: Optional[int] = None  # Timestamp of last processed bar
    last_update: Optional[datetime] = None


class SMCDataTracker:
    """
    Tracks SMC pivot data for multiple symbols.
    
    Updates pivots only when new bars form for efficiency.
    Provides real-time SMC data for Market Data Panel display.
    """
    
    def __init__(self, pivot_left: int = 2, pivot_right: int = 2, 
                 emit_on: str = "NONE", timeframe: int = 5, 
                 candle_buffer_size: int = 200):
        """
        Initialize SMC data tracker.
        
        Args:
            pivot_left: Number of bars to the left for pivot detection
            pivot_right: Number of bars to the right for pivot detection
            emit_on: "NONE" (pivots only), "CHoCH", "BOS", "BOTH"
            timeframe: Default timeframe for candle data (M5 = 5)
            candle_buffer_size: Number of candles to keep per symbol
        """
        self.pivot_left = pivot_left
        self.pivot_right = pivot_right
        self.emit_on = emit_on.upper()
        self.timeframe = timeframe
        self.candle_buffer_size = candle_buffer_size
        
        # Per-symbol data storage
        self._symbol_data: Dict[str, SMCData] = {}
        self._candle_buffers: Dict[str, List[Dict]] = {}
        
        # Internal tracking for structure events
        self._all_pivot_highs: Dict[str, List[Tuple[int, float]]] = {}  # symbol -> [(index, price)]
        self._all_pivot_lows: Dict[str, List[Tuple[int, float]]] = {}
        self._all_events: Dict[str, List[Dict]] = {}  # symbol -> [events]
        self._bias: Dict[str, Optional[str]] = {}  # symbol -> bias
        
        logger.info(f"SMCDataTracker initialized: pivot_left={pivot_left}, pivot_right={pivot_right}, "
                   f"emit_on={emit_on}, timeframe=M{timeframe}")
    
    def get_smc_data(self, symbol: str) -> Dict:
        """
        Get SMC data for a symbol.
        
        Returns:
            Dictionary with pivot_high, pivot_low, choch_price, bos_price, bias
        """
        if symbol not in self._symbol_data:
            return {
                "pivot_high": None,
                "pivot_low": None,
                "choch_price": None,
                "bos_price": None,
                "bias": None,
                "last_update": None
            }
        
        data = self._symbol_data[symbol]
        return {
            "pivot_high": data.pivot_high,
            "pivot_low": data.pivot_low,
            "choch_price": data.choch_price,
            "bos_price": data.bos_price,
            "bias": data.bias,
            "last_update": data.last_update
        }
    
    def update_candles(self, symbol: str, candles: List[Dict]) -> bool:
        """
        Update candle buffer for a symbol and recalculate SMC data if new bar.
        
        Args:
            symbol: Symbol name
            candles: List of candle dicts with 'time', 'open', 'high', 'low', 'close'
            
        Returns:
            True if SMC data was recalculated (new bar detected)
        """
        if not candles or len(candles) < self.pivot_left + self.pivot_right + 3:
            return False
        
        # Initialize if needed
        if symbol not in self._symbol_data:
            self._symbol_data[symbol] = SMCData()
            self._candle_buffers[symbol] = []
            self._all_pivot_highs[symbol] = []
            self._all_pivot_lows[symbol] = []
            self._all_events[symbol] = []
            self._bias[symbol] = None
        
        # Check if new bar
        current_bar_time = candles[-1].get('time')
        last_bar_time = self._symbol_data[symbol].last_bar_time
        
        if last_bar_time is not None and current_bar_time == last_bar_time:
            # Same bar, no need to recalculate
            return False
        
        # New bar detected - update candle buffer
        self._candle_buffers[symbol] = candles[-self.candle_buffer_size:]
        self._symbol_data[symbol].last_bar_time = current_bar_time
        
        # Recalculate SMC data
        self._calculate_smc(symbol)
        
        return True
    
    def _calculate_smc(self, symbol: str) -> None:
        """Calculate SMC pivots and events for a symbol."""
        candles = self._candle_buffers.get(symbol, [])
        if len(candles) < self.pivot_left + self.pivot_right + 3:
            return
        
        # Extract OHLC arrays
        opens, highs, lows, closes = extract_ohlc_arrays(candles)
        
        # Reset tracking
        self._all_pivot_highs[symbol] = []
        self._all_pivot_lows[symbol] = []
        self._all_events[symbol] = []
        self._bias[symbol] = None
        
        # Detect pivots
        self._detect_pivots(symbol, highs, lows)
        
        # Detect structure events (BOS/CHoCH)
        self._detect_structure_events(symbol, candles, opens, highs, lows, closes)
        
        # Update active lines based on emit_on setting
        self._update_active_lines(symbol)
        
        # Update timestamp
        self._symbol_data[symbol].last_update = datetime.now()
        
        logger.debug(f"SMCDataTracker: {symbol} - pivot_high={self._symbol_data[symbol].pivot_high}, "
                    f"pivot_low={self._symbol_data[symbol].pivot_low}, bias={self._symbol_data[symbol].bias}")
    
    def _detect_pivots(self, symbol: str, highs: List[float], lows: List[float]) -> None:
        """Detect fractal pivots."""
        left, right = self.pivot_left, self.pivot_right
        start = left
        end = len(highs) - right
        
        for i in range(start, end):
            if fractal_pivot_high(highs, i, left, right):
                self._all_pivot_highs[symbol].append((i, highs[i]))
            if fractal_pivot_low(lows, i, left, right):
                self._all_pivot_lows[symbol].append((i, lows[i]))
    
    def _detect_structure_events(self, symbol: str, candles: List[Dict], 
                                  opens: List[float], highs: List[float],
                                  lows: List[float], closes: List[float]) -> None:
        """Detect BOS and CHoCH events chronologically."""
        pivot_highs = self._all_pivot_highs[symbol]
        pivot_lows = self._all_pivot_lows[symbol]
        
        if not pivot_highs and not pivot_lows:
            return
        
        bias = None
        
        # Process bars chronologically
        for i in range(len(closes)):
            # Find most recent pivot before this bar
            relevant_pivot_high = None
            relevant_pivot_high_idx = -1
            for pivot_idx, pivot_price in pivot_highs:
                if pivot_idx < i:
                    if relevant_pivot_high_idx == -1 or pivot_idx > relevant_pivot_high_idx:
                        relevant_pivot_high = pivot_price
                        relevant_pivot_high_idx = pivot_idx
            
            relevant_pivot_low = None
            relevant_pivot_low_idx = -1
            for pivot_idx, pivot_price in pivot_lows:
                if pivot_idx < i:
                    if relevant_pivot_low_idx == -1 or pivot_idx > relevant_pivot_low_idx:
                        relevant_pivot_low = pivot_price
                        relevant_pivot_low_idx = pivot_idx
            
            current_close = closes[i]
            event = None
            direction = None
            
            # Check for pivot high break
            if relevant_pivot_high is not None and current_close > relevant_pivot_high:
                if bias == "BEARISH":
                    event = "CHoCH"
                    direction = "UP"
                    bias = "BULLISH"
                elif bias == "BULLISH":
                    event = "BOS"
                    direction = "UP"
                else:
                    event = "BOS"
                    direction = "UP"
                    bias = "BULLISH"
            
            # Check for pivot low break
            elif relevant_pivot_low is not None and current_close < relevant_pivot_low:
                if bias == "BULLISH":
                    event = "CHoCH"
                    direction = "DOWN"
                    bias = "BEARISH"
                elif bias == "BEARISH":
                    event = "BOS"
                    direction = "DOWN"
                else:
                    event = "BOS"
                    direction = "DOWN"
                    bias = "BEARISH"
            
            if event:
                self._all_events[symbol].append({
                    "event_type": event,
                    "direction": direction,
                    "price": current_close,  # CHoCH/BOS price = close price when pivot was broken
                    "index": i
                })
        
        self._bias[symbol] = bias
    
    def _update_active_lines(self, symbol: str) -> None:
        """Update active pivot/event prices based on emit_on setting."""
        data = self._symbol_data[symbol]
        data.pivot_high = None
        data.pivot_low = None
        data.choch_price = None
        data.bos_price = None
        data.bias = self._bias.get(symbol)
        
        pivot_highs = self._all_pivot_highs.get(symbol, [])
        pivot_lows = self._all_pivot_lows.get(symbol, [])
        events = self._all_events.get(symbol, [])
        
        if self.emit_on == "NONE":
            # Track most recent pivot levels
            if pivot_highs:
                # Most recent pivot high (highest index)
                most_recent = max(pivot_highs, key=lambda x: x[0])
                data.pivot_high = most_recent[1]
            
            if pivot_lows:
                # Most recent pivot low (highest index)
                most_recent = max(pivot_lows, key=lambda x: x[0])
                data.pivot_low = most_recent[1]
        
        elif self.emit_on == "BOS":
            # Track BOS event line
            for event in reversed(events):
                if event["event_type"] == "BOS":
                    data.bos_price = event["price"]
                    break
        
        elif self.emit_on in ("CHOCH", "CHoCH"):
            # Track CHoCH event line
            choch_events = [e for e in events if e["event_type"] == "CHoCH"]
            if choch_events:
                # Use most recent CHoCH
                data.choch_price = choch_events[-1]["price"]
        
        elif self.emit_on == "BOTH":
            # Track both BOS and CHoCH
            for event in reversed(events):
                if event["event_type"] == "BOS" and data.bos_price is None:
                    data.bos_price = event["price"]
                elif event["event_type"] == "CHoCH" and data.choch_price is None:
                    data.choch_price = event["price"]
                
                if data.bos_price is not None and data.choch_price is not None:
                    break
        
        # Always track pivots for display (even if emit_on is not NONE)
        if data.pivot_high is None and pivot_highs:
            most_recent = max(pivot_highs, key=lambda x: x[0])
            data.pivot_high = most_recent[1]
        
        if data.pivot_low is None and pivot_lows:
            most_recent = max(pivot_lows, key=lambda x: x[0])
            data.pivot_low = most_recent[1]
    
    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from tracking."""
        if symbol in self._symbol_data:
            del self._symbol_data[symbol]
        if symbol in self._candle_buffers:
            del self._candle_buffers[symbol]
        if symbol in self._all_pivot_highs:
            del self._all_pivot_highs[symbol]
        if symbol in self._all_pivot_lows:
            del self._all_pivot_lows[symbol]
        if symbol in self._all_events:
            del self._all_events[symbol]
        if symbol in self._bias:
            del self._bias[symbol]
        logger.debug(f"SMCDataTracker: Removed symbol {symbol}")
    
    def get_all_symbols(self) -> List[str]:
        """Get list of all tracked symbols."""
        return list(self._symbol_data.keys())
    
    def set_parameters(self, pivot_left: int = None, pivot_right: int = None,
                       emit_on: str = None, timeframe: int = None) -> None:
        """Update tracker parameters and recalculate all symbols."""
        if pivot_left is not None:
            self.pivot_left = pivot_left
        if pivot_right is not None:
            self.pivot_right = pivot_right
        if emit_on is not None:
            self.emit_on = emit_on.upper()
        if timeframe is not None:
            self.timeframe = timeframe
        
        # Force recalculation for all symbols
        for symbol in list(self._symbol_data.keys()):
            self._symbol_data[symbol].last_bar_time = None
        
        logger.info(f"SMCDataTracker parameters updated: pivot_left={self.pivot_left}, "
                   f"pivot_right={self.pivot_right}, emit_on={self.emit_on}")
