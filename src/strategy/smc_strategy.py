"""
Smart Money Concepts (SMC) Strategy

This strategy matches the MT5 SMC indicator logic exactly:
- Tracks fractal pivot highs and lows
- Detects BOS (Break of Structure) and CHoCH (Change of Character) events
- Maintains market bias (BULLISH/BEARISH)
- Tracks active line prices (most recent unbroken pivot/event prices)
- Makes SMC prices available as operands for conditions
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import logging

from .base_strategy import BaseStrategy
from .smc_utils import extract_ohlc_arrays, fractal_pivot_high, fractal_pivot_low

logger = logging.getLogger(__name__)


@dataclass
class Pivot:
    """Represents a pivot point"""
    kind: str  # "high" | "low"
    price: float
    index: int  # Index in the candles array (forward indexing: 0 = oldest)


@dataclass
class StructureEvent:
    """Represents a BOS or CHoCH event"""
    event_type: str  # "BOS" | "CHoCH"
    direction: str  # "UP" | "DOWN"
    price: float  # Close price of the candle that broke the pivot (NOT the pivot price itself)
    index: int  # Index in the candles array


class SMCStrategy(BaseStrategy):
    """
    SMC Strategy matching MT5 indicator logic
    
    The strategy tracks:
    - Pivot highs and lows (fractal pivots)
    - BOS and CHoCH events
    - Market bias (BULLISH/BEARISH)
    - Active line prices (most recent unbroken pivot/event prices)
    
    Active lines are tracked based on emit_on setting:
    - "NONE": Track pivot high/low lines
    - "BOS": Track BOS event line
    - "CHoCH": Track CHoCH event line
    - "BOTH": Track both BOS and CHoCH lines
    
    IMPORTANT: CHoCH Price Definition
    - CHoCH price = Close price of the candle that broke the pivot
    - NOT the pivot price itself, but the close price when the pivot was broken
    - This is the confirmation level where the structure change was confirmed
    - Example: If pivot high is at 4500 and price breaks above with close at 4493.669,
      then CHoCH price = 4493.669 (the close price, not 4500)
    """

    def __init__(
        self,
        name: str,
        symbol: str,
        timeframe: int,
        pivot_left: int = 2,
        pivot_right: int = 2,
        emit_on: str = "NONE",  # "NONE" | "CHoCH" | "BOS" | "BOTH"
        buy_filters: Optional[List[Dict]] = None,
        sell_filters: Optional[List[Dict]] = None,
    ):
        super().__init__(name, symbol)
        self.timeframe = timeframe

        # Pivot settings
        self.pivot_left = int(pivot_left)
        self.pivot_right = int(pivot_right)
        self.emit_on = emit_on.upper()  # Normalize to uppercase

        # Post-filter chains (AND/OR) for buy/sell
        self.buy_filters: List[Dict] = buy_filters or []
        self.sell_filters: List[Dict] = sell_filters or []

        # Display-friendly description
        self.entry_conditions_text = [
            f"SMC: emit_on={self.emit_on}, pivots={self.pivot_left}/{self.pivot_right}"
        ]

        # State tracking
        self.bias: Optional[str] = None  # "BULLISH" | "BEARISH" | None
        
        # Pivot tracking (all pivots for MT5-style active line detection)
        self.all_pivot_highs: List[Pivot] = []  # All pivot highs (for finding unbroken ones)
        self.all_pivot_lows: List[Pivot] = []   # All pivot lows (for finding unbroken ones)
        self.last_pivot_high: Optional[Pivot] = None  # Last confirmed pivot (for quick reference)
        self.last_pivot_low: Optional[Pivot] = None   # Last confirmed pivot (for quick reference)
        
        # Event tracking (all events for chronological processing)
        self.all_events: List[StructureEvent] = []  # All BOS/CHoCH events in chronological order
        
        # Active line prices (most recent unbroken pivot/event)
        self.active_pivot_high_price: Optional[float] = None
        self.active_pivot_low_price: Optional[float] = None
        self.active_choch_price: Optional[float] = None
        self.active_bos_price: Optional[float] = None
        
        # Track previous price for crossover detection (LTP/tick-based)
        self._prev_filter_price: Optional[float] = None
        
        # Bar caching for efficiency (recompute pivots only on new bars)
        self._last_bar_time: Optional[int] = None  # Timestamp of last processed bar
        
        # Last event prices (for reference)
        self.last_choch_price: Optional[float] = None
        self.last_bos_price: Optional[float] = None
        self.last_choch_direction: Optional[str] = None
        self.last_bos_direction: Optional[str] = None

        # For filter cross detection
        self._prev_filter_price: Optional[float] = None

        # Optional MT5 connector (for fetching correct timeframe candles)
        self.mt5_connector = None

    def set_mt5_connector(self, mt5_connector) -> None:
        """Set MT5 connector for fetching candles"""
        self.mt5_connector = mt5_connector

    def set_filters(self, buy_filters: List[Dict], sell_filters: List[Dict]) -> None:
        """Set buy and sell filter conditions"""
        self.buy_filters = buy_filters or []
        self.sell_filters = sell_filters or []

    def _get_candles(self, count: int = 300) -> List[Dict]:
        """Get candles on the strategy timeframe. Uses MT5Connector if available."""
        if self.mt5_connector and hasattr(self.mt5_connector, "is_connected") and self.mt5_connector.is_connected():
            try:
                rates = self.mt5_connector.get_rates(self.symbol, self.timeframe, count, 0)
                if rates is None:
                    return []
                return list(rates)
            except Exception as e:
                logger.error(f"SMCStrategy {self.name}: Error fetching candles via MT5Connector: {e}", exc_info=True)
                return []
        return []

    def _update_pivots(self, highs: List[float], lows: List[float]) -> None:
        """
        Update pivot tracking by scanning for ALL confirmed pivots.
        Tracks all pivots (not just last) to match MT5 indicator logic for active line detection.
        
        Matches MT5 indicator's UpdatePivots() logic - stores all pivots in arrays.
        """
        left, right = self.pivot_left, self.pivot_right
        if len(highs) < left + right + 3:
            return

        # Reset pivot lists for this calculation cycle
        # We'll rebuild them from all confirmed pivots (like MT5 does)
        self.all_pivot_highs = []
        self.all_pivot_lows = []
        
        # Scan all bars that can have confirmed pivots (like MT5 does)
        start = left
        end = len(highs) - right

        for i in range(start, end):
            if fractal_pivot_high(highs, i, left, right):
                pivot = Pivot(kind="high", price=highs[i], index=i)
                self.all_pivot_highs.append(pivot)
                self.last_pivot_high = pivot  # Keep last for quick reference
            if fractal_pivot_low(lows, i, left, right):
                pivot = Pivot(kind="low", price=lows[i], index=i)
                self.all_pivot_lows.append(pivot)
                self.last_pivot_low = pivot  # Keep last for quick reference

    def _detect_structure_chronological(self, candles: List[Dict], opens: List[float], highs: List[float], 
                                       lows: List[float], closes: List[float]) -> None:
        """
        Detect BOS/CHoCH events by processing candles chronologically (oldest to newest).
        This ensures correct bias tracking, matching MT5 indicator logic.
        
        Matches MT5 indicator's DetectStructure() logic in OnCalculate().
        """
        # Reset events for this calculation cycle
        self.all_events = []
        self.bias = None
        
        # Track pivots as we process chronologically
        # Note: We use all_pivot_highs/all_pivot_lows from _update_pivots() for structure detection
        # But we also track them here for chronological processing
        confirmed_pivots_high: List[Tuple[int, float]] = []  # (index, price)
        confirmed_pivots_low: List[Tuple[int, float]] = []  # (index, price)
        
        # Process bars chronologically (oldest to newest)
        for i in range(len(closes)):
            # Check if this bar is a confirmed pivot
            if i >= self.pivot_left and i < len(closes) - self.pivot_right:
                # Check for pivot high
                if fractal_pivot_high(highs, i, self.pivot_left, self.pivot_right):
                    confirmed_pivots_high.append((i, highs[i]))
                # Check for pivot low
                if fractal_pivot_low(lows, i, self.pivot_left, self.pivot_right):
                    confirmed_pivots_low.append((i, lows[i]))
            
            # Find the most recent pivot that occurred BEFORE this bar
            relevant_pivot_high = None
            relevant_pivot_high_idx = -1
            for pivot_idx, pivot_price in confirmed_pivots_high:
                if pivot_idx < i:  # Pivot occurred before current bar
                    if relevant_pivot_high_idx == -1 or pivot_idx > relevant_pivot_high_idx:
                        relevant_pivot_high = pivot_price
                        relevant_pivot_high_idx = pivot_idx
            
            relevant_pivot_low = None
            relevant_pivot_low_idx = -1
            for pivot_idx, pivot_price in confirmed_pivots_low:
                if pivot_idx < i:  # Pivot occurred before current bar
                    if relevant_pivot_low_idx == -1 or pivot_idx > relevant_pivot_low_idx:
                        relevant_pivot_low = pivot_price
                        relevant_pivot_low_idx = pivot_idx
            
            # Check if current bar breaks a pivot
            current_close = closes[i]
            event = None
            direction = None
            
            # Check for pivot high break
            if relevant_pivot_high is not None and current_close > relevant_pivot_high:
                if self.bias == "BEARISH":
                    event = "CHoCH"
                    direction = "UP"
                    self.bias = "BULLISH"
                elif self.bias == "BULLISH":
                    event = "BOS"
                    direction = "UP"
                else:  # bias is None
                    event = "BOS"
                    direction = "UP"
                    self.bias = "BULLISH"
            
            # Check for pivot low break
            elif relevant_pivot_low is not None and current_close < relevant_pivot_low:
                if self.bias == "BULLISH":
                    event = "CHoCH"
                    direction = "DOWN"
                    self.bias = "BEARISH"
                elif self.bias == "BEARISH":
                    event = "BOS"
                    direction = "DOWN"
                else:  # bias is None
                    event = "BOS"
                    direction = "DOWN"
                    self.bias = "BEARISH"
            
            # Store event if detected
            if event:
                # IMPORTANT: CHoCH/BOS price is the CLOSE price of the candle that broke the pivot
                # This is the confirmation level where the structure change was confirmed
                # NOT the pivot price itself, but the close price when the pivot was broken
                self.all_events.append(StructureEvent(
                    event_type=event,
                    direction=direction,
                    price=current_close,  # Close price of candle that broke the pivot
                    index=i
                ))
                
                # Update last event prices
                if event == "CHoCH":
                    # CHoCH price = close price of the candle that broke the pivot
                    self.last_choch_price = current_close
                    self.last_choch_direction = direction
                elif event == "BOS":
                    self.last_bos_price = current_close
                    self.last_bos_direction = direction

    def _update_active_lines(self) -> None:
        """
        Update active line prices based on emit_on setting.
        Active line = most recent unbroken pivot/event.
        
        Matches MT5 indicator's horizontal line drawing logic.
        """
        # Reset active lines
        self.active_pivot_high_price = None
        self.active_pivot_low_price = None
        self.active_choch_price = None
        self.active_bos_price = None
        
        # Update based on emit_on setting (case-insensitive comparison)
        emit_on_upper = self.emit_on.upper()
        
        if emit_on_upper == "NONE":
            # Track pivot lines - find most recent unbroken pivot (MT5 logic)
            # Match MT5 indicator's logic: find most recent pivot that hasn't been broken
            # A pivot is "broken" if there's a newer pivot of the same type
            
            # Find most recent unbroken pivot high (MT5 logic)
            # MT5 finds the most recent pivot and checks if there's a newer one
            # If no newer pivot exists, the current one is "active" (unbroken)
            if self.all_pivot_highs:
                # Sort by index descending (most recent = highest index = first in list)
                sorted_highs = sorted(self.all_pivot_highs, key=lambda p: p.index, reverse=True)
                
                if sorted_highs:
                    # The most recent pivot is the first one (highest index)
                    # In MT5 logic, this is the "active" pivot if no newer one exists
                    # Since we're at the current bar, the most recent pivot is the active one
                    most_recent_pivot = sorted_highs[0]
                    self.active_pivot_high_price = most_recent_pivot.price
                    logger.debug(f"SMCStrategy {self.name}: Active pivot high = {self.active_pivot_high_price} "
                               f"(index={most_recent_pivot.index}, from {len(self.all_pivot_highs)} total pivots)")
            
            # Find most recent unbroken pivot low (same logic)
            if self.all_pivot_lows:
                sorted_lows = sorted(self.all_pivot_lows, key=lambda p: p.index, reverse=True)
                if sorted_lows:
                    most_recent_pivot = sorted_lows[0]
                    self.active_pivot_low_price = most_recent_pivot.price
                    logger.debug(f"SMCStrategy {self.name}: Active pivot low = {self.active_pivot_low_price} "
                               f"(index={most_recent_pivot.index}, from {len(self.all_pivot_lows)} total pivots)")
        
        elif emit_on_upper == "BOS":
            # Track BOS event line (most recent BOS)
            for event in reversed(self.all_events):  # Start from most recent
                if event.event_type == "BOS":
                    self.active_bos_price = event.price
                    break
        
        elif emit_on_upper in ("CHOCH", "CHoCH"):
            # Track CHoCH event line - MT5 logic for selecting active CHoCH
            # MT5 appears to use: The CHoCH of the same direction that occurred 
            # BEFORE the most recent opposite-direction CHoCH
            # This ensures the CHoCH is still relevant to the current market structure
            
            choch_events = [e for e in self.all_events if e.event_type == "CHoCH"]
            
            if choch_events:
                # Find the most recent CHoCH
                most_recent_choch = choch_events[-1]
                most_recent_direction = most_recent_choch.direction
                
                # Find the most recent opposite-direction CHoCH
                most_recent_opposite = None
                for event in reversed(self.all_events):
                    if event.event_type == "CHoCH" and event.direction != most_recent_direction:
                        most_recent_opposite = event
                        break
                
                if most_recent_opposite:
                    # There's an opposite-direction CHoCH
                    # Find the CHoCH of the same direction as most_recent that occurred BEFORE the opposite
                    opposite_index = self.all_events.index(most_recent_opposite)
                    
                    # Look backwards from the opposite event for a CHoCH of the same direction
                    for i in range(opposite_index - 1, -1, -1):
                        event = self.all_events[i]
                        if event.event_type == "CHoCH" and event.direction == most_recent_direction:
                            # event.price is the close price of the candle that broke the pivot
                            self.active_choch_price = event.price
                            logger.debug(f"SMCStrategy {self.name}: Found CHoCH event at price {event.price} "
                                       f"(direction={event.direction}, before opposite {most_recent_opposite.direction} "
                                       f"at {most_recent_opposite.price}), setting active_choch_price")
                            break
                    
                    # If we didn't find one before the opposite, use the most recent of the same direction
                    if self.active_choch_price is None:
                        self.active_choch_price = most_recent_choch.price
                        logger.debug(f"SMCStrategy {self.name}: Using most recent CHoCH at price {most_recent_choch.price} "
                                   f"(no same-direction CHoCH found before opposite)")
                else:
                    # No opposite-direction CHoCH found, use most recent
                    self.active_choch_price = most_recent_choch.price
                    logger.debug(f"SMCStrategy {self.name}: Found CHoCH event at price {most_recent_choch.price}, "
                               f"setting active_choch_price (no opposite found, index={most_recent_choch.index})")
            else:
                logger.debug(f"SMCStrategy {self.name}: No CHoCH events found in {len(self.all_events)} total events")
        
        elif emit_on_upper == "BOTH":
            # Track both BOS and CHoCH lines
            for event in reversed(self.all_events):  # Start from most recent
                if event.event_type == "BOS" and self.active_bos_price is None:
                    self.active_bos_price = event.price
                elif event.event_type == "CHoCH" and self.active_choch_price is None:
                    self.active_choch_price = event.price
                
                # Stop when both are found
                if self.active_bos_price is not None and self.active_choch_price is not None:
                    break

    def _resolve_operand(self, field: str, current_price: float, ohlc: Dict, market_data: Dict = None) -> Optional[float]:
        """
        Resolve operand using unified indicator resolver.
        Falls back to internal SMC tracking if unified resolver doesn't have SMC pivots.
        
        For tick-based cross detection, current_price is the live tick/LTP, not candle close.
        """
        # Build context for unified resolver
        # IMPORTANT: Use current_price (live tick/LTP) for "price" and "current_price" fields
        # This allows intrabar cross detection
        context = {
            "price": current_price,  # Live tick/LTP for cross detection
            "ohlc": ohlc if ohlc else {},
        }
        
        # Add SMC pivots from internal state
        smc_pivots = {}
        if self.active_pivot_high_price is not None:
            smc_pivots["pivot_high"] = self.active_pivot_high_price
        if self.active_pivot_low_price is not None:
            smc_pivots["pivot_low"] = self.active_pivot_low_price
        if self.active_choch_price is not None:
            # CHoCH price = close price of candle that broke the pivot (confirmation level)
            smc_pivots["choch_price"] = self.active_choch_price
        if self.active_bos_price is not None:
            smc_pivots["bos_price"] = self.active_bos_price
        context["smc_pivots"] = smc_pivots
        
        # Add market_data context if available (may override internal pivots)
        if market_data:
            # Use market_data SMC pivots if available, otherwise use internal
            if "smc_pivots" in market_data and market_data["smc_pivots"]:
                context["smc_pivots"] = market_data["smc_pivots"]
            context["vwap"] = market_data.get("vwap")
            context["ema"] = market_data.get("ema")
            context["indicators"] = market_data.get("indicators", {})
        
        # Try unified resolver first
        from .unified_indicator_resolver import resolve_operand
        result = resolve_operand(field, context)
        if result is not None:
            return result
        
        return None

    def _evaluate_filter_condition(self, cond: Dict, current_price: float, ohlc: Dict, 
                                  prev_price: Optional[float], market_data: Dict = None) -> bool:
        """Evaluate a single filter condition"""
        # Support both naming conventions: left_field/right_field and left_operand/right_operand
        left_field = cond.get("left_field") or cond.get("left_operand")
        right_field = cond.get("right_field") or cond.get("right_operand")
        
        left = self._resolve_operand(left_field, current_price, ohlc, market_data)
        right = self._resolve_operand(right_field, current_price, ohlc, market_data)
        
        if left is None or right is None:
            logger.debug(f"SMCStrategy {self.name}: Filter condition failed - left={left}, right={right} (fields: {left_field}, {right_field})")
            return False
        
        op = cond.get("operator", "").lower().replace("_", " ").strip()
        # Normalize operator names
        if op in ("crosses above", "crosses_above", "crossover"):
            if prev_price is None:
                return False
            result = prev_price < right <= left
            logger.debug(f"SMCStrategy {self.name}: Crosses Above check - prev={prev_price}, right={right}, left={left}, result={result}")
            return result
        elif op in ("crosses under", "crosses_under", "crossunder"):
            if prev_price is None:
                logger.debug(f"SMCStrategy {self.name}: Crosses Under check FAILED - prev_price is None")
                return False
            result = prev_price > right >= left
            logger.debug(f"SMCStrategy {self.name}: Crosses Under check - prev={prev_price:.5f}, right={right:.5f}, left={left:.5f}, "
                       f"check1(prev>right)={prev_price > right}, check2(right>=left)={right >= left}, result={result}")
            return result
        elif op == "any_cross":
            if prev_price is None:
                return False
            return (prev_price < right <= left) or (prev_price > right >= left)
        elif op == ">":
            return left > right
        elif op == "<":
            return left < right
        elif op == ">=":
            return left >= right
        elif op == "<=":
            return left <= right
        elif op == "==":
            return abs(left - right) < 1e-5
        else:
            logger.warning(f"SMCStrategy {self.name}: Unknown operator '{op}' in filter condition")
            return False

    def _evaluate_filter_chain(self, filters: List[Dict], current_price: float, ohlc: Dict, 
                              market_data: Dict = None) -> bool:
        """Evaluate a chain of filter conditions with AND/OR connectors"""
        if not filters:
            return True
        
        cumulative = None
        prev_connector = None
        for cond in filters:
            res = self._evaluate_filter_condition(cond, current_price, ohlc, self._prev_filter_price, market_data)
            if cumulative is None:
                cumulative = res
            else:
                connector = prev_connector or "OR"
                if connector == "AND":
                    cumulative = cumulative and res
                else:
                    cumulative = cumulative or res
            prev_connector = cond.get("connector", "OR")
        return bool(cumulative)

    def generate_signal(self, market_data: Dict) -> Optional[str]:
        """
        Generate trading signal based on SMC analysis and user-defined conditions.
        
        Uses TICK/LTP for cross detection (intrabar signals) while computing pivots/events
        only when a new bar forms (for efficiency and MT5 parity).
        
        The strategy does NOT auto-generate signals on BOS/CHoCH events.
        Instead, it evaluates user-defined conditions that can reference SMC prices.
        """
        # Get candles on strategy timeframe
        candles = self._get_candles(count=300)
        if not candles:
            # Fallback to rates provided by engine (might be on M1)
            candles = market_data.get("rates") or []

        if not candles or len(candles) < 20:
            return None

        # Check if we have a new bar (recompute pivots/events only on bar change)
        current_bar_time = candles[-1].get('time')
        is_new_bar = (self._last_bar_time is None or current_bar_time != self._last_bar_time)
        
        if is_new_bar:
            # Extract OHLC arrays
            opens, highs, lows, closes = extract_ohlc_arrays(candles)
            
            # Update pivots (tracks all pivots, not just last)
            self._update_pivots(highs, lows)
            
            # Detect structure events chronologically (for correct bias tracking)
            self._detect_structure_chronological(candles, opens, highs, lows, closes)
            
            # Update active lines based on emit_on setting
            # This uses the pivot lists to find most recent unbroken pivots (MT5 logic)
            self._update_active_lines()
            
            # Update cached bar time
            self._last_bar_time = current_bar_time
            
            logger.debug(f"SMCStrategy {self.name}: New bar detected, pivots updated - "
                       f"pivot_low={self.active_pivot_low_price}, pivot_high={self.active_pivot_high_price}, "
                       f"choch={self.active_choch_price}, bos={self.active_bos_price}")
        
        # Get CURRENT TICK/LTP price (not candle close) for cross detection
        current_price = market_data.get("current_price")
        if current_price is None:
            # Fallback to last candle close if no tick price available
            current_price = float(candles[-1].get('close', 0))
        
        # Get last OHLC for context
        last_ohlc = {
            "open": float(candles[-1].get('open', 0)),
            "high": float(candles[-1].get('high', 0)),
            "low": float(candles[-1].get('low', 0)),
            "close": float(candles[-1].get('close', 0)),
        }
        
        # Build market_data context for unified resolver
        strategy_market_data = {
            "smc_pivots": {
                "pivot_high": self.active_pivot_high_price,
                "pivot_low": self.active_pivot_low_price,
                "choch_price": self.active_choch_price,
                "bos_price": self.active_bos_price,
            },
            "ohlc": last_ohlc,
            "indicators": market_data.get("indicators", {}) if isinstance(market_data, dict) else {}
        }
        
        # Evaluate buy conditions using LIVE TICK/LTP
        if self.buy_filters:
            # Filter out disabled conditions
            active_buy_filters = [f for f in self.buy_filters if f.get("enabled", True)]
            if active_buy_filters:
                buy_result = self._evaluate_filter_chain(active_buy_filters, current_price, last_ohlc, strategy_market_data)
                logger.debug(f"SMCStrategy {self.name}: Buy filter evaluation - result={buy_result}, "
                           f"active_choch_price={self.active_choch_price}, current_price={current_price:.5f}, "
                           f"prev_price={self._prev_filter_price}, filters={len(active_buy_filters)}")
                if buy_result:
                    logger.info(f"SMCStrategy {self.name}: ✅ Buy filter condition met! LTP={current_price:.5f}, "
                              f"prev={self._prev_filter_price}, CHoCH={self.active_choch_price}")
                    self._prev_filter_price = current_price
                    return "BUY"
                elif self.active_choch_price is None:
                    # Count CHoCH events
                    choch_count = sum(1 for e in self.all_events if e.event_type == "CHoCH")
                    logger.debug(f"SMCStrategy {self.name}: No CHoCH price available yet (emit_on={self.emit_on}, total_events={len(self.all_events)}, choch_events={choch_count})")
        
        # Evaluate sell conditions using LIVE TICK/LTP
        if self.sell_filters:
            # Filter out disabled conditions
            active_sell_filters = [f for f in self.sell_filters if f.get("enabled", True)]
            if active_sell_filters:
                sell_result = self._evaluate_filter_chain(active_sell_filters, current_price, last_ohlc, strategy_market_data)
                logger.debug(f"SMCStrategy {self.name}: Sell filter evaluation - result={sell_result}, "
                           f"current_price={current_price:.5f}, prev_price={self._prev_filter_price}, "
                           f"pivot_low={self.active_pivot_low_price}")
                if sell_result:
                    logger.info(f"SMCStrategy {self.name}: ✅ Sell filter condition met! LTP={current_price:.5f}, "
                              f"prev={self._prev_filter_price}, pivot_low={self.active_pivot_low_price}")
                    self._prev_filter_price = current_price
                    return "SELL"
        
        # Update previous price for next tick
        self._prev_filter_price = current_price
        return None

    def to_dict(self) -> Dict:
        """Convert strategy to dictionary for serialization"""
        base = super().to_dict()
        base.update({
            "strategy_type": "smc",
            "timeframe": self.timeframe,
            "pivot_left": self.pivot_left,
            "pivot_right": self.pivot_right,
            "emit_on": self.emit_on,
            "buy_filters": self.buy_filters,
            "sell_filters": self.sell_filters,
        })
        return base

    @classmethod
    def from_dict(cls, data: Dict, mt5_connector=None) -> "SMCStrategy":
        """Create strategy instance from dictionary"""
        strategy = cls(
            name=data["name"],
            symbol=data["symbol"],
            timeframe=data.get("timeframe"),
            pivot_left=data.get("pivot_left", 2),
            pivot_right=data.get("pivot_right", 2),
            emit_on=data.get("emit_on", "NONE"),
            buy_filters=data.get("buy_filters", []),
            sell_filters=data.get("sell_filters", []),
        )
        strategy.enabled = data.get("enabled", False)
        strategy.set_mt5_connector(mt5_connector)
        strategy.entry_conditions_text = [
            f"SMC: emit_on={strategy.emit_on}, pivots={strategy.pivot_left}/{strategy.pivot_right}"
        ]

        # Restore common configuration (backward compatible)
        strategy.trade_monitoring_mode = data.get("trade_monitoring_mode", getattr(strategy, "trade_monitoring_mode", "LTP"))
        strategy.lot_size = data.get("lot_size", getattr(strategy, "lot_size", None))
        strategy.sl_type = data.get("sl_type", getattr(strategy, "sl_type", None))
        strategy.sl_value = data.get("sl_value", 20.0)
        strategy.sl_enabled = data.get("sl_enabled", True)
        strategy.use_ratio = data.get("use_ratio", True)
        strategy.tp_value = data.get("tp_value", 40.0)
        strategy.tp_enabled = data.get("tp_enabled", True)

        # Advanced Risk Management
        strategy.enable_trailing_sl = data.get("enable_trailing_sl", getattr(strategy, "enable_trailing_sl", False))
        strategy.trailing_sl_gap = data.get("trailing_sl_gap", getattr(strategy, "trailing_sl_gap", 0.0))
        strategy.enable_profit_lock = data.get("enable_profit_lock", getattr(strategy, "enable_profit_lock", False))
        strategy.profit_lock_trigger = data.get("profit_lock_trigger", getattr(strategy, "profit_lock_trigger", 0.0))
        strategy.profit_lock_value = data.get("profit_lock_value", getattr(strategy, "profit_lock_value", 0.0))
        strategy.profit_trail_step = data.get("profit_trail_step", getattr(strategy, "profit_trail_step", 0.0))
        strategy.profit_trail_amount = data.get("profit_trail_amount", getattr(strategy, "profit_trail_amount", 0.0))

        # Trail Wait & Trade (W&T)
        strategy.enable_wt = data.get("enable_wt", getattr(strategy, "enable_wt", False))
        strategy.wt_value = data.get("wt_value", getattr(strategy, "wt_value", 0.0))
        strategy.wt_is_percentage = data.get("wt_is_percentage", getattr(strategy, "wt_is_percentage", False))

        # Position preservation
        strategy.preserve_position = data.get("preserve_position", getattr(strategy, "preserve_position", False))

        return strategy
