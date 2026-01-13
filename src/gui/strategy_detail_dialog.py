"""
Strategy Detail Dialog
Shows complete strategy configuration in a read-only dialog
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QScrollArea,
                             QWidget, QLabel, QGroupBox, QPushButton, QTextEdit, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from typing import Dict, Any
import MetaTrader5 as mt5

from ..strategy.base_strategy import BaseStrategy
from ..strategy.ohlc_price_strategy import OHLCPriceStrategy
from ..strategy.vwap_strategy import VWAPStrategy
from ..strategy.ema_strategy import EMAStrategy
from ..strategy.supertrend_strategy import SuperTrendStrategy
# SMMA strategy removed - not working properly
# from ..strategy.smma_strategy import SMMAStrategy
from ..strategy.smc_strategy import SMCStrategy
from ..strategy.session_first_candle_strategy import SessionFirstCandleStrategy
from ..tools.vwap_validator import VWAPValidator
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StrategyDetailDialog(QDialog):
    """Dialog showing complete strategy details"""
    
    def __init__(self, strategy: BaseStrategy, parent=None):
        super().__init__(parent)
        self.strategy = strategy
        self.setWindowTitle(f"Strategy Details: {strategy.name}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setup_ui()
        self.load_strategy_data()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)
        
        # Store layout reference for adding groups
        self.content_layout = content_layout
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
    
    def load_strategy_data(self):
        """Load and display strategy data"""
        # Basic Information
        basic_group = QGroupBox("Basic Information")
        basic_layout = QVBoxLayout()
        
        # Get strategy type
        strategy_type = getattr(self.strategy, 'strategy_type', None)
        if not strategy_type:
            # Try to infer from class type
            if isinstance(self.strategy, OHLCPriceStrategy):
                strategy_type = "OHLC Price Strategy"
            elif isinstance(self.strategy, VWAPStrategy):
                strategy_type = "VWAP Strategy"
            elif isinstance(self.strategy, EMAStrategy):
                strategy_type = "EMA Strategy"
            elif isinstance(self.strategy, SuperTrendStrategy):
                strategy_type = "SuperTrend Strategy"
            # SMMA strategy removed - not working properly
            # elif isinstance(self.strategy, SMMAStrategy):
            #     strategy_type = "SMMA Strategy"
            elif isinstance(self.strategy, SMCStrategy):
                strategy_type = "SMC Strategy"
            else:
                strategy_type = "Unknown Strategy"
        
        # Get trade direction
        trade_direction = getattr(self.strategy, 'trade_direction', 'both')
        direction_display = {
            'long': 'Long-only (BUY trades only)',
            'short': 'Short-only (SELL trades only)',
            'both': 'Long & Short (Both BUY and SELL trades)'
        }.get(trade_direction, trade_direction)
        
        # Determine active directions
        if trade_direction == 'long':
            active_directions = "[ACTIVE] LONG | [INACTIVE] SHORT"
        elif trade_direction == 'short':
            active_directions = "[INACTIVE] LONG | [ACTIVE] SHORT"
        else:  # both
            active_directions = "[ACTIVE] LONG | [ACTIVE] SHORT"
        
        basic_info = [
            ("Name:", self.strategy.name),
            ("Symbol:", self.strategy.symbol),
            ("Strategy Type:", strategy_type),
            ("Trade Direction:", direction_display),
            ("Active Directions:", active_directions),
            ("Status:", "Enabled" if self.strategy.enabled else "Disabled"),
            ("Timeframe:", self._format_timeframe(getattr(self.strategy, 'timeframe', mt5.TIMEFRAME_M1))),
        ]
        
        for label, value in basic_info:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{label}</b>"))
            row.addWidget(QLabel(str(value)))
            row.addStretch()
            basic_layout.addLayout(row)
        
        basic_group.setLayout(basic_layout)
        self.content_layout.addWidget(basic_group)
        
        # Strategy-specific sections
        if isinstance(self.strategy, OHLCPriceStrategy):
            self._load_ohlc_details()
        elif isinstance(self.strategy, VWAPStrategy):
            self._load_vwap_details()
        elif isinstance(self.strategy, EMAStrategy):
            self._load_ema_details()
        elif isinstance(self.strategy, SuperTrendStrategy):
            self._load_supertrend_details()
        # SMMA strategy removed - not working properly
        # elif isinstance(self.strategy, SMMAStrategy):
        #     self._load_smma_details()
        elif isinstance(self.strategy, SMCStrategy):
            self._load_smc_details()
        elif isinstance(self.strategy, SessionFirstCandleStrategy):
            self._load_session_first_candle_details()
        
        # Buy Conditions
        buy_group = QGroupBox("Buy Conditions")
        buy_layout = QVBoxLayout()
        
        # Check if strategy auto-generates signals
        # SMMA strategy removed - not working properly
        is_auto_signal = isinstance(self.strategy, SuperTrendStrategy)  # Removed SMMAStrategy
        # is_auto_signal = isinstance(self.strategy, (SuperTrendStrategy, SMMAStrategy))
        
        if is_auto_signal:
            if isinstance(self.strategy, SuperTrendStrategy):
                buy_layout.addWidget(QLabel("<i>Disabled - SuperTrend auto-generates BUY signals based on trend flips</i>"))
            # elif isinstance(self.strategy, SMMAStrategy):
            #     buy_layout.addWidget(QLabel("<i>Disabled - SMMA auto-generates BUY Entry signals when price crosses above High of crossover candle</i>"))
        elif hasattr(self.strategy, 'buy_conditions') and self.strategy.buy_conditions:
            for i, condition in enumerate(self.strategy.buy_conditions, 1):
                condition_text = self._format_condition(condition, "BUY")
                label = QLabel(f"<b>Condition {i}:</b> {condition_text}")
                label.setWordWrap(True)
                label.setStyleSheet("padding: 5px;")
                buy_layout.addWidget(label)
        else:
            buy_layout.addWidget(QLabel("No buy conditions defined"))
        
        buy_group.setLayout(buy_layout)
        self.content_layout.addWidget(buy_group)
        
        # Sell Conditions
        sell_group = QGroupBox("Sell Conditions")
        sell_layout = QVBoxLayout()
        
        if is_auto_signal:
            if isinstance(self.strategy, SuperTrendStrategy):
                sell_layout.addWidget(QLabel("<i>Disabled - SuperTrend auto-generates SELL signals based on trend flips</i>"))
            # SMMA strategy removed - not working properly
            # elif isinstance(self.strategy, SMMAStrategy):
            #     sell_layout.addWidget(QLabel("<i>Disabled - SMMA auto-generates SELL Entry signals when price crosses below Low of crossunder candle</i>"))
        elif hasattr(self.strategy, 'sell_conditions') and self.strategy.sell_conditions:
            for i, condition in enumerate(self.strategy.sell_conditions, 1):
                condition_text = self._format_condition(condition, "SELL")
                label = QLabel(f"<b>Condition {i}:</b> {condition_text}")
                label.setWordWrap(True)
                label.setStyleSheet("padding: 5px;")
                sell_layout.addWidget(label)
        else:
            sell_layout.addWidget(QLabel("No sell conditions defined"))
        
        sell_group.setLayout(sell_layout)
        self.content_layout.addWidget(sell_group)
        
        # SL/TP Configuration
        sl_tp_group = QGroupBox("Stop Loss / Take Profit Configuration")
        sl_tp_layout = QVBoxLayout()
        
        sl_type = getattr(self.strategy, 'sl_type', None)
        sl_type_display = sl_type if sl_type else "Not set"
        sl_value = getattr(self.strategy, 'sl_value', 0.0)
        use_ratio = getattr(self.strategy, 'use_ratio', False)
        tp_value = getattr(self.strategy, 'tp_value', 0.0)
        
        # Format SL value with units
        if sl_type:
            if "Pips" in sl_type:
                sl_value_str = f"{sl_value:.2f} pips"
            elif "Points" in sl_type:
                sl_value_str = f"{sl_value:.2f} points"
            elif "Percentage" in sl_type:
                sl_value_str = f"{sl_value:.2f}%"
            else:
                sl_value_str = f"{sl_value:.2f}"
        else:
            sl_value_str = f"{sl_value:.2f}"
        
        # Format TP value
        if use_ratio:
            tp_value_str = f"{tp_value:.2f} (1:{tp_value/sl_value:.1f} ratio)" if sl_value > 0 else f"{tp_value:.2f}"
        else:
            if sl_type and "Pips" in sl_type:
                tp_value_str = f"{tp_value:.2f} pips"
            elif sl_type and "Points" in sl_type:
                tp_value_str = f"{tp_value:.2f} points"
            elif sl_type and "Percentage" in sl_type:
                tp_value_str = f"{tp_value:.2f}%"
            else:
                tp_value_str = f"{tp_value:.2f}"
        
        sl_enabled = getattr(self.strategy, 'sl_enabled', True)
        tp_enabled = getattr(self.strategy, 'tp_enabled', True)
        lot_size = getattr(self.strategy, 'lot_size', None)
        trade_monitoring_mode = getattr(self.strategy, 'trade_monitoring_mode', 'LTP')
        
        sl_tp_info = [
            ("SL Enabled:", "Yes" if sl_enabled else "No"),
            ("SL Type:", sl_type_display),
            ("SL Value:", sl_value_str),
            ("TP Enabled:", "Yes" if tp_enabled else "No"),
            ("Use Ratio:", "Yes" if use_ratio else "No"),
            ("TP Value:", tp_value_str),
            ("Lot Size:", f"{lot_size:.2f}" if lot_size else "Default (from settings)"),
            ("Trade Monitoring Mode:", trade_monitoring_mode),
        ]
        
        for label, value in sl_tp_info:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{label}</b>"))
            row.addWidget(QLabel(str(value)))
            row.addStretch()
            sl_tp_layout.addLayout(row)
        
        sl_tp_group.setLayout(sl_tp_layout)
        self.content_layout.addWidget(sl_tp_group)
        
        # Re-Entry Settings
        reentry_group = QGroupBox("Re-Entry Settings")
        reentry_layout = QVBoxLayout()
        
        # Re-entry on SL
        reentry_sl_enabled = getattr(self.strategy, 'reentry_on_sl_enabled', False)
        reentry_sl_mode = getattr(self.strategy, 'reentry_on_sl_mode', None)
        reentry_sl_count = getattr(self.strategy, 'reentry_on_sl_count', 0)
        
        reentry_layout.addWidget(QLabel(f"<b>Re-Entry on SL:</b> {'Enabled' if reentry_sl_enabled else 'Disabled'}"))
        if reentry_sl_enabled:
            reentry_layout.addWidget(QLabel(f"  Mode: {reentry_sl_mode or 'Not set'}"))
            reentry_layout.addWidget(QLabel(f"  Max Count: {reentry_sl_count}"))
        
        # Re-entry on TP
        reentry_tp_enabled = getattr(self.strategy, 'reentry_on_tp_enabled', False)
        reentry_tp_mode = getattr(self.strategy, 'reentry_on_tp_mode', None)
        reentry_tp_count = getattr(self.strategy, 'reentry_on_tp_count', 0)
        
        reentry_layout.addWidget(QLabel(f"<b>Re-Entry on TP:</b> {'Enabled' if reentry_tp_enabled else 'Disabled'}"))
        if reentry_tp_enabled:
            reentry_layout.addWidget(QLabel(f"  Mode: {reentry_tp_mode or 'Not set'}"))
            reentry_layout.addWidget(QLabel(f"  Max Count: {reentry_tp_count}"))
        
        reentry_group.setLayout(reentry_layout)
        self.content_layout.addWidget(reentry_group)
        
        # Position Preservation
        preserve_group = QGroupBox("Position Management")
        preserve_layout = QVBoxLayout()
        
        preserve_position = getattr(self.strategy, 'preserve_position', False)
        preserve_layout.addWidget(QLabel(f"<b>Preserve Position:</b> {'Enabled' if preserve_position else 'Disabled'}"))
        if preserve_position:
            preserve_layout.addWidget(QLabel("  Prevents opening duplicate positions for the same strategy, symbol, and direction"))
        
        preserve_group.setLayout(preserve_layout)
        self.content_layout.addWidget(preserve_group)
        
        # Advanced Risk Management
        risk_group = QGroupBox("Advanced Risk Management")
        risk_layout = QVBoxLayout()
        
        # Trailing Stop-Loss
        trailing_sl_enabled = getattr(self.strategy, 'enable_trailing_sl', False)
        trailing_sl_gap = getattr(self.strategy, 'trailing_sl_gap', 0.0)
        
        risk_layout.addWidget(QLabel(f"<b>Trailing Stop-Loss:</b> {'Enabled' if trailing_sl_enabled else 'Disabled'}"))
        if trailing_sl_enabled:
            risk_layout.addWidget(QLabel(f"  SL Gap: {trailing_sl_gap:.2f} points"))
            risk_layout.addWidget(QLabel("  Automatically moves stop-loss behind price at fixed gap distance"))
        
        # Profit Lock
        profit_lock_enabled = getattr(self.strategy, 'enable_profit_lock', False)
        profit_lock_trigger = getattr(self.strategy, 'profit_lock_trigger', 0.0)
        profit_lock_value = getattr(self.strategy, 'profit_lock_value', 0.0)
        profit_trail_step = getattr(self.strategy, 'profit_trail_step', 0.0)
        profit_trail_amount = getattr(self.strategy, 'profit_trail_amount', 0.0)
        
        risk_layout.addWidget(QLabel(f"<b>Profit Lock + Trailing:</b> {'Enabled' if profit_lock_enabled else 'Disabled'}"))
        if profit_lock_enabled:
            risk_layout.addWidget(QLabel(f"  Trigger Profit: ${profit_lock_trigger:.2f}"))
            risk_layout.addWidget(QLabel(f"  Min. Locked Profit: ${profit_lock_value:.2f}"))
            if profit_trail_step > 0:
                risk_layout.addWidget(QLabel(f"  Trail Step: ${profit_trail_step:.2f}"))
                risk_layout.addWidget(QLabel(f"  Trail Amount: ${profit_trail_amount:.2f}"))
            risk_layout.addWidget(QLabel("  Locks minimum profit once trigger is reached, then trails upward"))
        
        risk_group.setLayout(risk_layout)
        self.content_layout.addWidget(risk_group)
        
        # Time Rules
        if hasattr(self.strategy, 'time_rules') and self.strategy.time_rules:
            time_group = QGroupBox("Trading Time Rules")
            time_layout = QVBoxLayout()
            
            for i, rule in enumerate(self.strategy.time_rules, 1):
                start = rule.get('start_time', 'N/A')
                end = rule.get('end_time', 'N/A')
                days = rule.get('days', None)
                days_str = f"Days: {days}" if days else "All days"
                time_layout.addWidget(QLabel(f"<b>Rule {i}:</b> {start} - {end} ({days_str})"))
            
            time_group.setLayout(time_layout)
            self.content_layout.addWidget(time_group)
        
        # Indicators
        if self.strategy.indicators:
            indicators_group = QGroupBox("Indicators")
            indicators_layout = QVBoxLayout()
            
            for name, indicator in self.strategy.indicators.items():
                indicator_type = type(indicator).__name__
                indicators_layout.addWidget(QLabel(f"<b>{name}:</b> {indicator_type}"))
            
            indicators_group.setLayout(indicators_layout)
            self.content_layout.addWidget(indicators_group)
        
        # Add stretch at the end
        self.content_layout.addStretch()
    
    def _load_ohlc_details(self):
        """Load OHLC-specific details"""
        if not isinstance(self.strategy, OHLCPriceStrategy):
            return
        
        ohlc_group = QGroupBox("OHLC Strategy Settings")
        ohlc_layout = QVBoxLayout()
        
        session_type = getattr(self.strategy, 'session_type', 'NY')
        
        ohlc_info = [
            ("Session Type:", session_type),
        ]
        
        for label, value in ohlc_info:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{label}</b>"))
            row.addWidget(QLabel(str(value)))
            row.addStretch()
            ohlc_layout.addLayout(row)
        
        ohlc_group.setLayout(ohlc_layout)
        self.content_layout.addWidget(ohlc_group)
    
    def _load_vwap_details(self):
        """Load VWAP-specific details"""
        if not isinstance(self.strategy, VWAPStrategy):
            return
        
        vwap_group = QGroupBox("VWAP Strategy Settings")
        vwap_layout = QVBoxLayout()
        
        session_type = getattr(self.strategy, 'session_type', 'NY')
        std_bands = getattr(self.strategy, 'std_bands', [1.0, 1.5, 2.0])
        swing_period = getattr(self.strategy, 'swing_period', 10)
        
        # Entry strategies
        mean_reversion_enabled = getattr(self.strategy, 'enable_mean_reversion', False)
        trend_following_enabled = getattr(self.strategy, 'enable_trend_following', False)
        breakout_enabled = getattr(self.strategy, 'enable_breakout', False)
        
        # Format std bands
        std_bands_str = ', '.join(map(str, std_bands))
        
        vwap_info = [
            ("Session Type:", session_type),
            ("Standard Deviation Bands:", std_bands_str),
            ("Swing Period:", f"{swing_period} candles"),
            ("Mean Reversion Entry:", "Enabled" if mean_reversion_enabled else "Disabled"),
            ("Trend Following Entry:", "Enabled" if trend_following_enabled else "Disabled"),
            ("Breakout Entry:", "Enabled" if breakout_enabled else "Disabled"),
        ]
        
        for label, value in vwap_info:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{label}</b>"))
            row.addWidget(QLabel(str(value)))
            row.addStretch()
            vwap_layout.addLayout(row)
        
        vwap_group.setLayout(vwap_layout)
        self.content_layout.addWidget(vwap_group)
        
        # Add current VWAP values display
        self._load_current_vwap_values()
    
    def _load_current_vwap_values(self):
        """Load and display current VWAP values"""
        if not isinstance(self.strategy, VWAPStrategy):
            return
        
        # Try to get current VWAP data if strategy is initialized
        try:
            vwap_data = self.strategy._get_vwap_data()
            if not vwap_data:
                # Strategy not initialized or no data yet
                vwap_display_group = QGroupBox("Current VWAP Values")
                vwap_display_layout = QVBoxLayout()
                vwap_display_layout.addWidget(QLabel("<i>VWAP data not available. Strategy needs to be running to display current values.</i>"))
                vwap_display_group.setLayout(vwap_display_layout)
                self.content_layout.addWidget(vwap_display_group)
                return
            
            vwap_value = vwap_data.get('vwap')
            bands = vwap_data.get('bands', {})
            session_info = vwap_data.get('session_info', {})
            
            vwap_display_group = QGroupBox("Current VWAP Values")
            vwap_display_layout = QVBoxLayout()
            
            # Current VWAP
            vwap_row = QHBoxLayout()
            vwap_row.addWidget(QLabel("<b>Current VWAP:</b>"))
            vwap_label = QLabel(f"{vwap_value:.5f}" if vwap_value else "N/A")
            vwap_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
            vwap_row.addWidget(vwap_label)
            vwap_row.addStretch()
            vwap_display_layout.addLayout(vwap_row)
            
            # Bands
            if bands:
                bands_label = QLabel("<b>Standard Deviation Bands:</b>")
                vwap_display_layout.addWidget(bands_label)
                
                for std_dev, band_data in sorted(bands.items()):
                    upper = band_data.get('upper')
                    lower = band_data.get('lower')
                    band_row = QHBoxLayout()
                    band_row.addWidget(QLabel(f"  STD {std_dev}:"))
                    band_row.addWidget(QLabel(f"Upper: {upper:.5f}" if upper else "Upper: N/A"))
                    band_row.addWidget(QLabel(f"Lower: {lower:.5f}" if lower else "Lower: N/A"))
                    band_row.addStretch()
                    vwap_display_layout.addLayout(band_row)
            
            # Session info
            if session_info:
                session_start = session_info.get('session_start_time')
                cumulative_volume = session_info.get('cumulative_volume', 0)
                if session_start or cumulative_volume:
                    session_label = QLabel("<b>Session Information:</b>")
                    vwap_display_layout.addWidget(session_label)
                    
                    if session_start:
                        session_row = QHBoxLayout()
                        session_row.addWidget(QLabel("  Session Start:"))
                        session_row.addWidget(QLabel(str(session_start)))
                        session_row.addStretch()
                        vwap_display_layout.addLayout(session_row)
                    
                    if cumulative_volume:
                        volume_row = QHBoxLayout()
                        volume_row.addWidget(QLabel("  Cumulative Volume:"))
                        volume_row.addWidget(QLabel(f"{cumulative_volume:.2f}"))
                        volume_row.addStretch()
                        vwap_display_layout.addLayout(volume_row)
            
            # Export button
            export_btn = QPushButton("Export VWAP Snapshot")
            export_btn.clicked.connect(lambda: self._export_vwap_snapshot(vwap_data))
            vwap_display_layout.addWidget(export_btn)
            
            vwap_display_group.setLayout(vwap_display_layout)
            self.content_layout.addWidget(vwap_display_group)
            
        except Exception as e:
            logger.error(f"Error loading current VWAP values: {e}", exc_info=True)
            error_group = QGroupBox("Current VWAP Values")
            error_layout = QVBoxLayout()
            error_layout.addWidget(QLabel(f"<i>Error loading VWAP data: {str(e)}</i>"))
            error_group.setLayout(error_layout)
            self.content_layout.addWidget(error_group)
    
    def _export_vwap_snapshot(self, vwap_data: Dict):
        """Export current VWAP snapshot to file"""
        try:
            # Get current price if available
            current_price = 0.0
            if hasattr(self.strategy, 'mt5_connector') and self.strategy.mt5_connector:
                try:
                    tick = self.strategy.mt5_connector.get_latest_tick(self.strategy.symbol)
                    if tick:
                        current_price = (tick.get('bid', 0) + tick.get('ask', 0)) / 2.0
                except:
                    pass
            
            # Open file dialog
            file_path, selected_filter = QFileDialog.getSaveFileName(
                self,
                "Export VWAP Snapshot",
                f"vwap_snapshot_{self.strategy.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "JSON Files (*.json);;CSV Files (*.csv);;All Files (*)"
            )
            
            if not file_path:
                return
            
            # Determine format from file extension
            format_type = 'csv' if file_path.endswith('.csv') else 'json'
            
            # Export using validator
            validator = VWAPValidator()
            success = validator.export_vwap_snapshot(
                vwap_data=vwap_data,
                current_price=current_price,
                symbol=self.strategy.symbol,
                output_path=file_path,
                format=format_type
            )
            
            if success:
                QMessageBox.information(self, "Export Successful", 
                                      f"VWAP snapshot exported successfully to:\n{file_path}")
            else:
                QMessageBox.warning(self, "Export Failed", 
                                  "Failed to export VWAP snapshot. Check logs for details.")
                
        except Exception as e:
            logger.error(f"Error exporting VWAP snapshot: {e}", exc_info=True)
            QMessageBox.critical(self, "Export Error", 
                               f"Error exporting VWAP snapshot:\n{str(e)}")
    
    def _format_condition(self, condition, signal_type: str) -> str:
        """Format a condition object to human-readable text - matches Trading Bot Panel format"""
        # Handle dictionary conditions (from Trading Bot Panel)
        if isinstance(condition, dict):
            price_ref = condition.get('price_reference', 'Current Price')
            operator = condition.get('operator', '')
            ohlc_field = condition.get('ohlc_field')
            vwap_field = condition.get('vwap_field')
            value = condition.get('value')
            
            if ohlc_field:
                ohlc_display = ohlc_field.replace('_', ' ').title()
                return f"{price_ref} {operator} Previous {ohlc_display.upper()}"
            elif vwap_field:
                # Format VWAP field names to match Trading Bot Panel
                vwap_display_map = {
                    'vwap': 'VWAP',
                    'upper_band_1': 'Upper Band (1 STD)',
                    'upper_band_1.5': 'Upper Band (1.5 STD)',
                    'upper_band_2': 'Upper Band (2 STD)',
                    'lower_band_1': 'Lower Band (1 STD)',
                    'lower_band_1.5': 'Lower Band (1.5 STD)',
                    'lower_band_2': 'Lower Band (2 STD)',
                }
                field_name = vwap_display_map.get(vwap_field, vwap_field.replace('_', ' ').title())
                return f"{price_ref} {operator} {field_name}"
            elif value is not None:
                return f"{price_ref} {operator} {value}"
            else:
                return f"{price_ref} {operator}"
        
        # Handle condition objects (from strategy classes)
        if hasattr(condition, 'price_reference'):
            price_ref = condition.price_reference
            operator = condition.operator
            ohlc_field = getattr(condition, 'ohlc_field', None)
            vwap_field = getattr(condition, 'vwap_field', None)
            value = getattr(condition, 'value', None)
            
            if ohlc_field:
                ohlc_display = ohlc_field.replace('_', ' ').title()
                return f"{price_ref} {operator} Previous {ohlc_display.upper()}"
            elif vwap_field:
                # Format VWAP field names to match Trading Bot Panel
                vwap_display_map = {
                    'vwap': 'VWAP',
                    'upper_band_1': 'Upper Band (1 STD)',
                    'upper_band_1.5': 'Upper Band (1.5 STD)',
                    'upper_band_2': 'Upper Band (2 STD)',
                    'lower_band_1': 'Lower Band (1 STD)',
                    'lower_band_1.5': 'Lower Band (1.5 STD)',
                    'lower_band_2': 'Lower Band (2 STD)',
                }
                field_name = vwap_display_map.get(vwap_field, vwap_field.replace('_', ' ').title())
                return f"{price_ref} {operator} {field_name}"
            elif value is not None:
                return f"{price_ref} {operator} {value}"
            else:
                return f"{price_ref} {operator}"
        
        return str(condition)
    
    def _format_timeframe(self, timeframe: int) -> str:
        """Format MT5 timeframe to string"""
        timeframe_map = {
            mt5.TIMEFRAME_M1: "M1 (1 Minute)",
            mt5.TIMEFRAME_M5: "M5 (5 Minutes)",
            mt5.TIMEFRAME_M15: "M15 (15 Minutes)",
            mt5.TIMEFRAME_M30: "M30 (30 Minutes)",
            mt5.TIMEFRAME_H1: "H1 (1 Hour)",
            mt5.TIMEFRAME_H4: "H4 (4 Hours)",
            mt5.TIMEFRAME_D1: "D1 (Daily)",
        }
        return timeframe_map.get(timeframe, f"Unknown ({timeframe})")
    
    def _load_ema_details(self):
        """Load EMA-specific details"""
        if not isinstance(self.strategy, EMAStrategy):
            return
        
        ema_group = QGroupBox("EMA Strategy Settings")
        ema_layout = QVBoxLayout()
        
        ema_periods = getattr(self.strategy, 'ema_periods', {})
        
        ema_info = [
            ("EMA 1 Period:", str(ema_periods.get('ema_1', 20))),
            ("EMA 2 Period:", str(ema_periods.get('ema_2', 50))),
            ("EMA 3 Period:", str(ema_periods.get('ema_3', 100))),
            ("EMA 4 Period:", str(ema_periods.get('ema_4', 200))),
        ]
        
        for label, value in ema_info:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{label}</b>"))
            row.addWidget(QLabel(str(value)))
            row.addStretch()
            ema_layout.addLayout(row)
        
        ema_group.setLayout(ema_layout)
        self.content_layout.addWidget(ema_group)
    
    def _load_supertrend_details(self):
        """Load SuperTrend-specific details"""
        if not isinstance(self.strategy, SuperTrendStrategy):
            return
        
        st_group = QGroupBox("SuperTrend Strategy Settings")
        st_layout = QVBoxLayout()
        
        period = getattr(self.strategy, 'period', 10)
        multiplier = getattr(self.strategy, 'multiplier', 3.0)
        use_wilder_atr = getattr(self.strategy, 'use_wilder_atr', True)
        atr_method = "Wilder ATR" if use_wilder_atr else "SMA(TR)"
        
        st_info = [
            ("ATR Period:", str(period)),
            ("ATR Multiplier:", f"{multiplier:.1f}"),
            ("ATR Method:", atr_method),
        ]
        
        for label, value in st_info:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{label}</b>"))
            row.addWidget(QLabel(str(value)))
            row.addStretch()
            st_layout.addLayout(row)
        
        st_layout.addWidget(QLabel("<i>Note: SuperTrend auto-generates signals based on trend flips</i>"))
        
        st_group.setLayout(st_layout)
        self.content_layout.addWidget(st_group)
    
    # SMMA strategy removed - not working properly
    # def _load_smma_details(self):
    #     """Load SMMA-specific details"""
    #     if not isinstance(self.strategy, SMMAStrategy):
    #         return
    #     
    #     smma_group = QGroupBox("SMMA Strategy Settings")
    #     smma_layout = QVBoxLayout()
    #     
    #     length = getattr(self.strategy, 'length', 7)
    #     source_price = getattr(self.strategy, 'source_price', 'close')
    #     
    #     # Format source price display
    #     source_price_display = {
    #         'close': 'Close',
    #         'open': 'Open',
    #         'high': 'High',
    #         'low': 'Low',
    #         'median': 'Median (H+L)/2',
    #         'typical': 'Typical (H+L+C)/3',
    #         'weighted': 'Weighted (H+L+C+C)/4'
    #     }.get(source_price.lower(), source_price.title())
    #     
    #     smma_info = [
    #         ("SMMA Length:", str(length)),
    #         ("Source Price:", source_price_display),
    #     ]
    #     
    #     for label, value in smma_info:
    #         row = QHBoxLayout()
    #         row.addWidget(QLabel(f"<b>{label}</b>"))
    #         row.addWidget(QLabel(str(value)))
    #         row.addStretch()
    #         smma_layout.addLayout(row)
    #     
    #     smma_layout.addWidget(QLabel("<i>Note: SMMA auto-generates signals based on Buy Entry/Sell Entry detection</i>"))
    #     smma_layout.addWidget(QLabel("<i>Buy Entry: Price crosses above High of crossover candle</i>"))
    #     smma_layout.addWidget(QLabel("<i>Sell Entry: Price crosses below Low of crossunder candle</i>"))
    #     
    #     smma_group.setLayout(smma_layout)
    #     self.content_layout.addWidget(smma_group)
    
    def _load_smc_details(self):
        """Load SMC-specific details"""
        if not isinstance(self.strategy, SMCStrategy):
            return
        
        smc_group = QGroupBox("SMC Strategy Settings")
        smc_layout = QVBoxLayout()
        
        pivot_left = getattr(self.strategy, 'pivot_left', 2)
        pivot_right = getattr(self.strategy, 'pivot_right', 2)
        emit_on = getattr(self.strategy, 'emit_on', 'NONE')
        
        smc_info = [
            ("Pivot Left:", str(pivot_left)),
            ("Pivot Right:", str(pivot_right)),
            ("Emit On:", emit_on),
        ]
        
        for label, value in smc_info:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{label}</b>"))
            row.addWidget(QLabel(str(value)))
            row.addStretch()
            smc_layout.addLayout(row)
        
        smc_layout.addWidget(QLabel("<i>Note: SMC generates signals based on BOS/CHoCH events</i>"))
        smc_layout.addWidget(QLabel("<i>Buy/Sell conditions act as filters, not signal generators</i>"))
        
        smc_group.setLayout(smc_layout)
        self.content_layout.addWidget(smc_group)
    
    def _load_session_first_candle_details(self):
        """Load Session First Candle-specific details"""
        if not isinstance(self.strategy, SessionFirstCandleStrategy):
            return
        
        from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QHBoxLayout, QLabel
        
        sfc_group = QGroupBox("Session First Candle Strategy Settings")
        sfc_layout = QVBoxLayout()
        
        # Session configuration
        session1_start = getattr(self.strategy, 'session1_start_hour', 0)
        session1_end = getattr(self.strategy, 'session1_end_hour', 9)
        session2_start = getattr(self.strategy, 'session2_start_hour', 8)
        session2_end = getattr(self.strategy, 'session2_end_hour', 17)
        session3_start = getattr(self.strategy, 'session3_start_hour', 13)
        session3_end = getattr(self.strategy, 'session3_end_hour', 22)
        
        # Get current session high/low if available
        session_high = None
        session_low = None
        active_session = 0
        if hasattr(self.strategy, 'session_first_candle'):
            session_high = self.strategy.session_first_candle.get_session_high()
            session_low = self.strategy.session_first_candle.get_session_low()
            active_session = self.strategy.session_first_candle.get_current_session()
        
        sfc_info = [
            ("Session 1", f"{session1_start:02d}:00 - {session1_end:02d}:00"),
            ("Session 2", f"{session2_start:02d}:00 - {session2_end:02d}:00" if session2_start >= 0 else "Disabled"),
            ("Session 3", f"{session3_start:02d}:00 - {session3_end:02d}:00" if session3_start >= 0 else "Disabled"),
            ("Active Session", str(active_session) if active_session > 0 else "None"),
            ("Current High Line", f"{session_high:.5f}" if session_high is not None else "N/A"),
            ("Current Low Line", f"{session_low:.5f}" if session_low is not None else "N/A"),
        ]
        
        for label, value in sfc_info:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"<b>{label}:</b>"))
            row.addWidget(QLabel(str(value)))
            row.addStretch()
            sfc_layout.addLayout(row)
        
        sfc_layout.addWidget(QLabel("<i>Note: High/Low lines are calculated from the first candle of each session</i>"))
        
        sfc_group.setLayout(sfc_layout)
        self.content_layout.addWidget(sfc_group)

