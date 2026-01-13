"""
SMMA Trading Strategy
Trading strategy based on Smoothed Moving Average (SMMA) with auto-generated entry signals.
Matches MT5 indicator behavior exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import logging

import MetaTrader5 as mt5

from .base_strategy import BaseStrategy
from ..indicators.smma import SMMA

logger = logging.getLogger(__name__)


@dataclass
class SMMASnapshot:
    """SMMA indicator snapshot for UI display"""
    smma_value: Optional[float]
    high: float  # High of crossover candle (buy entry level)
    low: float   # Low of crossover candle (buy entry level)
    high_s: float  # High of crossunder candle (sell entry level)
    low_s: float   # Low of crossunder candle (sell entry level)
    valid_buy: bool
    valid_sell: bool
    time: Optional[datetime]


class SMMAStrategy(BaseStrategy):
    """
    Alert-driven SMMA strategy that listens for MT5 indicator alerts.
    
    This strategy does NOT calculate signals internally. Instead, it:
    - Listens for alerts from MT5 SMMA indicator
    - When alert is received, triggers trade with configured SL/TP/lot size
    - All configuration (SL, TP, lot size, timeframe, direction) is handled in platform
    
    The MT5 indicator sends alerts when buy/sell entry arrows appear.
    """
    
    def __init__(
        self,
        name: str,
        symbol: str,
        timeframe: int = None,
        length: int = 7,
        source_price: str = "close",
    ):
        """
        Initialize SMMA Strategy
        
        Args:
            name: Strategy name
            symbol: Trading symbol
            timeframe: MT5 timeframe (default: M1)
            length: SMMA period (default: 7)
            source_price: Source price type - "close", "open", "high", "low", 
                         "median", "typical", "weighted"
        """
        super().__init__(name, symbol)
        self.timeframe = timeframe or mt5.TIMEFRAME_M1
        self.length = int(length)
        self.source_price = source_price.lower()
        
        # Initialize SMMA indicator
        self.smma_indicator = SMMA(period=self.length, source_price=self.source_price)
        self.add_indicator("SMMA", self.smma_indicator)
        
        self.mt5_connector = None
        
        # State variables (persistent like MT5 'var' variables)
        # These track the signal/entry state across ticks
        self.entry_high: float = 0.0
        self.entry_low: float = 0.0
        self.entry_high_s: float = 0.0
        self.entry_low_s: float = 0.0
        self.high: float = 0.0  # High of crossover candle (buy entry level)
        self.low: float = 0.0   # Low of crossover candle (buy entry level)
        self.high_s: float = 0.0  # High of crossunder candle (sell entry level)
        self.low_s: float = 0.0   # Low of crossunder candle (sell entry level)
        self.valid_buy: bool = False
        self.valid_sell: bool = False
        self.f1: bool = False  # Flag to track buy signal state
        self.f2: bool = False  # Flag to track sell signal state
        
        # Track previous values for cross detection
        self.previous_close: Optional[float] = None
        self.previous_smma: Optional[float] = None
        
        # Snapshot caching for UI
        self._last_snapshot_at: Optional[datetime] = None
        self._last_snapshot: Optional[SMMASnapshot] = None
        
        # Alert-driven mode
        self.alert_driven = True  # This strategy is alert-driven
        self.last_alert_time: Optional[datetime] = None
    
    def set_mt5_connector(self, mt5_connector) -> None:
        """Set MT5 connector"""
        old_connector = self.mt5_connector
        self.mt5_connector = mt5_connector
        # Initialize state from historical candles when connector is set (or changed)
        if mt5_connector and (old_connector is None or old_connector != mt5_connector):
            self._initialize_state_from_history()
    
    def _initialize_state_from_history(self):
        """Initialize strategy state by processing historical candles"""
        if not self.mt5_connector or not self.mt5_connector.is_connected():
            return
        
        # Check trade direction - reset f1/f2 if strategy is direction-restricted
        trade_direction = getattr(self, 'trade_direction', 'both')
        if trade_direction == 'short':
            # Short-only: reset any buy state
            self.f1 = False
            self.high = 0.0
            self.low = 0.0
            self.valid_buy = False
            self.entry_high = 0.0
            self.entry_low = 0.0
        elif trade_direction == 'long':
            # Long-only: reset any sell state
            self.f2 = False
            self.high_s = 0.0
            self.low_s = 0.0
            self.valid_sell = False
            self.entry_high_s = 0.0
            self.entry_low_s = 0.0
        
        candles = self._get_candles(count=max(200, self.length * 10 + 50))
        if not candles or len(candles) < self.length + 1:
            return
        
        # Compute SMMA values
        smma_values = self._compute_smma_values(candles)
        if not smma_values or len(smma_values) < 2:
            return
        
        # Process all candles to build up state (except the very last one, which we'll check in generate_signal)
        # Process from oldest to newest
        for i in range(self.length, len(candles) - 1):  # Skip last candle, process it in generate_signal
            if i >= len(smma_values) or smma_values[i] is None:
                continue
            
            if i == 0:
                continue
            
            prev_idx = i - 1
            if prev_idx >= len(smma_values) or smma_values[prev_idx] is None:
                continue
            
            candle = candles[i]
            prev_candle = candles[prev_idx]
            
            current_close = float(candle["close"])
            prev_close = float(prev_candle["close"])
            current_high = float(candle["high"])
            current_low = float(candle["low"])
            
            current_smma = smma_values[i]
            prev_smma = smma_values[prev_idx]
            
            # Detect crossover/crossunder
            signal_candle = self._is_crossover(current_close, prev_close, current_smma, prev_smma)
            sig_candle = self._is_crossunder(current_close, prev_close, current_smma, prev_smma)
            
            # Handle signal candle (crossover) - Buy signal
            if signal_candle and not self.f1:
                self.low = current_low
                self.high = current_high
                self.valid_buy = True
                self.valid_sell = False
                logger.debug(f"SMMAStrategy {self.name}: Historical Buy Signal detected at candle {i} - High={self.high}, Low={self.low}")
            
            # Handle signal candle (crossunder) - Sell signal
            if sig_candle and not self.f2:
                self.high_s = current_high
                self.low_s = current_low
                self.valid_buy = False
                self.valid_sell = True
                logger.debug(f"SMMAStrategy {self.name}: Historical Sell Signal detected at candle {i} - High_s={self.high_s}, Low_s={self.low_s}")
            
            # Check for buy entry (price crosses above High)
            # MT5 logic: buy = (currentClose > High) && (prevClose <= High)
            if self.high > 0.0 and self.valid_buy and not self.f1:
                buy_entry = (current_close > self.high) and (prev_close <= self.high)
                if buy_entry:
                    self.f1 = True
                    self.f2 = False
                    self.entry_high = self.high
                    self.entry_low = self.low
                    logger.debug(f"SMMAStrategy {self.name}: Historical Buy Entry detected at candle {i}")
            
            # Check for sell entry (price crosses below Low_s)
            # MT5 logic: sell = (currentClose < Low_s) && (prevClose >= Low_s)
            if self.low_s > 0.0 and self.valid_sell and not self.f2:
                sell_entry = (current_close < self.low_s) and (prev_close >= self.low_s)
                if sell_entry:
                    self.f1 = False
                    self.f2 = True
                    self.entry_high_s = current_high
                    self.entry_low_s = current_low
                    logger.debug(f"SMMAStrategy {self.name}: Historical Sell Entry detected at candle {i}")
            
            # Reset buy levels when price crosses below entry_low
            # MT5 logic: if(entry_low > 0.0 && i + 1 < rates_total) { if(IsCrossunder(...)) }
            # Note: MT5 doesn't reset entry_high/entry_low here, only High/Low
            if self.entry_low > 0.0:
                if self._is_crossunder(current_close, prev_close, self.entry_low, self.entry_low):
                    self.high = 0.0
                    self.low = 0.0
                    self.f1 = False
                    self.valid_buy = False
                    # Note: Keep entry_high/entry_low (MT5 doesn't reset them)
                    logger.debug(f"SMMAStrategy {self.name}: Historical Buy levels reset at candle {i}")
            
            # Reset sell levels when price crosses above entry_high_s
            # MT5 logic: if(entry_high_s > 0.0 && i + 1 < rates_total) { if(IsCrossover(...)) }
            # Note: MT5 doesn't reset entry_high_s/entry_low_s here, only High_s/Low_s
            if self.entry_high_s > 0.0:
                if self._is_crossover(current_close, prev_close, self.entry_high_s, self.entry_high_s):
                    self.high_s = 0.0
                    self.low_s = 0.0
                    self.f2 = False
                    self.valid_sell = False
                    # Note: Keep entry_high_s/entry_low_s (MT5 doesn't reset them)
                    logger.debug(f"SMMAStrategy {self.name}: Historical Sell levels reset at candle {i}")
        
        # Set previous values from second-to-last candle
        if len(candles) >= 2 and len(smma_values) >= 2:
            self.previous_close = float(candles[-2]["close"])
            self.previous_smma = smma_values[-2] if smma_values[-2] is not None else None
        
        logger.info(f"SMMAStrategy {self.name}: State initialized - valid_buy={self.valid_buy}, valid_sell={self.valid_sell}, "
                   f"high={self.high}, low={self.low}, high_s={self.high_s}, low_s={self.low_s}")
    
    def _get_candles(self, count: int = 350) -> List[Dict]:
        """Get historical candles from MT5"""
        if not self.mt5_connector or not self.mt5_connector.is_connected():
            return []
        
        try:
            rates = self.mt5_connector.get_rates(self.symbol, self.timeframe, count, 0)
            if rates is None or len(rates) == 0:
                return []
            
            candles: List[Dict] = []
            for r in rates:
                candles.append({
                    "time": r["time"],
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "tick_volume": float(r.get("tick_volume", 0)),
                    "spread": float(r.get("spread", 0)),
                    "real_volume": float(r.get("real_volume", 0)),
                })
            return candles
        except Exception as e:
            logger.error(f"SMMAStrategy {self.name}: Failed to fetch candles: {e}", exc_info=True)
            return []
    
    def _compute_smma_values(self, candles: List[Dict]) -> List[Optional[float]]:
        """Compute SMMA values for candles"""
        if len(candles) < self.length:
            return []
        
        # Update indicator with candles
        self.smma_indicator.update(candles)
        return self.smma_indicator.get_values()
    
    def _is_crossover(self, current: float, previous: float, level_current: float, level_previous: float) -> bool:
        """Check if crossover occurred (price crosses above level)"""
        return current > level_current and previous <= level_previous
    
    def _is_crossunder(self, current: float, previous: float, level_current: float, level_previous: float) -> bool:
        """Check if crossunder occurred (price crosses below level)"""
        return current < level_current and previous >= level_previous
    
    def get_smma_snapshot(self) -> Optional[Dict]:
        """Get SMMA snapshot for UI display"""
        now = datetime.now()
        if self._last_snapshot_at and self._last_snapshot and (now - self._last_snapshot_at).total_seconds() < 2.0:
            s = self._last_snapshot
            return {
                "smma_value": s.smma_value,
                "high": s.high,
                "low": s.low,
                "high_s": s.high_s,
                "low_s": s.low_s,
                "valid_buy": s.valid_buy,
                "valid_sell": s.valid_sell,
                "time": s.time,
                "length": self.length,
                "source_price": self.source_price,
            }
        
        candles = self._get_candles(count=max(200, self.length * 10 + 50))
        if not candles:
            return None
        
        smma_values = self._compute_smma_values(candles)
        if not smma_values or smma_values[-1] is None:
            return None
        
        snap = SMMASnapshot(
            smma_value=smma_values[-1],
            high=self.high,
            low=self.low,
            high_s=self.high_s,
            low_s=self.low_s,
            valid_buy=self.valid_buy,
            valid_sell=self.valid_sell,
            time=candles[-1].get("time") if candles else None,
        )
        
        self._last_snapshot = snap
        self._last_snapshot_at = now
        
        return {
            "smma_value": snap.smma_value,
            "high": snap.high,
            "low": snap.low,
            "high_s": snap.high_s,
            "low_s": snap.low_s,
            "valid_buy": snap.valid_buy,
            "valid_sell": snap.valid_sell,
            "time": snap.time,
            "length": self.length,
            "source_price": self.source_price,
        }
    
    def trigger_from_alert(self, action: str, price: float) -> Optional[str]:
        """
        Trigger trade from MT5 alert (alert-driven mode)
        
        Args:
            action: "BUY" or "SELL"
            price: Entry price from alert
            
        Returns:
            "BUY" or "SELL" signal, or None if alert should be ignored
        """
        # Check if alert matches strategy direction
        if not self.should_accept_alert(action):
            logger.debug(f"SMMAStrategy {self.name}: Alert {action} ignored - direction mismatch")
            return None
        
        # Check for duplicate alerts (same action within same minute)
        now = datetime.now()
        if self.last_alert_time and (now - self.last_alert_time).total_seconds() < 60:
            logger.debug(f"SMMAStrategy {self.name}: Duplicate alert ignored (within 60 seconds)")
            return None
        
        self.last_alert_time = now
        
        logger.info(f"SMMAStrategy {self.name}: Alert received - {action} @ {price:.5f}")
        return action
    
    def should_accept_alert(self, action: str) -> bool:
        """
        Check if alert should be accepted based on strategy direction
        
        Args:
            action: "BUY" or "SELL"
            
        Returns:
            True if alert should be accepted, False otherwise
        """
        trade_direction = getattr(self, 'trade_direction', 'both')
        action_upper = action.upper()
        
        if trade_direction == 'long':
            return action_upper == 'BUY'
        elif trade_direction == 'short':
            return action_upper == 'SELL'
        else:  # 'both'
            return action_upper in ['BUY', 'SELL']
    
    def generate_signal(self, market_data: Dict) -> Optional[str]:
        """
        Generate signal - DISABLED for alert-driven mode
        
        This method is kept for backward compatibility but returns None.
        The strategy now relies on trigger_from_alert() for entry signals.
        
        Returns:
            None (strategy is alert-driven)
        """
        # Alert-driven strategy does not calculate signals internally
        # Signals come from MT5 indicator alerts via trigger_from_alert()
        return None
        
        # Compute SMMA values
        smma_values = self._compute_smma_values(candles)
        if not smma_values or len(smma_values) < 2:
            return None
        
        # Get current and previous values (latest is at index -1)
        current_close = float(candles[-1]["close"])
        prev_close = float(candles[-2]["close"]) if len(candles) >= 2 else current_close
        current_high = float(candles[-1]["high"])
        current_low = float(candles[-1]["low"])
        
        current_smma = smma_values[-1]
        prev_smma = smma_values[-2] if len(smma_values) >= 2 else current_smma
        
        if current_smma is None or prev_smma is None:
            return None
        
        # Update snapshot cache
        candles_snap = self._get_candles(count=max(200, self.length * 10 + 50))
        if candles_snap:
            self._last_snapshot = SMMASnapshot(
                smma_value=current_smma,
                high=self.high,
                low=self.low,
                high_s=self.high_s,
                low_s=self.low_s,
                valid_buy=self.valid_buy,
                valid_sell=self.valid_sell,
                time=candles_snap[-1].get("time") if candles_snap else None,
            )
            self._last_snapshot_at = datetime.now()
        
        # Detect crossover/crossunder (signal candles)
        signal_candle = self._is_crossover(current_close, prev_close, current_smma, prev_smma)
        sig_candle = self._is_crossunder(current_close, prev_close, current_smma, prev_smma)
        
        # Check trade direction to prevent conflicting signals
        trade_direction = getattr(self, 'trade_direction', 'both')
        
        # Handle signal candle (crossover) - Buy signal
        # MT5 logic: if(signal_candle && !f1)
        # Only update high/low when NOT already in buy state (matching MT5 exactly)
        # Also skip if strategy is short-only (can't take buy signals)
        if signal_candle and not self.f1 and trade_direction != 'short':
            self.low = current_low
            self.high = current_high
            self.valid_buy = True
            self.valid_sell = False
            logger.debug(f"SMMAStrategy {self.name}: Buy Signal detected (crossover) - High={self.high}, Low={self.low}")
        
        # Handle signal candle (crossunder) - Sell signal
        # MT5 logic: if(sig_candle && !f2)
        # Only update high_s/low_s when NOT already in sell state (matching MT5 exactly)
        # Also skip if strategy is long-only (can't take sell signals)
        if sig_candle and not self.f2 and trade_direction != 'long':
            self.high_s = current_high
            self.low_s = current_low
            self.valid_buy = False
            self.valid_sell = True
            # For short-only strategies, ensure f1 is reset when sell signal detected
            if trade_direction == 'short' and self.f1:
                self.f1 = False
                self.entry_high = 0.0
                self.entry_low = 0.0
                logger.debug(f"SMMAStrategy {self.name}: Reset f1 (buy state) for short-only strategy")
            logger.debug(f"SMMAStrategy {self.name}: Sell Signal detected (crossunder) - High_s={self.high_s}, Low_s={self.low_s}")
        
        # Buy condition: Price crosses above the High of the crossover candle
        # MT5 logic: buy = (currentClose > High) && (prevClose <= High)
        # Use exact MT5 logic: current close > High AND previous close <= High
        buy_entry = False
        if self.high > 0.0 and self.valid_buy and not self.f1:
            # Exact MT5 entry detection logic
            buy_entry = (current_close > self.high) and (prev_close <= self.high)
            if buy_entry:
                logger.info(f"SMMAStrategy {self.name}: Buy Entry detected - Price crossed above High={self.high}")
        
        # Sell condition: Price crosses below the Low of the crossunder candle
        # MT5 logic: sell = (currentClose < Low_s) && (prevClose >= Low_s)
        # Use exact MT5 logic: current close < Low_s AND previous close >= Low_s
        sell_entry = False
        if self.low_s > 0.0 and self.valid_sell and not self.f2:
            # Exact MT5 entry detection logic
            sell_entry = (current_close < self.low_s) and (prev_close >= self.low_s)
            if sell_entry:
                logger.info(f"SMMAStrategy {self.name}: Sell Entry detected - Price crossed below Low_s={self.low_s}")
        
        # Handle buy entry (filter by direction)
        if buy_entry:
            # Check direction filtering
            trade_direction = getattr(self, 'trade_direction', 'both')
            if trade_direction == 'short':
                # Short-only mode: ignore buy entry
                logger.debug(f"SMMAStrategy {self.name}: Buy Entry ignored (Short-only mode)")
            else:
                self.f1 = True
                self.f2 = False
                self.entry_high = self.high
                self.entry_low = self.low
                logger.info(f"SMMAStrategy {self.name}: ✅ Buy Entry detected - Price crossed above High={self.high}")
                self.previous_close = current_close
                self.previous_smma = current_smma
                return "BUY"
        
        # Reset buy levels when price crosses below entry_low
        # MT5 logic: if(entry_low > 0.0 && i + 1 < rates_total) { if(IsCrossunder(...)) }
        # Note: MT5 doesn't reset entry_high/entry_low here, only High/Low
        if self.entry_low > 0.0:
            if self._is_crossunder(current_close, prev_close, self.entry_low, self.entry_low):
                self.high = 0.0
                self.low = 0.0
                self.f1 = False
                self.valid_buy = False
                # Note: Keep entry_high/entry_low (MT5 doesn't reset them)
                logger.debug(f"SMMAStrategy {self.name}: Buy levels reset - price crossed below entry_low")
        
        # Handle sell entry (filter by direction)
        if sell_entry:
            # Check direction filtering
            trade_direction = getattr(self, 'trade_direction', 'both')
            if trade_direction == 'long':
                # Long-only mode: ignore sell entry
                logger.debug(f"SMMAStrategy {self.name}: Sell Entry ignored (Long-only mode)")
            else:
                self.entry_high_s = current_high
                self.entry_low_s = current_low
                self.f1 = False
                self.f2 = True
                logger.info(f"SMMAStrategy {self.name}: ✅ Sell Entry detected - Price crossed below Low_s={self.low_s}")
                self.previous_close = current_close
                self.previous_smma = current_smma
                return "SELL"
        
        # Reset sell levels when price crosses above entry_high_s
        # MT5 logic: if(entry_high_s > 0.0 && i + 1 < rates_total) { if(IsCrossover(...)) }
        # Note: MT5 doesn't reset entry_high_s/entry_low_s here, only High_s/Low_s
        if self.entry_high_s > 0.0:
            if self._is_crossover(current_close, prev_close, self.entry_high_s, self.entry_high_s):
                self.high_s = 0.0
                self.low_s = 0.0
                self.f2 = False
                self.valid_sell = False
                # Note: Keep entry_high_s/entry_low_s (MT5 doesn't reset them)
                logger.debug(f"SMMAStrategy {self.name}: Sell levels reset - price crossed above entry_high_s")
        
        # Update previous values for next tick
        self.previous_close = current_close
        self.previous_smma = current_smma
        
        return None
    
    def to_dict(self) -> Dict:
        """Convert strategy to dictionary for serialization"""
        base_dict = super().to_dict()
        base_dict.update({
            "strategy_type": "smma",
            "timeframe": self.timeframe,
            "length": self.length,
            "source_price": self.source_price,
            "trade_direction": getattr(self, 'trade_direction', 'both'),
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict, mt5_connector=None) -> "SMMAStrategy":
        """Create strategy from dictionary"""
        strategy = cls(
            name=data["name"],
            symbol=data["symbol"],
            timeframe=data.get("timeframe"),
            length=int(data.get("length", 7)),
            source_price=data.get("source_price", "close"),
        )
        strategy.enabled = data.get("enabled", False)
        strategy.set_mt5_connector(mt5_connector)
        
        # Restore direction
        strategy.trade_direction = data.get("trade_direction", getattr(strategy, "trade_direction", "both"))
        
        # Restore common configuration (backward compatible)
        strategy.trade_monitoring_mode = data.get("trade_monitoring_mode", getattr(strategy, "trade_monitoring_mode", "LTP"))
        strategy.lot_size = data.get("lot_size", getattr(strategy, "lot_size", None))
        strategy.sl_type = data.get("sl_type", getattr(strategy, "sl_type", None))
        strategy.sl_value = data.get("sl_value", getattr(strategy, "sl_value", 20.0))
        strategy.sl_enabled = data.get("sl_enabled", getattr(strategy, "sl_enabled", True))
        strategy.use_ratio = data.get("use_ratio", getattr(strategy, "use_ratio", True))
        strategy.tp_value = data.get("tp_value", getattr(strategy, "tp_value", 40.0))
        strategy.tp_enabled = data.get("tp_enabled", getattr(strategy, "tp_enabled", True))
        
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
