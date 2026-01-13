"""
Font Utilities
Utility functions for font management and styling
"""

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget
from typing import Optional

from ..config.fonts import (
    get_font_family, 
    get_monospace_font_family,
    FontSize, 
    FontWeight,
    FONT_CONFIG
)


def create_font(
    size: int = FontSize.NORMAL,
    weight: int = FontWeight.REGULAR,
    family: Optional[str] = None
) -> QFont:
    """
    Create a QFont object with specified properties
    
    Args:
        size: Font size in points
        weight: Font weight (400=Regular, 500=Medium, 600=SemiBold, 700=Bold)
        family: Font family (None uses default from config)
    
    Returns:
        QFont object
    """
    if family is None:
        # Extract first font from family string (before comma)
        family = get_font_family().split(',')[0].strip()
    
    font = QFont(family, size, weight)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    return font


def create_monospace_font(
    size: int = FontSize.NORMAL,
    weight: int = FontWeight.REGULAR
) -> QFont:
    """
    Create a monospace QFont object for code/logs
    
    Args:
        size: Font size in points
        weight: Font weight
    
    Returns:
        QFont object
    """
    family = get_monospace_font_family().split(',')[0].strip()
    font = QFont(family, size, weight)
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


def get_stylesheet_font_string(
    size: str = 'normal',
    weight: str = 'regular',
    family: Optional[str] = None
) -> str:
    """
    Get CSS font string for stylesheets
    
    Args:
        size: Font size key ('tiny', 'small', 'normal', 'medium', 'large', 'extra_large')
        weight: Font weight key ('regular', 'medium', 'semi_bold', 'bold')
        family: Custom font family (None uses default)
    
    Returns:
        CSS font string
    """
    if family is None:
        family = FONT_CONFIG['family']
    
    font_size = FONT_CONFIG['sizes'].get(size, FontSize.NORMAL)
    font_weight = FONT_CONFIG['weights'].get(weight, FontWeight.REGULAR)
    
    return f"font-family: {family}; font-size: {font_size}pt; font-weight: {font_weight};"


def apply_font_to_widget(
    widget: QWidget,
    size: str = 'normal',
    weight: str = 'regular',
    monospace: bool = False
) -> None:
    """
    Apply font to a widget
    
    Args:
        widget: Widget to apply font to
        size: Font size key
        weight: Font weight key
        monospace: Whether to use monospace font
    """
    font_size = FONT_CONFIG['sizes'].get(size, FontSize.NORMAL)
    font_weight = FONT_CONFIG['weights'].get(weight, FontWeight.REGULAR)
    
    if monospace:
        font = create_monospace_font(font_size, font_weight)
    else:
        font = create_font(font_size, font_weight)
    
    widget.setFont(font)


def get_base_stylesheet_font() -> str:
    """
    Get base font stylesheet string for application-wide use
    
    Returns:
        CSS font string
    """
    return get_stylesheet_font_string('normal', 'regular')

