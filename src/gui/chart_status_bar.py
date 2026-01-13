"""
Chart Status Bar Component
Displays OHLC, current price, and other market information
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
import logging

from ..utils.font_utils import get_stylesheet_font_string

logger = logging.getLogger(__name__)


class ChartStatusBar(QWidget):
    """Status bar for chart displaying OHLC and market data"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.current_price = None
        self.current_ohlc = None
        self.price_change = None
        self.volume = None
        self.spread = None
    
    def setup_ui(self):
        """Setup the status bar UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(15)
        
        # Current Price
        price_font_style = get_stylesheet_font_string('normal', 'semi_bold')
        self.price_label = QLabel("Price: --")
        self.price_label.setStyleSheet(f"{price_font_style} color: #ffffff;")
        layout.addWidget(self.price_label)
        
        layout.addWidget(self._create_separator())
        
        # OHLC
        ohlc_font_style = get_stylesheet_font_string('normal', 'regular')
        self.ohlc_label = QLabel("O: --  H: --  L: --  C: --")
        self.ohlc_label.setStyleSheet(f"{ohlc_font_style} color: #cccccc;")
        layout.addWidget(self.ohlc_label)
        
        layout.addWidget(self._create_separator())
        
        # Price Change
        self.change_label = QLabel("Change: --")
        self.change_label.setStyleSheet(f"{ohlc_font_style} color: #cccccc;")
        layout.addWidget(self.change_label)
        
        layout.addWidget(self._create_separator())
        
        # Volume
        self.volume_label = QLabel("Volume: --")
        self.volume_label.setStyleSheet(f"{ohlc_font_style} color: #cccccc;")
        layout.addWidget(self.volume_label)
        
        layout.addWidget(self._create_separator())
        
        # Spread
        self.spread_label = QLabel("Spread: --")
        self.spread_label.setStyleSheet(f"{ohlc_font_style} color: #cccccc;")
        layout.addWidget(self.spread_label)
        
        layout.addStretch()
    
    def _create_separator(self) -> QLabel:
        """Create a vertical separator"""
        separator = QLabel("|")
        separator_font_style = get_stylesheet_font_string('normal', 'regular')
        separator.setStyleSheet(f"{separator_font_style} color: #666666;")
        return separator
    
    def update_price(self, bid: float = None, ask: float = None, price: float = None):
        """Update current price display"""
        if price is not None:
            self.current_price = price
            self.price_label.setText(f"Price: {price:.5f}")
        elif bid is not None and ask is not None:
            mid = (bid + ask) / 2.0
            self.current_price = mid
            self.price_label.setText(f"Price: {mid:.5f} (Bid: {bid:.5f} / Ask: {ask:.5f})")
        elif bid is not None:
            self.current_price = bid
            self.price_label.setText(f"Price: {bid:.5f}")
        elif ask is not None:
            self.current_price = ask
            self.price_label.setText(f"Price: {ask:.5f}")
    
    def update_ohlc(self, open: float, high: float, low: float, close: float):
        """Update OHLC display"""
        self.current_ohlc = {'open': open, 'high': high, 'low': low, 'close': close}
        self.ohlc_label.setText(f"O: {open:.5f}  H: {high:.5f}  L: {low:.5f}  C: {close:.5f}")
        
        # Calculate price change if we have previous close
        if self.current_price and close:
            change = close - open
            change_pct = (change / open * 100) if open != 0 else 0
            color = "#4CAF50" if change >= 0 else "#F44336"
            self.change_label.setText(f"Change: {change:+.5f} ({change_pct:+.2f}%)")
            self.change_label.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def update_volume(self, volume: float):
        """Update volume display"""
        self.volume = volume
        if volume:
            self.volume_label.setText(f"Volume: {volume:,.0f}")
        else:
            self.volume_label.setText("Volume: --")
    
    def update_spread(self, spread: float):
        """Update spread display"""
        self.spread = spread
        if spread:
            self.spread_label.setText(f"Spread: {spread:.5f}")
        else:
            self.spread_label.setText("Spread: --")
    
    def clear(self):
        """Clear all displays"""
        self.price_label.setText("Price: --")
        self.ohlc_label.setText("O: --  H: --  L: --  C: --")
        self.change_label.setText("Change: --")
        self.change_label.setStyleSheet("color: #cccccc;")
        self.volume_label.setText("Volume: --")
        self.spread_label.setText("Spread: --")
        self.current_price = None
        self.current_ohlc = None
        self.price_change = None
        self.volume = None
        self.spread = None

