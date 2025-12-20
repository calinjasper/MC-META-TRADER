"""
Custom Indicator Panel - Support/Resistance Based
GUI for Support/Resistance indicator with breakout trading
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QDoubleSpinBox, QSpinBox,
                             QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QCheckBox, QTextEdit, QSplitter)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QFont
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime
import requests
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


class SupportResistanceCalculator:
    """Calculate Support and Resistance levels"""
    
    def __init__(self, lookback_period: int = 50, min_touches: int = 2, strength_threshold: float = 0.5):
        """
        Initialize Support/Resistance calculator
        
        Args:
            lookback_period: Number of bars to look back for finding peaks/troughs
            min_touches: Minimum number of touches required to confirm a level
            strength_threshold: Minimum strength (0-1) to consider a level significant
        """
        self.lookback_period = lookback_period
        self.min_touches = min_touches
        self.strength_threshold = strength_threshold
    
    def find_peaks_troughs(self, df: pd.DataFrame) -> Tuple[List[float], List[float]]:
        """Find local peaks (resistance) and troughs (support)"""
        highs = df['high'].values
        lows = df['low'].values
        
        peaks = []
        troughs = []
        
        # Find peaks (local maxima)
        for i in range(self.lookback_period, len(highs) - self.lookback_period):
            is_peak = True
            for j in range(i - self.lookback_period, i + self.lookback_period + 1):
                if j != i and highs[j] >= highs[i]:
                    is_peak = False
                    break
            if is_peak:
                peaks.append((i, highs[i]))
        
        # Find troughs (local minima)
        for i in range(self.lookback_period, len(lows) - self.lookback_period):
            is_trough = True
            for j in range(i - self.lookback_period, i + self.lookback_period + 1):
                if j != i and lows[j] <= lows[i]:
                    is_trough = False
                    break
            if is_trough:
                troughs.append((i, lows[i]))
        
        return peaks, troughs
    
    def cluster_levels(self, levels: List[Tuple[int, float]], price_tolerance: float = 0.001) -> List[Dict]:
        """
        Cluster nearby levels together and calculate strength
        
        Args:
            levels: List of (index, price) tuples
            price_tolerance: Percentage tolerance for clustering (0.001 = 0.1%)
            
        Returns:
            List of level dictionaries with price, strength, and touches
        """
        if not levels:
            return []
        
        # Sort by price
        sorted_levels = sorted(levels, key=lambda x: x[1])
        
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # Check if this level is within tolerance of current cluster
            cluster_avg = np.mean([l[1] for l in current_cluster])
            if abs(level[1] - cluster_avg) / cluster_avg <= price_tolerance:
                current_cluster.append(level)
            else:
                # Save current cluster and start new one
                if len(current_cluster) >= self.min_touches:
                    cluster_price = np.mean([l[1] for l in current_cluster])
                    strength = len(current_cluster) / (self.lookback_period / 10)  # Normalize strength
                    strength = min(strength, 1.0)  # Cap at 1.0
                    
                    if strength >= self.strength_threshold:
                        clusters.append({
                            'price': cluster_price,
                            'strength': strength,
                            'touches': len(current_cluster),
                            'indices': [l[0] for l in current_cluster]
                        })
                
                current_cluster = [level]
        
        # Don't forget the last cluster
        if len(current_cluster) >= self.min_touches:
            cluster_price = np.mean([l[1] for l in current_cluster])
            strength = len(current_cluster) / (self.lookback_period / 10)
            strength = min(strength, 1.0)
            
            if strength >= self.strength_threshold:
                clusters.append({
                    'price': cluster_price,
                    'strength': strength,
                    'touches': len(current_cluster),
                    'indices': [l[0] for l in current_cluster]
                })
        
        return clusters
    
    def calculate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Support and Resistance levels
        
        Returns:
            Dictionary with 'support_levels' and 'resistance_levels' lists
        """
        peaks, troughs = self.find_peaks_troughs(df)
        
        # Cluster resistance levels (from peaks)
        resistance_levels = self.cluster_levels(peaks)
        
        # Cluster support levels (from troughs)
        support_levels = self.cluster_levels(troughs)
        
        # Sort by price (descending for resistance, ascending for support)
        resistance_levels.sort(key=lambda x: x['price'], reverse=True)
        support_levels.sort(key=lambda x: x['price'])
        
        return {
            'support_levels': support_levels,
            'resistance_levels': resistance_levels
        }


