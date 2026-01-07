"""
Theme Toggle Button Component
A toggle button that switches between light and dark themes with sun/moon icons
"""

import logging
from PyQt6.QtWidgets import QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen

logger = logging.getLogger(__name__)


class ThemeToggleButton(QPushButton):
    """Toggle button for switching between light and dark themes"""
    
    theme_toggled = pyqtSignal()  # Emits when theme is toggled
    
    def __init__(self, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self._is_dark = theme_manager.get_current_theme() == "dark"
        
        # Button setup
        self.setCheckable(False)  # We'll handle state ourselves
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(48, 48)
        self.setToolTip("Toggle theme (Light/Dark)")
        
        # Accessibility
        self.setAccessibleName("Theme toggle button")
        self._update_aria_label()
        
        # Create icons
        self._create_icons()
        
        # Update icon based on current theme
        self._update_icon()
        
        # Connect theme manager signal to update button state
        self.theme_manager.theme_changed.connect(self._on_theme_changed)
        
        # Connect button click
        self.clicked.connect(self._on_button_clicked)
        
        # Set up keyboard navigation
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def _create_icons(self):
        """Create sun and moon icons as QPixmaps"""
        size = 32
        
        # Sun icon (light theme - filled)
        sun_pixmap = QPixmap(size, size)
        sun_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(sun_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw sun (filled circle)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 193, 7)))  # Amber/Gold for sun
        center_x, center_y = size // 2, size // 2
        radius = 8
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        # Draw rays (simple lines around the sun) - 4 cardinal directions
        painter.setPen(QPen(QColor(255, 193, 7), 2))
        ray_length = 3
        ray_start = radius + 2
        # Right
        painter.drawLine(center_x + ray_start, center_y, center_x + ray_start + ray_length, center_y)
        # Bottom
        painter.drawLine(center_x, center_y + ray_start, center_x, center_y + ray_start + ray_length)
        # Left
        painter.drawLine(center_x - ray_start, center_y, center_x - ray_start - ray_length, center_y)
        # Top
        painter.drawLine(center_x, center_y - ray_start, center_x, center_y - ray_start - ray_length)
        
        painter.end()
        self.sun_icon_filled = QIcon(sun_pixmap)
        
        # Sun icon (outline - for dark mode)
        sun_outline_pixmap = QPixmap(size, size)
        sun_outline_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(sun_outline_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(150, 150, 150), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        painter.end()
        self.sun_icon_outline = QIcon(sun_outline_pixmap)
        
        # Moon icon (dark theme - filled)
        moon_pixmap = QPixmap(size, size)
        moon_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(moon_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(144, 202, 249)))  # Light blue for moon
        # Draw crescent moon shape using two overlapping circles
        # First draw the main circle
        painter.drawEllipse(4, 4, 20, 20)
        # Then draw a smaller offset circle with composition mode to create crescent
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        painter.setBrush(QBrush(QColor(255, 255, 255)))  # White brush for composition mode
        painter.drawEllipse(8, 2, 18, 18)
        painter.end()
        self.moon_icon_filled = QIcon(moon_pixmap)
        
        # Moon icon (outline - for light mode)
        moon_outline_pixmap = QPixmap(size, size)
        moon_outline_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(moon_outline_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(150, 150, 150), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Draw crescent moon outline using arc
        painter.drawArc(4, 4, 20, 20, 45 * 16, 270 * 16)  # Arc for crescent (45 to 315 degrees)
        painter.end()
        self.moon_icon_outline = QIcon(moon_outline_pixmap)
        
    def _update_icon(self):
        """Update button icon based on current theme"""
        if self._is_dark:
            # Dark mode: moon filled, sun outlined
            self.setIcon(self.moon_icon_filled)
            self.setToolTip("Switch to light theme")
        else:
            # Light mode: sun filled, moon outlined
            self.setIcon(self.sun_icon_filled)
            self.setToolTip("Switch to dark theme")
        
        self._update_aria_label()
        
    def _update_aria_label(self):
        """Update ARIA label for accessibility"""
        if self._is_dark:
            self.setAccessibleDescription("Switch to light theme")
        else:
            self.setAccessibleDescription("Switch to dark theme")
    
    def _on_theme_changed(self, theme: str):
        """Handle theme change from theme manager"""
        self._is_dark = (theme == "dark")
        self._update_icon()
    
    def _on_button_clicked(self):
        """Handle button click - toggle theme"""
        self.theme_manager.toggle_theme()
        self.theme_toggled.emit()
        
        # Animate button press
        self._animate_click()
    
    def _animate_click(self):
        """Animate button press for visual feedback"""
        # Visual feedback is handled by the theme manager's stylesheet
        # The button will automatically update its appearance based on theme
        pass
    
    def keyPressEvent(self, event):
        """Handle keyboard events"""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.click()
            event.accept()
        else:
            super().keyPressEvent(event)
    
    def sizeHint(self) -> QSize:
        """Return preferred size"""
        return QSize(48, 48)

