"""
Chart Widget using TradingView Lightweight Charts
Embeds HTML/JS chart via QWebEngineView with QWebChannel bridge
"""

import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                             QLabel, QPushButton, QCheckBox, QSpinBox, 
                             QGroupBox, QGridLayout, QScrollArea, QToolButton,
                             QFrame)
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QUrl, Qt, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import QIcon
from ..utils.symbol_mapper import SymbolMapper
from .indicator_settings_dialog import IndicatorSettingsDialog
import uuid

logger = logging.getLogger(__name__)


class CustomWebEnginePage(QWebEnginePage):
    """Custom page class to capture console messages"""
    
    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        """Log JavaScript console messages to Python logger"""
        logger.debug(f"JS Console [{level}] {message} (line {lineNumber})")


class TradingViewBridge(QObject):
    """Bridge object for QWebChannel communication with JavaScript"""
    
    # Signals that JavaScript can connect to
    candlesUpdated = pyqtSignal(list)
    indicatorsUpdated = pyqtSignal(list)
    pageReady = pyqtSignal()
    markersUpdated = pyqtSignal(list)  # Combined: signals + trade levels
    symbolChanged = pyqtSignal(str, str)  # symbol, timeframe
    fitContentRequested = pyqtSignal()  # Request to fit chart content
    
    def __init__(self):
        super().__init__()
        self._ready = False
    
    @pyqtSlot()
    def emitReady(self):
        """Called by JavaScript when page is ready"""
        self._ready = True
        logger.info("TradingView chart page is ready")
        self.pageReady.emit()  # Emit signal to trigger on_page_ready callback
    
    def is_ready(self):
        """Check if the page is ready"""
        return self._ready
    
    def update_candles(self, candles_data: List[Dict]):
        """
        Update candlestick data
        
        Args:
            candles_data: List of candle dicts with {time, open, high, low, close}
        """
        if self._ready:
            self.candlesUpdated.emit(candles_data)
    
    def update_indicators(self, indicators_data: List[Dict]):
        """
        Update indicator lines
        
        Args:
            indicators_data: List of indicator dicts with {name, color, width, points}
        """
        if self._ready:
            self.indicatorsUpdated.emit(indicators_data)
    
    def request_fit_content(self):
        """Request the chart to fit content (zoom to show all data)"""
        if self._ready:
            self.fitContentRequested.emit()