class IndicatorRunnerThread(QThread):
    """Thread for running Support/Resistance indicator"""
    
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
        
        # Verify symbol
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            self.status_update.emit(f"Symbol {symbol} not found in MT5")
            mt5.shutdown()
            return
        
        symbol = symbol_info.name
        mt5.symbol_select(symbol, True)
        self.status_update.emit(f"Symbol {symbol} verified and ready")
        
        last_signal = None
        last_breakout_level = None
        first_check = True
        
        # Initialize Support/Resistance calculator
        lookback = self.config.get('sr_lookback', 50)
        min_touches = self.config.get('sr_min_touches', 2)
        strength_threshold = self.config.get('sr_strength', 0.5)
        sr_calculator = SupportResistanceCalculator(lookback, min_touches, strength_threshold)
        
        try:
            while self.running:
                # Check MT5 connection
                if not mt5.terminal_info():
                    self.status_update.emit(f"MT5 disconnected. Attempting to reconnect...")
                    if mt5.initialize():
                        self.status_update.emit(f"Reconnected to MT5")
                        symbol_info = mt5.symbol_info(symbol)
                        if symbol_info:
                            mt5.symbol_select(symbol, True)
                    else:
                        self.status_update.emit(f"Failed to reconnect to MT5. Check MT5 terminal.")
                        self.msleep(check_interval * 1000)
                        continue
                
                # Get rates - need more data for SR calculation
                rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, max(200, lookback * 3))
                
                if rates is None or len(rates) == 0:
                    from datetime import datetime, timedelta
                    rates = mt5.copy_rates_from(symbol, timeframe, datetime.now() - timedelta(days=7), 500)
                    
                    if rates is None or len(rates) == 0:
                        symbol_info = mt5.symbol_info(symbol)
                        if symbol_info is None:
                            self.status_update.emit(f"Symbol {symbol} not found. Trying to add to Market Watch...")
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
                
                if len(df) < lookback * 2:
                    self.status_update.emit(f"Insufficient data for {symbol} (got {len(df)} bars, need at least {lookback * 2})")
                    self.msleep(check_interval * 1000)
                    continue
                
                # Calculate Support/Resistance levels
                sr_data = sr_calculator.calculate(df)
                support_levels = sr_data['support_levels']
                resistance_levels = sr_data['resistance_levels']
                
                # Get current price
                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    current_price = df['close'].iloc[-1]
                else:
                    current_price = tick.last
                
                # Find nearest support and resistance
                nearest_support = None
                nearest_resistance = None
                
                for support in support_levels:
                    if support['price'] < current_price:
                        if nearest_support is None or support['price'] > nearest_support['price']:
                            nearest_support = support
                
                for resistance in resistance_levels:
                    if resistance['price'] > current_price:
                        if nearest_resistance is None or resistance['price'] < nearest_resistance['price']:
                            nearest_resistance = resistance
                
                # Prepare indicator values for display
                indicator_values = {
                    'Current Price': round(current_price, 5)
                }
                
                if nearest_support:
                    indicator_values['Nearest Support'] = round(nearest_support['price'], 5)
                    indicator_values['Support Strength'] = round(nearest_support['strength'], 2)
                    indicator_values['Support Touches'] = nearest_support['touches']
                else:
                    indicator_values['Nearest Support'] = "--"
                    indicator_values['Support Strength'] = "--"
                    indicator_values['Support Touches'] = "--"
                
                if nearest_resistance:
                    indicator_values['Nearest Resistance'] = round(nearest_resistance['price'], 5)
                    indicator_values['Resistance Strength'] = round(nearest_resistance['strength'], 2)
                    indicator_values['Resistance Touches'] = nearest_resistance['touches']
                else:
                    indicator_values['Nearest Resistance'] = "--"
                    indicator_values['Resistance Strength'] = "--"
                    indicator_values['Resistance Touches'] = "--"
                
                # Add all levels count
                indicator_values['Total Support Levels'] = len(support_levels)
                indicator_values['Total Resistance Levels'] = len(resistance_levels)
                
                # Emit indicator values
                self.indicator_values_updated.emit(indicator_values)
                
                # Check for breakouts (only if trading is enabled)
                if not self.config.get('monitoring_only', False):
                    breakout_confirmation = self.config.get('sr_breakout_confirmation', 0.001)  # 0.1% default
                    signal = None
                    
                    # Check resistance breakout (BUY signal)
                    if nearest_resistance and self.config.get('sr_resistance_breakout_buy', True):
                        breakout_price = nearest_resistance['price'] * (1 + breakout_confirmation)
                        if current_price >= breakout_price and last_breakout_level != nearest_resistance['price']:
                            signal = "BUY"
                            last_breakout_level = nearest_resistance['price']
                            self.status_update.emit(f"Resistance breakout detected at {nearest_resistance['price']:.5f}")
                    
                    # Check support breakdown (SELL signal)
                    if nearest_support and self.config.get('sr_support_breakdown_sell', True):
                        breakdown_price = nearest_support['price'] * (1 - breakout_confirmation)
                        if current_price <= breakdown_price and last_breakout_level != nearest_support['price']:
                            signal = "SELL"
                            last_breakout_level = nearest_support['price']
                            self.status_update.emit(f"Support breakdown detected at {nearest_support['price']:.5f}")
                    
                    # On first check, just log
                    if first_check:
                        if signal:
                            self.status_update.emit(f"Current condition: {signal} signal detected. Waiting for signal change to execute...")
                        else:
                            self.status_update.emit(f"Monitoring {symbol} for Support/Resistance breakouts...")
                        first_check = False
                        last_signal = signal
                        self.msleep(check_interval * 1000)
                        continue
                    
                    # Only send signal if it's different from the last signal
                    if signal and signal != last_signal:
                        # Calculate SL/TP
                        sl, tp = self._calculate_sl_tp(df, signal, nearest_support, nearest_resistance, current_price)
                        quantity = self.config.get('quantity', 0.01)
                        
                        self.signal_generated.emit(signal, quantity, sl, tp)
                        last_signal = signal
                        self.status_update.emit(f"Signal change detected: {signal} for {symbol}")
                    elif signal == last_signal and signal:
                        self.status_update.emit(f"Breakout condition still met: {signal} (no new signal - waiting for change)")
                    elif not signal:
                        if last_signal:
                            self.status_update.emit(f"Breakout condition no longer met. Last signal was: {last_signal}")
                            last_signal = None
                            last_breakout_level = None
                else:
                    # Monitoring-only mode
                    if first_check:
                        self.status_update.emit(f"Monitoring {symbol} - Support/Resistance levels updating...")
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
            pass  # Don't shutdown MT5 - main app manages it
    
    def _calculate_sl_tp(self, df: pd.DataFrame, signal: str, 
                         nearest_support: Optional[Dict], nearest_resistance: Optional[Dict],
                         current_price: float) -> Tuple[float, float]:
        """Calculate Stop Loss and Take Profit based on Support/Resistance"""
        risk_reward = self.config.get('risk_reward_ratio', 2.0)
        
        if signal == "BUY":
            # SL below nearest support or below entry
            if nearest_support:
                sl = nearest_support['price'] * 0.999  # Slightly below support
            else:
                # Use ATR or fixed percentage
                sl = current_price * 0.995  # 0.5% below
            
            # TP above nearest resistance or based on risk:reward
            risk = current_price - sl
            tp = current_price + (risk * risk_reward)
            
            if nearest_resistance and tp > nearest_resistance['price']:
                # Adjust TP to be slightly below resistance
                tp = nearest_resistance['price'] * 0.999
        
        else:  # SELL
            # SL above nearest resistance or above entry
            if nearest_resistance:
                sl = nearest_resistance['price'] * 1.001  # Slightly above resistance
            else:
                sl = current_price * 1.005  # 0.5% above
            
            # TP below nearest support or based on risk:reward
            risk = sl - current_price
            tp = current_price - (risk * risk_reward)
            
            if nearest_support and tp < nearest_support['price']:
                # Adjust TP to be slightly above support
                tp = nearest_support['price'] * 1.001
        
        return sl, tp
    
    def stop(self):
        """Stop the indicator"""
        self.running = False


