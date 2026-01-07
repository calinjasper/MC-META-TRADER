"""
Theme Manager
Handles light and dark theme switching with comprehensive color palettes
"""

import logging
from typing import Dict, Literal
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

ThemeMode = Literal["light", "dark", "system"]


class ThemeManager(QObject):
    """Manages application themes with light and dark color palettes"""
    
    theme_changed = pyqtSignal(str)  # Emits "light" or "dark"
    
    # Light theme colors (WCAG AA compliant)
    LIGHT_COLORS = {
        # Primary backgrounds
        "background": "#FFFFFF",
        "surface": "#F5F5F5",
        "surface_variant": "#E0E0E0",
        
        # Text colors
        "text_primary": "#212121",
        "text_secondary": "#757575",
        "text_disabled": "#BDBDBD",
        "text_inverse": "#FFFFFF",
        
        # Accent/brand colors
        "primary": "#1976D2",
        "primary_variant": "#1565C0",
        "secondary": "#424242",
        "accent": "#FF9800",
        
        # Semantic colors
        "success": "#4CAF50",
        "warning": "#FF9800",
        "error": "#F44336",
        "info": "#2196F3",
        
        # Borders and dividers
        "border": "#E0E0E0",
        "border_focus": "#1976D2",
        "divider": "#BDBDBD",
        
        # Interactive states
        "hover": "#F5F5F5",
        "selected": "#E3F2FD",
        "pressed": "#BBDEFB",
        
        # Table colors
        "table_background": "#FFFFFF",
        "table_alternate": "#FAFAFA",
        "table_header": "#EEEEEE",
        "table_selected": "#E3F2FD",
        
        # Chart/widget backgrounds
        "chart_background": "#FFFFFF",
        "widget_background": "#F5F5F5",
    }
    
    # Dark theme colors (WCAG AA compliant)
    DARK_COLORS = {
        # Primary backgrounds
        "background": "#121212",
        "surface": "#1E1E1E",
        "surface_variant": "#2B2B2B",
        
        # Text colors
        "text_primary": "#FFFFFF",
        "text_secondary": "#B0B0B0",
        "text_disabled": "#666666",
        "text_inverse": "#212121",
        
        # Accent/brand colors
        "primary": "#90CAF9",
        "primary_variant": "#64B5F6",
        "secondary": "#B0B0B0",
        "accent": "#FFB74D",
        
        # Semantic colors
        "success": "#81C784",
        "warning": "#FFB74D",
        "error": "#E57373",
        "info": "#64B5F6",
        
        # Borders and dividers
        "border": "#424242",
        "border_focus": "#90CAF9",
        "divider": "#424242",
        
        # Interactive states
        "hover": "#2B2B2B",
        "selected": "#2C3E50",
        "pressed": "#1E1E1E",
        
        # Table colors
        "table_background": "#1E1E1E",
        "table_alternate": "#2B2B2B",
        "table_header": "#2B2B2B",
        "table_selected": "#2C3E50",
        
        # Chart/widget backgrounds
        "chart_background": "#121212",
        "widget_background": "#1E1E1E",
    }
    
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self._current_theme: ThemeMode = "dark"
        self._resolved_theme: Literal["light", "dark"] = "dark"
        
        # Load theme preference
        self._load_theme_preference()
        
    def _load_theme_preference(self):
        """Load theme preference from config or detect system preference"""
        if self.config:
            saved_theme = self.config.get("ui.theme", "system")
            if saved_theme in ["light", "dark"]:
                self._current_theme = saved_theme
                self._resolved_theme = saved_theme
            elif saved_theme == "system":
                self._current_theme = "system"
                self._resolved_theme = self._detect_system_preference()
        else:
            # No config, try to detect system preference
            self._current_theme = "system"
            self._resolved_theme = self._detect_system_preference()
        
        logger.info(f"ThemeManager: Loaded theme preference: {self._current_theme} (resolved: {self._resolved_theme})")
    
    def _detect_system_preference(self) -> Literal["light", "dark"]:
        """Detect system color scheme preference"""
        try:
            # On Windows, check registry or use default to dark for trading apps
            # For now, default to dark as trading applications typically use dark themes
            import platform
            if platform.system() == "Windows":
                # Could use winreg to check Windows theme, but defaulting to dark for trading apps
                return "dark"
            else:
                # On Linux/Mac, could check environment variables or use dark as default
                return "dark"
        except Exception as e:
            logger.warning(f"ThemeManager: Could not detect system preference: {e}, defaulting to dark")
            return "dark"
    
    def get_current_theme(self) -> Literal["light", "dark"]:
        """Get the currently active theme (resolved, not "system")"""
        return self._resolved_theme
    
    def get_theme_mode(self) -> ThemeMode:
        """Get the theme mode (light, dark, or system)"""
        return self._current_theme
    
    def set_theme(self, theme: ThemeMode):
        """Set the theme mode"""
        if theme == "system":
            self._current_theme = "system"
            self._resolved_theme = self._detect_system_preference()
        elif theme in ["light", "dark"]:
            self._current_theme = theme
            self._resolved_theme = theme
        else:
            logger.warning(f"ThemeManager: Invalid theme '{theme}', using dark")
            self._current_theme = "dark"
            self._resolved_theme = "dark"
        
        # Save preference
        if self.config:
            self.config.set("ui.theme", self._current_theme)
            self.config.save()
        
        # Apply theme
        self.apply_theme()
        
        # Emit signal
        self.theme_changed.emit(self._resolved_theme)
        
        logger.info(f"ThemeManager: Theme changed to {self._current_theme} (resolved: {self._resolved_theme})")
    
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        if self._resolved_theme == "light":
            self.set_theme("dark")
        else:
            self.set_theme("light")
    
    def get_colors(self) -> Dict[str, str]:
        """Get color palette for current theme"""
        if self._resolved_theme == "light":
            return self.LIGHT_COLORS.copy()
        else:
            return self.DARK_COLORS.copy()
    
    def get_color(self, key: str, default: str = "#000000") -> str:
        """Get a specific color from current theme"""
        colors = self.get_colors()
        return colors.get(key, default)
    
    def apply_theme(self):
        """Apply theme stylesheet to the entire application"""
        colors = self.get_colors()
        
        stylesheet = f"""
        /* Main Window */
        QMainWindow {{
            background-color: {colors['background']};
            color: {colors['text_primary']};
        }}
        
        /* Central Widget */
        QWidget {{
            background-color: {colors['background']};
            color: {colors['text_primary']};
        }}
        
        /* Menu Bar */
        QMenuBar {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border-bottom: 1px solid {colors['border']};
            padding: 2px;
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: 4px 8px;
            border-radius: 4px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {colors['hover']};
        }}
        
        QMenuBar::item:pressed {{
            background-color: {colors['pressed']};
        }}
        
        /* Menu */
        QMenu {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
        }}
        
        QMenu::item {{
            padding: 4px 20px;
        }}
        
        QMenu::item:selected {{
            background-color: {colors['selected']};
        }}
        
        /* Status Bar */
        QStatusBar {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border-top: 1px solid {colors['border']};
        }}
        
        /* Buttons */
        QPushButton {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 6px 12px;
            min-height: 20px;
        }}
        
        QPushButton:hover {{
            background-color: {colors['hover']};
            border-color: {colors['border_focus']};
        }}
        
        QPushButton:pressed {{
            background-color: {colors['pressed']};
        }}
        
        QPushButton:disabled {{
            background-color: {colors['surface_variant']};
            color: {colors['text_disabled']};
            border-color: {colors['border']};
        }}
        
        /* Labels */
        QLabel {{
            background-color: transparent;
            color: {colors['text_primary']};
        }}
        
        /* Line Edits */
        QLineEdit {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        
        QLineEdit:focus {{
            border-color: {colors['border_focus']};
        }}
        
        /* Text Edits */
        QTextEdit {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
        }}
        
        /* Spin Boxes */
        QSpinBox, QDoubleSpinBox {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 4px;
        }}
        
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {colors['border_focus']};
        }}
        
        /* Combo Boxes */
        QComboBox {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        
        QComboBox:focus {{
            border-color: {colors['border_focus']};
        }}
        
        QComboBox::drop-down {{
            border: none;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {colors['text_secondary']};
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            selection-background-color: {colors['selected']};
        }}
        
        /* Tab Widget */
        QTabWidget::pane {{
            background-color: {colors['background']};
            border: 1px solid {colors['border']};
        }}
        
        QTabBar::tab {{
            background-color: {colors['surface']};
            color: {colors['text_secondary']};
            border: 1px solid {colors['border']};
            padding: 8px 16px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {colors['background']};
            color: {colors['text_primary']};
            border-bottom: 2px solid {colors['primary']};
        }}
        
        QTabBar::tab:hover {{
            background-color: {colors['hover']};
        }}
        
        /* Group Boxes */
        QGroupBox {{
            border: 1px solid {colors['border']};
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            background-color: {colors['surface']};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: {colors['text_primary']};
        }}
        
        /* Scroll Bars */
        QScrollBar:vertical {{
            background-color: {colors['surface_variant']};
            width: 12px;
            border: none;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {colors['border']};
            min-height: 20px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {colors['text_secondary']};
        }}
        
        QScrollBar:horizontal {{
            background-color: {colors['surface_variant']};
            height: 12px;
            border: none;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {colors['border']};
            min-width: 20px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors['text_secondary']};
        }}
        
        /* Tables */
        QTableWidget {{
            background-color: {colors['table_background']};
            alternate-background-color: {colors['table_alternate']};
            color: {colors['text_primary']};
            gridline-color: {colors['border']};
            border: 1px solid {colors['border']};
        }}
        
        QTableWidget::item {{
            padding: 4px;
        }}
        
        QTableWidget::item:selected {{
            background-color: {colors['table_selected']};
            color: {colors['text_primary']};
        }}
        
        QHeaderView::section {{
            background-color: {colors['table_header']};
            color: {colors['text_primary']};
            padding: 6px;
            border: 1px solid {colors['border']};
            font-weight: bold;
        }}
        
        /* Checkboxes and Radio Buttons */
        QCheckBox, QRadioButton {{
            color: {colors['text_primary']};
        }}
        
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 2px solid {colors['border']};
            border-radius: 3px;
            background-color: {colors['surface']};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {colors['primary']};
            border-color: {colors['primary']};
        }}
        
        QRadioButton::indicator {{
            border-radius: 8px;
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {colors['primary']};
            border-color: {colors['primary']};
        }}
        
        /* Progress Bars */
        QProgressBar {{
            background-color: {colors['surface_variant']};
            border: 1px solid {colors['border']};
            border-radius: 4px;
            text-align: center;
            color: {colors['text_primary']};
        }}
        
        QProgressBar::chunk {{
            background-color: {colors['primary']};
            border-radius: 3px;
        }}
        
        /* Tool Tips */
        QToolTip {{
            background-color: {colors['surface']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            padding: 4px;
        }}
        """
        
        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet)
            logger.info(f"ThemeManager: Applied {self._resolved_theme} theme stylesheet")
    
    def get_stylesheet_snippet(self, widget_type: str) -> str:
        """
        Get a stylesheet snippet for a specific widget type.
        Useful for widgets that need custom styling beyond the global theme.
        """
        colors = self.get_colors()
        
        # This can be extended for specific widget types
        snippets = {
            "success_button": f"""
                QPushButton {{
                    background-color: {colors['success']};
                    color: {colors['text_inverse']};
                }}
            """,
            "error_button": f"""
                QPushButton {{
                    background-color: {colors['error']};
                    color: {colors['text_inverse']};
                }}
            """,
            "warning_button": f"""
                QPushButton {{
                    background-color: {colors['warning']};
                    color: {colors['text_inverse']};
                }}
            """,
            "primary_button": f"""
                QPushButton {{
                    background-color: {colors['primary']};
                    color: {colors['text_inverse']};
                }}
            """,
        }
        
        return snippets.get(widget_type, "")

