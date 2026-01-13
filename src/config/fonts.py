"""
Font Configuration
Centralized font configuration for the trading platform
"""

import platform
from typing import List, Tuple


def get_font_family() -> str:
    """
    Get the primary font family based on the operating system
    
    Returns:
        Font family string with fallbacks
    """
    system = platform.system()
    
    if system == "Windows":
        # Windows: Segoe UI is the modern system font
        return "Segoe UI, Inter, Roboto, Arial, sans-serif"
    elif system == "Darwin":  # macOS
        # macOS: SF Pro Display is the system font
        return "SF Pro Display, Inter, Roboto, Arial, sans-serif"
    else:  # Linux and others
        # Linux: Roboto is commonly available
        return "Roboto, Inter, Arial, sans-serif"


def get_monospace_font_family() -> str:
    """
    Get monospace font family for code/logs
    
    Returns:
        Monospace font family string with fallbacks
    """
    system = platform.system()
    
    if system == "Windows":
        return "Consolas, 'Courier New', monospace"
    elif system == "Darwin":  # macOS
        return "SF Mono, Menlo, 'Courier New', monospace"
    else:  # Linux
        return "'DejaVu Sans Mono', 'Liberation Mono', 'Courier New', monospace"


# Font Size Constants
class FontSize:
    """Font size constants for different UI elements"""
    TINY = 8      # Tooltips, hints
    SMALL = 10    # Secondary text, labels
    NORMAL = 12   # Body text, inputs
    MEDIUM = 14   # Headings, buttons
    LARGE = 18    # Section headers
    EXTRA_LARGE = 22  # Main titles


# Font Weight Constants
class FontWeight:
    """Font weight constants"""
    REGULAR = 400      # Body text, labels
    MEDIUM = 500      # Buttons, emphasized text
    SEMI_BOLD = 600   # Section headers
    BOLD = 700        # Main titles, important values


# Font Configuration Dictionary
FONT_CONFIG = {
    'family': get_font_family(),
    'monospace_family': get_monospace_font_family(),
    'sizes': {
        'tiny': FontSize.TINY,
        'small': FontSize.SMALL,
        'normal': FontSize.NORMAL,
        'medium': FontSize.MEDIUM,
        'large': FontSize.LARGE,
        'extra_large': FontSize.EXTRA_LARGE,
    },
    'weights': {
        'regular': FontWeight.REGULAR,
        'medium': FontWeight.MEDIUM,
        'semi_bold': FontWeight.SEMI_BOLD,
        'bold': FontWeight.BOLD,
    }
}


def get_stylesheet_font(size: str = 'normal', weight: str = 'regular') -> str:
    """
    Get CSS font string for stylesheets
    
    Args:
        size: Font size key ('tiny', 'small', 'normal', 'medium', 'large', 'extra_large')
        weight: Font weight key ('regular', 'medium', 'semi_bold', 'bold')
    
    Returns:
        CSS font string
    """
    font_size = FONT_CONFIG['sizes'].get(size, FontSize.NORMAL)
    font_weight = FONT_CONFIG['weights'].get(weight, FontWeight.REGULAR)
    font_family = FONT_CONFIG['family']
    
    return f"font-family: {font_family}; font-size: {font_size}pt; font-weight: {font_weight};"

