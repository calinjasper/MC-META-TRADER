"""
Chart Widget
Displays price charts with indicator overlays and trading bot indicators
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                             QPushButton, QLabel, QCheckBox, QGroupBox, QToolTip, QLineEdit)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPen, QBrush, QColor, QMouseEvent, QEnterEvent
import pyqtgraph as pg
from pyqtgraph import DateAxisItem, InfiniteLine, TextItem
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
import math

from ..data_feed import DataFeed
from ..indicators.vwap import VWAP


class CandlestickItem(pg.GraphicsObject):
    """Custom candlestick item for pyqtgraph"""
    
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        # Convert datetime to timestamp for pyqtgraph
        self.data = []
        
        if not data:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("CandlestickItem: No data provided")
            self.generatePicture()
            return
        
        for time, open_price, high, low, close in data:
            if isinstance(time, datetime):
                time_ts = time.timestamp()
            else:
                time_ts = float(time)
            
            # Validate data
            if not all(isinstance(x, (int, float)) and not (isinstance(x, float) and (x != x or x == float('inf') or x == float('-inf'))) 
                       for x in [time_ts, open_price, high, low, close]):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Invalid candlestick data: time={time_ts}, O={open_price}, H={high}, L={low}, C={close}")
                continue
            
            self.data.append((time_ts, open_price, high, low, close))
        
        if not self.data:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("CandlestickItem: No valid data after processing")
            # Create empty picture with valid boundingRect to prevent rendering issues
            self.picture = pg.QtGui.QPicture()
            return
        
        self.generatePicture()
    
    def generatePicture(self):
        self.picture = pg.QtGui.QPicture()
        painter = pg.QtGui.QPainter(self.picture)
        
        # Calculate candle width based on time range
        if len(self.data) > 1:
            time_range = self.data[-1][0] - self.data[0][0]
            w = time_range / len(self.data) * 0.6  # 60% of bar width
        else:
            w = 3600  # Default 1 hour width
        
        for time, open_price, high, low, close in self.data:
            # Determine if bullish (green) or bearish (red)
            is_bullish = close >= open_price
            
            # Set colors
            if is_bullish:
                body_color = QColor(0, 255, 0)  # Green
                wick_color = QColor(0, 200, 0)
            else:
                body_color = QColor(255, 0, 0)  # Red
                wick_color = QColor(200, 0, 0)
            
            # Draw wick (high-low line)
            painter.setPen(QPen(wick_color, 1))
            painter.drawLine(pg.QtCore.QPointF(time, low), pg.QtCore.QPointF(time, high))
            
            # Draw body
            body_top = max(open_price, close)
            body_bottom = min(open_price, close)
            body_height = body_top - body_bottom
            
            if body_height > 0:
                painter.setBrush(QBrush(body_color))
                painter.setPen(QPen(body_color, 1))
                painter.drawRect(pg.QtCore.QRectF(
                    time - w/2, body_bottom,
                    w, body_height
                ))
            else:
                # Doji - draw as line
                painter.setPen(QPen(body_color, 2))
                painter.drawLine(
                    pg.QtCore.QPointF(time - w/2, open_price),
                    pg.QtCore.QPointF(time + w/2, open_price)
                )
        
        painter.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        if not hasattr(self, 'picture') or self.picture is None:
            return pg.QtCore.QRectF()
        br = self.picture.boundingRect()
        if br.isNull() or br.isEmpty():
            # Return a default rect if picture is invalid
            if self.data:
                # Calculate from data
                times = [d[0] for d in self.data]
                prices = [d[2] for d in self.data] + [d[3] for d in self.data]  # highs and lows
                if times and prices:
                    return pg.QtCore.QRectF(
                        min(times) - 3600, min(prices) - 1,
                        max(times) - min(times) + 7200, max(prices) - min(prices) + 2
                    )
            return pg.QtCore.QRectF()
        return pg.QtCore.QRectF(br)
    
    def update_candle(self, index: int, open_price: float, high: float, low: float, close: float):
        """Update a single candle at given index"""
        if 0 <= index < len(self.data):
            self.data[index] = (self.data[index][0], open_price, high, low, close)
            self.generatePicture()
            self.update()


class CurrentBarItem(pg.GraphicsObject):
    """Real-time forming candle visualization"""
    
    def __init__(self, bar_time: datetime, open_price: float, candle_width: float):
        pg.GraphicsObject.__init__(self)
        self.bar_time = bar_time
        self.bar_time_ts = bar_time.timestamp() if isinstance(bar_time, datetime) else bar_time
        self.open_price = open_price
        self.high = open_price
        self.low = open_price
        self.close = open_price
        self.candle_width = candle_width
        self.generatePicture()
    
    def update_bar(self, high: float, low: float, close: float):
        """Update current bar with new high/low/close"""
        self.high = max(self.high, high)
        self.low = min(self.low, low)
        self.close = close
        self.generatePicture()
        self.update()
    
    def generatePicture(self):
        self.picture = pg.QtGui.QPicture()
        painter = pg.QtGui.QPainter(self.picture)
        
        is_bullish = self.close >= self.open_price
        
        if is_bullish:
            body_color = QColor(0, 255, 0)  # Green
            wick_color = QColor(0, 200, 0)
        else:
            body_color = QColor(255, 0, 0)  # Red
            wick_color = QColor(200, 0, 0)
        
        # Draw wick
        painter.setPen(QPen(wick_color, 1))
        painter.drawLine(pg.QtCore.QPointF(self.bar_time_ts, self.low), 
                        pg.QtCore.QPointF(self.bar_time_ts, self.high))
        
        # Draw body
        body_top = max(self.open_price, self.close)
        body_bottom = min(self.open_price, self.close)
        body_height = body_top - body_bottom
        
        if body_height > 0:
            painter.setBrush(QBrush(body_color))
            painter.setPen(QPen(body_color, 1))
            painter.drawRect(pg.QtCore.QRectF(
                self.bar_time_ts - self.candle_width/2, body_bottom,
                self.candle_width, body_height
            ))
        else:
            painter.setPen(QPen(body_color, 2))
            painter.drawLine(
                pg.QtCore.QPointF(self.bar_time_ts - self.candle_width/2, self.open_price),
                pg.QtCore.QPointF(self.bar_time_ts + self.candle_width/2, self.open_price)
            )
        
        painter.end()
    
    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)
    
    def boundingRect(self):
        return pg.QtCore.QRectF(
            self.bar_time_ts - self.candle_width/2, self.low,
            self.candle_width, self.high - self.low
        )


class ChartWidget(QWidget):
    """Price chart with indicator support and trading bot indicators"""
    
    def __init__(self, data_feed: DataFeed, mt5_connector=None, strategy_manager=None, market_data_panel=None):
        super().__init__()
        self.data_feed = data_feed
        self.mt5 = mt5_connector
        self.strategy_manager = strategy_manager
        self.market_data_panel = market_data_panel
        self.current_symbol = None
        self.current_timeframe = mt5.TIMEFRAME_H1
        self.indicators = {}
        self.bot_indicator_items = []  # Store bot indicator plot items
        self.general_vwap_items = []  # Store general VWAP plot items
        self.chart_times = []  # Store chart times for reference
        self.chart_rates = []  # Store chart rates for reference
        self.vwap_indicator = None  # General VWAP indicator instance
        
        # Real-time candle tracking
        self.current_bar = None  # Current forming bar: {'time': datetime, 'open': float, 'high': float, 'low': float, 'close': float}
        self.current_bar_item = None  # CurrentBarItem for real-time rendering
        self.candlestick_item = None  # Main candlestick item for completed bars
        self.last_bar_time = None  # Time of last completed bar
        
        # Interactive features
        self.crosshair_vline = None  # Vertical crosshair line
        self.crosshair_hline = None  # Horizontal crosshair line
        self.crosshair_price_label = None  # Price label on right axis
        self.crosshair_time_label = None  # Time label on bottom axis
        self.crosshair_enabled = True
        self.tooltip_timer = QTimer()
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self._update_tooltip)
        self.last_mouse_pos = None
        
        # Zoom/pan state
        self.zoom_state = None
        
        # Update throttling for real-time updates
        self.update_throttle_timer = QTimer()
        self.update_throttle_timer.setSingleShot(True)
        self.last_update_time = 0
        self.update_throttle_ms = 100  # Max 10 updates per second
        
        self.setup_ui()
        
        # Connect to data feed signals
        if hasattr(data_feed, 'tick_received'):
            # Update symbol list when new ticks arrive
            self.data_feed.tick_received.connect(self._on_tick_received)
            # Real-time candle updates
            self.data_feed.tick_received.connect(self._on_tick_for_candle_update)
    
    def setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Symbol selector
        symbol_label = QLabel("Symbol:")
        self.symbol_combo = QComboBox()
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed)
        controls_layout.addWidget(symbol_label)
        controls_layout.addWidget(self.symbol_combo)
        
        # Timeframe selector
        timeframe_label = QLabel("Timeframe:")
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems([
            "M1", "M5", "M15", "M30", "H1", "H4", "D1"
        ])
        self.timeframe_combo.setCurrentText("H1")
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        controls_layout.addWidget(timeframe_label)
        controls_layout.addWidget(self.timeframe_combo)
        
        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_chart)
        controls_layout.addWidget(refresh_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Zoom and Pan Controls Toolbar
        zoom_toolbar = QHBoxLayout()
        
        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setToolTip("Zoom In (or use mouse wheel)")
        zoom_in_btn.clicked.connect(self.zoom_in)
        zoom_toolbar.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setToolTip("Zoom Out (or use mouse wheel)")
        zoom_out_btn.clicked.connect(self.zoom_out)
        zoom_toolbar.addWidget(zoom_out_btn)
        
        fit_data_btn = QPushButton("Fit")
        fit_data_btn.setToolTip("Fit to Data (or press 0/Home)")
        fit_data_btn.clicked.connect(self.fit_to_data)
        zoom_toolbar.addWidget(fit_data_btn)
        
        reset_view_btn = QPushButton("Reset")
        reset_view_btn.setToolTip("Reset View")
        reset_view_btn.clicked.connect(self.reset_view)
        zoom_toolbar.addWidget(reset_view_btn)
        
        zoom_toolbar.addStretch()
        
        # Crosshair toggle
        self.crosshair_check = QCheckBox("Crosshair")
        self.crosshair_check.setChecked(True)
        self.crosshair_check.stateChanged.connect(self._on_crosshair_toggled)
        zoom_toolbar.addWidget(self.crosshair_check)
        
        layout.addLayout(zoom_toolbar)
        
        # Bot indicator controls
        bot_controls_group = QGroupBox("Bot Indicators")
        bot_controls_layout = QHBoxLayout()
        
        self.show_ohlc_bots_check = QCheckBox("Show OHLC Bots")
        self.show_ohlc_bots_check.setChecked(True)
        self.show_ohlc_bots_check.stateChanged.connect(self.refresh_chart)
        bot_controls_layout.addWidget(self.show_ohlc_bots_check)
        
        self.show_vwap_bots_check = QCheckBox("Show VWAP Bots")
        self.show_vwap_bots_check.setChecked(True)
        self.show_vwap_bots_check.stateChanged.connect(self.refresh_chart)
        bot_controls_layout.addWidget(self.show_vwap_bots_check)
        
        self.show_signals_check = QCheckBox("Show Signals")
        self.show_signals_check.setChecked(True)
        self.show_signals_check.stateChanged.connect(self.refresh_chart)
        bot_controls_layout.addWidget(self.show_signals_check)
        
        bot_controls_layout.addStretch()
        bot_controls_group.setLayout(bot_controls_layout)
        layout.addWidget(bot_controls_group)
        
        # General VWAP indicator controls
        vwap_controls_group = QGroupBox("VWAP Indicator")
        vwap_controls_layout = QVBoxLayout()
        
        # First row: Show VWAP checkbox and session type
        vwap_row1 = QHBoxLayout()
        self.show_vwap_check = QCheckBox("Show VWAP")
        self.show_vwap_check.setChecked(False)
        self.show_vwap_check.stateChanged.connect(self.refresh_chart)
        vwap_row1.addWidget(self.show_vwap_check)
        
        vwap_row1.addWidget(QLabel("Session:"))
        self.vwap_session_combo = QComboBox()
        self.vwap_session_combo.addItems(["NY", "London", "Asia", "All"])
        self.vwap_session_combo.setCurrentText("NY")
        self.vwap_session_combo.currentTextChanged.connect(self.refresh_chart)
        vwap_row1.addWidget(self.vwap_session_combo)
        
        vwap_row1.addStretch()
        vwap_controls_layout.addLayout(vwap_row1)
        
        # Second row: Show bands checkbox and STD levels
        vwap_row2 = QHBoxLayout()
        self.show_vwap_bands_check = QCheckBox("Show Bands")
        self.show_vwap_bands_check.setChecked(True)
        self.show_vwap_bands_check.stateChanged.connect(self.refresh_chart)
        vwap_row2.addWidget(self.show_vwap_bands_check)
        
        vwap_row2.addWidget(QLabel("STD Levels:"))
        self.vwap_std_levels_input = QLineEdit()
        self.vwap_std_levels_input.setText("1.0, 1.5, 2.0")
        self.vwap_std_levels_input.setPlaceholderText("1.0, 1.5, 2.0")
        self.vwap_std_levels_input.setMaximumWidth(150)
        self.vwap_std_levels_input.editingFinished.connect(self.refresh_chart)
        vwap_row2.addWidget(self.vwap_std_levels_input)
        
        vwap_row2.addStretch()
        vwap_controls_layout.addLayout(vwap_row2)
        
        vwap_controls_group.setLayout(vwap_controls_layout)
        layout.addWidget(vwap_controls_group)
        
        # Chart with proper axis configuration (TradingView-like)
        # Use DateAxisItem for X-axis (time) and right axis for price
        date_axis = DateAxisItem(orientation='bottom')
        right_axis = pg.AxisItem('right')
        
        # Improve axis styling
        date_axis.setPen(pg.mkPen(color='white', width=1))
        date_axis.setTextPen(pg.mkPen(color='white'))
        right_axis.setPen(pg.mkPen(color='white', width=1))
        right_axis.setTextPen(pg.mkPen(color='white'))
        
        self.chart = pg.PlotWidget(
            axisItems={'bottom': date_axis, 'right': right_axis}
        )
        self.chart.setLabel('right', 'Price', color='white')
        self.chart.setLabel('bottom', 'Time', color='white')
        
        # Add legend for indicator identification (TradingView-like)
        self.chart.addLegend(
            offset=(10, 10), 
            labelTextColor='white', 
            brush=pg.mkBrush(color=(30, 30, 30, 220)), 
            border=pg.mkPen(color='white', width=1),
            labelTextSize='9pt'
        )
        
        # Improve chart styling (TradingView-like)
        self.chart.setBackground('black')
        self.chart.showGrid(x=True, y=True, alpha=0.3)
        
        # Store plot items with metadata for tooltip detection
        self.plot_items_metadata = {}  # plot_item -> {'name': str, 'type': str, 'values': list, 'times': list}
        
        # Hide left axis (we're using right axis for price)
        self.chart.hideAxis('left')
        
        # Enable mouse tracking for crosshair and tooltips
        self.chart.setMouseTracking(True)
        self.chart.getViewBox().setMouseEnabled(x=True, y=True)  # Enable pan
        
        # Enable keyboard focus for shortcuts
        self.chart.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Connect mouse events for crosshair and tooltips
        self.chart.scene().sigMouseMoved.connect(self._on_mouse_moved)
        self.chart.scene().sigMouseClicked.connect(self._on_mouse_clicked)
        
        # Connect to viewbox signals for mouse leave
        self.chart.getViewBox().sigRangeChanged.connect(self._on_view_range_changed)
        
        layout.addWidget(self.chart)
        
        # Update symbol list
        self.update_symbol_list()
    
    def update_symbol_list(self):
        """Update symbol combo box with all available symbols"""
        self.symbol_combo.clear()
        
        # First, add symbols that are already in the data feed
        for symbol in self.data_feed.symbols:
            self.symbol_combo.addItem(symbol)
        
        # Also add all available symbols from MT5 if connector is available
        if self.mt5 and self.mt5.is_connected():
            try:
                available_symbols = self.mt5.get_available_symbols()
                for symbol in available_symbols:
                    # Only add if not already in the list
                    if self.symbol_combo.findText(symbol) == -1:
                        self.symbol_combo.addItem(symbol)
            except Exception as e:
                pass  # Silently fail if can't get symbols
        
        # Make combo box editable so user can type symbol names
        self.symbol_combo.setEditable(True)
        self.symbol_combo.lineEdit().setPlaceholderText("Select or type symbol")
        
        # Set current symbol if available
        if self.data_feed.symbols and not self.current_symbol:
            self.current_symbol = self.data_feed.symbols[0]
            self.symbol_combo.setCurrentText(self.current_symbol)
            self.refresh_chart()
        elif self.current_symbol:
            # Restore current selection
            index = self.symbol_combo.findText(self.current_symbol)
            if index >= 0:
                self.symbol_combo.setCurrentIndex(index)
    
    def _on_tick_received(self, symbol: str, tick_data: dict):
        """Handle tick received signal to update symbol list"""
        # Check if this symbol is new
        if self.symbol_combo.findText(symbol) == -1:
            self.symbol_combo.addItem(symbol)
    
    def _on_tick_for_candle_update(self, symbol: str, tick_data: dict):
        """Handle tick for real-time candle updates"""
        if symbol != self.current_symbol:
            return
        
        # Throttle updates
        current_time = datetime.now().timestamp() * 1000
        if current_time - self.last_update_time < self.update_throttle_ms:
            return
        
        self.last_update_time = current_time
        self.update_current_bar(tick_data)
    
    def on_symbol_changed(self, symbol: str):
        """Handle symbol change"""
        if symbol:
            symbol = symbol.strip()
            # Don't convert to uppercase - keep original case from MT5
            # Ensure symbol is added to data feed if not already
            if symbol not in self.data_feed.symbols:
                if self.mt5 and self.mt5.is_connected():
                    # Try to add symbol to data feed (case-insensitive matching)
                    added = self.data_feed.add_symbol(symbol)
                    if added:
                        # Get the correct symbol name (with proper case)
                        for feed_symbol in self.data_feed.symbols:
                            if feed_symbol.upper() == symbol.upper():
                                symbol = feed_symbol
                                break
            
            self.current_symbol = symbol
            # Update combo box to show correct case
            index = self.symbol_combo.findText(symbol)
            if index >= 0:
                self.symbol_combo.setCurrentIndex(index)
            self.refresh_chart()
    
    def on_timeframe_changed(self, timeframe: str):
        """Handle timeframe change"""
        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }
        self.current_timeframe = timeframe_map.get(timeframe, mt5.TIMEFRAME_H1)
        self.refresh_chart()
    
    def refresh_chart(self):
        """Refresh the chart"""
        # #region agent log
        import json
        try:
            with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'sessionId': 'debug-session',
                    'runId': 'run1',
                    'hypothesisId': 'A',
                    'location': 'chart_widget.py:524',
                    'message': 'refresh_chart entry',
                    'data': {'current_symbol': self.current_symbol},
                    'timestamp': int(datetime.now().timestamp() * 1000)
                }) + '\n')
        except: pass
        # #endregion
        
        if not self.current_symbol:
            self.chart.setTitle("No symbol selected")
            return
        
        # Resolve correct symbol name (case-insensitive, handle variations)
        resolved_symbol = self._resolve_symbol_name(self.current_symbol)
        
        # #region agent log
        try:
            with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'sessionId': 'debug-session',
                    'runId': 'run1',
                    'hypothesisId': 'A',
                    'location': 'chart_widget.py:531',
                    'message': 'symbol resolution result',
                    'data': {'current_symbol': self.current_symbol, 'resolved_symbol': resolved_symbol},
                    'timestamp': int(datetime.now().timestamp() * 1000)
                }) + '\n')
        except: pass
        # #endregion
        
        if not resolved_symbol:
            self.chart.setTitle(f"{self.current_symbol} - Symbol not available")
            return
        
        # Ensure symbol is in data feed
        if resolved_symbol not in self.data_feed.symbols:
            if self.mt5 and self.mt5.is_connected():
                add_result = self.data_feed.add_symbol(resolved_symbol)
                # #region agent log
                try:
                    with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({
                            'sessionId': 'debug-session',
                            'runId': 'run1',
                            'hypothesisId': 'B',
                            'location': 'chart_widget.py:537',
                            'message': 'data feed add_symbol result',
                            'data': {'resolved_symbol': resolved_symbol, 'add_result': add_result, 'in_feed': resolved_symbol in self.data_feed.symbols},
                            'timestamp': int(datetime.now().timestamp() * 1000)
                        }) + '\n')
                except: pass
                # #endregion
                if not add_result:
                    self.chart.setTitle(f"{resolved_symbol} - Symbol not available")
                    return
        
        # Ensure symbol is selected in MT5
        if self.mt5 and self.mt5.is_connected():
            import MetaTrader5 as mt5
            select_result = mt5.symbol_select(resolved_symbol, True)
            # #region agent log
            try:
                with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        'sessionId': 'debug-session',
                        'runId': 'run1',
                        'hypothesisId': 'C',
                        'location': 'chart_widget.py:546',
                        'message': 'MT5 symbol_select result',
                        'data': {'resolved_symbol': resolved_symbol, 'select_result': select_result},
                        'timestamp': int(datetime.now().timestamp() * 1000)
                    }) + '\n')
            except: pass
            # #endregion
        
        # Clear chart
        self.chart.clear()
        
        # Reset crosshair items (will be recreated on mouse move)
        self.crosshair_vline = None
        self.crosshair_hline = None
        self.crosshair_price_label = None
        self.crosshair_time_label = None
        self.current_bar_item = None
        
        # Get rates with resolved symbol
        rates = self.data_feed.get_rates(resolved_symbol, self.current_timeframe, 200)
        
        # #region agent log
        try:
            with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    'sessionId': 'debug-session',
                    'runId': 'run1',
                    'hypothesisId': 'D',
                    'location': 'chart_widget.py:559',
                    'message': 'data feed get_rates result',
                    'data': {'resolved_symbol': resolved_symbol, 'rates_count': len(rates) if rates else 0, 'timeframe': self.current_timeframe},
                    'timestamp': int(datetime.now().timestamp() * 1000)
                }) + '\n')
        except: pass
        # #endregion
        
        # If data feed doesn't have rates, try getting them directly from MT5
        if not rates and self.mt5 and self.mt5.is_connected():
            rates = self.mt5.get_rates(resolved_symbol, self.current_timeframe, 200)
            # #region agent log
            try:
                with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        'sessionId': 'debug-session',
                        'runId': 'run1',
                        'hypothesisId': 'D',
                        'location': 'chart_widget.py:563',
                        'message': 'MT5 fallback get_rates result',
                        'data': {'resolved_symbol': resolved_symbol, 'rates_count': len(rates) if rates else 0},
                        'timestamp': int(datetime.now().timestamp() * 1000)
                    }) + '\n')
            except: pass
            # #endregion
        
        if not rates or len(rates) == 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Chart refresh: no rates for {resolved_symbol} ({self.timeframe_combo.currentText()})")
            self.chart.setTitle(f"{resolved_symbol} - No data available")
            return
        
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Chart refresh: {resolved_symbol} {self.timeframe_combo.currentText()} rates={len(rates)}")

            # Extract + validate + sort data by time (defensive: MT5/data feed order can vary)
            def _safe_to_datetime(value):
                if isinstance(value, datetime):
                    return value
                if isinstance(value, (int, float)):
                    try:
                        # MT5 timestamps are seconds. If milliseconds slip in, normalize.
                        ts = float(value)
                        if ts > 10_000_000_000:  # ~year 2286 in seconds, so likely ms
                            ts = ts / 1000.0
                        return datetime.fromtimestamp(ts)
                    except Exception:
                        return None
                try:
                    return datetime.fromisoformat(str(value))
                except Exception:
                    try:
                        ts = float(value)
                        if ts > 10_000_000_000:
                            ts = ts / 1000.0
                        return datetime.fromtimestamp(ts)
                    except Exception:
                        return None

            rows = []
            for r in rates:
                t = _safe_to_datetime(r.get('time'))
                if not t:
                    continue
                try:
                    o = float(r.get('open'))
                    h = float(r.get('high'))
                    l = float(r.get('low'))
                    c = float(r.get('close'))
                except Exception:
                    continue
                # Basic sanity: skip obviously invalid bars
                if not all(np.isfinite(x) for x in [o, h, l, c]):
                    continue
                rows.append((t, o, h, l, c, r))

            rows.sort(key=lambda x: x[0])

            times = [x[0] for x in rows]
            opens = [x[1] for x in rows]
            highs = [x[2] for x in rows]
            lows = [x[3] for x in rows]
            closes = [x[4] for x in rows]
            sorted_rates = [x[5] for x in rows]
            
            # #region agent log
            try:
                with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        'sessionId': 'debug-session',
                        'runId': 'run1',
                        'hypothesisId': 'E',
                        'location': 'chart_widget.py:618',
                        'message': 'data validation result',
                        'data': {'resolved_symbol': resolved_symbol, 'original_rates_count': len(rates), 'valid_rows_count': len(rows), 'times_count': len(times), 'closes_count': len(closes)},
                        'timestamp': int(datetime.now().timestamp() * 1000)
                    }) + '\n')
            except: pass
            # #endregion
            
            if not times or not closes:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"No valid data extracted. Times: {len(times)}, Closes: {len(closes)}")
                self.chart.setTitle(f"{resolved_symbol} - Invalid data")
                return
            
            # Prepare candlestick data (datetime -> converted to timestamp inside CandlestickItem)
            candlestick_data = list(zip(times, opens, highs, lows, closes))
            
            # Log candlestick creation
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Creating candlesticks for {resolved_symbol}: {len(candlestick_data)} candles")
            
            # Create and add candlestick item for completed bars
            try:
                # #region agent log
                try:
                    with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({
                            'sessionId': 'debug-session',
                            'runId': 'run1',
                            'hypothesisId': 'F',
                            'location': 'chart_widget.py:644',
                            'message': 'before candlestick creation',
                            'data': {'resolved_symbol': resolved_symbol, 'candlestick_data_count': len(candlestick_data)},
                            'timestamp': int(datetime.now().timestamp() * 1000)
                        }) + '\n')
                except: pass
                # #endregion
                self.candlestick_item = CandlestickItem(candlestick_data)
                # #region agent log
                try:
                    import json
                    br = self.candlestick_item.boundingRect()
                    with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({
                            'sessionId': 'debug-session',
                            'runId': 'run1',
                            'hypothesisId': 'F',
                            'location': 'chart_widget.py:763',
                            'message': 'candlestick item created',
                            'data': {'resolved_symbol': resolved_symbol, 'data_count': len(self.candlestick_item.data), 'boundingRect': {'x': br.x(), 'y': br.y(), 'width': br.width(), 'height': br.height()}},
                            'timestamp': int(datetime.now().timestamp() * 1000)
                        }) + '\n')
                except Exception as e:
                    try:
                        with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                            f.write(json.dumps({
                                'sessionId': 'debug-session',
                                'runId': 'run1',
                                'hypothesisId': 'F',
                                'location': 'chart_widget.py:763',
                                'message': 'candlestick item created (boundingRect error)',
                                'data': {'resolved_symbol': resolved_symbol, 'error': str(e)},
                                'timestamp': int(datetime.now().timestamp() * 1000)
                            }) + '\n')
                    except: pass
                # #endregion
                self.chart.addItem(self.candlestick_item)
                # #region agent log
                try:
                    with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({
                            'sessionId': 'debug-session',
                            'runId': 'run1',
                            'hypothesisId': 'F',
                            'location': 'chart_widget.py:764',
                            'message': 'after addItem',
                            'data': {'resolved_symbol': resolved_symbol, 'chart_items_count': len(self.chart.listDataItems()), 'all_items_count': len(self.chart.items) if hasattr(self.chart, 'items') else 'N/A'},
                            'timestamp': int(datetime.now().timestamp() * 1000)
                        }) + '\n')
                except: pass
                # #endregion
                logger.debug(f"Added candlestick item to chart. Chart items count: {len(self.chart.listDataItems())}")
            except Exception as e:
                # #region agent log
                try:
                    with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({
                            'sessionId': 'debug-session',
                            'runId': 'run1',
                            'hypothesisId': 'F',
                            'location': 'chart_widget.py:648',
                            'message': 'candlestick creation error',
                            'data': {'resolved_symbol': resolved_symbol, 'error': str(e), 'error_type': type(e).__name__},
                            'timestamp': int(datetime.now().timestamp() * 1000)
                        }) + '\n')
                except: pass
                # #endregion
                logger.error(f"Error creating/adding candlestick item: {e}", exc_info=True)
                raise
            
            # Store times as timestamps for bot indicators
            self.chart_times = times
            self.chart_rates = sorted_rates
            
            # Initialize current bar tracking
            self._initialize_current_bar(sorted_rates[-1] if sorted_rates else None)
            
            # Set title with data info
            self.chart.setTitle(f"{resolved_symbol} - {self.timeframe_combo.currentText()} ({len(sorted_rates)} bars)")
            
            # Update bot indicators
            self.update_bot_indicators(times, sorted_rates)
            
            # Update general VWAP indicator
            self.update_general_vwap(times, sorted_rates)
            
            # Enable auto-range to fit data (including candlestick)
            if self.candlestick_item:
                br = self.candlestick_item.boundingRect()
                if not br.isNull() and not br.isEmpty():
                    # Set view range to include candlestick data
                    self.chart.setXRange(br.left(), br.right(), padding=0.1)
                    self.chart.setYRange(br.top(), br.bottom(), padding=0.1)
                else:
                    # Fallback to auto-range
                    self.chart.enableAutoRange()
            else:
                self.chart.enableAutoRange()
            
            # Force chart update
            self.chart.update()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            error_symbol = resolved_symbol if 'resolved_symbol' in locals() else self.current_symbol
            # #region agent log
            try:
                import json
                with open(r'c:\mc_meta\.cursor\debug.log', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        'sessionId': 'debug-session',
                        'runId': 'run1',
                        'hypothesisId': 'ALL',
                        'location': 'chart_widget.py:820',
                        'message': 'refresh_chart exception',
                        'data': {'error_symbol': error_symbol, 'current_symbol': self.current_symbol, 'error': str(e), 'error_type': type(e).__name__},
                        'timestamp': int(datetime.now().timestamp() * 1000)
                    }) + '\n')
            except: pass
            # #endregion
            logger.error(f"Error plotting chart for {error_symbol}: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.chart.setTitle(f"{error_symbol} - Error: {str(e)}")
    
    def update_tick(self, symbol: str, tick_data: Dict):
        """Update chart with new tick (optional real-time update)"""
        if symbol == self.current_symbol:
            # Could implement real-time tick update here
            pass
    
    def _resolve_symbol_name(self, symbol: str) -> Optional[str]:
        """
        Resolve the correct symbol name using multiple methods
        
        Returns:
            Resolved symbol name or None if not found
        """
        if not symbol:
            return None
        
        # First, try case-insensitive match in data_feed
        symbol_upper = symbol.upper()
        for feed_symbol in self.data_feed.symbols:
            if feed_symbol.upper() == symbol_upper:
                return feed_symbol
        
        # Try to get symbol info from MT5 (this returns correct case)
        if self.mt5 and self.mt5.is_connected():
            symbol_info = self.mt5.get_symbol_info(symbol)
            if symbol_info:
                return symbol_info['name']
            
            # Try SymbolMapper as fallback
            from ..utils.symbol_mapper import SymbolMapper
            symbol_mapper = SymbolMapper(self.mt5)
            mapped_symbol = symbol_mapper.find_symbol(symbol)
            if mapped_symbol:
                return mapped_symbol
        
        # Return original if nothing found (will fail later, but at least we tried)
        return symbol
    
    def add_indicator(self, indicator_name: str, values: List[float], color: str = 'y'):
        """Add an indicator to the chart"""
        if not self.current_symbol:
            return
        
        rates = self.data_feed.get_rates(self.current_symbol, self.current_timeframe, 200)
        if not rates or len(rates) != len(values):
            return
        
        times = [r['time'].timestamp() for r in rates]
        
        # Filter out None values
        valid_times = []
        valid_values = []
        for t, v in zip(times, values):
            if v is not None:
                valid_times.append(t)
                valid_values.append(v)
        
        if valid_times:
            self.chart.plot(
                valid_times, 
                valid_values, 
                pen=pg.mkPen(color=color, width=1.5), 
                name=indicator_name,
                antialias=True
            )
    
    def update_bot_indicators(self, times: List[datetime], rates: List[Dict]):
        """Update trading bot indicators on the chart"""
        if not self.strategy_manager or not self.current_symbol:
            return
        
        # Clear existing bot indicators
        for item in self.bot_indicator_items:
            try:
                self.chart.removeItem(item)
            except:
                pass
        self.bot_indicator_items.clear()
        
        # Get all enabled strategies
        enabled_strategies = self.strategy_manager.get_enabled_strategies()
        
        # Filter strategies matching current symbol (case-insensitive)
        matching_strategies = []
        for strategy in enabled_strategies:
            if strategy.symbol.upper() == self.current_symbol.upper():
                matching_strategies.append(strategy)
        
        if not matching_strategies:
            return
        
        # Get time range for indicators (convert to timestamps for plotting)
        if not times:
            return
        
        # Convert datetime to timestamps for plotting
        time_min_ts = times[0].timestamp() if isinstance(times[0], datetime) else times[0]
        time_max_ts = times[-1].timestamp() if isinstance(times[-1], datetime) else times[-1]
        
        # Display indicators for each matching strategy
        for strategy in matching_strategies:
            strategy_name = strategy.name
            
            # OHLC Bot Indicators
            if hasattr(strategy, 'get_ohlc_data') and self.show_ohlc_bots_check.isChecked():
                ohlc_data = strategy.get_ohlc_data()
                
                # If strategy doesn't have OHLC data, try to get it from market_data_panel
                if not ohlc_data and self.market_data_panel:
                    symbol_upper = self.current_symbol.upper()
                    for symbol_key in self.market_data_panel.ohlc_data.keys():
                        if symbol_key.upper() == symbol_upper:
                            ohlc_data = self.market_data_panel.ohlc_data[symbol_key]
                            break
                
                if ohlc_data:
                    # Draw OHLC levels as horizontal lines
                    open_price = ohlc_data.get('open')
                    high_price = ohlc_data.get('high')
                    low_price = ohlc_data.get('low')
                    close_price = ohlc_data.get('close')
                    
                    if open_price:
                        line = self.chart.plot(
                            [time_min_ts, time_max_ts],
                            [open_price, open_price],
                            pen=pg.mkPen(color='b', width=1, style=Qt.PenStyle.DashLine),
                            name=f"{strategy_name} - Open"
                        )
                        self.bot_indicator_items.append(line)
                    
                    if high_price:
                        line = self.chart.plot(
                            [time_min_ts, time_max_ts],
                            [high_price, high_price],
                            pen=pg.mkPen(color='g', width=1, style=Qt.PenStyle.DashLine),
                            name=f"{strategy_name} - High"
                        )
                        self.bot_indicator_items.append(line)
                    
                    if low_price:
                        line = self.chart.plot(
                            [time_min_ts, time_max_ts],
                            [low_price, low_price],
                            pen=pg.mkPen(color='r', width=1, style=Qt.PenStyle.DashLine),
                            name=f"{strategy_name} - Low"
                        )
                        self.bot_indicator_items.append(line)
                    
                    if close_price:
                        line = self.chart.plot(
                            [time_min_ts, time_max_ts],
                            [close_price, close_price],
                            pen=pg.mkPen(color='y', width=1, style=Qt.PenStyle.DashLine),
                            name=f"{strategy_name} - Close"
                        )
                        self.bot_indicator_items.append(line)
            
            # VWAP Bot Indicators (from strategies)
            if hasattr(strategy, 'vwap_indicator') and strategy.vwap_indicator and self.show_vwap_bots_check.isChecked():
                vwap_indicator = strategy.vwap_indicator
                vwap_value = vwap_indicator.get_vwap()
                
                if vwap_value:
                    # Draw VWAP line with improved styling
                    line = self.chart.plot(
                        [time_min_ts, time_max_ts],
                        [vwap_value, vwap_value],
                        pen=pg.mkPen(color='#00CED1', width=2.5),  # Dark turquoise, thicker
                        name=f"{strategy_name} - VWAP",
                        antialias=True
                    )
                    self.bot_indicator_items.append(line)
                    
                    # Draw standard deviation bands with improved colors
                    if hasattr(strategy, 'std_bands'):
                        # Color scheme for strategy VWAP bands (slightly different from general VWAP)
                        upper_colors = {
                            1.0: '#FF8A80',   # Light red
                            1.5: '#FF5252',   # Medium red
                            2.0: '#D32F2F',   # Dark red
                        }
                        lower_colors = {
                            1.0: '#81C784',   # Light green
                            1.5: '#66BB6A',   # Medium green
                            2.0: '#388E3C',   # Dark green
                        }
                        
                        for std_dev in strategy.std_bands:
                            upper, lower = vwap_indicator.get_bands(std_dev)
                            if upper and lower:
                                # Get color for this STD level
                                upper_color = upper_colors.get(std_dev, '#FF8A80')
                                lower_color = lower_colors.get(std_dev, '#81C784')
                                
                                # Upper band
                                upper_line = self.chart.plot(
                                    [time_min_ts, time_max_ts],
                                    [upper, upper],
                                    pen=pg.mkPen(color=upper_color, width=1.5, style=Qt.PenStyle.DashLine),
                                    name=f"{strategy_name} - Upper {std_dev}STD",
                                    antialias=True
                                )
                                self.bot_indicator_items.append(upper_line)
                                
                                # Lower band
                                lower_line = self.chart.plot(
                                    [time_min_ts, time_max_ts],
                                    [lower, lower],
                                    pen=pg.mkPen(color=lower_color, width=1.5, style=Qt.PenStyle.DashLine),
                                    name=f"{strategy_name} - Lower {std_dev}STD",
                                    antialias=True
                                )
                                self.bot_indicator_items.append(lower_line)
            
            # Signal Markers
            if self.show_signals_check.isChecked() and hasattr(strategy, 'signal_history'):
                signal_history = strategy.signal_history
                if signal_history:
                    # Get signal times and prices from history
                    signal_times = []
                    signal_prices = []
                    signal_types = []
                    
                    for signal_data in signal_history:
                        signal_time = signal_data.get('time')
                        signal = signal_data.get('signal')
                        tick_data = signal_data.get('data', {}).get('tick', {})
                        
                        if signal_time and signal in ['BUY', 'SELL']:
                            # Convert time to datetime if needed
                            if isinstance(signal_time, datetime):
                                signal_times.append(signal_time)
                            elif isinstance(signal_time, (int, float)):
                                signal_times.append(datetime.fromtimestamp(signal_time))
                            
                            # Get price from tick data or rates
                            price = None
                            if tick_data:
                                price = (tick_data.get('bid', 0) + tick_data.get('ask', 0)) / 2.0
                            
                            # If no price from tick, find closest rate
                            if not price or price == 0:
                                # Find closest rate by time
                                for rate in rates:
                                    rate_time = rate['time']
                                    if isinstance(rate_time, datetime):
                                        rt = rate_time
                                    elif isinstance(rate_time, (int, float)):
                                        rt = datetime.fromtimestamp(rate_time)
                                    else:
                                        continue
                                    
                                    if isinstance(signal_times[-1], datetime):
                                        if abs((rt - signal_times[-1]).total_seconds()) < 3600:  # Within 1 hour
                                            price = rate['close']
                                            break
                            
                            if price and price > 0:
                                signal_prices.append(price)
                                signal_types.append(signal)
                    
                    # Plot BUY signals (green up arrows)
                    buy_times = [t for t, s in zip(signal_times, signal_types) if s == 'BUY']
                    buy_prices = [p for p, s in zip(signal_prices, signal_types) if s == 'BUY']
                    
                    if buy_times and buy_prices:
                        # Convert times to timestamps
                        buy_times_ts = []
                        for t in buy_times:
                            if isinstance(t, datetime):
                                buy_times_ts.append(t.timestamp())
                            else:
                                buy_times_ts.append(float(t))
                        
                        # Use scatter plot with arrow symbols
                        buy_scatter = pg.ScatterPlotItem(
                            x=buy_times_ts,
                            y=buy_prices,
                            pen=pg.mkPen(color='g', width=2),
                            brush=pg.mkBrush(color='g'),
                            symbol='t',  # Triangle up
                            size=15,
                            name=f"{strategy_name} - BUY Signals"
                        )
                        self.chart.addItem(buy_scatter)
                        self.bot_indicator_items.append(buy_scatter)
                    
                    # Plot SELL signals (red down arrows)
                    sell_times = [t for t, s in zip(signal_times, signal_types) if s == 'SELL']
                    sell_prices = [p for p, s in zip(signal_prices, signal_types) if s == 'SELL']
                    
                    if sell_times and sell_prices:
                        # Convert times to timestamps
                        sell_times_ts = []
                        for t in sell_times:
                            if isinstance(t, datetime):
                                sell_times_ts.append(t.timestamp())
                            else:
                                sell_times_ts.append(float(t))
                        
                        sell_scatter = pg.ScatterPlotItem(
                            x=sell_times_ts,
                            y=sell_prices,
                            pen=pg.mkPen(color='r', width=2),
                            brush=pg.mkBrush(color='r'),
                            symbol='t3',  # Triangle down
                            size=15,
                            name=f"{strategy_name} - SELL Signals"
                        )
                        self.chart.addItem(sell_scatter)
                        self.bot_indicator_items.append(sell_scatter)
    
    def _calculate_vwap_for_chart(self, rates: List[Dict], session_type: str) -> Tuple[List[float], Dict[float, Tuple[List[float], List[float]]]]:
        """
        Calculate VWAP values and dynamic bands for chart data
        
        Args:
            rates: List of rate dictionaries with OHLCV data
            session_type: Session type ('NY', 'London', 'Asia', 'All')
            
        Returns:
            Tuple of (vwap_values, bands_dict) where:
            - vwap_values: List of VWAP values aligned with rates
            - bands_dict: Dictionary mapping std_dev to (upper_bands_list, lower_bands_list)
        """
        if not rates:
            return [], {}
        
        try:
            # Initialize VWAP indicator
            vwap_indicator = VWAP(session_type=session_type, use_typical_price=True)
            
            # Convert rates to candle format for VWAP calculation
            candles = []
            for rate in rates:
                candle = {
                    'time': rate['time'],
                    'open': rate['open'],
                    'high': rate['high'],
                    'low': rate['low'],
                    'close': rate['close'],
                    'tick_volume': rate.get('tick_volume', rate.get('volume', 1.0)),
                    'volume': rate.get('tick_volume', rate.get('volume', 1.0))
                }
                candles.append(candle)
            
            # Get STD levels from input
            std_levels_str = self.vwap_std_levels_input.text().strip()
            try:
                std_levels = [float(x.strip()) for x in std_levels_str.split(',') if x.strip()]
            except:
                std_levels = [1.0, 1.5, 2.0]  # Default
            
            # Calculate VWAP and bands incrementally for each candle
            vwap_values = []
            bands_dict = {std_dev: ([], []) for std_dev in std_levels}  # Initialize with empty lists
            
            # Process each candle incrementally to get dynamic bands
            for candle in candles:
                # Process this candle through VWAP calculation
                candle_time = candle.get('time')
                if isinstance(candle_time, (int, float)):
                    candle_time = datetime.fromtimestamp(candle_time)
                elif not isinstance(candle_time, datetime):
                    try:
                        candle_time = datetime.fromisoformat(str(candle_time))
                    except:
                        vwap_values.append(None)
                        for std_dev in std_levels:
                            bands_dict[std_dev][0].append(None)
                            bands_dict[std_dev][1].append(None)
                        continue
                
                # Initialize session start time if not set
                if vwap_indicator.session_start_time is None:
                    session_start = vwap_indicator._get_session_start_time(candle_time)
                    vwap_indicator._reset_session(session_start)
                
                # Check if session should reset
                if vwap_indicator._should_reset_session(candle_time):
                    session_start = vwap_indicator._get_session_start_time(candle_time)
                    vwap_indicator._reset_session(session_start)
                
                # Get price and volume
                price = vwap_indicator._get_price(candle)
                volume = float(candle.get('tick_volume', candle.get('volume', 1.0)))
                
                if volume <= 0:
                    # Use previous VWAP if volume is 0
                    vwap_values.append(vwap_indicator.current_vwap if vwap_indicator.current_vwap else None)
                    for std_dev in std_levels:
                        if vwap_indicator.current_vwap:
                            # Try to get bands with current state
                            upper, lower = vwap_indicator.get_bands(std_dev)
                            bands_dict[std_dev][0].append(upper)
                            bands_dict[std_dev][1].append(lower)
                        else:
                            bands_dict[std_dev][0].append(None)
                            bands_dict[std_dev][1].append(None)
                    continue
                
                # Update cumulative values
                vwap_indicator.cumulative_price_volume += price * volume
                vwap_indicator.cumulative_volume += volume
                
                # Calculate VWAP
                if vwap_indicator.cumulative_volume > 0:
                    vwap = vwap_indicator.cumulative_price_volume / vwap_indicator.cumulative_volume
                    vwap_indicator.current_vwap = vwap
                    vwap_values.append(vwap)
                    
                    # Store price and volume for STD calculation
                    vwap_indicator.prices.append(price)
                    vwap_indicator.volumes.append(volume)
                    
                    # Clear STD cache to force recalculation
                    vwap_indicator.std_cache.clear()
                    
                    # Calculate bands for current point using accumulated data
                    for std_dev in std_levels:
                        upper, lower = vwap_indicator.get_bands(std_dev)
                        if upper is not None and lower is not None:
                            bands_dict[std_dev][0].append(upper)  # Upper band
                            bands_dict[std_dev][1].append(lower)  # Lower band
                        else:
                            bands_dict[std_dev][0].append(None)
                            bands_dict[std_dev][1].append(None)
                else:
                    vwap_values.append(None)
                    for std_dev in std_levels:
                        bands_dict[std_dev][0].append(None)
                        bands_dict[std_dev][1].append(None)
            
            return vwap_values, bands_dict
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating VWAP for chart: {e}", exc_info=True)
            return [], {}
    
    def update_general_vwap(self, times: List[datetime], rates: List[Dict]):
        """Update general VWAP indicator on chart"""
        # Clear existing general VWAP items and their metadata
        for item in self.general_vwap_items:
            try:
                self.chart.removeItem(item)
                # Remove from metadata
                if hasattr(self, 'plot_items_metadata') and item in self.plot_items_metadata:
                    del self.plot_items_metadata[item]
            except:
                pass
        self.general_vwap_items.clear()
        
        # Check if VWAP should be shown
        if not self.show_vwap_check.isChecked() or not self.current_symbol or not rates:
            return
        
        try:
            # Get session type
            session_type = self.vwap_session_combo.currentText()
            
            # Calculate VWAP
            vwap_values, bands_dict = self._calculate_vwap_for_chart(rates, session_type)
            
            if not vwap_values:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"VWAP calculation returned no values. Rates count: {len(rates) if rates else 0}")
                return
            
            # Ensure times and vwap_values are aligned
            if len(times) != len(vwap_values):
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Times and VWAP values length mismatch: times={len(times)}, vwap_values={len(vwap_values)}. Using min length.")
                # Use the minimum length to avoid index errors
                min_len = min(len(times), len(vwap_values))
                times = times[:min_len]
                vwap_values = vwap_values[:min_len]
            
            # Convert times to timestamps
            times_ts = []
            for t in times:
                if isinstance(t, datetime):
                    times_ts.append(t.timestamp())
                else:
                    times_ts.append(float(t))
            
            # Filter out None values and align with times
            # Ensure times_ts and vwap_values have the same length
            min_len = min(len(times_ts), len(vwap_values))
            valid_times = []
            valid_vwap = []
            for i in range(min_len):
                t = times_ts[i]
                v = vwap_values[i]
                if v is not None:
                    valid_times.append(t)
                    valid_vwap.append(v)
            
            if not valid_times:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"No valid VWAP values to plot. Times: {len(times_ts)}, VWAP values: {len(vwap_values)}")
                return
            
            # Plot VWAP line with improved styling (TradingView-like)
            vwap_line = self.chart.plot(
                valid_times,
                valid_vwap,
                pen=pg.mkPen(color='#00FFFF', width=2.5),  # Bright cyan, thicker
                name="VWAP",
                antialias=True
            )
            self.general_vwap_items.append(vwap_line)
            # Store metadata for tooltip detection
            self.plot_items_metadata[vwap_line] = {
                'name': 'VWAP',
                'type': 'vwap',
                'values': valid_vwap,
                'times': valid_times
            }
            
            # Plot bands if enabled (dynamic bands that follow VWAP)
            if self.show_vwap_bands_check.isChecked() and bands_dict:
                # Color scheme: Different shades for different STD levels
                # Upper bands: Red/Pink shades (darker for higher STD)
                # Lower bands: Green shades (darker for higher STD)
                upper_colors = {
                    1.0: '#FF6B6B',   # Light red
                    1.5: '#FF5252',   # Medium red
                    2.0: '#F44336',   # Dark red
                }
                lower_colors = {
                    1.0: '#66BB6A',   # Light green
                    1.5: '#4CAF50',   # Medium green
                    2.0: '#388E3C',   # Dark green
                }
                
                for std_dev, (upper_bands, lower_bands) in sorted(bands_dict.items()):
                    # Filter and align band values with valid VWAP times
                    valid_upper = []
                    valid_lower = []
                    valid_band_times = []
                    
                    # Ensure we have matching lengths
                    min_len = min(len(times_ts), len(vwap_values), len(upper_bands), len(lower_bands))
                    for i in range(min_len):
                        t = times_ts[i]
                        v = vwap_values[i]
                        u = upper_bands[i] if i < len(upper_bands) else None
                        l = lower_bands[i] if i < len(lower_bands) else None
                        
                        if v is not None and u is not None and l is not None:
                            valid_band_times.append(t)
                            valid_upper.append(u)
                            valid_lower.append(l)
                    
                    if not valid_band_times:
                        continue
                    
                    # Calculate price range for label offset (use band values for context)
                    if valid_upper and valid_lower:
                        price_range = max(max(valid_upper), max(valid_lower)) - min(min(valid_upper), min(valid_lower))
                        # Use a percentage of price range for label offset (1-2% of range)
                        label_offset = max(price_range * 0.015, 1.0)  # At least 1.0, or 1.5% of range
                    elif valid_upper:
                        price_range = max(valid_upper) - min(valid_upper)
                        label_offset = max(price_range * 0.015, 1.0)
                    elif valid_lower:
                        price_range = max(valid_lower) - min(valid_lower)
                        label_offset = max(price_range * 0.015, 1.0)
                    else:
                        label_offset = 1.0  # Fallback fixed offset
                    
                    # Get colors
                    upper_color = upper_colors.get(std_dev, '#FF6B6B')
                    lower_color = lower_colors.get(std_dev, '#66BB6A')
                    
                    # Plot upper band as dynamic line
                    upper_line = self.chart.plot(
                        valid_band_times,
                        valid_upper,
                        pen=pg.mkPen(color=upper_color, width=1.5, style=Qt.PenStyle.DashLine),
                        name=f"VWAP Upper {std_dev}STD",
                        antialias=True
                    )
                    self.general_vwap_items.append(upper_line)
                    # Store metadata
                    self.plot_items_metadata[upper_line] = {
                        'name': f'VWAP Upper {std_dev}STD',
                        'type': 'band_upper',
                        'values': valid_upper,
                        'times': valid_band_times,
                        'std_dev': std_dev
                    }
                    
                    # Add text label for upper band at the rightmost point
                    if valid_band_times and valid_upper:
                        last_time = valid_band_times[-1]
                        last_upper = valid_upper[-1]
                        
                        upper_label = pg.TextItem(
                            text=f"Upper ({std_dev} STD)",
                            color=upper_color,  # Match band color
                            anchor=(1, 0)  # Anchor to right, top
                        )
                        # Position slightly above the line
                        upper_label.setPos(last_time, last_upper + label_offset)
                        self.chart.addItem(upper_label)
                        self.general_vwap_items.append(upper_label)
                    
                    # Plot lower band as dynamic line
                    lower_line = self.chart.plot(
                        valid_band_times,
                        valid_lower,
                        pen=pg.mkPen(color=lower_color, width=1.5, style=Qt.PenStyle.DashLine),
                        name=f"VWAP Lower {std_dev}STD",
                        antialias=True
                    )
                    self.general_vwap_items.append(lower_line)
                    # Store metadata
                    self.plot_items_metadata[lower_line] = {
                        'name': f'VWAP Lower {std_dev}STD',
                        'type': 'band_lower',
                        'values': valid_lower,
                        'times': valid_band_times,
                        'std_dev': std_dev
                    }
                    
                    # Add text label for lower band at the rightmost point
                    if valid_band_times and valid_lower:
                        last_time = valid_band_times[-1]
                        last_lower = valid_lower[-1]
                        
                        lower_label = pg.TextItem(
                            text=f"Lower ({std_dev} STD)",
                            color=lower_color,  # Match band color
                            anchor=(1, 1)  # Anchor to right, bottom
                        )
                        # Position slightly below the line
                        lower_label.setPos(last_time, last_lower - label_offset)
                        self.chart.addItem(lower_label)
                        self.general_vwap_items.append(lower_label)
                    
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating general VWAP: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    # ========== Phase 1: Real-Time Candle Formation ==========

    def _get_timeframe_duration(self, timeframe: int) -> timedelta:
        """Return the bar duration for a given MT5 timeframe."""
        timeframe_durations = {
            mt5.TIMEFRAME_M1: timedelta(minutes=1),
            mt5.TIMEFRAME_M5: timedelta(minutes=5),
            mt5.TIMEFRAME_M15: timedelta(minutes=15),
            mt5.TIMEFRAME_M30: timedelta(minutes=30),
            mt5.TIMEFRAME_H1: timedelta(hours=1),
            mt5.TIMEFRAME_H4: timedelta(hours=4),
            mt5.TIMEFRAME_D1: timedelta(days=1),
        }
        return timeframe_durations.get(timeframe, timedelta(hours=1))
        
    def _get_bar_start_time(self, t: datetime, timeframe: int) -> datetime:
        """
        Normalize a datetime to the start of its bar for the given timeframe.
        This avoids invalid `minute` values (e.g., 60) and handles rollover safely.
        """
        if timeframe == mt5.TIMEFRAME_D1:
            return t.replace(hour=0, minute=0, second=0, microsecond=0)

        if timeframe == mt5.TIMEFRAME_H4:
            hour = (t.hour // 4) * 4
            return t.replace(hour=hour, minute=0, second=0, microsecond=0)

        if timeframe == mt5.TIMEFRAME_H1:
            return t.replace(minute=0, second=0, microsecond=0)

        duration = self._get_timeframe_duration(timeframe)
        minutes = max(1, int(duration.total_seconds() // 60))
        t0 = t.replace(second=0, microsecond=0)
        rounded_minute = (t0.minute // minutes) * minutes
        return t0.replace(minute=rounded_minute)
    
    def _is_new_bar(self, tick_time: datetime, timeframe: int) -> bool:
        """Check if tick time indicates a new bar should start"""
        if not self.current_bar:
            return True
        
        current_bar_time = self.current_bar['time']

        current_bar_start = self._get_bar_start_time(current_bar_time, timeframe)
        tick_bar_start = self._get_bar_start_time(tick_time, timeframe)
        return tick_bar_start > current_bar_start
    
    def _initialize_current_bar(self, last_rate: Optional[Dict]):
        """Initialize current bar tracking from last completed bar"""
        if not last_rate:
            return
        
        # Get the last bar's time and close price
        last_time = last_rate['time']
        if isinstance(last_time, (int, float)):
            try:
                last_time = datetime.fromtimestamp(float(last_time))
            except Exception:
                return
        if not isinstance(last_time, datetime):
            return

        duration = self._get_timeframe_duration(self.current_timeframe)
        last_bar_start = self._get_bar_start_time(last_time, self.current_timeframe)
        bar_start = last_bar_start + duration
        
        # Initialize current bar
        close_price = float(last_rate['close'])
        self.current_bar = {
            'time': bar_start,
            'open': close_price,  # Current bar opens at previous bar's close
            'high': close_price,
            'low': close_price,
            'close': close_price
        }
        
        # Calculate candle width for current bar
        if self.candlestick_item and len(self.candlestick_item.data) > 1:
            time_range = self.candlestick_item.data[-1][0] - self.candlestick_item.data[0][0]
            candle_width = time_range / len(self.candlestick_item.data) * 0.6
        else:
            candle_width = 3600  # Default 1 hour
        
        # Create current bar item
        if self.current_bar_item:
            self.chart.removeItem(self.current_bar_item)
        
        self.current_bar_item = CurrentBarItem(bar_start, close_price, candle_width)
        self.chart.addItem(self.current_bar_item)
    
    def update_current_bar(self, tick_data: Dict):
        """Update current forming bar with new tick data"""
        if not self.current_symbol or not self.current_bar:
            return
        
        tick_time = tick_data.get('time')
        if isinstance(tick_time, (int, float)):
            tick_time = datetime.fromtimestamp(tick_time)
        elif not isinstance(tick_time, datetime):
            return
        
        # Get price from tick (use mid price)
        bid = tick_data.get('bid', 0)
        ask = tick_data.get('ask', 0)
        price = (bid + ask) / 2.0 if bid > 0 and ask > 0 else tick_data.get('last', 0)
        
        if price <= 0:
            return
        
        # Check if new bar should start
        if self._is_new_bar(tick_time, self.current_timeframe):
            # Finalize previous bar
            if self.current_bar_item:
                self.chart.removeItem(self.current_bar_item)
            
            # Add completed bar to candlestick item
            if self.candlestick_item:
                bar_time_ts = self.current_bar['time'].timestamp()
                self.candlestick_item.data.append((
                    bar_time_ts,
                    self.current_bar['open'],
                    self.current_bar['high'],
                    self.current_bar['low'],
                    self.current_bar['close']
                ))
                self.candlestick_item.generatePicture()
                self.candlestick_item.update()
            
            # Start new bar (align to bar start time, not raw tick time)
            new_bar_start = self._get_bar_start_time(tick_time, self.current_timeframe)
            self.current_bar = {
                'time': new_bar_start,
                'open': price,
                'high': price,
                'low': price,
                'close': price
            }
            
            # Calculate candle width
            if self.candlestick_item and len(self.candlestick_item.data) > 1:
                time_range = self.candlestick_item.data[-1][0] - self.candlestick_item.data[0][0]
                candle_width = time_range / len(self.candlestick_item.data) * 0.6
            else:
                candle_width = 3600
            
            self.current_bar_item = CurrentBarItem(new_bar_start, price, candle_width)
            self.chart.addItem(self.current_bar_item)
        else:
            # Update current bar
            self.current_bar['high'] = max(self.current_bar['high'], price)
            self.current_bar['low'] = min(self.current_bar['low'], price)
            self.current_bar['close'] = price
            
            # Update visual representation
            if self.current_bar_item:
                self.current_bar_item.update_bar(
                    self.current_bar['high'],
                    self.current_bar['low'],
                    self.current_bar['close']
                )
    
    # ========== Phase 2: Context-Aware Tooltips ==========
    
    def _on_mouse_moved(self, pos: QPoint):
        """Handle mouse movement for tooltips and crosshair"""
        self.last_mouse_pos = pos
        
        # Update crosshair
        if self.crosshair_enabled:
            self._update_crosshair(pos)
        
        # Schedule tooltip update (throttled)
        if not self.tooltip_timer.isActive():
            self.tooltip_timer.start(100)  # Update tooltip every 100ms
    
    def leaveEvent(self, event):
        """Handle mouse leave event"""
        # Hide crosshair when mouse leaves widget
        if self.crosshair_enabled:
            self._remove_crosshair()
        QToolTip.hideText()
        self.last_mouse_pos = None
        super().leaveEvent(event)
    
    def enterEvent(self, event):
        """Handle mouse enter event"""
        # Restore crosshair if enabled
        if self.crosshair_enabled and self.last_mouse_pos:
            self._update_crosshair(self.last_mouse_pos)
        super().enterEvent(event)
    
    def _on_mouse_clicked(self, event):
        """Handle mouse clicks"""
        pass  # Can be extended for click interactions
    
    def _update_tooltip(self):
        """Update tooltip based on mouse position"""
        if not self.last_mouse_pos:
            return
        
        # Convert mouse position to chart coordinates
        viewbox = self.chart.getViewBox()
        scene_pos = self.chart.mapToScene(self.last_mouse_pos)
        chart_pos = viewbox.mapSceneToView(scene_pos)
        
        time_ts = chart_pos.x()
        price = chart_pos.y()
        
        # Find closest element
        tooltip_text = self._get_tooltip_text(time_ts, price)
        
        if tooltip_text:
            # Show tooltip near cursor
            global_pos = self.chart.mapToGlobal(self.last_mouse_pos)
            QToolTip.showText(global_pos, tooltip_text, self.chart)
    
    def _get_tooltip_text(self, time_ts: float, price: float) -> Optional[str]:
        """Get tooltip text for given chart coordinates"""
        if not self.current_symbol:
            return None
        
        tooltip_parts = []
        
        # Convert timestamp to datetime
        try:
            time_dt = datetime.fromtimestamp(time_ts)
            time_str = time_dt.strftime("%Y-%m-%d %H:%M:%S")
            tooltip_parts.append(f"Time: {time_str}")
            tooltip_parts.append(f"Price: {price:.5f}")
        except:
            return None
        
        # Check for candlestick
        if self.candlestick_item:
            for i, (t, open_p, high, low, close_p) in enumerate(self.candlestick_item.data):
                # Check if time is within candle range
                if self.candlestick_item.data and len(self.candlestick_item.data) > 1:
                    time_range = self.candlestick_item.data[-1][0] - self.candlestick_item.data[0][0]
                    candle_width = time_range / len(self.candlestick_item.data) * 0.6
                else:
                    candle_width = 3600
                
                if abs(t - time_ts) < candle_width / 2:
                    # Found matching candle
                    body_size = abs(close_p - open_p)
                    upper_wick = high - max(open_p, close_p)
                    lower_wick = min(open_p, close_p) - low
                    change = close_p - open_p
                    change_pct = (change / open_p * 100) if open_p > 0 else 0
                    
                    tooltip_parts.append("")
                    tooltip_parts.append("Candlestick:")
                    tooltip_parts.append(f"  Open: {open_p:.5f}")
                    tooltip_parts.append(f"  High: {high:.5f}")
                    tooltip_parts.append(f"  Low: {low:.5f}")
                    tooltip_parts.append(f"  Close: {close_p:.5f}")
                    tooltip_parts.append(f"  Body: {body_size:.5f}")
                    tooltip_parts.append(f"  Upper Wick: {upper_wick:.5f}")
                    tooltip_parts.append(f"  Lower Wick: {lower_wick:.5f}")
                    tooltip_parts.append(f"  Change: {change:+.5f} ({change_pct:+.2f}%)")
                    break
        
        # Check for current bar
        if self.current_bar_item and abs(self.current_bar_item.bar_time_ts - time_ts) < self.current_bar_item.candle_width / 2:
            tooltip_parts.append("")
            tooltip_parts.append("Current Bar (Forming):")
            tooltip_parts.append(f"  Open: {self.current_bar['open']:.5f}")
            tooltip_parts.append(f"  High: {self.current_bar['high']:.5f}")
            tooltip_parts.append(f"  Low: {self.current_bar['low']:.5f}")
            tooltip_parts.append(f"  Close: {self.current_bar['close']:.5f}")
        
        # Check for general VWAP indicator lines (closest line detection)
        closest_line_info = self._find_closest_indicator_line(time_ts, price)
        if closest_line_info:
            tooltip_parts.append("")
            tooltip_parts.append(f"Indicator: {closest_line_info['name']}")
            if closest_line_info['type'] == 'vwap':
                tooltip_parts.append(f"  Value: {closest_line_info['value']:.5f}")
                tooltip_parts.append(f"  Distance from Price: {abs(price - closest_line_info['value']):.5f}")
            elif closest_line_info['type'] in ['band_upper', 'band_lower']:
                tooltip_parts.append(f"  Value: {closest_line_info['value']:.5f}")
                tooltip_parts.append(f"  STD Level: {closest_line_info.get('std_dev', 'N/A')}")
                tooltip_parts.append(f"  Distance from Price: {abs(price - closest_line_info['value']):.5f}")
        
        # Check for indicator lines (VWAP, bands, OHLC levels) from strategies
        if self.strategy_manager:
            enabled_strategies = self.strategy_manager.get_enabled_strategies()
            for strategy in enabled_strategies:
                if strategy.symbol.upper() != self.current_symbol.upper():
                    continue
                
                # VWAP - check if price is near VWAP line (within reasonable distance)
                if hasattr(strategy, 'vwap_indicator') and strategy.vwap_indicator:
                    vwap_value = strategy.vwap_indicator.get_vwap()
                    if vwap_value:
                        # Calculate distance threshold based on price range
                        view_range = self.chart.getViewBox().viewRange()
                        price_range = view_range[1][1] - view_range[1][0]
                        threshold = price_range * 0.01  # 1% of visible price range
                        
                        if abs(price - vwap_value) < threshold:
                            tooltip_parts.append("")
                            tooltip_parts.append(f"{strategy.name} - VWAP: {vwap_value:.5f}")
                            if hasattr(strategy, 'std_bands'):
                                for std_dev in strategy.std_bands:
                                    upper, lower = strategy.vwap_indicator.get_bands(std_dev)
                                    if upper and abs(price - upper) < threshold:
                                        tooltip_parts.append(f"  Upper {std_dev}STD: {upper:.5f}")
                                    elif lower and abs(price - lower) < threshold:
                                        tooltip_parts.append(f"  Lower {std_dev}STD: {lower:.5f}")
                
                # OHLC levels - check if price is near level lines
                if hasattr(strategy, 'get_ohlc_data'):
                    ohlc_data = strategy.get_ohlc_data()
                    if not ohlc_data and self.market_data_panel:
                        symbol_upper = self.current_symbol.upper()
                        for symbol_key in self.market_data_panel.ohlc_data.keys():
                            if symbol_key.upper() == symbol_upper:
                                ohlc_data = self.market_data_panel.ohlc_data[symbol_key]
                                break
                    
                    if ohlc_data:
                        # Calculate distance threshold
                        view_range = self.chart.getViewBox().viewRange()
                        price_range = view_range[1][1] - view_range[1][0]
                        threshold = price_range * 0.01  # 1% of visible price range
                        
                        for level_name, level_price in [('Open', ohlc_data.get('open')), 
                                                          ('High', ohlc_data.get('high')),
                                                          ('Low', ohlc_data.get('low')),
                                                          ('Close', ohlc_data.get('close'))]:
                            if level_price and abs(price - level_price) < threshold:
                                tooltip_parts.append("")
                                tooltip_parts.append(f"{strategy.name} - {level_name}: {level_price:.5f}")
                                break  # Only show first matching level
        
        return "\n".join(tooltip_parts) if tooltip_parts else None
    
    def _find_closest_indicator_line(self, time_ts: float, price: float, threshold: float = None) -> Optional[Dict]:
        """
        Find the closest indicator line to the mouse cursor
        
        Args:
            time_ts: Timestamp at mouse position
            price: Price at mouse position
            threshold: Maximum distance threshold (auto-calculated if None)
            
        Returns:
            Dictionary with line information or None
        """
        if not hasattr(self, 'plot_items_metadata') or not self.plot_items_metadata:
            return None
        
        # Auto-calculate threshold based on price range if not provided
        if threshold is None:
            view_range = self.chart.getViewBox().viewRange()
            if view_range and len(view_range) > 1:
                price_range = view_range[1][1] - view_range[1][0]
                threshold = price_range * 0.02  # 2% of price range
            else:
                threshold = abs(price) * 0.01  # 1% of current price
        
        closest_item = None
        min_distance = float('inf')
        
        for plot_item, metadata in self.plot_items_metadata.items():
            try:
                if metadata['type'] == 'vwap':
                    # For VWAP line, find closest point on the line
                    times = metadata.get('times', [])
                    values = metadata.get('values', [])
                    
                    if not times or not values:
                        continue
                    
                    # Find closest time point
                    closest_idx = min(range(len(times)), key=lambda i: abs(times[i] - time_ts))
                    line_value = values[closest_idx]
                    distance = abs(price - line_value)
                    
                    if distance < min_distance and distance < threshold:
                        min_distance = distance
                        closest_item = {
                            'name': metadata['name'],
                            'type': 'vwap',
                            'value': line_value,
                            'distance': distance
                        }
                
                elif metadata['type'] in ['band_upper', 'band_lower']:
                    # For bands (horizontal lines), check distance to line value
                    line_value = metadata.get('value')
                    if line_value is not None:
                        distance = abs(price - line_value)
                        if distance < min_distance and distance < threshold:
                            min_distance = distance
                            closest_item = {
                                'name': metadata['name'],
                                'type': metadata['type'],
                                'value': line_value,
                                'std_dev': metadata.get('std_dev'),
                                'distance': distance
                            }
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Error checking plot item for tooltip: {e}")
                continue
        
        return closest_item
    
    # ========== Phase 3: Zoom and Pan Controls ==========
    
    def zoom_in(self):
        """Zoom in"""
        viewbox = self.chart.getViewBox()
        viewbox.scaleBy((0.8, 0.8))
    
    def zoom_out(self):
        """Zoom out"""
        viewbox = self.chart.getViewBox()
        viewbox.scaleBy((1.25, 1.25))
    
    def fit_to_data(self):
        """Fit chart to show all data"""
        self.chart.enableAutoRange()
        self.chart.autoRange()
    
    def reset_view(self):
        """Reset view to default"""
        self.fit_to_data()
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        key = event.key()
        
        # Zoom controls
        if key == Qt.Key.Key_Plus or key == Qt.Key.Key_Equal:
            self.zoom_in()
            event.accept()
        elif key == Qt.Key.Key_Minus:
            self.zoom_out()
            event.accept()
        elif key == Qt.Key.Key_0 or key == Qt.Key.Key_Home:
            self.fit_to_data()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def _on_view_range_changed(self):
        """Handle view range changes (for crosshair label positioning)"""
        if self.crosshair_enabled and self.last_mouse_pos:
            self._update_crosshair(self.last_mouse_pos)
    
    # ========== Phase 4: Crosshair Cursor ==========
    
    def _on_crosshair_toggled(self, state):
        """Handle crosshair toggle"""
        self.crosshair_enabled = (state == Qt.CheckState.Checked)
        if not self.crosshair_enabled:
            self._remove_crosshair()
        elif self.last_mouse_pos:
            self._update_crosshair(self.last_mouse_pos)
    
    def _update_crosshair(self, mouse_pos: QPoint):
        """Update crosshair position"""
        if not self.crosshair_enabled:
            return
        
        # Convert mouse position to chart coordinates
        viewbox = self.chart.getViewBox()
        scene_pos = self.chart.mapToScene(mouse_pos)
        chart_pos = viewbox.mapSceneToView(scene_pos)
        
        time_ts = chart_pos.x()
        price = chart_pos.y()
        
        # Create or update vertical line
        if not self.crosshair_vline:
            self.crosshair_vline = InfiniteLine(pos=time_ts, angle=90, movable=False, pen=pg.mkPen(color='w', width=1, style=Qt.PenStyle.DashLine))
            self.chart.addItem(self.crosshair_vline)
        else:
            self.crosshair_vline.setValue(time_ts)
        
        # Create or update horizontal line
        if not self.crosshair_hline:
            self.crosshair_hline = InfiniteLine(pos=price, angle=0, movable=False, pen=pg.mkPen(color='w', width=1, style=Qt.PenStyle.DashLine))
            self.chart.addItem(self.crosshair_hline)
        else:
            self.crosshair_hline.setValue(price)
        
        # Update price label on right axis
        if not self.crosshair_price_label:
            self.crosshair_price_label = TextItem(text="", color='w', anchor=(1, 0.5))
            self.chart.addItem(self.crosshair_price_label)
        
        # Position price label on right side
        view_range = viewbox.viewRange()
        price_text = f"{price:.5f}"
        self.crosshair_price_label.setText(price_text)
        self.crosshair_price_label.setPos(view_range[0][1], price)  # Right edge, at price level
        
        # Update time label on bottom axis
        if not self.crosshair_time_label:
            self.crosshair_time_label = TextItem(text="", color='w', anchor=(0.5, 1))
            self.chart.addItem(self.crosshair_time_label)
        
        # Format time
        try:
            time_dt = datetime.fromtimestamp(time_ts)
            time_text = time_dt.strftime("%Y-%m-%d %H:%M")
        except:
            time_text = str(time_ts)
        
        self.crosshair_time_label.setText(time_text)
        self.crosshair_time_label.setPos(time_ts, view_range[1][0])  # At time, bottom edge
    
    def _remove_crosshair(self):
        """Remove crosshair from chart"""
        if self.crosshair_vline:
            self.chart.removeItem(self.crosshair_vline)
            self.crosshair_vline = None
        if self.crosshair_hline:
            self.chart.removeItem(self.crosshair_hline)
            self.crosshair_hline = None
        if self.crosshair_price_label:
            self.chart.removeItem(self.crosshair_price_label)
            self.crosshair_price_label = None
        if self.crosshair_time_label:
            self.chart.removeItem(self.crosshair_time_label)
            self.crosshair_time_label = None