class ChartWidget(QWidget):
    """Chart widget with TradingView Lightweight Charts"""
    
    def __init__(self, data_feed, mt5, strategy_manager, market_data_panel, order_manager=None):
        super().__init__()
        self.data_feed = data_feed
        self.mt5 = mt5
        self.strategy_manager = strategy_manager
        self.market_data_panel = market_data_panel
        self.order_manager = order_manager
        
        # State
        self.current_symbol = "EURUSD"
        self.current_timeframe = None
        self.timeframe_combo = None
        self.current_chart_type = "Candles"
        self.current_theme = "Dark"
        self.crosshair_enabled = True
        
        # Bridge for QWebChannel
        self.bridge = TradingViewBridge()
        
        # Symbol mapper for resolving symbol names
        self.symbol_mapper = SymbolMapper(mt5)
        
        # Chart renderers for indicator data
        from .chart_renderers import VWAPRenderer, EMARenderer, SuperTrendRenderer, SMCRenderer
        self.vwap_renderer = None  # Will be initialized with proper chart
        self.ema_renderer = None
        self.supertrend_renderer = None
        self.smc_renderer = None
        
        # Active indicators list - each indicator is a dict with:
        # {id, type, visible, settings}
        self.active_indicators = []
        
        # Signal and trade level display
        self.show_signals = False
        self.show_trade_levels = False
        self.strategy_signals = []  # List of {time, type, price, strategy_name, symbol, timestamp}
        
        # Signal persistence
        self.signals_file = Path("data/strategy_signals.json")
        self.load_signals_from_file()
        
        self.setup_ui()
        self.setup_connections()
        
        logger.info("ChartWidget initialized with TradingView Lightweight Charts")
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Control panel (top row with symbol, timeframe, add indicator dropdown)
        control_panel = self.create_control_panel()
        layout.addWidget(control_panel)
        
        # Indicator management panel (shows active indicators)
        self.indicator_panel = self.create_indicator_panel()
        layout.addWidget(self.indicator_panel)
        
        # Web view for TradingView chart
        self.web_view = QWebEngineView()
        
        # Use custom page to capture console messages
        custom_page = CustomWebEnginePage(self.web_view)
        self.web_view.setPage(custom_page)
        
        # Enable necessary web settings
        settings = custom_page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        
        # Setup QWebChannel
        self.channel = QWebChannel()
        self.channel.registerObject('tradingViewBridge', self.bridge)
        custom_page.setWebChannel(self.channel)
        
        # Load the HTML file
        html_path = Path(__file__).parent / 'tradingview_chart.html'
        if html_path.exists():
            self.web_view.setUrl(QUrl.fromLocalFile(str(html_path)))
            logger.info(f"Loading TradingView chart from: {html_path}")
        else:
            logger.error(f"TradingView chart HTML not found: {html_path}")
        
        layout.addWidget(self.web_view, stretch=1)
        
        # Status bar at bottom
        from .chart_status_bar import ChartStatusBar
        self.status_bar = ChartStatusBar(self)
        layout.addWidget(self.status_bar)
    
    def create_control_panel(self) -> QWidget:
        """Create the control panel with symbol, timeframe, and add indicator dropdown"""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Symbol selector
        layout.addWidget(QLabel("Symbol:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.setMinimumWidth(120)
        self.symbol_combo.addItems(["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", 
                                     "USDCAD", "NZDUSD", "XAUUSD", "US30"])
        self.symbol_combo.setCurrentText(self.current_symbol)
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed)
        layout.addWidget(self.symbol_combo)
        
        layout.addSpacing(20)
        
        # Timeframe selector
        layout.addWidget(QLabel("Timeframe:"))
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["M1", "M5", "M15", "M30", "H1", "H4", "D1"])
        self.timeframe_combo.setCurrentText("M15")
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        layout.addWidget(self.timeframe_combo)
        
        layout.addSpacing(20)
        
        # Chart Type selector
        layout.addWidget(QLabel("Chart Type:"))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["Candles", "Line", "Area", "Bars", "Hollow Candles", "Heikin Ashi"])
        self.chart_type_combo.setCurrentText("Candles")
        self.chart_type_combo.currentTextChanged.connect(self.on_chart_type_changed)
        layout.addWidget(self.chart_type_combo)
        
        layout.addSpacing(20)
        
        # Theme selector
        layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        from ..config.chart_themes import get_available_themes
        self.theme_combo.addItems(get_available_themes())
        self.theme_combo.setCurrentText("Dark")
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        layout.addWidget(self.theme_combo)
        
        layout.addSpacing(20)
        
        # Add Indicator dropdown
        layout.addWidget(QLabel("Indicator:"))
        self.add_indicator_combo = QComboBox()
        self.add_indicator_combo.setMinimumWidth(150)
        self.add_indicator_combo.addItems([
            "Add Indicator...",
            "EMA",
            "VWAP",
            "SuperTrend",
            "SMC",
            "OHLC",
            "RSI",
            "MACD",
            "Bollinger Bands"
        ])
        self.add_indicator_combo.currentTextChanged.connect(self.on_add_indicator)
        layout.addWidget(self.add_indicator_combo)
        
        layout.addSpacing(20)
        
        # Show Signals checkbox
        self.show_signals_check = QCheckBox("Show Signals")
        self.show_signals_check.setToolTip("Display buy/sell signals from strategies")
        self.show_signals_check.toggled.connect(self.on_show_signals_toggled)
        layout.addWidget(self.show_signals_check)
        
        # Trade Levels checkbox
        self.trade_levels_check = QCheckBox("Trade Levels")
        self.trade_levels_check.setToolTip("Display entry/exit lines for active trades")
        self.trade_levels_check.toggled.connect(self.on_trade_levels_toggled)
        layout.addWidget(self.trade_levels_check)
        
        layout.addSpacing(20)
        
        # Crosshair checkbox
        self.crosshair_check = QCheckBox("Crosshair")
        self.crosshair_check.setToolTip("Enable crosshair with price/time display")
        self.crosshair_check.setChecked(True)  # Default enabled
        self.crosshair_check.toggled.connect(self.on_crosshair_toggled)
        layout.addWidget(self.crosshair_check)
        
        layout.addSpacing(20)
        
        # Import History button
        import_btn = QPushButton("Import MT5 History")
        import_btn.setToolTip("Import closed trades from MT5 history")
        import_btn.clicked.connect(self.import_mt5_history)
        layout.addWidget(import_btn)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_chart)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        
        return panel
    
    def create_indicator_panel(self) -> QWidget:
        """Create the indicator management panel with scroll area"""
        # Container widget
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(5, 0, 5, 5)
        
        # Label
        label = QLabel("Active Indicators:")
        label.setStyleSheet("font-weight: bold;")
        container_layout.addWidget(label)
        
        # Scroll area for indicator list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(100)
        scroll.setFrameShape(QFrame.Shape.StyledPanel)
        
        # Widget inside scroll area
        self.indicator_list_widget = QWidget()
        self.indicator_list_layout = QVBoxLayout(self.indicator_list_widget)
        self.indicator_list_layout.setContentsMargins(5, 5, 5, 5)
        self.indicator_list_layout.setSpacing(5)
        self.indicator_list_layout.addStretch()
        
        scroll.setWidget(self.indicator_list_widget)
        container_layout.addWidget(scroll)
        
        return container
    
    def setup_connections(self):
        """Setup signal connections"""
        # Connect to bridge ready signal
        self.bridge.pageReady.connect(self.on_page_ready)
        
        # Connect to data feed updates
        if self.data_feed:
            # Subscribe to updates for the current symbol
            self.ensure_symbol_subscribed()
        
        # Setup automatic refresh timer for live updates
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_chart)
        self.refresh_timer.start(1000)  # Refresh every 1 second for live updates
    
    def ensure_symbol_subscribed(self):
        """Ensure current symbol is subscribed in data feed"""
        if self.data_feed and self.current_symbol:
            try:
                # Resolve symbol name to actual MT5 symbol
                actual_symbol = self.symbol_mapper.find_symbol(self.current_symbol)
                if not actual_symbol:
                    logger.warning(f"Could not resolve symbol: {self.current_symbol}")
                    actual_symbol = self.current_symbol
                
                # Use add_symbol to ensure symbol is in data feed
                if actual_symbol not in self.data_feed.symbols:
                    self.data_feed.add_symbol(actual_symbol)
                    logger.debug(f"Added {actual_symbol} to data feed (requested: {self.current_symbol})")
            except Exception as e:
                logger.error(f"Error adding {self.current_symbol} to data feed: {e}")
    
    def on_page_ready(self):
        """Called when the TradingView chart page is ready"""
        logger.info("TradingView chart page ready, loading initial data")
        self.refresh_chart()
        # Fit content on initial load
        self.bridge.request_fit_content()
    
    def on_symbol_changed(self, symbol: str):
        """Handle symbol change"""
        logger.info(f"=== SYMBOL CHANGE EVENT START ===")
        logger.info(f"Old symbol: {self.current_symbol}")
        logger.info(f"New symbol: {symbol}")
        
        self.current_symbol = symbol
        
        # Notify chart about symbol change
        timeframe = self.get_timeframe_str()
        logger.info(f"Emitting symbolChanged signal: {symbol}, {timeframe}")
        self.bridge.symbolChanged.emit(symbol, timeframe)
        
        logger.info(f"Ensuring symbol subscribed: {symbol}")
        self.ensure_symbol_subscribed()
        
        logger.info(f"Triggering chart refresh for: {symbol}")
        # Note: fitContent will be triggered automatically via updateSymbolName setting shouldFitContent flag
        self.refresh_chart()
        logger.info(f"=== SYMBOL CHANGE EVENT END ===")
    
    def on_timeframe_changed(self, timeframe_str: str):
        """Handle timeframe change"""
        logger.info(f"Timeframe changed to: {timeframe_str}")
        self.ensure_symbol_subscribed()
        self.refresh_chart()
        # Request fit content when timeframe changes
        self.bridge.request_fit_content()
    
    def on_chart_type_changed(self, chart_type: str):
        """Handle chart type change"""
        logger.info(f"Chart type changed to: {chart_type}")
        self.current_chart_type = chart_type
        if self.bridge.is_ready():
            # Send chart type change to JavaScript
            self.web_view.page().runJavaScript(f"changeChartType('{chart_type}');")
            self.refresh_chart()
    
    def on_theme_changed(self, theme_name: str):
        """Handle theme change"""
        logger.info(f"Theme changed to: {theme_name}")
        self.current_theme = theme_name
        if self.bridge.is_ready():
            from ..config.chart_themes import get_theme
            theme = get_theme(theme_name)
            # Send theme to JavaScript
            theme_json = json.dumps(theme)
            self.web_view.page().runJavaScript(f"applyTheme({theme_json});")
    
    def on_crosshair_toggled(self, enabled: bool):
        """Handle crosshair enable/disable"""
        logger.info(f"Crosshair {'enabled' if enabled else 'disabled'}")
        self.crosshair_enabled = enabled
        if self.bridge.is_ready():
            self.web_view.page().runJavaScript(f"setCrosshairEnabled({str(enabled).lower()});")
    
    def on_add_indicator(self, indicator_type: str):
        """Handle adding a new indicator from dropdown"""
        if indicator_type == "Add Indicator...":
            return
        
        # Reset dropdown to default
        self.add_indicator_combo.setCurrentIndex(0)
        
        # Add the indicator
        self.add_indicator(indicator_type)
    
    def on_show_signals_toggled(self, checked: bool):
        """Handle show signals toggle"""
        self.show_signals = checked
        logger.info(f"Show signals {'enabled' if checked else 'disabled'}")
        self.refresh_chart()
    
    def on_trade_levels_toggled(self, checked: bool):
        """Handle trade levels toggle"""
        self.show_trade_levels = checked
        logger.info(f"Trade levels {'enabled' if checked else 'disabled'}")
        self.refresh_chart()
    
    def add_indicator(self, indicator_type: str):
        """Add a new indicator instance"""
        # Create default settings for each indicator type
        default_settings = self.get_default_indicator_settings(indicator_type)
        
        # Create indicator instance
        indicator = {
            'id': str(uuid.uuid4()),
            'type': indicator_type,
            'visible': True,
            'settings': default_settings
        }
        
        self.active_indicators.append(indicator)
        logger.info(f"Added indicator: {indicator_type} (ID: {indicator['id']})")
        
        # Update UI
        self.update_indicator_list_ui()
        
        # Refresh chart
        self.refresh_chart()
    
    def get_default_indicator_settings(self, indicator_type: str) -> Dict[str, Any]:
        """Get default settings for an indicator type"""
        defaults = {
            'EMA': {
                'periods': [20, 50, 100, 200],
                'colors': ['#FFA726', '#42A5F5', '#AB47BC', '#66BB6A'],
                'line_width': 2,
                'visible': True
            },
            'VWAP': {
                'bands': [1.0, 1.5, 2.0],
                'band_visibility': {1.0: True, 1.5: False, 2.0: False},
                'band_colors': {
                    1.0: {'upper': '#FF6B6B', 'lower': '#66BB6A'},
                    1.5: {'upper': '#FF5252', 'lower': '#4CAF50'},
                    2.0: {'upper': '#F44336', 'lower': '#388E3C'}
                },
                'swing_period': 10,
                'color': '#00FFFF',
                'line_width': 2,
                'visible': True
            },
            'SuperTrend': {
                'atr_period': 10,
                'atr_multiplier': 3.0,
                'atr_method': 'ATR (Wilder)',
                'up_color': '#00E676',
                'down_color': '#FF1744',
                'line_width': 2,
                'visible': True
            },
            'SMC': {
                'pivot_left': 2,
                'pivot_right': 2,
                'emit_signals': 'CHoCH only (bias flips)',
                'high_color': '#FFCA28',
                'low_color': '#29B6F6',
                'line_width': 2,
                'visible': True
            },
            'OHLC': {
                'session_type': 'daily',
                'show_open': True,
                'show_high': True,
                'show_low': True,
                'show_close': True,
                'open_color': '#4CAF50',
                'high_color': '#2196F3',
                'low_color': '#FF9800',
                'close_color': '#9C27B0',
                'line_width': 2,
                'line_style': 2,
                'visible': True
            },
            'RSI': {
                'period': 14,
                'overbought': 70,
                'oversold': 30,
                'color': '#FF6B6B',
                'line_width': 2,
                'show_levels': True,
                'overbought_color': '#FF1744',
                'oversold_color': '#00E676',
                'visible': True
            },
            'MACD': {
                'fast_period': 12,
                'slow_period': 26,
                'signal_period': 9,
                'macd_color': '#2196F3',
                'signal_color': '#FF9800',
                'histogram_color': '#9E9E9E',
                'line_width': 2,
                'visible': True
            },
            'Bollinger Bands': {
                'period': 20,
                'num_std': 2.0,
                'upper_color': '#FF6B6B',
                'middle_color': '#42A5F5',
                'lower_color': '#66BB6A',
                'line_width': 2,
                'show_middle': True,
                'visible': True
            }
        }
        return defaults.get(indicator_type, {}).copy()
    
    def update_indicator_list_ui(self):
        """Update the indicator list display"""
        from PyQt6.QtWidgets import QApplication
        
        # Clear existing widgets (except the stretch)
        while self.indicator_list_layout.count() > 1:
            item = self.indicator_list_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                # Disconnect all signals to prevent stale connections
                widget.setParent(None)
                widget.deleteLater()
        
        # Process events to ensure widgets are deleted
        QApplication.processEvents()
        
        # Add indicator rows
        for indicator in self.active_indicators:
            row_widget = self.create_indicator_row(indicator)
            self.indicator_list_layout.insertWidget(
                self.indicator_list_layout.count() - 1, row_widget
            )
    
    def create_indicator_row(self, indicator: Dict) -> QWidget:
        """Create a row widget for an indicator"""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        
        # Visibility toggle button
        visibility_btn = QToolButton()
        visibility_btn.setText("👁" if indicator['visible'] else "⊗")
        visibility_btn.setToolTip("Toggle visibility")
        visibility_btn.setFixedSize(25, 25)
        visibility_btn.clicked.connect(
            lambda checked=False, ind_id=indicator['id']: self.toggle_indicator_visibility(ind_id)
        )
        layout.addWidget(visibility_btn)
        
        # Settings button
        settings_btn = QToolButton()
        settings_btn.setText("⚙")
        settings_btn.setToolTip("Settings")
        settings_btn.setFixedSize(25, 25)
        settings_btn.clicked.connect(
            lambda checked=False, ind_id=indicator['id']: self.open_indicator_settings(ind_id)
        )
        layout.addWidget(settings_btn)
        
        # Delete button
        delete_btn = QToolButton()
        delete_btn.setText("🗑")
        delete_btn.setToolTip("Remove indicator")
        delete_btn.setFixedSize(25, 25)
        delete_btn.clicked.connect(
            lambda checked=False, ind_id=indicator['id']: self.remove_indicator(ind_id)
        )
        layout.addWidget(delete_btn)
        
        # Indicator label
        label_text = self.get_indicator_label(indicator)
        label = QLabel(label_text)
        layout.addWidget(label)
        
        layout.addStretch()
        
        return row
    
    def get_indicator_label(self, indicator: Dict) -> str:
        """Get display label for an indicator"""
        ind_type = indicator['type']
        settings = indicator['settings']
        
        if ind_type == 'EMA':
            periods = settings.get('periods', [])
            return f"EMA ({', '.join(str(p) for p in periods)})"
        elif ind_type == 'VWAP':
            bands = settings.get('bands', [])
            period = settings.get('swing_period', 10)
            return f"VWAP (Bands: {', '.join(str(b) for b in bands)}, Period: {period})"
        elif ind_type == 'SuperTrend':
            period = settings.get('atr_period', 10)
            mult = settings.get('atr_multiplier', 3.0)
            method = settings.get('atr_method', 'ATR (Wilder)')
            method_short = "ATR Wilder" if "Wilder" in method else "SMA(TR)"
            return f"SuperTrend (Period: {period}, Mult: {mult}, {method_short})"
        elif ind_type == 'SMC':
            left = settings.get('pivot_left', 2)
            right = settings.get('pivot_right', 2)
            emit = settings.get('emit_signals', 'CHoCH only')
            emit_short = emit.split('(')[0].strip()
            return f"SMC (Pivot: {left}/{right}, Emit: {emit_short})"
        elif ind_type == 'OHLC':
            session = settings.get('session_type', 'daily').capitalize()
            return f"OHLC ({session})"
        elif ind_type == 'RSI':
            period = settings.get('period', 14)
            return f"RSI ({period})"
        elif ind_type == 'MACD':
            fast = settings.get('fast_period', 12)
            slow = settings.get('slow_period', 26)
            signal = settings.get('signal_period', 9)
            return f"MACD ({fast}, {slow}, {signal})"
        elif ind_type == 'Bollinger Bands':
            period = settings.get('period', 20)
            std = settings.get('num_std', 2.0)
            return f"BB ({period}, {std}σ)"
        
        return ind_type
    
    def toggle_indicator_visibility(self, indicator_id: str):
        """Toggle visibility of an indicator"""
        for indicator in self.active_indicators:
            if indicator['id'] == indicator_id:
                indicator['visible'] = not indicator['visible']
                indicator['settings']['visible'] = indicator['visible']
                logger.info(f"Toggled visibility for {indicator['type']}: {indicator['visible']}")
                break
        
        # Update UI and refresh chart
        self.update_indicator_list_ui()
        self.refresh_chart()
    
    def open_indicator_settings(self, indicator_id: str):
        """Open settings dialog for an indicator"""
        for indicator in self.active_indicators:
            if indicator['id'] == indicator_id:
                dialog = IndicatorSettingsDialog(
                    indicator['type'],
                    indicator['settings'],
                    self
                )
                if dialog.exec() == dialog.DialogCode.Accepted:
                    # Update settings
                    new_settings = dialog.get_settings()
                    indicator['settings'] = new_settings
                    indicator['visible'] = new_settings.get('visible', True)
                    logger.info(f"Updated settings for {indicator['type']}")
                    self.update_indicator_list_ui()
                    self.refresh_chart()
                break
    
    def remove_indicator(self, indicator_id: str):
        """Remove an indicator"""
        # Find and remove the indicator from data model first
        for i, indicator in enumerate(self.active_indicators):
            if indicator['id'] == indicator_id:
                removed = self.active_indicators.pop(i)
                logger.info(f"Removed indicator: {removed['type']}")
                break
        
        # Update UI and refresh chart
        self.update_indicator_list_ui()
        self.refresh_chart()
    
    def get_timeframe_str(self) -> str:
        """Get current timeframe as string"""
        if self.timeframe_combo:
            return self.timeframe_combo.currentText()
        return "M15"
    
    def get_mt5_timeframe(self) -> Optional[int]:
        """Convert timeframe string to MT5 constant"""
        try:
            import MetaTrader5 as mt5
            timeframe_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1,
            }
            return timeframe_map.get(self.get_timeframe_str())
        except Exception as e:
            logger.error(f"Error getting MT5 timeframe: {e}")
            return None
    
    def refresh_chart(self):
        """Refresh chart data"""
        if not self.bridge.is_ready():
            logger.debug("Chart not ready yet, skipping refresh")
            return
        
        # Only refresh if widget is visible (performance optimization)
        if not self.isVisible():
            return
        
        try:
            # Get candle data
            candles = self.get_candle_data()
            if candles:
                self.bridge.update_candles(candles)
                logger.debug(f"Updated {len(candles)} candles")
            
            # Get indicator data
            indicators = self.get_indicator_data()
            if indicators:
                self.bridge.update_indicators(indicators)
                logger.debug(f"Updated {len(indicators)} indicators")
            
            # Get signal markers
            markers = self.get_signal_markers()
            logger.info(f"DEBUG: show_signals={self.show_signals}, signal_markers_count={len(markers)}, strategy_signals_stored={len(self.strategy_signals)}")
            
            # Get trade level markers
            trade_markers = self.get_trade_level_markers()
            logger.info(f"DEBUG: show_trade_levels={self.show_trade_levels}, trade_markers_count={len(trade_markers)}")
            
            # Combine signal markers and trade markers
            all_markers = markers + trade_markers
            logger.debug(f"Total markers: {len(all_markers)} (signals: {len(markers)}, trades: {len(trade_markers)})")
            
            # Send combined markers - both signals and trades
            if all_markers or self.show_signals or self.show_trade_levels:  # Send even empty to clear
                self.bridge.markersUpdated.emit(all_markers)
                logger.debug(f"Updated {len(all_markers)} total markers")
            
            # Update status bar
            self._update_status_bar()
        
        except Exception as e:
            logger.error(f"Error refreshing chart: {e}", exc_info=True)
    
    def _update_status_bar(self):
        """Update status bar with current market data"""
        if not hasattr(self, 'status_bar'):
            return
        
        try:
            actual_symbol = self.symbol_mapper.find_symbol(self.current_symbol)
            if not actual_symbol:
                actual_symbol = self.current_symbol
            
            # Get current tick
            if self.data_feed:
                tick = self.data_feed.get_latest_tick(actual_symbol)
                if tick:
                    bid = tick.get('bid', 0)
                    ask = tick.get('ask', 0)
                    spread = tick.get('spread', 0)
                    
                    if bid > 0 and ask > 0:
                        self.status_bar.update_price(bid=bid, ask=ask)
                        if spread:
                            self.status_bar.update_spread(spread)
            
            # Get last candle OHLC
            candles = self.get_candle_data()
            if candles and len(candles) > 0:
                last_candle = candles[-1]
                open_val = last_candle.get('open')
                high_val = last_candle.get('high')
                low_val = last_candle.get('low')
                close_val = last_candle.get('close')
                
                if all(v is not None for v in [open_val, high_val, low_val, close_val]):
                    self.status_bar.update_ohlc(open_val, high_val, low_val, close_val)
            
            # Get volume from last candle if available
            if candles and len(candles) > 0:
                last_candle = candles[-1]
                volume = last_candle.get('tick_volume') or last_candle.get('volume')
                if volume:
                    self.status_bar.update_volume(volume)
        
        except Exception as e:
            logger.debug(f"Error updating status bar: {e}")
    
    def get_candle_data(self) -> List[Dict]:
        """
        Get candlestick data from data feed or market data panel
        
        Returns:
            List of candle dicts with {time, open, high, low, close}
        """
        try:
            # Resolve symbol name to actual MT5 symbol
            logger.info(f"Symbol Resolution: Requested={self.current_symbol}")
            actual_symbol = self.symbol_mapper.find_symbol(self.current_symbol)
            
            if not actual_symbol:
                logger.warning(f"Symbol Resolution: Could not resolve symbol: {self.current_symbol}")
                actual_symbol = self.current_symbol
            else:
                if actual_symbol != self.current_symbol:
                    logger.info(f"Symbol Resolution: Mapped {self.current_symbol} -> {actual_symbol}")
                else:
                    logger.info(f"Symbol Resolution: Using exact symbol: {actual_symbol}")
            
            candles = []
            
            # Try to get from market data panel first (if available)
            if self.market_data_panel and hasattr(self.market_data_panel, 'get_ohlc_data'):
                ohlc_data = self.market_data_panel.get_ohlc_data(actual_symbol)
                if ohlc_data and len(ohlc_data) > 0:
                    logger.info(f"Got {len(ohlc_data)} candles for {actual_symbol} from market data panel")
                    candles = self._convert_to_tradingview_candles(ohlc_data)
                    if candles:
                        self._log_price_verification(candles, actual_symbol)
            
            # Fallback to data feed if market data panel didn't provide candles
            if not candles and self.data_feed:
                timeframe = self.get_mt5_timeframe()
                if timeframe is not None:
                    rates = self.data_feed.get_rates(actual_symbol, timeframe, count=500)
                    if rates is not None and len(rates) > 0:
                        logger.info(f"Got {len(rates)} candles for {actual_symbol} from data feed")
                        candles = self._convert_to_tradingview_candles(rates)
                        if candles:
                            self._log_price_verification(candles, actual_symbol)
            
            if not candles:
                logger.warning(f"No candle data available for {self.current_symbol} (resolved to: {actual_symbol})")
                return []
            
            # Update the last candle with current tick price for live price movement
            if candles and len(candles) > 0:
                # Get current tick to update the last (forming) candle
                if self.data_feed:
                    tick = self.data_feed.get_latest_tick(actual_symbol)
                    if tick:
                        # Calculate current price (mid of bid/ask)
                        bid = tick.get('bid', 0)
                        ask = tick.get('ask', 0)
                        if bid > 0 and ask > 0:
                            current_price = (bid + ask) / 2.0
                        elif bid > 0:
                            current_price = bid
                        elif ask > 0:
                            current_price = ask
                        else:
                            current_price = None
                        
                        if current_price and current_price > 0:
                            # Update the last candle with current tick price
                            last_candle = candles[-1].copy()
                            
                            # Ensure we have valid OHLC values
                            last_open = last_candle.get('open', current_price)
                            last_high = last_candle.get('high', current_price)
                            last_low = last_candle.get('low', current_price)
                            
                            # Update high/low/close with current price
                            last_candle['high'] = max(last_high, current_price)
                            last_candle['low'] = min(last_low, current_price)
                            last_candle['close'] = current_price
                            
                            # Replace the last candle with updated one
                            candles[-1] = last_candle
                            logger.debug(f"Updated last candle with current price: {current_price:.5f} (H: {last_candle['high']:.5f}, L: {last_candle['low']:.5f})")
            
            return candles
        
        except Exception as e:
            logger.error(f"Error getting candle data: {e}", exc_info=True)
            return []
    
    def _log_price_verification(self, candles: List[Dict], symbol: str):
        """Log first and last few candles for price verification"""
        try:
            if not candles:
                return
            
            logger.info(f"Price Verification for {symbol}:")
            logger.info(f"  Total candles: {len(candles)}")
            
            # Log first candle
            first = candles[0]
            logger.info(f"  First candle: O={first.get('open', 'N/A')}, H={first.get('high', 'N/A')}, L={first.get('low', 'N/A')}, C={first.get('close', 'N/A')}")
            
            # Log last candle
            last = candles[-1]
            logger.info(f"  Last candle:  O={last.get('open', 'N/A')}, H={last.get('high', 'N/A')}, L={last.get('low', 'N/A')}, C={last.get('close', 'N/A')}")
            
            # Calculate approximate price range for sanity check
            closes = [c.get('close', 0) for c in candles if c.get('close')]
            if closes:
                avg_price = sum(closes) / len(closes)
                min_price = min(closes)
                max_price = max(closes)
                logger.info(f"  Price range: Min={min_price:.5f}, Max={max_price:.5f}, Avg={avg_price:.5f}")
        except Exception as e:
            logger.warning(f"Error logging price verification: {e}")
    
    def _convert_to_tradingview_candles(self, rates) -> List[Dict]:
        """
        Convert MT5 rates to TradingView Lightweight Charts format
        
        Args:
            rates: MT5 rates data (list of dicts or numpy structured array)
        
        Returns:
            List of candle dicts with {time, open, high, low, close}
        """
        candles = []
        try:
            for rate in rates:
                # Handle both dict and structured array
                if hasattr(rate, 'keys'):
                    time_val = rate.get('time')
                    open_val = rate.get('open')
                    high_val = rate.get('high')
                    low_val = rate.get('low')
                    close_val = rate.get('close')
                else:
                    time_val = rate['time'] if 'time' in rate.dtype.names else None
                    open_val = rate['open'] if 'open' in rate.dtype.names else None
                    high_val = rate['high'] if 'high' in rate.dtype.names else None
                    low_val = rate['low'] if 'low' in rate.dtype.names else None
                    close_val = rate['close'] if 'close' in rate.dtype.names else None
                
                # Convert datetime to Unix timestamp
                if isinstance(time_val, datetime):
                    time_unix = int(time_val.timestamp())
                else:
                    time_unix = int(time_val)
                
                candles.append({
                    'time': time_unix,
                    'open': float(open_val),
                    'high': float(high_val),
                    'low': float(low_val),
                    'close': float(close_val)
                })
        except Exception as e:
            logger.error(f"Error converting candles: {e}", exc_info=True)
        
        return candles
    
    def get_indicator_data(self) -> List[Dict]:
        """
        Get indicator data to overlay on chart
        
        Returns:
            List of indicator dicts with {name, color, width, points}
        """
        indicators = []
        
        try:
            # Resolve symbol name to actual MT5 symbol
            actual_symbol = self.symbol_mapper.find_symbol(self.current_symbol)
            if not actual_symbol:
                actual_symbol = self.current_symbol
            
            # Get rates for indicator calculations
            rates = None
            times = None
            
            if self.market_data_panel and hasattr(self.market_data_panel, 'get_ohlc_data'):
                ohlc_data = self.market_data_panel.get_ohlc_data(actual_symbol)
                if ohlc_data and len(ohlc_data) > 0:
                    rates = ohlc_data
                    times = [r.get('time') if hasattr(r, 'keys') else r['time'] for r in rates]
            elif self.data_feed:
                timeframe = self.get_mt5_timeframe()
                if timeframe is not None:
                    rates = self.data_feed.get_rates(actual_symbol, timeframe, count=500)
                    if rates is not None and len(rates) > 0:
                        times = [r.get('time') if hasattr(r, 'keys') else r['time'] for r in rates]
            
            if not rates or not times:
                return indicators
            
            # Convert rates to list of dicts if needed
            rates_list = []
            for r in rates:
                if hasattr(r, 'keys'):
                    # Ensure tick_volume exists
                    if 'tick_volume' not in r and 'volume' not in r:
                        r['tick_volume'] = 1.0
                    elif 'tick_volume' not in r and 'volume' in r:
                        r['tick_volume'] = r['volume']
                    rates_list.append(r)
                else:
                    # Handle structured array
                    tick_vol = 0
                    if 'tick_volume' in r.dtype.names:
                        tick_vol = int(r['tick_volume'])
                    elif 'volume' in r.dtype.names:
                        tick_vol = int(r['volume'])
                    else:
                        tick_vol = 1.0  # Default to 1.0 instead of 0 for VWAP calculation
                    
                    rates_list.append({
                        'time': r['time'],
                        'open': float(r['open']),
                        'high': float(r['high']),
                        'low': float(r['low']),
                        'close': float(r['close']),
                        'tick_volume': tick_vol
                    })
            
            # Loop through active indicators and calculate each one
            for indicator in self.active_indicators:
                if not indicator.get('visible', True):
                    continue
                
                ind_type = indicator['type']
                settings = indicator['settings']
                ind_id = indicator['id']
                
                if ind_type == 'EMA':
                    ema_data = self._calculate_ema_indicator(times, rates_list, settings, ind_id)
                    if ema_data:
                        indicators.extend(ema_data)
                
                elif ind_type == 'VWAP':
                    vwap_data = self._calculate_vwap_indicator(times, rates_list, settings, ind_id)
                    if vwap_data:
                        indicators.extend(vwap_data)
                
                elif ind_type == 'SuperTrend':
                    st_data = self._calculate_supertrend_indicator(times, rates_list, settings, ind_id)
                    if st_data:
                        indicators.extend(st_data)
                
                elif ind_type == 'SMC':
                    smc_data = self._calculate_smc_indicator(times, rates_list, settings, ind_id)
                    if smc_data:
                        indicators.extend(smc_data)
                
                elif ind_type == 'OHLC':
                    ohlc_data = self._calculate_ohlc_indicator(settings, ind_id)
                    if ohlc_data:
                        indicators.extend(ohlc_data)
                
                elif ind_type == 'RSI':
                    rsi_data = self._calculate_rsi_indicator(times, rates_list, settings, ind_id)
                    if rsi_data:
                        indicators.extend(rsi_data)
                
                elif ind_type == 'MACD':
                    macd_data = self._calculate_macd_indicator(times, rates_list, settings, ind_id)
                    if macd_data:
                        indicators.extend(macd_data)
                
                elif ind_type == 'Bollinger Bands':
                    bb_data = self._calculate_bollinger_indicator(times, rates_list, settings, ind_id)
                    if bb_data:
                        indicators.extend(bb_data)
        
        except Exception as e:
            logger.error(f"Error getting indicator data: {e}", exc_info=True)
        
        return indicators
    
    def _calculate_vwap_indicator(self, times: List, rates: List[Dict], 
                                   settings: Dict[str, Any], ind_id: str) -> List[Dict]:
        """Calculate VWAP indicator data with custom settings"""
        try:
            # Validate input data
            if not rates or not times:
                logger.warning(f"VWAP: Empty rates or times data for indicator {ind_id}")
                return []
            
            # Validate that rates have required fields
            required_fields = ['time', 'high', 'low', 'close']
            sample_rate = rates[0] if rates else {}
            missing_fields = [field for field in required_fields if field not in sample_rate]
            if missing_fields:
                logger.error(f"VWAP: Missing required fields in rates: {missing_fields}")
                return []
            
            # Ensure rates have tick_volume field (VWAP needs it)
            # If missing, add default value of 1.0
            for rate in rates:
                if 'tick_volume' not in rate and 'volume' not in rate:
                    rate['tick_volume'] = 1.0
                elif 'tick_volume' not in rate and 'volume' in rate:
                    rate['tick_volume'] = rate['volume']
            
            from ..indicators.vwap import VWAP
            vwap = VWAP()
            
            # Get band configuration from settings
            std_levels = settings.get('bands', [1.0, 1.5, 2.0])
            band_visibility = settings.get('band_visibility', {1.0: True, 1.5: False, 2.0: False})
            band_colors = settings.get('band_colors', {
                1.0: {'upper': '#FF6B6B', 'lower': '#66BB6A'},
                1.5: {'upper': '#FF5252', 'lower': '#4CAF50'},
                2.0: {'upper': '#F44336', 'lower': '#388E3C'}
            })
            
            # Calculate VWAP with bands
            vwap_values, bands_dict = vwap.calculate_with_bands(rates, std_levels)
            
            # Debug: Check if VWAP calculation returned values
            if not vwap_values:
                logger.warning(f"VWAP: calculate_with_bands() returned empty list for indicator {ind_id}")
                return []
            
            # Check if all values are None
            valid_count = sum(1 for v in vwap_values if v is not None)
            if valid_count == 0:
                logger.warning(f"VWAP: All calculated values are None for indicator {ind_id}")
                return []
            
            # Validate that vwap_values matches times length
            if len(vwap_values) != len(times):
                logger.warning(f"VWAP: Length mismatch - times: {len(times)}, vwap_values: {len(vwap_values)}")
                # Use minimum length to avoid index errors
                min_len = min(len(times), len(vwap_values))
                times = times[:min_len]
                vwap_values = vwap_values[:min_len]
                # Also truncate bands
                for std_dev in bands_dict:
                    bands_dict[std_dev] = (
                        bands_dict[std_dev][0][:min_len],
                        bands_dict[std_dev][1][:min_len]
                    )
            
            # Get settings
            color = settings.get('color', '#00FFFF')
            line_width = settings.get('line_width', 2)
            
            indicators = []
            
            # Create VWAP line
            if vwap_values:
                points = []
                for i, (time_val, vwap_val) in enumerate(zip(times, vwap_values)):
                    if vwap_val is not None:
                        # Handle time conversion - support both datetime and timestamp
                        try:
                            if isinstance(time_val, datetime):
                                time_unix = int(time_val.timestamp())
                            elif isinstance(time_val, (int, float)):
                                time_unix = int(time_val)
                            else:
                                # Try to convert string or other formats
                                logger.warning(f"VWAP: Unexpected time format at index {i}: {type(time_val)}")
                                continue
                            
                            points.append({'time': time_unix, 'value': float(vwap_val)})
                        except (ValueError, TypeError, AttributeError) as e:
                            logger.warning(f"VWAP: Error converting time at index {i}: {e}")
                            continue
                
                if points:
                    logger.info(f"VWAP: Successfully calculated {len(points)} points for indicator {ind_id}")
                    indicators.append({
                        'name': f'VWAP_{ind_id}',
                        'color': color,
                        'width': line_width,
                        'points': points
                    })
            
            # Create band lines for each enabled band level
            for std_dev in sorted(std_levels):
                if not band_visibility.get(std_dev, False):
                    continue
                
                upper_bands, lower_bands = bands_dict.get(std_dev, ([], []))
                colors = band_colors.get(std_dev, {'upper': '#FF6B6B', 'lower': '#66BB6A'})
                upper_color = colors.get('upper', '#FF6B6B')
                lower_color = colors.get('lower', '#66BB6A')
                
                # Upper band
                upper_points = []
                for i, (time_val, upper_val) in enumerate(zip(times, upper_bands)):
                    if upper_val is not None and i < len(times):
                        try:
                            if isinstance(time_val, datetime):
                                time_unix = int(time_val.timestamp())
                            elif isinstance(time_val, (int, float)):
                                time_unix = int(time_val)
                            else:
                                continue
                            
                            upper_points.append({'time': time_unix, 'value': float(upper_val)})
                        except (ValueError, TypeError, AttributeError):
                            continue
                
                if upper_points:
                    indicators.append({
                        'name': f'VWAP_Upper_{std_dev}σ_{ind_id}',
                        'color': upper_color,
                        'width': 1,
                        'points': upper_points,
                        'line_style': 2  # Dashed line
                    })
                
                # Lower band
                lower_points = []
                for i, (time_val, lower_val) in enumerate(zip(times, lower_bands)):
                    if lower_val is not None and i < len(times):
                        try:
                            if isinstance(time_val, datetime):
                                time_unix = int(time_val.timestamp())
                            elif isinstance(time_val, (int, float)):
                                time_unix = int(time_val)
                            else:
                                continue
                            
                            lower_points.append({'time': time_unix, 'value': float(lower_val)})
                        except (ValueError, TypeError, AttributeError):
                            continue
                
                if lower_points:
                    indicators.append({
                        'name': f'VWAP_Lower_{std_dev}σ_{ind_id}',
                        'color': lower_color,
                        'width': 1,
                        'points': lower_points,
                        'line_style': 2  # Dashed line
                    })
            
            if indicators:
                return indicators
            else:
                logger.warning(f"VWAP: No valid points generated for indicator {ind_id}")
        except Exception as e:
            logger.error(f"Error calculating VWAP indicator {ind_id}: {e}", exc_info=True)
        
        return []
    
    def _calculate_ema_indicator(self, times: List, rates: List[Dict], 
                                  settings: Dict[str, Any], ind_id: str) -> List[Dict]:
        """Calculate EMA indicator data with custom settings"""
        try:
            from ..indicators.ema import EMA
            
            # Get settings
            periods = settings.get('periods', [20, 50, 100, 200])
            colors = settings.get('colors', ['#FFA726', '#42A5F5', '#AB47BC', '#66BB6A'])
            line_width = settings.get('line_width', 2)
            
            indicators = []
            for i, period in enumerate(periods):
                color = colors[i] if i < len(colors) else '#FFFFFF'
                ema = EMA(period)
                ema_values = ema.calculate(rates)
                
                if ema_values:
                    points = []
                    for time_val, ema_val in zip(times, ema_values):
                        if ema_val is not None:
                            time_unix = int(time_val.timestamp()) if isinstance(time_val, datetime) else int(time_val)
                            points.append({'time': time_unix, 'value': float(ema_val)})
                    
                    if points:
                        indicators.append({
                            'name': f'EMA({period})_{ind_id}',
                            'color': color,
                            'width': line_width,
                            'points': points
                        })
            
            return indicators
        except Exception as e:
            logger.debug(f"Error calculating EMA: {e}")
        
        return []
    
    def _calculate_supertrend_indicator(self, times: List, rates: List[Dict], 
                                        settings: Dict[str, Any], ind_id: str) -> List[Dict]:
        """Calculate SuperTrend indicator data with custom settings"""
        try:
            from ..strategy.supertrend_strategy import compute_supertrend
            
            # Get settings
            atr_period = settings.get('atr_period', 10)
            atr_multiplier = settings.get('atr_multiplier', 3.0)
            atr_method = settings.get('atr_method', 'ATR (Wilder)')
            up_color = settings.get('up_color', '#00E676')
            down_color = settings.get('down_color', '#FF1744')
            line_width = settings.get('line_width', 2)
            
            use_wilder_atr = 'Wilder' in atr_method
            
            # Prepare candles
            candles = []
            for r in rates:
                candles.append({
                    "time": r.get("time"),
                    "open": float(r.get("open")),
                    "high": float(r.get("high")),
                    "low": float(r.get("low")),
                    "close": float(r.get("close")),
                })
            
            trend, atr, up_final, dn_final = compute_supertrend(
                candles=candles,
                period=atr_period,
                multiplier=atr_multiplier,
                use_wilder_atr=use_wilder_atr
            )
            
            if not trend:
                return []
            
            indicators = []
            
            # Active SuperTrend line
            st_up_points = []
            st_dn_points = []
            
            for i, (time_val, trend_val) in enumerate(zip(times, trend)):
                if i >= len(up_final) or i >= len(dn_final):
                    break
                
                time_unix = int(time_val.timestamp()) if isinstance(time_val, datetime) else int(time_val)
                
                if int(trend_val) == 1 and dn_final[i] is not None:
                    st_up_points.append({'time': time_unix, 'value': float(dn_final[i])})
                elif int(trend_val) == -1 and up_final[i] is not None:
                    st_dn_points.append({'time': time_unix, 'value': float(up_final[i])})
            
            if st_up_points:
                indicators.append({
                    'name': f'SuperTrend_UP_{ind_id}',
                    'color': up_color,
                    'width': line_width,
                    'points': st_up_points
                })
            
            if st_dn_points:
                indicators.append({
                    'name': f'SuperTrend_DOWN_{ind_id}',
                    'color': down_color,
                    'width': line_width,
                    'points': st_dn_points
                })
            
            return indicators
        
        except Exception as e:
            logger.debug(f"Error calculating SuperTrend: {e}")
        
        return []
    
    def _calculate_smc_indicator(self, times: List, rates: List[Dict], 
                                  settings: Dict[str, Any], ind_id: str) -> List[Dict]:
        """Calculate SMC indicator data with custom settings"""
        try:
            # Validate input data
            if not rates or not times:
                logger.warning(f"SMC: Empty rates or times data for indicator {ind_id}")
                return []
            
            if len(rates) != len(times):
                logger.warning(f"SMC: Length mismatch - times: {len(times)}, rates: {len(rates)}")
                return []
            
            # Get settings
            pivot_left = settings.get('pivot_left', 2)
            pivot_right = settings.get('pivot_right', 2)
            emit_signals = settings.get('emit_signals', 'CHoCH only (bias flips)')
            high_color = settings.get('high_color', '#FFCA28')
            low_color = settings.get('low_color', '#29B6F6')
            line_width = settings.get('line_width', 2)
            
            # Normalize emit_signals setting
            emit_mode = 'Both'
            if 'CHoCH' in emit_signals and 'BOS' not in emit_signals:
                emit_mode = 'CHoCH'
            elif 'BOS' in emit_signals and 'CHoCH' not in emit_signals:
                emit_mode = 'BOS'
            elif 'Both' in emit_signals or ('BOS' in emit_signals and 'CHoCH' in emit_signals):
                emit_mode = 'Both'
            
            # Import fractal pivot functions
            from ..strategy.smc_strategy import _fractal_pivot_high, _fractal_pivot_low
            
            # Extract high, low, and close price arrays from rates
            highs = []
            lows = []
            closes = []
            for r in rates:
                high = r.get('high')
                low = r.get('low')
                close = r.get('close')
                if high is None or low is None or close is None:
                    logger.warning(f"SMC: Missing high/low/close in rate data")
                    return []
                highs.append(float(high))
                lows.append(float(low))
                closes.append(float(close))
            
            # Get chart time range for horizontal line segments
            candles = self.get_candle_data()
            if not candles or len(candles) < 2:
                logger.warning(f"SMC: Not enough candles for line segments: {len(candles) if candles else 0}")
                return []
            
            # Get time range for horizontal segments
            start_time = candles[0]['time']
            end_time = candles[-1]['time']
            
            # Convert to Unix timestamp if needed
            if isinstance(start_time, datetime):
                start_time = int(start_time.timestamp())
            elif not isinstance(start_time, int):
                try:
                    start_time = int(start_time)
                except (ValueError, TypeError):
                    logger.error(f"SMC: Invalid start_time format: {start_time}")
                    return []
            
            if isinstance(end_time, datetime):
                end_time = int(end_time.timestamp())
            elif not isinstance(end_time, int):
                try:
                    end_time = int(end_time)
                except (ValueError, TypeError):
                    logger.error(f"SMC: Invalid end_time format: {end_time}")
                    return []
            
            # Calculate segment duration (small portion of total range for visibility)
            time_range = end_time - start_time
            segment_duration = max(3600, time_range // 50)  # At least 1 hour, or 2% of total range
            
            # Detect all pivot highs and pivot lows
            all_pivot_highs = []  # List of (index, price)
            all_pivot_lows = []   # List of (index, price)
            
            # Valid range for pivot detection: from pivot_left to len - pivot_right
            start_idx = pivot_left
            end_idx = len(highs) - pivot_right
            
            for i in range(start_idx, end_idx):
                if _fractal_pivot_high(highs, i, pivot_left, pivot_right):
                    all_pivot_highs.append((i, highs[i]))
                if _fractal_pivot_low(lows, i, pivot_left, pivot_right):
                    all_pivot_lows.append((i, lows[i]))
            
            # Track structure for filtering
            last_pivot_high = None  # (index, price)
            last_pivot_low = None   # (index, price)
            bias = None  # "BULLISH" | "BEARISH" | None
            relevant_pivot_highs = []  # Pivots that match emit_signals filter
            relevant_pivot_lows = []   # Pivots that match emit_signals filter
            structure_events = {}  # Map pivot index to structure event type
            
            # Process pivots chronologically and detect structure breaks
            # Combine and sort all pivots by index
            all_pivots = []
            for idx, price in all_pivot_highs:
                all_pivots.append(('high', idx, price))
            for idx, price in all_pivot_lows:
                all_pivots.append(('low', idx, price))
            all_pivots.sort(key=lambda x: x[1])  # Sort by index
            
            # Track structure breaks by iterating through candles and checking for breaks
            # After each pivot is detected, check subsequent candles for structure breaks
            for pivot_type, pivot_idx, pivot_price in all_pivots:
                # Update last pivot
                if pivot_type == 'high':
                    last_pivot_high = (pivot_idx, pivot_price)
                else:
                    last_pivot_low = (pivot_idx, pivot_price)
                
                # Check for structure breaks after this pivot
                # Look ahead to see if price breaks structure (up to 100 candles or next pivot)
                check_start = pivot_idx + pivot_right + 1  # Wait for pivot confirmation
                check_end = min(pivot_idx + 100, len(closes))
                
                structure_event = None
                for check_idx in range(check_start, check_end):
                    if check_idx >= len(closes):
                        break
                    
                    close_price = closes[check_idx]
                    
                    # Check if THIS specific pivot was broken
                    if pivot_type == 'high' and close_price > pivot_price:
                        # Price broke above THIS pivot high
                        if bias == "BEARISH":
                            structure_event = "CHoCH"
                        elif bias == "BULLISH":
                            structure_event = "BOS"
                        else:
                            structure_event = "BOS"  # Unknown bias = BOS
                        
                        # Update bias on CHoCH
                        if structure_event == "CHoCH":
                            bias = "BULLISH"
                        elif bias is None:
                            bias = "BULLISH"
                        
                        structure_events[pivot_idx] = structure_event
                        break
                    
                    if pivot_type == 'low' and close_price < pivot_price:
                        # Price broke below THIS pivot low
                        if bias == "BULLISH":
                            structure_event = "CHoCH"
                        elif bias == "BEARISH":
                            structure_event = "BOS"
                        else:
                            structure_event = "BOS"  # Unknown bias = BOS
                        
                        # Update bias on CHoCH
                        if structure_event == "CHoCH":
                            bias = "BEARISH"
                        elif bias is None:
                            bias = "BEARISH"
                        
                        structure_events[pivot_idx] = structure_event
                        break
            
            # Filter pivots based on emit_signals setting
            for pivot_type, pivot_idx, pivot_price in all_pivots:
                structure_event = structure_events.get(pivot_idx)
                should_include = False
                
                if emit_mode == 'Both':
                    # Show all structure-defining pivots
                    should_include = True
                elif emit_mode == 'CHoCH':
                    # Only show pivots that caused CHoCH
                    if structure_event == 'CHoCH':
                        should_include = True
                    # Also show last structure-defining pivots (current structure)
                    elif structure_event is None:
                        if (pivot_type == 'high' and last_pivot_high and pivot_idx == last_pivot_high[0]) or \
                           (pivot_type == 'low' and last_pivot_low and pivot_idx == last_pivot_low[0]):
                            should_include = True
                elif emit_mode == 'BOS':
                    # Only show pivots that caused BOS
                    if structure_event == 'BOS':
                        should_include = True
                    # Also show last structure-defining pivots (current structure)
                    elif structure_event is None:
                        if (pivot_type == 'high' and last_pivot_high and pivot_idx == last_pivot_high[0]) or \
                           (pivot_type == 'low' and last_pivot_low and pivot_idx == last_pivot_low[0]):
                            should_include = True
                
                if should_include:
                    if pivot_type == 'high':
                        relevant_pivot_highs.append((pivot_idx, pivot_price))
                    else:
                        relevant_pivot_lows.append((pivot_idx, pivot_price))
            
            # Fallback: If no pivots match filter, show last structure-defining pivots
            if not relevant_pivot_highs and not relevant_pivot_lows:
                if last_pivot_high:
                    relevant_pivot_highs.append(last_pivot_high)
                if last_pivot_low:
                    relevant_pivot_lows.append(last_pivot_low)
            
            indicators = []
            
            # Create separate horizontal line segments for each relevant pivot high
            for idx, price in relevant_pivot_highs:
                if idx < len(times):
                    time_val = times[idx]
                    
                    # Convert time to Unix timestamp
                    try:
                        if isinstance(time_val, datetime):
                            pivot_time = int(time_val.timestamp())
                        elif isinstance(time_val, (int, float)):
                            pivot_time = int(time_val)
                        else:
                            logger.warning(f"SMC: Unexpected time format at index {idx}: {type(time_val)}")
                            continue
                        
                        # Create a horizontal line segment around the pivot point
                        segment_start = pivot_time - segment_duration // 2
                        segment_end = pivot_time + segment_duration // 2
                        
                        indicators.append({
                            'name': f'SMC_PivotHigh_{ind_id}_{idx}',
                            'color': high_color,
                            'width': line_width,
                            'points': [
                                {'time': segment_start, 'value': float(price)},
                                {'time': segment_end, 'value': float(price)}
                            ]
                        })
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.warning(f"SMC: Error converting time at index {idx}: {e}")
                        continue
            
            # Create separate horizontal line segments for each relevant pivot low
            for idx, price in relevant_pivot_lows:
                if idx < len(times):
                    time_val = times[idx]
                    
                    # Convert time to Unix timestamp
                    try:
                        if isinstance(time_val, datetime):
                            pivot_time = int(time_val.timestamp())
                        elif isinstance(time_val, (int, float)):
                            pivot_time = int(time_val)
                        else:
                            logger.warning(f"SMC: Unexpected time format at index {idx}: {type(time_val)}")
                            continue
                        
                        # Create a horizontal line segment around the pivot point
                        segment_start = pivot_time - segment_duration // 2
                        segment_end = pivot_time + segment_duration // 2
                        
                        indicators.append({
                            'name': f'SMC_PivotLow_{ind_id}_{idx}',
                            'color': low_color,
                            'width': line_width,
                            'points': [
                                {'time': segment_start, 'value': float(price)},
                                {'time': segment_end, 'value': float(price)}
                            ]
                        })
                    except (ValueError, TypeError, AttributeError) as e:
                        logger.warning(f"SMC: Error converting time at index {idx}: {e}")
                        continue
            
            if indicators:
                logger.info(f"SMC: Successfully calculated {len(relevant_pivot_highs)} pivot highs and {len(relevant_pivot_lows)} pivot lows for indicator {ind_id} (emit_mode: {emit_mode}, total detected: {len(all_pivot_highs)} highs, {len(all_pivot_lows)} lows)")
            else:
                logger.info(f"SMC: No relevant pivots detected for indicator {ind_id} (emit_mode: {emit_mode})")
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating SMC indicator {ind_id}: {e}", exc_info=True)
        
        return []
    
    def detect_current_session(self) -> str:
        """
        Detect which trading session we're currently in based on UTC time
        
        Returns:
            'asian', 'european', or 'us'
        """
        from datetime import datetime, timezone
        
        # Get current UTC hour
        now_utc = datetime.now(timezone.utc)
        hour = now_utc.hour
        
        # Session priority (overlaps handled by priority order)
        # US session: 13:00-22:00 UTC (most important during overlap)
        if 13 <= hour < 22:
            return 'us'
        # European session: 08:00-17:00 UTC
        elif 8 <= hour < 17:
            return 'european'
        # Asian session: 00:00-09:00 UTC (plus late hours)
        else:
            return 'asian'
    
    def get_previous_session(self, current_session: str) -> str:
        """
        Get the previous trading session
        
        Args:
            current_session: 'asian', 'european', or 'us'
        
        Returns:
            Previous session name
        """
        session_order = ['asian', 'european', 'us']
        idx = session_order.index(current_session)
        prev_idx = (idx - 1) % len(session_order)
        return session_order[prev_idx]
    
    def _calculate_ohlc_indicator(self, settings: Dict, ind_id: str) -> List[Dict]:
        """Calculate OHLC indicator data"""
        try:
            logger.info(f"Starting OHLC calculation for indicator {ind_id}")
            
            # Import calculator
            try:
                from .custom_indicator_panel import PreviousSessionOHLCCalculator
                logger.debug("Successfully imported PreviousSessionOHLCCalculator")
            except ImportError as e:
                logger.error(f"Failed to import PreviousSessionOHLCCalculator: {e}")
                return []
            
            import MetaTrader5 as mt5
            
            # Resolve symbol name
            actual_symbol = self.symbol_mapper.find_symbol(self.current_symbol)
            if not actual_symbol:
                actual_symbol = self.current_symbol
            logger.info(f"OHLC: Using symbol {actual_symbol} (from {self.current_symbol})")
            
            # Get session type (default to 'daily' to match Market Watch)
            session_type = settings.get('session_type', 'daily')
            
            # Auto-detect if set to 'auto'
            if session_type == 'auto':
                current_session = self.detect_current_session()
                session_type = self.get_previous_session(current_session)
                logger.info(f"OHLC: Auto-detected current={current_session}, using previous={session_type}")
            else:
                logger.info(f"OHLC: Session type = {session_type}")
            
            # Calculate OHLC
            calculator = PreviousSessionOHLCCalculator(session_type)
            if not calculator.calculate_ohlc(actual_symbol):
                logger.warning(f"OHLC calculation failed for {actual_symbol}")
                return []
            
            ohlc = calculator.get_ohlc()
            logger.info(f"OHLC values: Open={ohlc.get('open')}, High={ohlc.get('high')}, "
                       f"Low={ohlc.get('low')}, Close={ohlc.get('close')}")
            
            # Validate OHLC values - check each value individually
            has_valid_values = False
            for key in ['open', 'high', 'low', 'close']:
                val = ohlc.get(key)
                if val is not None and val != 0:
                    has_valid_values = True
                    break
            
            if not has_valid_values:
                logger.warning(f"All OHLC values are None, zero, or missing. OHLC data: {ohlc}")
                return []
            
            # Get current time range for horizontal lines
            candles = self.get_candle_data()
            if not candles or len(candles) < 2:
                logger.warning(f"Not enough candles for OHLC: {len(candles) if candles else 0}")
                return []
            
            # Ensure times are Unix timestamps (integers)
            start_time = candles[0]['time']
            end_time = candles[-1]['time']
            
            # Convert to Unix timestamp if needed (candles should already be integers, but handle edge cases)
            if isinstance(start_time, datetime):
                start_time = int(start_time.timestamp())
            elif not isinstance(start_time, int):
                # Try to convert if it's a string or other type
                try:
                    start_time = int(start_time)
                except (ValueError, TypeError):
                    logger.error(f"Invalid start_time format: {start_time} (type: {type(start_time)})")
                    return []
            
            if isinstance(end_time, datetime):
                end_time = int(end_time.timestamp())
            elif not isinstance(end_time, int):
                # Try to convert if it's a string or other type
                try:
                    end_time = int(end_time)
                except (ValueError, TypeError):
                    logger.error(f"Invalid end_time format: {end_time} (type: {type(end_time)})")
                    return []
            
            logger.info(f"OHLC time range: {start_time} to {end_time}")
            
            # Create horizontal lines for each OHLC value
            lines_data = []
            
            # Create lines for each OHLC value that is valid and enabled
            if settings.get('show_open', True):
                open_val = ohlc.get('open')
                if open_val is not None and open_val != 0:
                    try:
                        plot_value = float(open_val)
                        lines_data.append({
                            'name': f'OHLC_Open_{ind_id}',
                            'color': settings.get('open_color', '#4CAF50'),
                            'width': settings.get('line_width', 2),
                            'points': [
                                {'time': start_time, 'value': plot_value},
                                {'time': end_time, 'value': plot_value}
                            ]
                        })
                        logger.info(f"Added OHLC Open line at {open_val:.5f}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error creating Open line: {e}, value={open_val}")
            
            if settings.get('show_high', True):
                high_val = ohlc.get('high')
                if high_val is not None and high_val != 0:
                    try:
                        plot_value = float(high_val)
                        lines_data.append({
                            'name': f'OHLC_High_{ind_id}',
                            'color': settings.get('high_color', '#2196F3'),
                            'width': settings.get('line_width', 2),
                            'points': [
                                {'time': start_time, 'value': plot_value},
                                {'time': end_time, 'value': plot_value}
                            ]
                        })
                        logger.info(f"Added OHLC High line at {high_val:.5f}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error creating High line: {e}, value={high_val}")
            
            if settings.get('show_low', True):
                low_val = ohlc.get('low')
                if low_val is not None and low_val != 0:
                    try:
                        plot_value = float(low_val)
                        lines_data.append({
                            'name': f'OHLC_Low_{ind_id}',
                            'color': settings.get('low_color', '#FF9800'),
                            'width': settings.get('line_width', 2),
                            'points': [
                                {'time': start_time, 'value': plot_value},
                                {'time': end_time, 'value': plot_value}
                            ]
                        })
                        logger.info(f"Added OHLC Low line at {low_val:.5f}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error creating Low line: {e}, value={low_val}")
            
            if settings.get('show_close', True):
                close_val = ohlc.get('close')
                if close_val is not None and close_val != 0:
                    try:
                        plot_value = float(close_val)
                        lines_data.append({
                            'name': f'OHLC_Close_{ind_id}',
                            'color': settings.get('close_color', '#9C27B0'),
                            'width': settings.get('line_width', 2),
                            'points': [
                                {'time': start_time, 'value': plot_value},
                                {'time': end_time, 'value': plot_value}
                            ]
                        })
                        logger.info(f"Added OHLC Close line at {close_val:.5f}")
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error creating Close line: {e}, value={close_val}")
            
            logger.info(f"OHLC: Returning {len(lines_data)} lines")
            return lines_data
            
        except Exception as e:
            logger.error(f"Error calculating OHLC indicator: {e}", exc_info=True)
            return []
    
    def _calculate_rsi_indicator(self, times: List, rates: List[Dict], 
                                  settings: Dict[str, Any], ind_id: str) -> List[Dict]:
        """Calculate RSI indicator data with custom settings"""
        try:
            from ..indicators.rsi import RSI
            
            # Get settings
            period = settings.get('period', 14)
            overbought = settings.get('overbought', 70)
            oversold = settings.get('oversold', 30)
            color = settings.get('color', '#FF6B6B')
            line_width = settings.get('line_width', 2)
            show_levels = settings.get('show_levels', True)
            overbought_color = settings.get('overbought_color', '#FF1744')
            oversold_color = settings.get('oversold_color', '#00E676')
            
            # Calculate RSI
            rsi = RSI(period)
            rsi_values = rsi.calculate(rates)
            
            if not rsi_values:
                return []
            
            indicators = []
            
            # RSI line
            points = []
            for time_val, rsi_val in zip(times, rsi_values):
                if rsi_val is not None:
                    time_unix = int(time_val.timestamp()) if isinstance(time_val, datetime) else int(time_val)
                    points.append({'time': time_unix, 'value': float(rsi_val)})
            
            if points:
                indicators.append({
                    'name': f'RSI({period})_{ind_id}',
                    'color': color,
                    'width': line_width,
                    'points': points
                })
                
                # Add overbought/oversold levels if enabled
                if show_levels and len(points) > 0:
                    # Get time range from points
                    start_time = points[0]['time']
                    end_time = points[-1]['time']
                    
                    # Overbought level
                    indicators.append({
                        'name': f'RSI_Overbought_{ind_id}',
                        'color': overbought_color,
                        'width': 1,
                        'points': [
                            {'time': start_time, 'value': float(overbought)},
                            {'time': end_time, 'value': float(overbought)}
                        ]
                    })
                    
                    # Oversold level
                    indicators.append({
                        'name': f'RSI_Oversold_{ind_id}',
                        'color': oversold_color,
                        'width': 1,
                        'points': [
                            {'time': start_time, 'value': float(oversold)},
                            {'time': end_time, 'value': float(oversold)}
                        ]
                    })
            
            return indicators
        
        except Exception as e:
            logger.error(f"Error calculating RSI indicator: {e}", exc_info=True)
            return []
    
    def _calculate_macd_indicator(self, times: List, rates: List[Dict], 
                                   settings: Dict[str, Any], ind_id: str) -> List[Dict]:
        """Calculate MACD indicator data with custom settings"""
        try:
            from ..indicators.macd import MACD
            
            # Get settings
            fast_period = settings.get('fast_period', 12)
            slow_period = settings.get('slow_period', 26)
            signal_period = settings.get('signal_period', 9)
            macd_color = settings.get('macd_color', '#2196F3')
            signal_color = settings.get('signal_color', '#FF9800')
            histogram_color = settings.get('histogram_color', '#9E9E9E')
            line_width = settings.get('line_width', 2)
            
            # Calculate MACD
            macd = MACD(fast_period, slow_period, signal_period)
            macd_line_values = macd.calculate(rates)
            signal_line_values = macd.get_signal_line()
            histogram_values = macd.get_histogram()
            
            if not macd_line_values:
                return []
            
            indicators = []
            
            # MACD line
            macd_points = []
            for time_val, macd_val in zip(times, macd_line_values):
                if macd_val is not None:
                    time_unix = int(time_val.timestamp()) if isinstance(time_val, datetime) else int(time_val)
                    macd_points.append({'time': time_unix, 'value': float(macd_val)})
            
            if macd_points:
                indicators.append({
                    'name': f'MACD_Line_{ind_id}',
                    'color': macd_color,
                    'width': line_width,
                    'points': macd_points
                })
            
            # Signal line
            signal_points = []
            for time_val, signal_val in zip(times, signal_line_values):
                if signal_val is not None:
                    time_unix = int(time_val.timestamp()) if isinstance(time_val, datetime) else int(time_val)
                    signal_points.append({'time': time_unix, 'value': float(signal_val)})
            
            if signal_points:
                indicators.append({
                    'name': f'MACD_Signal_{ind_id}',
                    'color': signal_color,
                    'width': line_width,
                    'points': signal_points
                })
            
            # Histogram (as bars/columns)
            histogram_points = []
            for time_val, hist_val in zip(times, histogram_values):
                if hist_val is not None:
                    time_unix = int(time_val.timestamp()) if isinstance(time_val, datetime) else int(time_val)
                    histogram_points.append({'time': time_unix, 'value': float(hist_val)})
            
            if histogram_points:
                indicators.append({
                    'name': f'MACD_Histogram_{ind_id}',
                    'color': histogram_color,
                    'width': 1,
                    'points': histogram_points,
                    'type': 'histogram'  # Special type for histogram rendering
                })
            
            return indicators
        
        except Exception as e:
            logger.error(f"Error calculating MACD indicator: {e}", exc_info=True)
            return []
    
    def _calculate_bollinger_indicator(self, times: List, rates: List[Dict], 
                                       settings: Dict[str, Any], ind_id: str) -> List[Dict]:
        """Calculate Bollinger Bands indicator data with custom settings"""
        try:
            from ..indicators.bollinger_bands import BollingerBands
            
            # Get settings
            period = settings.get('period', 20)
            num_std = settings.get('num_std', 2.0)
            upper_color = settings.get('upper_color', '#FF6B6B')
            middle_color = settings.get('middle_color', '#42A5F5')
            lower_color = settings.get('lower_color', '#66BB6A')
            line_width = settings.get('line_width', 2)
            show_middle = settings.get('show_middle', True)
            
            # Calculate Bollinger Bands
            bb = BollingerBands(period, num_std)
            middle_band_values = bb.calculate(rates)
            upper_band_values = bb.get_upper_band()
            lower_band_values = bb.get_lower_band()
            
            if not middle_band_values:
                return []
            
            indicators = []
            
            # Upper band
            upper_points = []
            for time_val, upper_val in zip(times, upper_band_values):
                if upper_val is not None:
                    time_unix = int(time_val.timestamp()) if isinstance(time_val, datetime) else int(time_val)
                    upper_points.append({'time': time_unix, 'value': float(upper_val)})
            
            if upper_points:
                indicators.append({
                    'name': f'BB_Upper_{ind_id}',
                    'color': upper_color,
                    'width': line_width,
                    'points': upper_points
                })
            
            # Middle band (SMA)
            if show_middle:
                middle_points = []
                for time_val, middle_val in zip(times, middle_band_values):
                    if middle_val is not None:
                        time_unix = int(time_val.timestamp()) if isinstance(time_val, datetime) else int(time_val)
                        middle_points.append({'time': time_unix, 'value': float(middle_val)})
                
                if middle_points:
                    indicators.append({
                        'name': f'BB_Middle_{ind_id}',
                        'color': middle_color,
                        'width': line_width,
                        'points': middle_points
                    })
            
            # Lower band
            lower_points = []
            for time_val, lower_val in zip(times, lower_band_values):
                if lower_val is not None:
                    time_unix = int(time_val.timestamp()) if isinstance(time_val, datetime) else int(time_val)
                    lower_points.append({'time': time_unix, 'value': float(lower_val)})
            
            if lower_points:
                indicators.append({
                    'name': f'BB_Lower_{ind_id}',
                    'color': lower_color,
                    'width': line_width,
                    'points': lower_points
                })
            
            return indicators
        
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands indicator: {e}", exc_info=True)
            return []
    
    def add_strategy_signal(self, symbol: str, signal_type: str, price: float, 
                           timestamp: datetime, strategy_name: str):
        """Store a strategy signal for display on chart"""
        # Add signal to memory
        self.strategy_signals.append({
            'time': int(timestamp.timestamp()),
            'type': signal_type,  # 'BUY' or 'SELL'
            'price': price,
            'strategy_name': strategy_name,
            'symbol': symbol,  # NEW: Add symbol for persistence
            'timestamp': timestamp.isoformat()  # NEW: Add ISO timestamp
        })
        
        # Keep up to 1000 signals for memory safety
        if len(self.strategy_signals) > 1000:
            self.strategy_signals = self.strategy_signals[-1000:]
        
        logger.info(f"Added signal marker: {strategy_name} {signal_type} at {price} for {symbol}")
        
        # Store in PocketBase if available
        if hasattr(self, 'pb_manager') and self.pb_manager:
            try:
                self.pb_manager.store_signal(self.strategy_signals[-1])
            except Exception as e:
                logger.error(f"Error storing signal in PocketBase: {e}")
        
        # Save to file
        self.save_signals_to_file()
        
        # Refresh chart if showing signals and it's the current symbol
        if self.show_signals and symbol == self.current_symbol:
            self.refresh_chart()
    
    def get_signal_markers(self) -> List[Dict]:
        """Get signal markers for the current symbol"""
        if not self.show_signals:
            return []
        
        markers = []
        for signal in self.strategy_signals:
            markers.append({
                'time': signal['time'],
                'position': 'belowBar' if signal['type'] == 'BUY' else 'aboveBar',
                'color': '#00E676' if signal['type'] == 'BUY' else '#FF1744',
                'shape': 'arrowUp' if signal['type'] == 'BUY' else 'arrowDown',
                'text': f"{signal['strategy_name']}: {signal['type']}"
            })
        return markers
    
    def get_trade_level_markers(self) -> List[Dict]:
        """Get markers for trade entries and exits on current symbol"""
        if not self.show_trade_levels:
            return []
        
        markers = []
        
        # Get positions for current symbol
        if not self.order_manager:
            return markers
        
        try:
            # Resolve symbol name
            actual_symbol = self.symbol_mapper.find_symbol(self.current_symbol)
            if not actual_symbol:
                actual_symbol = self.current_symbol
            
            # ACTIVE POSITIONS - Show entry markers
            positions = self.order_manager.get_positions(actual_symbol)
            
            for pos in positions:
                is_buy = pos['type'] == 0
                entry_time = pos.get('time')
                
                # Convert datetime to Unix timestamp
                if entry_time:
                    if hasattr(entry_time, 'timestamp'):
                        timestamp = int(entry_time.timestamp())
                    else:
                        from datetime import datetime
                        timestamp = int(datetime.now().timestamp())
                else:
                    continue  # Skip if no timestamp
                
                # Entry marker for active trade
                markers.append({
                    'time': timestamp,
                    'position': 'belowBar' if is_buy else 'aboveBar',
                    'color': '#26a69a' if is_buy else '#ef5350',  # Green for BUY, Red for SELL
                    'shape': 'arrowUp' if is_buy else 'arrowDown',
                    'text': f"{'BUY' if is_buy else 'SELL'} @{pos['price_open']:.5f}\n{pos['volume']:.2f} lots"
                })
            
            # HISTORICAL CLOSED TRADES - Show entry and exit markers
            if hasattr(self.order_manager, 'trade_history'):
                closed_trades = self.order_manager.trade_history.get_trades_for_symbol(actual_symbol)
                
                for trade in closed_trades:
                    if trade.get('status') == 'Closed':
                        is_buy = trade.get('direction', 'BUY') == 'BUY'
                        
                        # Entry marker (historical - semi-transparent)
                        entry_time = trade.get('entry_time')
                        if entry_time:
                            if hasattr(entry_time, 'timestamp'):
                                entry_timestamp = int(entry_time.timestamp())
                            else:
                                continue
                            
                            markers.append({
                                'time': entry_timestamp,
                                'position': 'belowBar' if is_buy else 'aboveBar',
                                'color': '#26a69a80' if is_buy else '#ef535080',  # Semi-transparent
                                'shape': 'arrowUp' if is_buy else 'arrowDown',
                                'text': f"{'BUY' if is_buy else 'SELL'} @{trade['entry_price']:.5f}"
                            })
                        
                        # Exit marker (historical)
                        exit_time = trade.get('exit_time')
                        if exit_time and trade.get('exit_price'):
                            if hasattr(exit_time, 'timestamp'):
                                exit_timestamp = int(exit_time.timestamp())
                            else:
                                continue
                            
                            profit = trade.get('profit', 0.0)
                            is_profit = profit > 0
                            exit_reason = trade.get('exit_reason', 'Close')
                            
                            markers.append({
                                'time': exit_timestamp,
                                'position': 'inBar',
                                'color': '#4caf50' if is_profit else '#f44336',  # Green for profit, Red for loss
                                'shape': 'circle',
                                'text': f"{exit_reason}\n@{trade['exit_price']:.5f}\n${profit:.2f}"
                            })
            
            if markers:
                logger.debug(f"Generated {len(markers)} trade level markers for {len(positions)} active positions")
        except Exception as e:
            logger.error(f"Error getting trade level markers: {e}", exc_info=True)
        
        return markers
    
    def get_trade_level_lines(self) -> List[Dict]:
        """Get price lines for active trades on current symbol"""
        if not self.show_trade_levels:
            return []
        
        lines = []
        
        # Get positions for current symbol
        if not self.order_manager:
            return lines
        
        try:
            # Resolve symbol name
            actual_symbol = self.symbol_mapper.find_symbol(self.current_symbol)
            if not actual_symbol:
                actual_symbol = self.current_symbol
            
            positions = self.order_manager.get_positions(actual_symbol)
            
            for pos in positions:
                # Entry line
                lines.append({
                    'price': pos['price_open'],
                    'color': '#2196F3' if pos['type'] == 0 else '#FF9800',  # Blue for BUY, Orange for SELL
                    'lineWidth': 2,
                    'lineStyle': 0,  # Solid
                    'axisLabelVisible': True,
                    'title': f"Entry: {pos['ticket']} {'BUY' if pos['type'] == 0 else 'SELL'} {pos['volume']:.2f}"
                })
                
                # Stop Loss line
                if pos.get('sl', 0.0) > 0:
                    lines.append({
                        'price': pos['sl'],
                        'color': '#F44336',  # Red
                        'lineWidth': 1,
                        'lineStyle': 2,  # Dashed
                        'axisLabelVisible': True,
                        'title': f"SL: {pos['ticket']}"
                    })
                
                # Take Profit line
                if pos.get('tp', 0.0) > 0:
                    lines.append({
                        'price': pos['tp'],
                        'color': '#4CAF50',  # Green
                        'lineWidth': 1,
                        'lineStyle': 2,  # Dashed
                        'axisLabelVisible': True,
                        'title': f"TP: {pos['ticket']}"
                    })
            
            # Add historical closed trades
            if hasattr(self.order_manager, 'trade_history'):
                closed_trades = self.order_manager.trade_history.get_trades_for_symbol(actual_symbol)
                
                for trade in closed_trades:
                    if trade.get('status') == 'Closed':
                        # Entry marker (semi-transparent, large dashed)
                        lines.append({
                            'price': trade['entry_price'],
                            'color': '#2196F340' if trade['direction'] == 'BUY' else '#FF980040',
                            'lineWidth': 1,
                            'lineStyle': 3,  # Large dashed
                            'axisLabelVisible': False,
                            'title': f"Closed Entry: {trade['ticket']}"
                        })
                        
                        # Exit marker (semi-transparent, large dashed)
                        if trade.get('exit_price'):
                            profit = trade.get('profit', 0.0)
                            exit_color = '#4CAF5040' if profit > 0 else '#F4433640'
                            lines.append({
                                'price': trade['exit_price'],
                                'color': exit_color,
                                'lineWidth': 1,
                                'lineStyle': 3,
                                'axisLabelVisible': False,
                                'title': f"Exit: {trade['ticket']} ${profit:.2f}"
                            })
            
            if lines:
                logger.debug(f"Generated {len(lines)} trade level lines for {len(positions)} active positions")
        except Exception as e:
            logger.error(f"Error getting trade level lines: {e}", exc_info=True)
        
        return lines
    
    def save_signals_to_file(self):
        """Save all signals to JSON file"""
        try:
            self.signals_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Group signals by symbol
            signals_by_symbol = {}
            for signal in self.strategy_signals:
                symbol = signal.get('symbol', 'UNKNOWN')
                if symbol not in signals_by_symbol:
                    signals_by_symbol[symbol] = []
                signals_by_symbol[symbol].append(signal)
            
            with open(self.signals_file, 'w') as f:
                json.dump(signals_by_symbol, f, indent=2, default=str)
            
            logger.info(f"Saved {len(self.strategy_signals)} signals to {self.signals_file}")
        except Exception as e:
            logger.error(f"Error saving signals: {e}", exc_info=True)
    
    def load_signals_from_file(self):
        """Load signals from JSON file on startup"""
        try:
            if not self.signals_file.exists():
                logger.info("No signals file found, starting fresh")
                return
            
            with open(self.signals_file, 'r') as f:
                signals_by_symbol = json.load(f)
            
            # Flatten back to list
            self.strategy_signals = []
            for symbol, signals in signals_by_symbol.items():
                self.strategy_signals.extend(signals)
            
            logger.info(f"Loaded {len(self.strategy_signals)} signals from {self.signals_file}")
        except Exception as e:
            logger.error(f"Error loading signals: {e}", exc_info=True)
    
    def update_chart_data(self):
        """Public method to trigger chart update (called by timers, etc.)"""
        self.refresh_chart()
    
    def update_tick(self, symbol: str, tick_data: Dict):
        """
        Handle tick updates (called by main window for real-time updates)
        For TradingView lightweight charts, we batch updates on timer refresh
        """
        # For now, we don't need to do anything per-tick
        # The chart will refresh on timer intervals
        pass
    
    def update_symbol_list(self):
        """Update the symbol list from MT5 (called when connected to MT5)"""
        if not self.mt5 or not self.mt5.is_connected():
            logger.debug("MT5 not connected, cannot update symbol list")
            return
        
        try:
            # Get available symbols from MT5
            symbols = self.mt5.get_available_symbols()
            if symbols:
                current_items = [self.symbol_combo.itemText(i) for i in range(self.symbol_combo.count())]
                
                # Add any new symbols that aren't in the list
                new_symbols = [s for s in symbols if s not in current_items]
                if new_symbols:
                    self.symbol_combo.addItems(new_symbols[:50])  # Limit to 50 new symbols to avoid clutter
                    logger.info(f"Added {len(new_symbols[:50])} new symbols to chart")
        except Exception as e:
            logger.error(f"Error updating symbol list: {e}", exc_info=True)
    
    def import_mt5_history(self):
        """Import historical trades from MT5"""
        from PyQt6.QtWidgets import QInputDialog, QMessageBox
        from datetime import timedelta
        
        # Check if order_manager is available
        if not self.order_manager:
            QMessageBox.warning(
                self,
                "Import Not Available",
                "Order manager not available. Cannot import history."
            )
            return
        
        # Ask for time range
        days, ok = QInputDialog.getInt(
            self,
            "Import MT5 History",
            "Import trades from last N days:",
            value=30,
            min=1,
            max=365
        )
        
        if not ok:
            return
        
        try:
            date_from = datetime.now() - timedelta(days=days)
            
            # Get deals from MT5
            deals = self.mt5.get_historical_deals(date_from)
            
            if not deals:
                QMessageBox.information(
                    self,
                    "Import Complete",
                    "No historical deals found in MT5."
                )
                return
            
            # Import into trade history
            imported_count = 0
            for deal in deals:
                # Check if already exists
                if not self.order_manager.trade_history.get_trade(deal['ticket']):
                    # Add as closed trade
                    self.order_manager.trade_history.add_trade(
                        ticket=deal['ticket'],
                        strategy_name="Imported from MT5",
                        symbol=deal['symbol'],
                        entry_price=deal['price'],  # Approximate
                        entry_time=deal['time'],
                        entry_condition="Historical Import",
                        volume=deal['volume'],
                        direction=deal['type']
                    )
                    
                    # Immediately close it with the exit data
                    self.order_manager.trade_history.close_trade(
                        ticket=deal['ticket'],
                        exit_price=deal['price'],
                        exit_time=deal['time'],
                        exit_condition="MT5 History",
                        profit=deal['profit']
                    )
                    
                    imported_count += 1
            
            QMessageBox.information(
                self,
                "Import Complete",
                f"Successfully imported {imported_count} trades from MT5 history.\n"
                f"(Skipped {len(deals) - imported_count} duplicates)"
            )
            
            logger.info(f"Imported {imported_count} trades from MT5 history")
            
            # Refresh chart to show historical trades
            self.refresh_chart()
            
        except Exception as e:
            logger.error(f"Error importing MT5 history: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Import Error",
                f"Failed to import MT5 history:\n{str(e)}"
            )

