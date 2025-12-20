"""
Custom Indicator Panel
GUI for creating and running Python-based custom indicators
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QDoubleSpinBox, QSpinBox,
                             QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QCheckBox, QTextEdit, QSplitter)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QFont
from typing import Dict, Optional, List, Any
from datetime import datetime
import requests
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class IndicatorRunnerThread(QThread):
    """Thread for running indicator calculations"""
    
    signal_generated = pyqtSignal(str, float, float, float)  # signal, quantity, sl, tp
    status_update = pyqtSignal(str)
    indicator_values_updated = pyqtSignal(dict)  # indicator values dictionary
    
    def __init__(self, config: Dict):
        super().__init__()
        self.config = config
        self.running = False
        self.mt5_connected = False
    
    def run(self):
        """Run indicator in loop"""
        self.running = True
        
        # Connect to MT5
        if not mt5.initialize():
            error = mt5.last_error()
            self.status_update.emit(f"MT5 initialization failed: {error}")
            return
        
        if self.config.get('mt5_login'):
            if not mt5.login(
                login=self.config['mt5_login'],
                password=self.config['mt5_password'],
                server=self.config['mt5_server']
            ):
                error = mt5.last_error()
                self.status_update.emit(f"MT5 login failed: {error}")
                mt5.shutdown()
                return
        
        self.mt5_connected = True
        self.status_update.emit("Connected to MT5")
        
        symbol = self.config['symbol']
        timeframe = self.config['timeframe']
        check_interval = self.config.get('check_interval', 60)
        
        # Get readable timeframe name for error messages
        timeframe_names = {
            mt5.TIMEFRAME_M1: "M1",
            mt5.TIMEFRAME_M5: "M5",
            mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_M30: "M30",
            mt5.TIMEFRAME_H1: "H1",
            mt5.TIMEFRAME_H4: "H4",
            mt5.TIMEFRAME_D1: "D1",
        }
        timeframe_name = timeframe_names.get(timeframe, f"TF{timeframe}")
        
        # Verify symbol is available - try different variations and case combinations
        symbol_variations = [
            symbol, 
            symbol.upper(), 
            symbol.lower(),
            symbol.capitalize(),
            # Try common variations for Gold
            "XAUUSD" if "XAU" in symbol.upper() else None,
            "GOLD" if "XAU" in symbol.upper() or "GOLD" in symbol.upper() else None,
        ]
        symbol_variations = [s for s in symbol_variations if s is not None]
        
        symbol_info = None
        actual_symbol = None
        
        for sym in symbol_variations:
            symbol_info = mt5.symbol_info(sym)
            if symbol_info is not None:
                actual_symbol = sym
                break
        
        # If still not found, try searching all symbols (case-insensitive)
        if symbol_info is None:
            all_symbols = mt5.symbols_get()
            if all_symbols:
                symbol_upper = symbol.upper()
                for s in all_symbols:
                    if s.name.upper() == symbol_upper:
                        symbol_info = s
                        actual_symbol = s.name
                        break
        
        if symbol_info is None:
            # Try to get available symbols to suggest alternatives
            all_symbols = mt5.symbols_get()
            if all_symbols:
                # Find similar symbols (check for XAU, GOLD, or similar patterns)
                symbol_upper = symbol.upper()
                similar = []
                for s in all_symbols[:50]:
                    s_name = s.name.upper()
                    if (symbol_upper in s_name or s_name in symbol_upper or 
                        ('XAU' in symbol_upper and 'XAU' in s_name) or
                        ('GOLD' in symbol_upper and 'GOLD' in s_name)):
                        similar.append(s.name)
                
                if similar:
                    self.status_update.emit(f"Symbol {symbol} not found. Similar symbols: {', '.join(similar[:5])}")
                else:
                    # Show first few available symbols
                    available = [s.name for s in all_symbols[:10]]
                    self.status_update.emit(f"Symbol {symbol} not found. Available symbols include: {', '.join(available)}")
            else:
                self.status_update.emit(f"Symbol {symbol} not found. Please add it to Market Watch in MT5 terminal.")
            mt5.shutdown()
            return
        
        # Use the actual symbol name that was found
        symbol = actual_symbol
        
        # Always try to add symbol to Market Watch (even if visible, to ensure it's accessible)
        if not mt5.symbol_select(symbol, True):
            # If symbol_select fails, try to get it anyway - some symbols work without being in Market Watch
            self.status_update.emit(f"Warning: Could not add {symbol} to Market Watch, but will try to use it anyway")
        else:
            if not symbol_info.visible:
                self.status_update.emit(f"Added {symbol} to Market Watch")
            else:
                self.status_update.emit(f"Symbol {symbol} is already in Market Watch")
        
        self.status_update.emit(f"Symbol {symbol} verified and ready")
        
        last_signal = None
        first_check = True  # Track if this is the first check
        
        try:
            while self.running:
                # Get rates
                rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 100)
                
                if rates is None or len(rates) == 0:
                    # Try alternative method
                    from datetime import datetime, timedelta
                    rates = mt5.copy_rates_from(symbol, timeframe, datetime.now() - timedelta(days=1), 100)
                    
                    if rates is None or len(rates) == 0:
                        # Check if MT5 is still connected
                        if not mt5.terminal_info():
                            self.status_update.emit(f"MT5 disconnected. Attempting to reconnect...")
                            # Try to reconnect
                            if mt5.initialize():
                                self.status_update.emit(f"Reconnected to MT5")
                                # Re-verify symbol after reconnection
                                symbol_info = mt5.symbol_info(symbol)
                                if symbol_info:
                                    mt5.symbol_select(symbol, True)
                            else:
                                self.status_update.emit(f"Failed to reconnect to MT5. Check MT5 terminal.")
                                self.msleep(check_interval * 1000)
                                continue
                        else:
                            # Check if symbol is still available
                            symbol_info = mt5.symbol_info(symbol)
                            if symbol_info is None:
                                self.status_update.emit(f"Symbol {symbol} not found. Trying to add to Market Watch...")
                                # Try to add symbol
                                if mt5.symbol_select(symbol, True):
                                    self.status_update.emit(f"Added {symbol} to Market Watch")
                                else:
                                    self.status_update.emit(f"Could not add {symbol} to Market Watch")
                            else:
                                self.status_update.emit(f"No data for {symbol} on {timeframe_name}. Symbol exists but no historical data available.")
                        self.msleep(check_interval * 1000)
                        continue
                
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                
                # Check if we have enough data
                if len(df) < 50:
                    self.status_update.emit(f"Insufficient data for {symbol} (got {len(df)} bars, need at least 50)")
                    self.msleep(check_interval * 1000)
                    continue
                
                # Calculate indicators
                indicators = self._calculate_indicators(df)
                
                # Extract current indicator values for display - all indicators are always calculated
                indicator_values = {}
                
                try:
                    # RSI
                    if 'rsi' in indicators and isinstance(indicators['rsi'], pd.Series) and len(indicators['rsi']) > 0:
                        rsi_val = indicators['rsi'].iloc[-1]
                        if pd.notna(rsi_val):
                            indicator_values['RSI'] = round(float(rsi_val), 2)
                    
                    # MACD
                    if 'macd' in indicators and isinstance(indicators['macd'], pd.Series) and len(indicators['macd']) > 0:
                        macd_val = indicators['macd'].iloc[-1]
                        if pd.notna(macd_val):
                            indicator_values['MACD'] = round(float(macd_val), 5)
                    
                    if 'macd_signal' in indicators and isinstance(indicators['macd_signal'], pd.Series) and len(indicators['macd_signal']) > 0:
                        sig_val = indicators['macd_signal'].iloc[-1]
                        if pd.notna(sig_val):
                            indicator_values['MACD Signal'] = round(float(sig_val), 5)
                    
                    if 'macd_histogram' in indicators and isinstance(indicators['macd_histogram'], pd.Series) and len(indicators['macd_histogram']) > 0:
                        hist_val = indicators['macd_histogram'].iloc[-1]
                        if pd.notna(hist_val):
                            indicator_values['MACD Histogram'] = round(float(hist_val), 5)
                    
                    # EMA
                    if 'ema_fast' in indicators and isinstance(indicators['ema_fast'], pd.Series) and len(indicators['ema_fast']) > 0:
                        ema_fast_val = indicators['ema_fast'].iloc[-1]
                        if pd.notna(ema_fast_val):
                            indicator_values['EMA Fast'] = round(float(ema_fast_val), 5)
                    
                    if 'ema_slow' in indicators and isinstance(indicators['ema_slow'], pd.Series) and len(indicators['ema_slow']) > 0:
                        ema_slow_val = indicators['ema_slow'].iloc[-1]
                        if pd.notna(ema_slow_val):
                            indicator_values['EMA Slow'] = round(float(ema_slow_val), 5)
                    
                    # SMA
                    if 'sma_fast' in indicators and isinstance(indicators['sma_fast'], pd.Series) and len(indicators['sma_fast']) > 0:
                        sma_fast_val = indicators['sma_fast'].iloc[-1]
                        if pd.notna(sma_fast_val):
                            indicator_values['SMA Fast'] = round(float(sma_fast_val), 5)
                    
                    if 'sma_slow' in indicators and isinstance(indicators['sma_slow'], pd.Series) and len(indicators['sma_slow']) > 0:
                        sma_slow_val = indicators['sma_slow'].iloc[-1]
                        if pd.notna(sma_slow_val):
                            indicator_values['SMA Slow'] = round(float(sma_slow_val), 5)
                    
                    # Bollinger Bands
                    if 'bb_upper' in indicators and isinstance(indicators['bb_upper'], pd.Series) and len(indicators['bb_upper']) > 0:
                        bb_upper_val = indicators['bb_upper'].iloc[-1]
                        if pd.notna(bb_upper_val):
                            indicator_values['BB Upper'] = round(float(bb_upper_val), 5)
                    
                    if 'bb_middle' in indicators and isinstance(indicators['bb_middle'], pd.Series) and len(indicators['bb_middle']) > 0:
                        bb_middle_val = indicators['bb_middle'].iloc[-1]
                        if pd.notna(bb_middle_val):
                            indicator_values['BB Middle'] = round(float(bb_middle_val), 5)
                    
                    if 'bb_lower' in indicators and isinstance(indicators['bb_lower'], pd.Series) and len(indicators['bb_lower']) > 0:
                        bb_lower_val = indicators['bb_lower'].iloc[-1]
                        if pd.notna(bb_lower_val):
                            indicator_values['BB Lower'] = round(float(bb_lower_val), 5)
                    
                    # Current price
                    if len(df) > 0:
                        indicator_values['Current Price'] = round(float(df['close'].iloc[-1]), 5)
                except Exception as e:
                    logger.error(f"Error extracting indicator values: {e}", exc_info=True)
                    self.status_update.emit(f"Error extracting indicator values: {e}")
                
                # Emit indicator values update (always emit, even if empty)
                # Log for debugging
                if len(indicator_values) > 0:
                    logger.info(f"Emitting {len(indicator_values)} indicator values: {list(indicator_values.keys())}")
                else:
                    logger.warning(f"No indicator values calculated! Indicators dict keys: {list(indicators.keys())}")
                self.indicator_values_updated.emit(indicator_values)
                
                # Only generate signals if trading is enabled (not monitoring-only mode)
                if not self.config.get('monitoring_only', False):
                    # Generate signal
                    signal = self._generate_signal(df, indicators)
                    
                    # Emit indicator values even on first check
                    # (values are already extracted and emitted above)
                    
                    # On first check, just log the current state but don't send signal
                    if first_check:
                        if signal:
                            self.status_update.emit(f"Current condition met: {signal} signal detected. Waiting for signal change to execute...")
                        else:
                            self.status_update.emit(f"Monitoring {symbol}... Current conditions not met. Waiting for signal...")
                        first_check = False
                        last_signal = signal  # Set last_signal to current state to prevent immediate execution
                        # Don't continue - let it sleep normally so values update
                    
                    # Only send signal if it's different from the last signal (signal change detected)
                    if signal and signal != last_signal:
                        # Calculate SL/TP
                        sl, tp = self._calculate_sl_tp(df, signal)
                        quantity = self.config.get('quantity', 0.01)
                        
                        self.signal_generated.emit(signal, quantity, sl, tp)
                        last_signal = signal
                        self.status_update.emit(f"Signal change detected: {signal} for {symbol}")
                    elif signal == last_signal and signal:
                        # Signal condition still met but same as before - don't send again
                        self.status_update.emit(f"Condition still met: {signal} (no new signal - waiting for change)")
                    elif not signal:
                        # Condition no longer met - reset last_signal if it was set
                        if last_signal:
                            self.status_update.emit(f"Signal condition no longer met. Last signal was: {last_signal}")
                            last_signal = None
                        else:
                            # Only log occasionally to avoid spam
                            pass
                else:
                    # Monitoring-only mode: just update values, no signal generation
                    if first_check:
                        self.status_update.emit(f"Monitoring {symbol} - Indicator values updating...")
                        first_check = False
                
                self.msleep(check_interval * 1000)
                
        except KeyboardInterrupt:
            self.status_update.emit("Indicator stopped by user")
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.status_update.emit(error_msg)
            logger.error(f"Indicator runner error: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            # Don't shutdown MT5 here - the main application manages the MT5 connection
            # Only shutdown if this thread created its own connection (which it doesn't anymore)
            # The main app's MT5 connection should remain active
            pass
    
    def stop(self):
        """Stop the indicator"""
        self.running = False
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all indicators - always calculate all indicators regardless of selection"""
        indicators = {}
        
        config = self.config
        
        # RSI - Always calculate (use MT5's built-in RSI calculation, same as strategy builder)
        period = config.get('rsi_period', 14)
        symbol = self.config.get('symbol')
        timeframe = self.config.get('timeframe')
        
        # Use MT5's iRSI() function (same as strategy builder) for exact values
        try:
            rsi_handle = mt5.iRSI(symbol, timeframe, period, mt5.PRICE_CLOSE)
            if rsi_handle != mt5.INVALID_HANDLE:
                # Get RSI values - get enough to match or exceed dataframe length
                rsi_count = max(len(df), 100)  # Get at least 100 values
                rsi_values = mt5.copy_indicator_buffer(rsi_handle, 0, 0, rsi_count)
                mt5.IndicatorRelease(rsi_handle)
                
                if rsi_values is not None and len(rsi_values) > 0:
                    # Convert numpy array to pandas Series
                    # MT5 RSI includes current forming bar, so values are already aligned
                    if len(rsi_values) >= len(df):
                        # Take the last len(df) values to match dataframe
                        rsi_series = pd.Series(list(rsi_values[-len(df):]))
                    else:
                        # Pad beginning with None if we have fewer values
                        rsi_series = pd.Series([None] * (len(df) - len(rsi_values)) + list(rsi_values))
                    indicators['rsi'] = rsi_series
                else:
                    # Fallback to manual calculation
                    self._calculate_rsi_manual(df, period, indicators)
            else:
                error = mt5.last_error()
                logger.warning(f"MT5 RSI handle invalid: {error}, using manual calculation")
                # Fallback to manual calculation if MT5 RSI handle invalid
                self._calculate_rsi_manual(df, period, indicators)
        except Exception as e:
            logger.warning(f"MT5 RSI calculation failed, using manual: {e}")
            # Fallback to manual calculation
            self._calculate_rsi_manual(df, period, indicators)
        
        # MACD - Always calculate
        fast = config.get('macd_fast', 12)
        slow = config.get('macd_slow', 26)
        signal_period = config.get('macd_signal', 9)
        
        try:
            macd_handle = mt5.iMACD(symbol, timeframe, fast, slow, signal_period, mt5.PRICE_CLOSE)
            if macd_handle != mt5.INVALID_HANDLE:
                macd_line = mt5.copy_indicator_buffer(macd_handle, 0, 0, len(df))
                signal_line = mt5.copy_indicator_buffer(macd_handle, 1, 0, len(df))
                histogram = mt5.copy_indicator_buffer(macd_handle, 2, 0, len(df))
                mt5.IndicatorRelease(macd_handle)
                
                if macd_line is not None and len(macd_line) > 0:
                    if len(macd_line) < len(df):
                        indicators['macd'] = pd.Series([None] * (len(df) - len(macd_line)) + list(macd_line))
                    else:
                        indicators['macd'] = pd.Series(list(macd_line[-len(df):]))
                    
                    if signal_line is not None and len(signal_line) > 0:
                        if len(signal_line) < len(df):
                            indicators['macd_signal'] = pd.Series([None] * (len(df) - len(signal_line)) + list(signal_line))
                        else:
                            indicators['macd_signal'] = pd.Series(list(signal_line[-len(df):]))
                    
                    if histogram is not None and len(histogram) > 0:
                        if len(histogram) < len(df):
                            indicators['macd_histogram'] = pd.Series([None] * (len(df) - len(histogram)) + list(histogram))
                        else:
                            indicators['macd_histogram'] = pd.Series(list(histogram[-len(df):]))
        except Exception as e:
            logger.warning(f"MT5 MACD calculation failed: {e}")
            # Fallback to manual calculation
            ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
            ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
            indicators['macd'] = ema_fast - ema_slow
            indicators['macd_signal'] = indicators['macd'].ewm(span=signal_period, adjust=False).mean()
            indicators['macd_histogram'] = indicators['macd'] - indicators['macd_signal']
        
        # EMA - Always calculate
        fast_period = config.get('ema_fast_period', 10)
        slow_period = config.get('ema_slow_period', 20)
        indicators['ema_fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
        indicators['ema_slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
        
        # SMA - Always calculate
        indicators['sma_fast'] = df['close'].rolling(window=fast_period).mean()
        indicators['sma_slow'] = df['close'].rolling(window=slow_period).mean()
        
        # Bollinger Bands - Always calculate
        period = config.get('bb_period', 20)
        std_dev = config.get('bb_std', 2.0)
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        indicators['bb_upper'] = sma + (std * std_dev)
        indicators['bb_middle'] = sma
        indicators['bb_lower'] = sma - (std * std_dev)
        
        return indicators
    
    def _calculate_rsi_manual(self, df: pd.DataFrame, period: int, indicators: Dict[str, Any]):
        """Fallback manual RSI calculation using Wilder's smoothing method (same as strategy builder)"""
        # Use the same RSI calculation as strategy builder (Wilder's smoothing)
        from ..indicators import RSI
        rsi_indicator = RSI(period)
        
        # Convert dataframe to list of dicts format expected by RSI indicator
        rates_list = []
        for _, row in df.iterrows():
            rates_list.append({
                'time': row['time'],
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'tick_volume': row.get('tick_volume', 0)
            })
        
        # Calculate RSI using the same method as strategy builder
        rsi_indicator.update(rates_list)
        rsi_values = rsi_indicator.get_values()
        
        # Convert to pandas Series
        if rsi_values and len(rsi_values) > 0:
            # Pad with None if needed to match dataframe length
            if len(rsi_values) < len(df):
                rsi_series = pd.Series([None] * (len(df) - len(rsi_values)) + rsi_values)
            else:
                rsi_series = pd.Series(rsi_values[-len(df):])
            indicators['rsi'] = rsi_series
        else:
            # Ultimate fallback - simple calculation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            indicators['rsi'] = 100 - (100 / (1 + rs))
    
    def _generate_signal(self, df: pd.DataFrame, indicators: Dict[str, Any]) -> Optional[str]:
        """Generate signal based on configured conditions"""
        config = self.config
        
        # Check BUY conditions
        buy_conditions_met = True
        
        # RSI BUY condition
        if config.get('use_rsi') and config.get('rsi_buy_enabled'):
            rsi = indicators.get('rsi')
            if rsi is not None and len(rsi) >= 2:
                operator = config.get('rsi_buy_operator', '>')
                value = config.get('rsi_buy_value', 30)
                current = rsi.iloc[-1]
                
                if operator == '>' and not (current > value):
                    buy_conditions_met = False
                elif operator == '<' and not (current < value):
                    buy_conditions_met = False
                elif operator == '>=' and not (current >= value):
                    buy_conditions_met = False
                elif operator == '<=' and not (current <= value):
                    buy_conditions_met = False
                elif operator == '==' and not (current == value):
                    buy_conditions_met = False
            else:
                buy_conditions_met = False
        
        # MACD BUY condition
        if config.get('use_macd') and config.get('macd_buy_enabled') and buy_conditions_met:
            macd = indicators.get('macd')
            macd_signal = indicators.get('macd_signal')
            if macd is not None and macd_signal is not None and len(macd) >= 2:
                operator = config.get('macd_buy_operator', '>')
                current_macd = macd.iloc[-1]
                current_signal = macd_signal.iloc[-1]
                
                if operator == '>' and not (current_macd > current_signal):
                    buy_conditions_met = False
                elif operator == '<' and not (current_macd < current_signal):
                    buy_conditions_met = False
                elif operator == 'cross_above':
                    prev_macd = macd.iloc[-2]
                    prev_signal = macd_signal.iloc[-2]
                    if not (prev_macd <= prev_signal and current_macd > current_signal):
                        buy_conditions_met = False
            else:
                buy_conditions_met = False
        
        # EMA/SMA Crossover BUY
        if config.get('use_ema_fast') and config.get('use_ema_slow') and config.get('ema_cross_buy_enabled') and buy_conditions_met:
            ema_fast = indicators.get('ema_fast')
            ema_slow = indicators.get('ema_slow')
            if ema_fast is not None and ema_slow is not None and len(ema_fast) >= 2:
                current_fast = ema_fast.iloc[-1]
                current_slow = ema_slow.iloc[-1]
                prev_fast = ema_fast.iloc[-2]
                prev_slow = ema_slow.iloc[-2]
                if not (prev_fast <= prev_slow and current_fast > current_slow):
                    buy_conditions_met = False
            else:
                buy_conditions_met = False
        
        if buy_conditions_met and (config.get('rsi_buy_enabled') or config.get('macd_buy_enabled') or config.get('ema_cross_buy_enabled')):
            return "BUY"
        
        # Check SELL conditions
        sell_conditions_met = True
        
        # RSI SELL condition
        if config.get('use_rsi') and config.get('rsi_sell_enabled'):
            rsi = indicators.get('rsi')
            if rsi is not None and len(rsi) >= 2:
                operator = config.get('rsi_sell_operator', '<')
                value = config.get('rsi_sell_value', 70)
                current = rsi.iloc[-1]
                
                if operator == '>' and not (current > value):
                    sell_conditions_met = False
                elif operator == '<' and not (current < value):
                    sell_conditions_met = False
                elif operator == '>=' and not (current >= value):
                    sell_conditions_met = False
                elif operator == '<=' and not (current <= value):
                    sell_conditions_met = False
                elif operator == '==' and not (current == value):
                    sell_conditions_met = False
            else:
                sell_conditions_met = False
        
        # MACD SELL condition
        if config.get('use_macd') and config.get('macd_sell_enabled') and sell_conditions_met:
            macd = indicators.get('macd')
            macd_signal = indicators.get('macd_signal')
            if macd is not None and macd_signal is not None and len(macd) >= 2:
                operator = config.get('macd_sell_operator', '<')
                current_macd = macd.iloc[-1]
                current_signal = macd_signal.iloc[-1]
                
                if operator == '>' and not (current_macd > current_signal):
                    sell_conditions_met = False
                elif operator == '<' and not (current_macd < current_signal):
                    sell_conditions_met = False
                elif operator == 'cross_below':
                    prev_macd = macd.iloc[-2]
                    prev_signal = macd_signal.iloc[-2]
                    if not (prev_macd >= prev_signal and current_macd < current_signal):
                        sell_conditions_met = False
            else:
                sell_conditions_met = False
        
        # EMA/SMA Crossover SELL
        if config.get('use_ema_fast') and config.get('use_ema_slow') and config.get('ema_cross_sell_enabled') and sell_conditions_met:
            ema_fast = indicators.get('ema_fast')
            ema_slow = indicators.get('ema_slow')
            if ema_fast is not None and ema_slow is not None and len(ema_fast) >= 2:
                current_fast = ema_fast.iloc[-1]
                current_slow = ema_slow.iloc[-1]
                prev_fast = ema_fast.iloc[-2]
                prev_slow = ema_slow.iloc[-2]
                if not (prev_fast >= prev_slow and current_fast < current_slow):
                    sell_conditions_met = False
            else:
                sell_conditions_met = False
        
        if sell_conditions_met and (config.get('rsi_sell_enabled') or config.get('macd_sell_enabled') or config.get('ema_cross_sell_enabled')):
            return "SELL"
        
        return None
    
    def _calculate_sl_tp(self, df: pd.DataFrame, signal: str) -> tuple[float, float]:
        """Calculate stop loss and take profit"""
        # Calculate ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14).mean().iloc[-1]
        
        current_price = df['close'].iloc[-1]
        risk_reward = self.config.get('risk_reward_ratio', 2.0)
        
        if signal == "BUY":
            sl = current_price - (atr * 1.5)
            tp = current_price + (atr * 1.5 * risk_reward)
        else:
            sl = current_price + (atr * 1.5)
            tp = current_price - (atr * 1.5 * risk_reward)
        
        return sl, tp


class CustomIndicatorPanel(QWidget):
    """Custom Indicator Panel for GUI-based indicator configuration"""
    
    def __init__(self, mt5_connector=None, signal_server_url: str = "http://localhost:8080"):
        super().__init__()
        self.mt5 = mt5_connector
        self.signal_server_url = signal_server_url.rstrip('/')
        self.runner_thread: Optional[IndicatorRunnerThread] = None
        self.setup_ui()
        self.setup_timers()
        
        # Auto-load available symbols after UI is ready
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, self.load_available_symbols)
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Configuration
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Symbol and Timeframe
        symbol_group = QGroupBox("Symbol & Timeframe")
        symbol_layout = QFormLayout()
        
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        # Start with empty list - will be populated by load_available_symbols
        symbol_layout.addRow("Symbol:", self.symbol_combo)
        
        # Refresh button for symbols
        refresh_symbols_btn = QPushButton("Refresh Symbols")
        refresh_symbols_btn.clicked.connect(self.load_available_symbols)
        symbol_layout.addRow("", refresh_symbols_btn)
        
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems([
            "M1", "M5", "M15", "M30", "H1", "H4", "D1"
        ])
        self.timeframe_combo.setCurrentText("M15")
        symbol_layout.addRow("Timeframe:", self.timeframe_combo)
        
        symbol_group.setLayout(symbol_layout)
        left_layout.addWidget(symbol_group)
        
        # Indicators Selection
        indicators_group = QGroupBox("Indicators")
        indicators_layout = QVBoxLayout()
        
        self.rsi_check = QCheckBox("RSI (Relative Strength Index)")
        self.rsi_check.setChecked(True)
        self.rsi_check.toggled.connect(lambda checked: self.rsi_group.setVisible(checked))
        indicators_layout.addWidget(self.rsi_check)
        
        self.macd_check = QCheckBox("MACD (Moving Average Convergence Divergence)")
        self.macd_check.toggled.connect(lambda checked: self.macd_group.setVisible(checked))
        indicators_layout.addWidget(self.macd_check)
        
        self.ema_check = QCheckBox("EMA Crossover (Fast & Slow)")
        self.ema_check.toggled.connect(lambda checked: self.ema_group.setVisible(checked))
        indicators_layout.addWidget(self.ema_check)
        
        self.sma_check = QCheckBox("SMA Crossover (Fast & Slow)")
        self.sma_check.toggled.connect(lambda checked: self.ema_group.setVisible(checked))
        indicators_layout.addWidget(self.sma_check)
        
        self.bb_check = QCheckBox("Bollinger Bands")
        # Bollinger Bands settings can be added later if needed
        indicators_layout.addWidget(self.bb_check)
        
        indicators_group.setLayout(indicators_layout)
        left_layout.addWidget(indicators_group)
        
        # RSI Settings
        self.rsi_group = QGroupBox("RSI Settings")
        rsi_layout = QFormLayout()
        
        self.rsi_period = QSpinBox()
        self.rsi_period.setRange(2, 100)
        self.rsi_period.setValue(14)
        rsi_layout.addRow("Period:", self.rsi_period)
        
        # RSI BUY conditions
        self.rsi_buy_check = QCheckBox("Enable BUY condition")
        self.rsi_buy_check.setChecked(True)
        rsi_layout.addRow("", self.rsi_buy_check)
        
        self.rsi_buy_operator = QComboBox()
        self.rsi_buy_operator.addItems([">", "<", ">=", "<=", "=="])
        self.rsi_buy_operator.setCurrentText(">")
        rsi_layout.addRow("BUY Operator:", self.rsi_buy_operator)
        
        self.rsi_buy_value = QDoubleSpinBox()
        self.rsi_buy_value.setRange(0, 100)
        self.rsi_buy_value.setValue(30)
        rsi_layout.addRow("BUY Value:", self.rsi_buy_value)
        
        # RSI SELL conditions
        self.rsi_sell_check = QCheckBox("Enable SELL condition")
        self.rsi_sell_check.setChecked(True)
        rsi_layout.addRow("", self.rsi_sell_check)
        
        self.rsi_sell_operator = QComboBox()
        self.rsi_sell_operator.addItems([">", "<", ">=", "<=", "=="])
        self.rsi_sell_operator.setCurrentText("<")
        rsi_layout.addRow("SELL Operator:", self.rsi_sell_operator)
        
        self.rsi_sell_value = QDoubleSpinBox()
        self.rsi_sell_value.setRange(0, 100)
        self.rsi_sell_value.setValue(70)
        rsi_layout.addRow("SELL Value:", self.rsi_sell_value)
        
        self.rsi_group.setLayout(rsi_layout)
        self.rsi_group.setVisible(True)  # Visible by default since RSI is checked
        left_layout.addWidget(self.rsi_group)
        
        # MACD Settings
        self.macd_group = QGroupBox("MACD Settings")
        self.macd_group.setVisible(False)  # Hidden by default
        macd_layout = QFormLayout()
        
        self.macd_fast = QSpinBox()
        self.macd_fast.setRange(1, 50)
        self.macd_fast.setValue(12)
        macd_layout.addRow("Fast Period:", self.macd_fast)
        
        self.macd_slow = QSpinBox()
        self.macd_slow.setRange(1, 100)
        self.macd_slow.setValue(26)
        macd_layout.addRow("Slow Period:", self.macd_slow)
        
        self.macd_signal_period = QSpinBox()
        self.macd_signal_period.setRange(1, 50)
        self.macd_signal_period.setValue(9)
        macd_layout.addRow("Signal Period:", self.macd_signal_period)
        
        self.macd_buy_check = QCheckBox("Enable BUY (MACD > Signal)")
        macd_layout.addRow("", self.macd_buy_check)
        
        self.macd_buy_operator = QComboBox()
        self.macd_buy_operator.addItems([">", "<", "cross_above"])
        self.macd_buy_operator.setCurrentText("cross_above")
        macd_layout.addRow("BUY Operator:", self.macd_buy_operator)
        
        self.macd_sell_check = QCheckBox("Enable SELL (MACD < Signal)")
        macd_layout.addRow("", self.macd_sell_check)
        
        self.macd_sell_operator = QComboBox()
        self.macd_sell_operator.addItems([">", "<", "cross_below"])
        self.macd_sell_operator.setCurrentText("cross_below")
        macd_layout.addRow("SELL Operator:", self.macd_sell_operator)
        
        self.macd_group.setLayout(macd_layout)
        left_layout.addWidget(self.macd_group)
        
        # EMA/SMA Settings
        self.ema_group = QGroupBox("EMA/SMA Crossover Settings")
        self.ema_group.setVisible(False)  # Hidden by default
        ema_layout = QFormLayout()
        
        self.ema_fast_period = QSpinBox()
        self.ema_fast_period.setRange(1, 200)
        self.ema_fast_period.setValue(10)
        ema_layout.addRow("Fast Period:", self.ema_fast_period)
        
        self.ema_slow_period = QSpinBox()
        self.ema_slow_period.setRange(1, 200)
        self.ema_slow_period.setValue(20)
        ema_layout.addRow("Slow Period:", self.ema_slow_period)
        
        self.ema_cross_buy_check = QCheckBox("Enable BUY (Fast crosses above Slow)")
        ema_layout.addRow("", self.ema_cross_buy_check)
        
        self.ema_cross_sell_check = QCheckBox("Enable SELL (Fast crosses below Slow)")
        ema_layout.addRow("", self.ema_cross_sell_check)
        
        self.ema_group.setLayout(ema_layout)
        left_layout.addWidget(self.ema_group)
        
        # Trading Settings
        trading_group = QGroupBox("Trading Settings")
        trading_layout = QFormLayout()
        
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.01, 100.0)
        self.quantity_spin.setSingleStep(0.01)
        self.quantity_spin.setValue(0.01)
        trading_layout.addRow("Lot Size:", self.quantity_spin)
        
        self.risk_reward = QDoubleSpinBox()
        self.risk_reward.setRange(0.5, 10.0)
        self.risk_reward.setSingleStep(0.5)
        self.risk_reward.setValue(2.0)
        trading_layout.addRow("Risk:Reward Ratio:", self.risk_reward)
        
        self.check_interval = QSpinBox()
        self.check_interval.setRange(10, 3600)
        self.check_interval.setValue(60)
        self.check_interval.setSuffix(" seconds")
        trading_layout.addRow("Check Interval:", self.check_interval)
        
        trading_group.setLayout(trading_layout)
        left_layout.addWidget(trading_group)
        
        # Control Buttons
        button_layout = QHBoxLayout()
        
        # Monitor Indicators button (for viewing values only)
        self.monitor_btn = QPushButton("Monitor Indicators")
        self.monitor_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.monitor_btn.clicked.connect(self.start_monitoring)
        self.monitor_btn.setToolTip("Start monitoring indicator values without trading")
        button_layout.addWidget(self.monitor_btn)
        
        # Start Trading button (for actual trading)
        self.start_btn = QPushButton("Start Trading")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.start_btn.clicked.connect(self.start_indicator)
        self.start_btn.setToolTip("Start trading with the configured conditions")
        button_layout.addWidget(self.start_btn)
        
        # Stop button
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_indicator)
        button_layout.addWidget(self.stop_btn)
        
        left_layout.addLayout(button_layout)
        left_layout.addStretch()
        
        splitter.addWidget(left_panel)
        
        # Right panel: Status and History
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        # Live Indicator Values
        values_group = QGroupBox("Live Indicator Values")
        values_layout = QFormLayout()
        
        self.indicator_values_labels = {}  # Store label widgets for each indicator
        
        # Create labels for common indicators (will be shown/hidden based on selection)
        self.rsi_value_label = QLabel("--")
        self.rsi_value_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        values_layout.addRow("RSI:", self.rsi_value_label)
        self.indicator_values_labels['RSI'] = self.rsi_value_label
        
        self.macd_value_label = QLabel("--")
        self.macd_value_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        values_layout.addRow("MACD:", self.macd_value_label)
        self.indicator_values_labels['MACD'] = self.macd_value_label
        
        self.macd_signal_label = QLabel("--")
        self.macd_signal_label.setStyleSheet("color: #FF9800;")
        values_layout.addRow("MACD Signal:", self.macd_signal_label)
        self.indicator_values_labels['MACD Signal'] = self.macd_signal_label
        
        self.macd_hist_label = QLabel("--")
        self.macd_hist_label.setStyleSheet("color: #9C27B0;")
        values_layout.addRow("MACD Histogram:", self.macd_hist_label)
        self.indicator_values_labels['MACD Histogram'] = self.macd_hist_label
        
        self.ema_fast_label = QLabel("--")
        self.ema_fast_label.setStyleSheet("font-weight: bold; color: #00BCD4;")
        values_layout.addRow("EMA Fast:", self.ema_fast_label)
        self.indicator_values_labels['EMA Fast'] = self.ema_fast_label
        
        self.ema_slow_label = QLabel("--")
        self.ema_slow_label.setStyleSheet("font-weight: bold; color: #009688;")
        values_layout.addRow("EMA Slow:", self.ema_slow_label)
        self.indicator_values_labels['EMA Slow'] = self.ema_slow_label
        
        self.sma_fast_label = QLabel("--")
        self.sma_fast_label.setStyleSheet("font-weight: bold; color: #00BCD4;")
        values_layout.addRow("SMA Fast:", self.sma_fast_label)
        self.indicator_values_labels['SMA Fast'] = self.sma_fast_label
        
        self.sma_slow_label = QLabel("--")
        self.sma_slow_label.setStyleSheet("font-weight: bold; color: #009688;")
        values_layout.addRow("SMA Slow:", self.sma_slow_label)
        self.indicator_values_labels['SMA Slow'] = self.sma_slow_label
        
        self.bb_upper_label = QLabel("--")
        self.bb_upper_label.setStyleSheet("color: #F44336;")
        values_layout.addRow("BB Upper:", self.bb_upper_label)
        self.indicator_values_labels['BB Upper'] = self.bb_upper_label
        
        self.bb_middle_label = QLabel("--")
        self.bb_middle_label.setStyleSheet("color: #FFC107;")
        values_layout.addRow("BB Middle:", self.bb_middle_label)
        self.indicator_values_labels['BB Middle'] = self.bb_middle_label
        
        self.bb_lower_label = QLabel("--")
        self.bb_lower_label.setStyleSheet("color: #4CAF50;")
        values_layout.addRow("BB Lower:", self.bb_lower_label)
        self.indicator_values_labels['BB Lower'] = self.bb_lower_label
        
        self.price_label = QLabel("--")
        self.price_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #FFFFFF;")
        values_layout.addRow("Current Price:", self.price_label)
        self.indicator_values_labels['Current Price'] = self.price_label
        
        values_group.setLayout(values_layout)
        right_layout.addWidget(values_group)
        
        # Status
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(100)
        self.status_text.setReadOnly(True)
        status_layout.addWidget(self.status_text)
        
        status_group.setLayout(status_layout)
        right_layout.addWidget(status_group)
        
        # Signal History
        history_label = QLabel("Signal History")
        history_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(history_label)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Time", "Symbol", "Action", "Quantity", "SL", "TP"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setAlternatingRowColors(True)
        right_layout.addWidget(self.history_table)
        
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
    
    def setup_timers(self):
        """Setup update timers"""
        pass
    
    def get_timeframe_mt5(self) -> int:
        """Convert timeframe string to MT5 constant"""
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }
        return tf_map.get(self.timeframe_combo.currentText(), mt5.TIMEFRAME_M15)
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return {
            'symbol': self.symbol_combo.currentText().upper(),
            'timeframe': self.get_timeframe_mt5(),
            'quantity': self.quantity_spin.value(),
            'risk_reward_ratio': self.risk_reward.value(),
            'check_interval': self.check_interval.value(),
            
            # Indicators
            'use_rsi': self.rsi_check.isChecked(),
            'use_macd': self.macd_check.isChecked(),
            'use_ema_fast': self.ema_check.isChecked() or self.sma_check.isChecked(),
            'use_ema_slow': self.ema_check.isChecked() or self.sma_check.isChecked(),
            'use_sma_fast': self.sma_check.isChecked(),
            'use_sma_slow': self.sma_check.isChecked(),
            'use_bb': self.bb_check.isChecked(),
            
            # RSI
            'rsi_period': self.rsi_period.value(),
            'rsi_buy_enabled': self.rsi_buy_check.isChecked(),
            'rsi_buy_operator': self.rsi_buy_operator.currentText(),
            'rsi_buy_value': self.rsi_buy_value.value(),
            'rsi_sell_enabled': self.rsi_sell_check.isChecked(),
            'rsi_sell_operator': self.rsi_sell_operator.currentText(),
            'rsi_sell_value': self.rsi_sell_value.value(),
            
            # MACD
            'macd_fast': self.macd_fast.value(),
            'macd_slow': self.macd_slow.value(),
            'macd_signal': self.macd_signal_period.value(),
            'macd_buy_enabled': self.macd_buy_check.isChecked(),
            'macd_buy_operator': self.macd_buy_operator.currentText(),
            'macd_sell_enabled': self.macd_sell_check.isChecked(),
            'macd_sell_operator': self.macd_sell_operator.currentText(),
            
            # EMA/SMA
            'ema_fast_period': self.ema_fast_period.value(),
            'ema_slow_period': self.ema_slow_period.value(),
            'ema_cross_buy_enabled': self.ema_cross_buy_check.isChecked(),
            'ema_cross_sell_enabled': self.ema_cross_sell_check.isChecked(),
        }
    
    def start_monitoring(self):
        """Start monitoring indicators only (no trading)"""
        config = self.get_config()
        
        # Validate
        if not config['symbol']:
            QMessageBox.warning(self, "Error", "Please select a symbol")
            return
        
        # Stop any existing thread
        if self.runner_thread:
            self.stop_indicator()
        
        # Create monitoring-only thread (no signal generation)
        config['monitoring_only'] = True
        self.runner_thread = IndicatorRunnerThread(config)
        self.runner_thread.status_update.connect(self.on_status_update)
        self.runner_thread.indicator_values_updated.connect(self.on_indicator_values_updated)
        self.runner_thread.start()
        
        self.monitor_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.add_status("Monitoring indicators started (no trading)")
    
    def start_indicator(self):
        """Start the indicator with trading enabled"""
        config = self.get_config()
        
        # Validate
        if not config['symbol']:
            QMessageBox.warning(self, "Error", "Please select a symbol")
            return
        
        if not (config.get('use_rsi') or config.get('use_macd') or config.get('use_ema_fast')):
            QMessageBox.warning(self, "Error", "Please select at least one indicator")
            return
        
        if not (config.get('rsi_buy_enabled') or config.get('macd_buy_enabled') or config.get('ema_cross_buy_enabled') or
                config.get('rsi_sell_enabled') or config.get('macd_sell_enabled') or config.get('ema_cross_sell_enabled')):
            QMessageBox.warning(self, "Error", "Please enable at least one BUY or SELL condition")
            return
        
        # Stop any existing thread
        if self.runner_thread:
            self.stop_indicator()
        
        # Create and start runner thread with trading enabled
        config['monitoring_only'] = False
        self.runner_thread = IndicatorRunnerThread(config)
        self.runner_thread.signal_generated.connect(self.on_signal_generated)
        self.runner_thread.status_update.connect(self.on_status_update)
        self.runner_thread.indicator_values_updated.connect(self.on_indicator_values_updated)
        self.runner_thread.start()
        
        self.monitor_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.add_status("Trading started")
    
    def stop_indicator(self):
        """Stop the indicator"""
        if self.runner_thread:
            self.runner_thread.stop()
            self.runner_thread.wait(5000)
            self.runner_thread = None
        
        self.monitor_btn.setEnabled(True)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.add_status("Stopped")
    
    def on_signal_generated(self, signal: str, quantity: float, sl: float, tp: float):
        """Handle signal generation"""
        config = self.get_config()
        symbol = config['symbol']
        
        # Send signal to server
        payload = {
            "symbol": symbol,
            "action": signal,
            "quantity": quantity,
            "stop_loss": sl,
            "take_profit": tp,
            "comment": f"Custom Indicator - {datetime.now().strftime('%H:%M:%S')}"
        }
        
        try:
            response = requests.post(
                f"{self.signal_server_url}/signal",
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                self.add_status(f"✓ {signal} signal sent successfully")
            else:
                error_msg = result.get('error', 'Unknown error')
                self.add_status(f"✗ Failed to send signal: {error_msg}")
                # Show error in message box for visibility
                QMessageBox.warning(
                    self,
                    "Signal Execution Failed",
                    f"Signal execution failed:\n\n{error_msg}\n\nCheck the Signals tab for more details."
                )
        except requests.exceptions.RequestException as e:
            error_msg = f"Error sending signal to server: {str(e)}"
            self.add_status(f"✗ {error_msg}")
            QMessageBox.critical(self, "Connection Error", error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.add_status(f"✗ {error_msg}")
            QMessageBox.critical(self, "Error", error_msg)
        
        # Add to history table
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        
        self.history_table.setItem(row, 0, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        self.history_table.setItem(row, 1, QTableWidgetItem(symbol))
        
        action_item = QTableWidgetItem(signal)
        if signal == "BUY":
            action_item.setForeground(QColor("#4CAF50"))
        else:
            action_item.setForeground(QColor("#f44336"))
        self.history_table.setItem(row, 2, action_item)
        
        self.history_table.setItem(row, 3, QTableWidgetItem(f"{quantity:.2f}"))
        self.history_table.setItem(row, 4, QTableWidgetItem(f"{sl:.5f}"))
        self.history_table.setItem(row, 5, QTableWidgetItem(f"{tp:.5f}"))
    
    def on_status_update(self, message: str):
        """Handle status update"""
        self.add_status(message)
    
    def on_indicator_values_updated(self, values: Dict[str, float]):
        """Handle indicator values update - always show all indicators"""
        # Update all indicator value labels - always visible
        for key, label in self.indicator_values_labels.items():
            if key in values:
                value = values[key]
                label.setText(str(value))
            else:
                # Show "--" if value not available
                label.setText("--")
            # Always make labels visible
            label.setVisible(True)
    
    def add_status(self, message: str):
        """Add status message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
    
    def load_available_symbols(self):
        """Load available symbols from MT5"""
        if not self.mt5 or not self.mt5.is_connected():
            self.add_status("MT5 not connected. Cannot load symbols.")
            QMessageBox.warning(self, "Not Connected", "Please connect to MT5 first before loading symbols.")
            return
        
        try:
            symbols = self.mt5.get_available_symbols()
            if symbols:
                current_text = self.symbol_combo.currentText()
                self.symbol_combo.clear()
                
                # Add all available symbols sorted
                for sym in sorted(symbols):
                    self.symbol_combo.addItem(sym)
                
                # Try to restore previous selection if it exists
                if current_text:
                    index = self.symbol_combo.findText(current_text, Qt.MatchFlag.MatchExactly)
                    if index >= 0:
                        self.symbol_combo.setCurrentIndex(index)
                    else:
                        # If not found, try case-insensitive match
                        for i in range(self.symbol_combo.count()):
                            if self.symbol_combo.itemText(i).upper() == current_text.upper():
                                self.symbol_combo.setCurrentIndex(i)
                                break
                
                # If no selection, select first symbol
                if self.symbol_combo.currentIndex() < 0 and self.symbol_combo.count() > 0:
                    self.symbol_combo.setCurrentIndex(0)
                
                self.add_status(f"Loaded {len(symbols)} available symbols")
                if len(symbols) > 0:
                    self.add_status(f"Available symbols: {', '.join(symbols[:10])}{'...' if len(symbols) > 10 else ''}")
            else:
                self.add_status("No symbols available. Please check your MT5 connection.")
                QMessageBox.warning(self, "No Symbols", "No symbols found. Please check your MT5 connection and broker account.")
        except Exception as e:
            error_msg = f"Error loading symbols: {str(e)}"
            self.add_status(error_msg)
            logger.error(f"Error loading symbols: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", error_msg)