class CustomIndicatorPanel(QWidget):
    """Custom Indicator Panel - Support/Resistance Based"""
    
    def __init__(self, mt5_connector, signal_server_url: str = "http://localhost:8080"):
        super().__init__()
        self.mt5 = mt5_connector
        self.signal_server_url = signal_server_url
        self.runner_thread: Optional[IndicatorRunnerThread] = None
        self.indicator_values_labels: Dict[str, QLabel] = {}
        
        self.setup_ui()
        self.setup_timers()
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel - Configuration
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        
        # Symbol & Timeframe
        symbol_group = QGroupBox("Symbol & Timeframe")
        symbol_layout = QFormLayout()
        
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.setPlaceholderText("Select or enter symbol")
        symbol_layout.addRow("Symbol:", self.symbol_combo)
        
        refresh_symbols_btn = QPushButton("Refresh Symbols")
        refresh_symbols_btn.clicked.connect(self.load_available_symbols)
        symbol_layout.addRow("", refresh_symbols_btn)
        
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["M1", "M5", "M15", "M30", "H1", "H4", "D1"])
        self.timeframe_combo.setCurrentText("M15")
        symbol_layout.addRow("Timeframe:", self.timeframe_combo)
        
        symbol_group.setLayout(symbol_layout)
        left_layout.addWidget(symbol_group)
        
        # Support/Resistance Settings
        sr_group = QGroupBox("Support/Resistance Settings")
        sr_layout = QFormLayout()
        
        self.sr_lookback = QSpinBox()
        self.sr_lookback.setRange(10, 200)
        self.sr_lookback.setValue(50)
        self.sr_lookback.setToolTip("Number of bars to look back for finding peaks/troughs")
        sr_layout.addRow("Lookback Period:", self.sr_lookback)
        
        self.sr_min_touches = QSpinBox()
        self.sr_min_touches.setRange(1, 10)
        self.sr_min_touches.setValue(2)
        self.sr_min_touches.setToolTip("Minimum number of touches required to confirm a level")
        sr_layout.addRow("Min Touches:", self.sr_min_touches)
        
        self.sr_strength = QDoubleSpinBox()
        self.sr_strength.setRange(0.1, 1.0)
        self.sr_strength.setSingleStep(0.1)
        self.sr_strength.setValue(0.5)
        self.sr_strength.setToolTip("Minimum strength (0-1) to consider a level significant")
        sr_layout.addRow("Strength Threshold:", self.sr_strength)
        
        self.sr_breakout_confirmation = QDoubleSpinBox()
        self.sr_breakout_confirmation.setRange(0.0001, 0.01)
        self.sr_breakout_confirmation.setSingleStep(0.0001)
        self.sr_breakout_confirmation.setValue(0.001)
        self.sr_breakout_confirmation.setDecimals(4)
        self.sr_breakout_confirmation.setToolTip("Breakout confirmation percentage (0.001 = 0.1%)")
        sr_layout.addRow("Breakout Confirmation:", self.sr_breakout_confirmation)
        
        sr_group.setLayout(sr_layout)
        left_layout.addWidget(sr_group)
        
        # Entry Conditions
        entry_group = QGroupBox("Entry Conditions")
        entry_layout = QFormLayout()
        
        self.sr_resistance_breakout_buy = QCheckBox("BUY on Resistance Breakout")
        self.sr_resistance_breakout_buy.setChecked(True)
        self.sr_resistance_breakout_buy.setToolTip("Enter BUY when price breaks above resistance")
        entry_layout.addRow("", self.sr_resistance_breakout_buy)
        
        self.sr_support_breakdown_sell = QCheckBox("SELL on Support Breakdown")
        self.sr_support_breakdown_sell.setChecked(True)
        self.sr_support_breakdown_sell.setToolTip("Enter SELL when price breaks below support")
        entry_layout.addRow("", self.sr_support_breakdown_sell)
        
        entry_group.setLayout(entry_layout)
        left_layout.addWidget(entry_group)
        
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
        
        self.monitor_btn = QPushButton("Monitor Indicators")
        self.monitor_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.monitor_btn.clicked.connect(self.start_monitoring)
        self.monitor_btn.setToolTip("Start monitoring indicator values without trading")
        button_layout.addWidget(self.monitor_btn)
        
        self.start_btn = QPushButton("Start Trading")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.start_btn.clicked.connect(self.start_indicator)
        self.start_btn.setToolTip("Start trading with the configured conditions")
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_indicator)
        button_layout.addWidget(self.stop_btn)
        
        left_layout.addLayout(button_layout)
        left_layout.addStretch()
        
        splitter.addWidget(left_panel)
        
        # Right Panel - Live Data & Status
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        
        # Live Indicator Values
        values_group = QGroupBox("Live Indicator Values")
        values_layout = QFormLayout()
        
        # Support/Resistance values
        self.price_label = QLabel("--")
        self.price_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #FFFFFF;")
        values_layout.addRow("Current Price:", self.price_label)
        self.indicator_values_labels['Current Price'] = self.price_label
        
        self.support_label = QLabel("--")
        self.support_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        values_layout.addRow("Nearest Support:", self.support_label)
        self.indicator_values_labels['Nearest Support'] = self.support_label
        
        self.support_strength_label = QLabel("--")
        self.support_strength_label.setStyleSheet("color: #4CAF50;")
        values_layout.addRow("Support Strength:", self.support_strength_label)
        self.indicator_values_labels['Support Strength'] = self.support_strength_label
        
        self.support_touches_label = QLabel("--")
        self.support_touches_label.setStyleSheet("color: #4CAF50;")
        values_layout.addRow("Support Touches:", self.support_touches_label)
        self.indicator_values_labels['Support Touches'] = self.support_touches_label
        
        self.resistance_label = QLabel("--")
        self.resistance_label.setStyleSheet("color: #f44336; font-weight: bold;")
        values_layout.addRow("Nearest Resistance:", self.resistance_label)
        self.indicator_values_labels['Nearest Resistance'] = self.resistance_label
        
        self.resistance_strength_label = QLabel("--")
        self.resistance_strength_label.setStyleSheet("color: #f44336;")
        values_layout.addRow("Resistance Strength:", self.resistance_strength_label)
        self.indicator_values_labels['Resistance Strength'] = self.resistance_strength_label
        
        self.resistance_touches_label = QLabel("--")
        self.resistance_touches_label.setStyleSheet("color: #f44336;")
        values_layout.addRow("Resistance Touches:", self.resistance_touches_label)
        self.indicator_values_labels['Resistance Touches'] = self.resistance_touches_label
        
        self.total_support_label = QLabel("--")
        self.total_support_label.setStyleSheet("color: #888;")
        values_layout.addRow("Total Support Levels:", self.total_support_label)
        self.indicator_values_labels['Total Support Levels'] = self.total_support_label
        
        self.total_resistance_label = QLabel("--")
        self.total_resistance_label.setStyleSheet("color: #888;")
        values_layout.addRow("Total Resistance Levels:", self.total_resistance_label)
        self.indicator_values_labels['Total Resistance Levels'] = self.total_resistance_label
        
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
            
            # Support/Resistance settings
            'sr_lookback': self.sr_lookback.value(),
            'sr_min_touches': self.sr_min_touches.value(),
            'sr_strength': self.sr_strength.value(),
            'sr_breakout_confirmation': self.sr_breakout_confirmation.value(),
            'sr_resistance_breakout_buy': self.sr_resistance_breakout_buy.isChecked(),
            'sr_support_breakdown_sell': self.sr_support_breakdown_sell.isChecked(),
        }
    
    def start_monitoring(self):
        """Start monitoring indicators only (no trading)"""
        config = self.get_config()
        
        if not config['symbol']:
            QMessageBox.warning(self, "Error", "Please select a symbol")
            return
        
        if self.runner_thread:
            self.stop_indicator()
        
        config['monitoring_only'] = True
        self.runner_thread = IndicatorRunnerThread(config)
        self.runner_thread.status_update.connect(self.on_status_update)
        self.runner_thread.indicator_values_updated.connect(self.on_indicator_values_updated)
        self.runner_thread.start()
        
        self.monitor_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.add_status("Monitoring Support/Resistance started (no trading)")
    
    def start_indicator(self):
        """Start the indicator with trading enabled"""
        config = self.get_config()
        
        if not config['symbol']:
            QMessageBox.warning(self, "Error", "Please select a symbol")
            return
        
        if not (config.get('sr_resistance_breakout_buy') or config.get('sr_support_breakdown_sell')):
            QMessageBox.warning(self, "Error", "Please enable at least one entry condition")
            return
        
        if self.runner_thread:
            self.stop_indicator()
        
        config['monitoring_only'] = False
        self.runner_thread = IndicatorRunnerThread(config)
        self.runner_thread.signal_generated.connect(self.on_signal_generated)
        self.runner_thread.status_update.connect(self.on_status_update)
        self.runner_thread.indicator_values_updated.connect(self.on_indicator_values_updated)
        self.runner_thread.start()
        
        self.monitor_btn.setEnabled(False)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.add_status("Support/Resistance trading started")
    
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
        
        payload = {
            "symbol": symbol,
            "action": signal,
            "quantity": quantity,
            "stop_loss": sl,
            "take_profit": tp,
            "comment": f"Support/Resistance Breakout - {datetime.now().strftime('%H:%M:%S')}"
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
        """Handle indicator values update"""
        for key, label in self.indicator_values_labels.items():
            if key in values:
                value = values[key]
                label.setText(str(value))
            else:
                label.setText("--")
            label.setVisible(True)
    
    def add_status(self, message: str):
        """Add status message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
    
    def load_available_symbols(self):
        """Load available symbols from MT5"""
        try:
            if not self.mt5 or not self.mt5.is_connected():
                QMessageBox.warning(self, "Not Connected", "Please connect to MT5 first")
                return
            
            symbols = self.mt5.get_available_symbols()
            if symbols:
                self.symbol_combo.clear()
                for symbol in symbols[:100]:  # Limit to first 100
                    self.symbol_combo.addItem(symbol)
                self.add_status(f"Loaded {len(symbols)} available symbols")
            else:
                QMessageBox.warning(self, "No Symbols", "No symbols found. Please check your MT5 connection and broker account.")
        except Exception as e:
            error_msg = f"Error loading symbols: {str(e)}"
            self.add_status(error_msg)
            logger.error(f"Error loading symbols: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", error_msg)

