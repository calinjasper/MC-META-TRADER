"""
VWAP Trading Strategy
Trading strategy based on Volume Weighted Average Price with multiple entry strategies
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
import MetaTrader5 as mt5

from .base_strategy import BaseStrategy
from ..indicators.vwap import VWAP
from ..indicators.volume import Volume
from ..indicators.pattern_detector import PatternDetector

logger = logging.getLogger(__name__)


class VWAPCondition:
    """Represents a single VWAP-based condition"""
    
    def __init__(
        self,
        price_reference: str,
        operator: str,
        vwap_field: str = None,
        value: float = None,
        left_field: str = None,
        right_field: str = None,
        connector: str = "OR",
    ):
        """
        Initialize a VWAP condition
        
        Args:
            price_reference: "Current Price", "VWAP", "Upper Band", "Lower Band"
            operator: ">", "<", ">=", "<=", "==", "Crosses Above", "Crosses Under", "Within Band", "Outside Band"
            vwap_field: "vwap", "upper_band_1", "upper_band_1.5", "upper_band_2", "lower_band_1", etc.
            value: Comparison value (optional, used for direct comparisons)
            left_field/right_field: operands selected in UI
            connector: logical connector to next condition
        """
        self.price_reference = price_reference
        self.operator = operator
        self.vwap_field = vwap_field
        self.value = value
        self.left_field = left_field or "price"
        self.right_field = right_field or vwap_field
        self.connector = connector or "OR"
        self.previous_state = None  # For cross detection
        self.previous_band_value = None  # Track previous band value for accurate cross detection
    
    def get_threshold(self, vwap_data: Dict) -> Optional[float]:
        """Get the threshold value for comparison"""
        if self.vwap_field:
            # Parse vwap_field (e.g., "upper_band_1.5" -> get upper band with 1.5 STD)
            if self.vwap_field.startswith('upper_band_'):
                std_dev = float(self.vwap_field.replace('upper_band_', ''))
                bands = vwap_data.get('bands', {})
                return bands.get(std_dev, {}).get('upper')
            elif self.vwap_field.startswith('lower_band_'):
                std_dev = float(self.vwap_field.replace('lower_band_', ''))
                bands = vwap_data.get('bands', {})
                return bands.get(std_dev, {}).get('lower')
            elif self.vwap_field == 'vwap':
                return vwap_data.get('vwap')
        elif self.value is not None:
            return self.value
        return None

    def _resolve_operand(self, field: str, current_price: float, vwap_data: Dict) -> Optional[float]:
        if field == "price":
            return current_price
        if field == "vwap":
            return vwap_data.get('vwap') if vwap_data else None
        if field and field.startswith("upper_band_"):
            std_dev = float(field.replace('upper_band_', ''))
            return vwap_data.get('bands', {}).get(std_dev, {}).get('upper') if vwap_data else None
        if field and field.startswith("lower_band_"):
            std_dev = float(field.replace('lower_band_', ''))
            return vwap_data.get('bands', {}).get(std_dev, {}).get('lower') if vwap_data else None
        return self.value
    
    def evaluate(self, current_price: float, vwap_data: Dict, previous_price: Optional[float] = None) -> bool:
        """Evaluate the condition"""
        left_val = self._resolve_operand(self.left_field, current_price, vwap_data)
        right_val = self._resolve_operand(self.right_field, current_price, vwap_data)
        if left_val is None or right_val is None:
            return False
        
        # Handle special operators
        if self.operator == "Within Band":
            if self.right_field and 'band' in self.right_field:
                std_dev = float(self.right_field.replace('upper_band_', '').replace('lower_band_', ''))
                bands = vwap_data.get('bands', {}).get(std_dev, {}) if vwap_data else {}
                upper = bands.get('upper')
                lower = bands.get('lower')
                if upper is not None and lower is not None:
                    return lower <= left_val <= upper
            return False
        
        if self.operator == "Outside Band":
            if self.right_field and 'band' in self.right_field:
                std_dev = float(self.right_field.replace('upper_band_', '').replace('lower_band_', ''))
                bands = vwap_data.get('bands', {}).get(std_dev, {}) if vwap_data else {}
                upper = bands.get('upper')
                lower = bands.get('lower')
                if upper is not None and lower is not None:
                    return left_val > upper or left_val < lower
            return False
        
        if self.operator == "Crosses Above":
            if previous_price is not None:
                was_below = previous_price < right_val
                is_above = left_val > right_val
                if was_below and is_above:
                    self.previous_state = True
                    self.previous_band_value = right_val
                    return True
            self.previous_state = left_val > right_val
            self.previous_band_value = right_val
            return False
        
        if self.operator == "Crosses Under":
            if previous_price is not None:
                was_above = previous_price > right_val
                is_below = left_val < right_val
                if was_above and is_below:
                    self.previous_state = False
                    self.previous_band_value = right_val
                    return True
            self.previous_state = left_val < right_val
            self.previous_band_value = right_val
            return False

        if self.operator == "Any_Cross":
            if previous_price is not None:
                crossed_up = previous_price < right_val <= left_val
                crossed_down = previous_price > right_val >= left_val
                if crossed_up or crossed_down:
                    self.previous_state = left_val >= right_val
                    return True
            self.previous_state = left_val >= right_val
            return False
        
        # Handle simple comparison operators
        if self.operator == ">":
            return left_val > right_val
        if self.operator == "<":
            return left_val < right_val
        if self.operator == ">=":
            return left_val >= right_val
        if self.operator == "<=":
            return left_val <= right_val
        if self.operator == "==":
            epsilon = 0.00001
            return abs(left_val - right_val) < epsilon
        
        return False
    
    def to_dict(self) -> Dict:
        """Convert condition to dictionary for serialization"""
        return {
            'price_reference': self.price_reference,
            'operator': self.operator,
            'vwap_field': self.vwap_field,
            'value': self.value,
            'left_field': self.left_field,
            'right_field': self.right_field,
            'connector': self.connector
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'VWAPCondition':
        """Create condition from dictionary"""
        return cls(
            price_reference=data.get('price_reference', 'Current Price'),
            operator=data.get('operator', '>'),
            vwap_field=data.get('vwap_field'),
            value=data.get('value'),
            left_field=data.get('left_field'),
            right_field=data.get('right_field'),
            connector=data.get('connector', data.get('logical_connector', 'OR'))
        )


class VWAPStrategy(BaseStrategy):
    """Trading strategy based on VWAP with multiple entry strategies"""
    
    def __init__(self, name: str, symbol: str, session_type: str = 'NY', timeframe: int = None):
        """
        Initialize VWAP strategy
        
        Args:
            name: Strategy name
            symbol: Trading symbol
            session_type: Trading session ('NY', 'London', 'Asia', 'All')
            timeframe: MT5 timeframe constant
        """
        super().__init__(name, symbol)
        self.session_type = session_type
        self.timeframe = timeframe or mt5.TIMEFRAME_M1
        
        # VWAP and Volume indicators
        self.vwap_indicator: Optional[VWAP] = None
        self.volume_indicator: Optional[Volume] = None
        
        # Standard deviation bands configuration
        self.std_bands: List[float] = [1.0, 1.5, 2.0]  # Default bands
        
        # Swing period for SL/TP calculation
        self.swing_period: int = 10
        
        # Entry strategy configurations
        self.enable_mean_reversion: bool = False
        self.mean_reversion_std_threshold: float = 1.5
        self.mean_reversion_pattern: str = 'Any'  # Pattern requirement
        self.mean_reversion_volume_requirement: str = 'Declining'  # 'Declining', 'Any', 'Increasing'
        
        self.enable_trend_following: bool = False
        self.trend_following_pattern: str = 'Any'
        self.trend_following_volume_requirement: str = 'Increasing'
        
        self.enable_breakout: bool = False
        self.breakout_consolidation_period: int = 5
        self.breakout_volume_requirement: str = 'Increasing'
        
        # Buy and sell conditions (simple VWAP-based)
        self.buy_conditions: List[VWAPCondition] = []
        self.sell_conditions: List[VWAPCondition] = []
        
        # Track previous price for cross detection
        self.previous_price: Optional[float] = None
        
        # Track previous candles for pattern detection
        self.previous_candles: List[Dict] = []
        self.max_candles_history = 20
        
        # Reference to MT5 connector for data
        self.mt5_connector = None
    
    def set_mt5_connector(self, mt5_connector):
        """Set reference to MT5 connector"""
        self.mt5_connector = mt5_connector
        self._initialize_indicators()
    
    def _initialize_indicators(self):
        """Initialize VWAP and Volume indicators"""
        if not self.mt5_connector:
            return
        
        self.vwap_indicator = VWAP(session_type=self.session_type, use_typical_price=True)
        self.volume_indicator = Volume(period=20)
        self.add_indicator('VWAP', self.vwap_indicator)
        self.add_indicator('Volume', self.volume_indicator)
    
    def add_buy_condition(self, condition: VWAPCondition) -> None:
        """Add a buy condition"""
        # Validation: If strategy already has sell conditions, warn but allow (for backward compatibility)
        if len(self.sell_conditions) > 0:
            logger.warning(f"Strategy {self.name} already has sell conditions. For separate buy/sell legs, strategies should have only buy OR only sell conditions.")
        self.buy_conditions.append(condition)
        logger.info(f"Added buy condition to {self.name}: {condition.operator} {condition.vwap_field or condition.value}")
    
    def add_sell_condition(self, condition: VWAPCondition) -> None:
        """Add a sell condition"""
        # Validation: If strategy already has buy conditions, warn but allow (for backward compatibility)
        if len(self.buy_conditions) > 0:
            logger.warning(f"Strategy {self.name} already has buy conditions. For separate buy/sell legs, strategies should have only buy OR only sell conditions.")
        self.sell_conditions.append(condition)
        logger.info(f"Added sell condition to {self.name}: {condition.operator} {condition.vwap_field or condition.value}")
    
    def _get_candles(self, count: int = 100) -> List[Dict]:
        """Get historical candles from MT5 using MT5Connector (handles symbol resolution)"""
        if not self.mt5_connector or not self.mt5_connector.is_connected():
            return []
        
        try:
            # Use MT5Connector.get_rates() which handles symbol case resolution
            rates = self.mt5_connector.get_rates(self.symbol, self.timeframe, count, 0)
            if rates is None or len(rates) == 0:
                logger.warning(f"Strategy {self.name}: No rates returned from MT5Connector for {self.symbol} (timeframe: {self.timeframe})")
                return []
            
            candles = []
            for rate in rates:
                candles.append({
                    'time': rate['time'] if isinstance(rate['time'], datetime) else datetime.fromtimestamp(rate['time']),
                    'open': float(rate['open']),
                    'high': float(rate['high']),
                    'low': float(rate['low']),
                    'close': float(rate['close']),
                    'tick_volume': float(rate.get('tick_volume', rate.get('volume', 1.0))),
                    'volume': float(rate.get('tick_volume', rate.get('volume', 1.0)))  # Use tick_volume as volume
                })
            
            logger.debug(f"Strategy {self.name}: Retrieved {len(candles)} candles for {self.symbol}")
            return candles
        except Exception as e:
            logger.error(f"Error getting candles for {self.symbol}: {e}", exc_info=True)
            return []
    
    def _update_indicators(self, candles: List[Dict]):
        """Update VWAP and Volume indicators with candle data"""
        if not self.vwap_indicator or not self.volume_indicator:
            return
        
        # Update indicators
        self.vwap_indicator.update(candles)
        self.volume_indicator.update(candles)
    
    def _get_vwap_data(self) -> Optional[Dict]:
        """Get current VWAP data including bands"""
        if not self.vwap_indicator:
            return None
        
        vwap_value = self.vwap_indicator.get_vwap()
        if vwap_value is None:
            return None
        
        # Calculate bands for all configured STD levels
        bands = {}
        for std_dev in self.std_bands:
            upper, lower = self.vwap_indicator.get_bands(std_dev)
            if upper is not None and lower is not None:
                bands[std_dev] = {'upper': upper, 'lower': lower}
        
        return {
            'vwap': vwap_value,
            'bands': bands,
            'session_info': self.vwap_indicator.get_session_info()
        }
    
    def _calculate_swing_high_low(self, candles: List[Dict], lookback: int = None) -> Tuple[Optional[float], Optional[float]]:
        """Calculate swing high and swing low"""
        if not candles or len(candles) < 3:
            return (None, None)
        
        lookback = lookback or self.swing_period
        lookback = min(lookback, len(candles) - 1)
        
        # Get recent candles
        recent_candles = candles[-lookback-1:]
        
        # Find swing high (local maximum)
        swing_high = None
        for i in range(1, len(recent_candles) - 1):
            high = recent_candles[i]['high']
            if (high >= recent_candles[i-1]['high'] and 
                high >= recent_candles[i+1]['high']):
                if swing_high is None or high > swing_high:
                    swing_high = high
        
        # Find swing low (local minimum)
        swing_low = None
        for i in range(1, len(recent_candles) - 1):
            low = recent_candles[i]['low']
            if (low <= recent_candles[i-1]['low'] and 
                low <= recent_candles[i+1]['low']):
                if swing_low is None or low < swing_low:
                    swing_low = low
        
        return (swing_high, swing_low)
    
    def _evaluate_mean_reversion(self, current_price: float, vwap_data: Dict, 
                                 candles: List[Dict], volume_momentum: str) -> Optional[str]:
        """Evaluate mean reversion entry strategy"""
        if not self.enable_mean_reversion:
            return None
        
        vwap = vwap_data.get('vwap')
        if vwap is None:
            return None
        
        # Check if price is >1.5 STD from VWAP
        distance_points, distance_std = self.vwap_indicator.get_distance_from_vwap(current_price)
        if distance_std is None:
            return None
        
        # Check STD threshold
        if abs(distance_std) < self.mean_reversion_std_threshold:
            return None
        
        # Check volume requirement
        if self.mean_reversion_volume_requirement == 'Declining' and volume_momentum != 'declining':
            return None
        elif self.mean_reversion_volume_requirement == 'Increasing' and volume_momentum != 'increasing':
            return None
        
        # Check for reversal pattern
        if candles and len(candles) >= 2:
            current_candle = candles[-1]
            previous_candle = candles[-2] if len(candles) > 1 else None
            pattern = PatternDetector.detect_pattern(current_candle, previous_candle)
            
            if not PatternDetector.matches_pattern(pattern, self.mean_reversion_pattern):
                return None
            
            # Check if price breaks back inside band
            # For LONG: price was below lower band, now above
            # For SHORT: price was above upper band, now below
            bands = vwap_data.get('bands', {})
            if self.mean_reversion_std_threshold in bands:
                band = bands[self.mean_reversion_std_threshold]
                upper = band.get('upper')
                lower = band.get('lower')
                
                if distance_std < 0:  # Price below VWAP
                    # Check for bullish reversal
                    if (PatternDetector.is_bullish_pattern(pattern) and 
                        current_price > lower):
                        return 'BUY'
                elif distance_std > 0:  # Price above VWAP
                    # Check for bearish reversal
                    if (PatternDetector.is_bearish_pattern(pattern) and 
                        current_price < upper):
                        return 'SELL'
        
        return None
    
    def _evaluate_trend_following(self, current_price: float, vwap_data: Dict,
                                 candles: List[Dict], volume_momentum: str) -> Optional[str]:
        """Evaluate trend following entry strategy"""
        if not self.enable_trend_following:
            return None
        
        vwap = vwap_data.get('vwap')
        if vwap is None or len(candles) < 3:
            return None
        
        # Determine trend direction
        # Check if VWAP is sloping upward (bullish) or downward (bearish)
        # Use recent candles to determine trend
        recent_prices = [c['close'] for c in candles[-5:]]
        price_trend = 'up' if recent_prices[-1] > recent_prices[0] else 'down'
        
        # Check if price is consistently above/below VWAP
        above_vwap_count = sum(1 for c in candles[-5:] if c['close'] > vwap)
        below_vwap_count = sum(1 for c in candles[-5:] if c['close'] < vwap)
        
        # Check volume requirement
        if self.trend_following_volume_requirement == 'Increasing' and volume_momentum != 'increasing':
            return None
        
        # Check for pattern at VWAP
        if candles and len(candles) >= 2:
            current_candle = candles[-1]
            previous_candle = candles[-2]
            pattern = PatternDetector.detect_pattern(current_candle, previous_candle)
            
            if not PatternDetector.matches_pattern(pattern, self.trend_following_pattern):
                return None
            
            # LONG: Price pulls back to VWAP in uptrend, bullish pattern
            if (price_trend == 'up' and above_vwap_count >= 3 and
                abs(current_price - vwap) / vwap < 0.001 and  # Near VWAP
                PatternDetector.is_bullish_pattern(pattern)):
                return 'BUY'
            
            # SHORT: Price rallies to VWAP in downtrend, bearish pattern
            if (price_trend == 'down' and below_vwap_count >= 3 and
                abs(current_price - vwap) / vwap < 0.001 and  # Near VWAP
                PatternDetector.is_bearish_pattern(pattern)):
                return 'SELL'
        
        return None
    
    def _evaluate_breakout(self, current_price: float, vwap_data: Dict,
                         candles: List[Dict], volume_momentum: str) -> Optional[str]:
        """Evaluate breakout entry strategy"""
        if not self.enable_breakout:
            return None
        
        vwap = vwap_data.get('vwap')
        if vwap is None or len(candles) < self.breakout_consolidation_period + 2:
            return None
        
        # Check volume requirement
        if self.breakout_volume_requirement == 'Increasing' and volume_momentum != 'increasing':
            return None
        
        # Check for consolidation around VWAP
        consolidation_candles = candles[-self.breakout_consolidation_period-1:-1]
        consolidation_high = max(c['high'] for c in consolidation_candles)
        consolidation_low = min(c['low'] for c in consolidation_candles)
        consolidation_range = consolidation_high - consolidation_low
        
        # Check if price was consolidating (small range relative to VWAP)
        if consolidation_range / vwap > 0.002:  # More than 0.2% range = not consolidating
            return None
        
        current_candle = candles[-1]
        previous_candle = candles[-2]
        
        # Check for breakout
        # LONG: Break above consolidation with higher lows
        if (current_candle['close'] > consolidation_high and
            current_candle['low'] > previous_candle['low']):  # Higher low
            return 'BUY'
        
        # SHORT: Break below consolidation with lower highs
        if (current_candle['close'] < consolidation_low and
            current_candle['high'] < previous_candle['high']):  # Lower high
            return 'SELL'
        
        return None

    def _evaluate_condition_chain(self, conditions: List[VWAPCondition], current_price: float, vwap_data: Dict) -> bool:
        if not conditions:
            return False
        cumulative = None
        prev_connector = None
        for cond in conditions:
            result = cond.evaluate(current_price, vwap_data, self.previous_price)
            if cumulative is None:
                cumulative = result
            else:
                connector = prev_connector or "OR"
                if connector == "AND":
                    cumulative = cumulative and result
                else:
                    cumulative = cumulative or result
            prev_connector = cond.connector or "OR"
        return bool(cumulative)
    
    def generate_signal(self, market_data: Dict) -> Optional[str]:
        """
        Generate trading signal based on VWAP conditions
        
        Args:
            market_data: Dictionary with current market data (must include 'tick' key)
            
        Returns:
            'BUY', 'SELL', or None
        """
        logger.info(f"Strategy {self.name}: generate_signal() called for symbol {self.symbol}")
        
        # Get current price from tick data
        tick = market_data.get('tick')
        if not tick:
            logger.warning(f"Strategy {self.name}: No tick data in market_data. Keys: {list(market_data.keys())}")
            return None
        
        current_price = (tick.get('bid', 0) + tick.get('ask', 0)) / 2.0
        if current_price == 0:
            current_price = tick.get('bid', tick.get('ask', 0))
        
        if current_price == 0:
            logger.warning(f"Strategy {self.name}: Invalid price in tick data")
            return None
        
        # Get candles for indicator calculation
        candles = self._get_candles(count=100)
        if not candles:
            logger.warning(f"Strategy {self.name}: No candles available (symbol={self.symbol}, timeframe={self.timeframe})")
            return None
        
        # Update indicators
        self._update_indicators(candles)
        
        # Get VWAP data
        vwap_data = self._get_vwap_data()
        if not vwap_data:
            logger.warning(f"Strategy {self.name}: No VWAP data available after indicator update")
            return None
        
        # Enhanced logging for validation
        vwap_value = vwap_data.get('vwap')
        bands = vwap_data.get('bands', {})
        session_info = vwap_data.get('session_info', {})
        
        # Log VWAP values and bands
        logger.debug(f"Strategy {self.name} VWAP Data: VWAP={vwap_value:.5f}, Price={current_price:.5f}, "
                    f"Price-VWAP={current_price - vwap_value:.5f}")
        
        # Log all band levels
        band_info = []
        for std_dev, band_data in bands.items():
            upper = band_data.get('upper')
            lower = band_data.get('lower')
            if upper and lower:
                band_info.append(f"STD{std_dev}: Upper={upper:.5f}, Lower={lower:.5f}")
        if band_info:
            logger.debug(f"Strategy {self.name} VWAP Bands: {', '.join(band_info)}")
        
        # Log session information
        if session_info:
            session_start = session_info.get('session_start_time')
            cumulative_volume = session_info.get('cumulative_volume', 0)
            logger.debug(f"Strategy {self.name} Session: Start={session_start}, Cumulative Volume={cumulative_volume:.2f}")
        
        # Get volume momentum
        volume_momentum = self.volume_indicator.get_volume_momentum() if self.volume_indicator else 'neutral'
        logger.debug(f"Strategy {self.name} Volume Momentum: {volume_momentum}")
        
        # Update previous candles
        self.previous_candles = candles[-self.max_candles_history:]
        
        # Evaluate entry strategies (priority: Mean Reversion > Trend Following > Breakout)
        signal = self._evaluate_mean_reversion(current_price, vwap_data, candles, volume_momentum)
        if signal:
            logger.info(f"Strategy {self.name}: Mean Reversion {signal} signal")
            self.previous_price = current_price
            return signal
        
        signal = self._evaluate_trend_following(current_price, vwap_data, candles, volume_momentum)
        if signal:
            logger.info(f"Strategy {self.name}: Trend Following {signal} signal")
            self.previous_price = current_price
            return signal
        
        signal = self._evaluate_breakout(current_price, vwap_data, candles, volume_momentum)
        if signal:
            logger.info(f"Strategy {self.name}: Breakout {signal} signal")
            self.previous_price = current_price
            return signal
        
        # Check simple buy/sell conditions (chain with AND/OR)
        try:
            if self._evaluate_condition_chain(self.buy_conditions, current_price, vwap_data):
                logger.info(f"Strategy {self.name}: ✅ Buy conditions met")
                self.previous_price = current_price
                return 'BUY'
        except Exception as e:
            logger.error(f"Error evaluating buy conditions in {self.name}: {e}", exc_info=True)
        
        try:
            if self._evaluate_condition_chain(self.sell_conditions, current_price, vwap_data):
                logger.info(f"Strategy {self.name}: ✅ Sell conditions met")
                self.previous_price = current_price
                return 'SELL'
        except Exception as e:
            logger.error(f"Error evaluating sell conditions in {self.name}: {e}", exc_info=True)
        
        self.previous_price = current_price
        return None
    
    def to_dict(self) -> Dict:
        """Convert strategy to dictionary for serialization"""
        base_dict = super().to_dict()
        base_dict.update({
            'strategy_type': 'vwap',
            'session_type': self.session_type,
            'timeframe': self.timeframe,
            'std_bands': self.std_bands,
            'swing_period': self.swing_period,
            'enable_mean_reversion': self.enable_mean_reversion,
            'mean_reversion_std_threshold': self.mean_reversion_std_threshold,
            'mean_reversion_pattern': self.mean_reversion_pattern,
            'mean_reversion_volume_requirement': self.mean_reversion_volume_requirement,
            'enable_trend_following': self.enable_trend_following,
            'trend_following_pattern': self.trend_following_pattern,
            'trend_following_volume_requirement': self.trend_following_volume_requirement,
            'enable_breakout': self.enable_breakout,
            'breakout_consolidation_period': self.breakout_consolidation_period,
            'breakout_volume_requirement': self.breakout_volume_requirement,
            'buy_conditions': [c.to_dict() for c in self.buy_conditions],
            'sell_conditions': [c.to_dict() for c in self.sell_conditions]
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict, mt5_connector=None) -> 'VWAPStrategy':
        """Create strategy from dictionary"""
        strategy = cls(
            name=data['name'],
            symbol=data['symbol'],
            session_type=data.get('session_type', 'NY'),
            timeframe=data.get('timeframe')
        )
        strategy.enabled = data.get('enabled', False)
        strategy.set_mt5_connector(mt5_connector)

        # Restore common configuration (backward compatible)
        strategy.trade_monitoring_mode = data.get('trade_monitoring_mode', getattr(strategy, 'trade_monitoring_mode', 'LTP'))
        strategy.lot_size = data.get('lot_size', getattr(strategy, 'lot_size', None))
        strategy.sl_type = data.get('sl_type', getattr(strategy, 'sl_type', None))
        strategy.sl_value = data.get('sl_value', getattr(strategy, 'sl_value', 20.0))
        strategy.use_ratio = data.get('use_ratio', getattr(strategy, 'use_ratio', True))
        strategy.tp_value = data.get('tp_value', getattr(strategy, 'tp_value', 40.0))

        # Advanced Risk Management
        strategy.enable_trailing_sl = data.get('enable_trailing_sl', getattr(strategy, 'enable_trailing_sl', False))
        strategy.trailing_sl_gap = data.get('trailing_sl_gap', getattr(strategy, 'trailing_sl_gap', 0.0))
        strategy.enable_profit_lock = data.get('enable_profit_lock', getattr(strategy, 'enable_profit_lock', False))
        strategy.profit_lock_trigger = data.get('profit_lock_trigger', getattr(strategy, 'profit_lock_trigger', 0.0))
        strategy.profit_lock_value = data.get('profit_lock_value', getattr(strategy, 'profit_lock_value', 0.0))
        strategy.profit_trail_step = data.get('profit_trail_step', getattr(strategy, 'profit_trail_step', 0.0))
        strategy.profit_trail_amount = data.get('profit_trail_amount', getattr(strategy, 'profit_trail_amount', 0.0))

        # Trail Wait & Trade (W&T)
        strategy.enable_wt = data.get('enable_wt', getattr(strategy, 'enable_wt', False))
        strategy.wt_value = data.get('wt_value', getattr(strategy, 'wt_value', 0.0))
        strategy.wt_is_percentage = data.get('wt_is_percentage', getattr(strategy, 'wt_is_percentage', False))

        # Position Preservation
        strategy.preserve_position = data.get('preserve_position', getattr(strategy, 'preserve_position', False))
        
        # Restore configuration
        strategy.std_bands = data.get('std_bands', [1.0, 1.5, 2.0])
        strategy.swing_period = data.get('swing_period', 10)
        strategy.enable_mean_reversion = data.get('enable_mean_reversion', False)
        strategy.mean_reversion_std_threshold = data.get('mean_reversion_std_threshold', 1.5)
        strategy.mean_reversion_pattern = data.get('mean_reversion_pattern', 'Any')
        strategy.mean_reversion_volume_requirement = data.get('mean_reversion_volume_requirement', 'Declining')
        strategy.enable_trend_following = data.get('enable_trend_following', False)
        strategy.trend_following_pattern = data.get('trend_following_pattern', 'Any')
        strategy.trend_following_volume_requirement = data.get('trend_following_volume_requirement', 'Increasing')
        strategy.enable_breakout = data.get('enable_breakout', False)
        strategy.breakout_consolidation_period = data.get('breakout_consolidation_period', 5)
        strategy.breakout_volume_requirement = data.get('breakout_volume_requirement', 'Increasing')
        
        # Restore buy/sell conditions
        for cond_data in data.get('buy_conditions', []):
            strategy.add_buy_condition(VWAPCondition.from_dict(cond_data))
        
        for cond_data in data.get('sell_conditions', []):
            strategy.add_sell_condition(VWAPCondition.from_dict(cond_data))
        
        return strategy

