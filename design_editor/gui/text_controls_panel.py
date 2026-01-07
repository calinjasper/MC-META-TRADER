"""
Text Controls Panel
Handles font, size, style, colors, alignment, and line spacing
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout,
                             QComboBox, QSpinBox, QCheckBox, QPushButton,
                             QColorDialog, QHBoxLayout, QLabel, QDoubleSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


class TextControlsPanel(QWidget):
    """Panel for text formatting controls"""
    
    changed = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.current_properties = {}
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Font Family
        font_group = QGroupBox("Font")
        font_layout = QFormLayout()
        
        self.font_family_combo = QComboBox()
        self.font_family_combo.addItems([
            "Arial", "Times New Roman", "Courier New", "Verdana",
            "Georgia", "Palatino", "Garamond", "Comic Sans MS",
            "Impact", "Trebuchet MS", "Helvetica", "Calibri"
        ])
        self.font_family_combo.currentTextChanged.connect(self.on_changed)
        font_layout.addRow("Family:", self.font_family_combo)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 200)
        self.font_size_spin.setValue(12)
        self.font_size_spin.valueChanged.connect(self.on_changed)
        font_layout.addRow("Size:", self.font_size_spin)
        
        font_group.setLayout(font_layout)
        layout.addWidget(font_group)
        
        # Text Style
        style_group = QGroupBox("Style")
        style_layout = QVBoxLayout()
        
        self.bold_check = QCheckBox("Bold")
        self.bold_check.toggled.connect(self.on_changed)
        style_layout.addWidget(self.bold_check)
        
        self.italic_check = QCheckBox("Italic")
        self.italic_check.toggled.connect(self.on_changed)
        style_layout.addWidget(self.italic_check)
        
        self.underline_check = QCheckBox("Underline")
        self.underline_check.toggled.connect(self.on_changed)
        style_layout.addWidget(self.underline_check)
        
        style_group.setLayout(style_layout)
        layout.addWidget(style_group)
        
        # Colors
        color_group = QGroupBox("Colors")
        color_layout = QFormLayout()
        
        self.text_color_btn = QPushButton("Text Color")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        self.text_color_label = QLabel("■")
        self.text_color_label.setStyleSheet("color: black; font-size: 20px;")
        color_row = QHBoxLayout()
        color_row.addWidget(self.text_color_btn)
        color_row.addWidget(self.text_color_label)
        color_row.addStretch()
        color_layout.addRow("Text:", color_row)
        
        self.bg_color_btn = QPushButton("Background")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        self.bg_color_label = QLabel("■")
        self.bg_color_label.setStyleSheet("color: white; background-color: white; border: 1px solid black; font-size: 20px;")
        bg_row = QHBoxLayout()
        bg_row.addWidget(self.bg_color_btn)
        bg_row.addWidget(self.bg_color_label)
        bg_row.addStretch()
        color_layout.addRow("Background:", bg_row)
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # Alignment
        align_group = QGroupBox("Alignment")
        align_layout = QVBoxLayout()
        
        align_buttons_layout = QHBoxLayout()
        self.align_left_btn = QPushButton("◄")
        self.align_left_btn.setCheckable(True)
        self.align_left_btn.setChecked(True)
        self.align_left_btn.clicked.connect(lambda: self.set_alignment("left"))
        align_buttons_layout.addWidget(self.align_left_btn)
        
        self.align_center_btn = QPushButton("◄►")
        self.align_center_btn.setCheckable(True)
        self.align_center_btn.clicked.connect(lambda: self.set_alignment("center"))
        align_buttons_layout.addWidget(self.align_center_btn)
        
        self.align_right_btn = QPushButton("►")
        self.align_right_btn.setCheckable(True)
        self.align_right_btn.clicked.connect(lambda: self.set_alignment("right"))
        align_buttons_layout.addWidget(self.align_right_btn)
        
        self.align_justify_btn = QPushButton("◄►◄")
        self.align_justify_btn.setCheckable(True)
        self.align_justify_btn.clicked.connect(lambda: self.set_alignment("justify"))
        align_buttons_layout.addWidget(self.align_justify_btn)
        
        align_layout.addLayout(align_buttons_layout)
        align_group.setLayout(align_layout)
        layout.addWidget(align_group)
        
        # Line Spacing
        spacing_group = QGroupBox("Line Spacing")
        spacing_layout = QFormLayout()
        
        self.line_spacing_spin = QDoubleSpinBox()
        self.line_spacing_spin.setRange(0.5, 5.0)
        self.line_spacing_spin.setSingleStep(0.1)
        self.line_spacing_spin.setValue(1.0)
        self.line_spacing_spin.valueChanged.connect(self.on_changed)
        spacing_layout.addRow("Spacing:", self.line_spacing_spin)
        
        spacing_group.setLayout(spacing_layout)
        layout.addWidget(spacing_group)
        
        layout.addStretch()
        
        # Initialize colors
        self.text_color = QColor(0, 0, 0)
        self.bg_color = QColor(255, 255, 255)
    
    def set_alignment(self, alignment):
        """Set text alignment"""
        # Uncheck other buttons
        self.align_left_btn.setChecked(False)
        self.align_center_btn.setChecked(False)
        self.align_right_btn.setChecked(False)
        self.align_justify_btn.setChecked(False)
        
        # Check selected button
        if alignment == "left":
            self.align_left_btn.setChecked(True)
        elif alignment == "center":
            self.align_center_btn.setChecked(True)
        elif alignment == "right":
            self.align_right_btn.setChecked(True)
        elif alignment == "justify":
            self.align_justify_btn.setChecked(True)
        
        self.on_changed()
    
    def choose_text_color(self):
        """Open color dialog for text color"""
        color = QColorDialog.getColor(self.text_color, self, "Choose Text Color")
        if color.isValid():
            self.text_color = color
            self.text_color_label.setStyleSheet(
                f"color: {color.name()}; font-size: 20px;")
            self.on_changed()
    
    def choose_bg_color(self):
        """Open color dialog for background color"""
        color = QColorDialog.getColor(self.bg_color, self, "Choose Background Color")
        if color.isValid():
            self.bg_color = color
            self.bg_color_label.setStyleSheet(
                f"color: {color.name()}; background-color: {color.name()}; "
                f"border: 1px solid black; font-size: 20px;")
            self.on_changed()
    
    def on_changed(self):
        """Emit changed signal with current properties"""
        properties = {
            'font_family': self.font_family_combo.currentText(),
            'font_size': self.font_size_spin.value(),
            'bold': self.bold_check.isChecked(),
            'italic': self.italic_check.isChecked(),
            'underline': self.underline_check.isChecked(),
            'text_color': self.text_color.name(),
            'bg_color': self.bg_color.name(),
            'alignment': self.get_alignment(),
            'line_spacing': self.line_spacing_spin.value()
        }
        self.current_properties = properties
        self.changed.emit(properties)
    
    def get_alignment(self):
        """Get current alignment"""
        if self.align_left_btn.isChecked():
            return "left"
        elif self.align_center_btn.isChecked():
            return "center"
        elif self.align_right_btn.isChecked():
            return "right"
        elif self.align_justify_btn.isChecked():
            return "justify"
        return "left"
    
    def load_properties(self, properties):
        """Load properties from element"""
        if not properties:
            return
        
        self.font_family_combo.setCurrentText(properties.get('font_family', 'Arial'))
        self.font_size_spin.setValue(properties.get('font_size', 12))
        self.bold_check.setChecked(properties.get('bold', False))
        self.italic_check.setChecked(properties.get('italic', False))
        self.underline_check.setChecked(properties.get('underline', False))
        
        text_color = QColor(properties.get('text_color', '#000000'))
        if text_color.isValid():
            self.text_color = text_color
            self.text_color_label.setStyleSheet(
                f"color: {text_color.name()}; font-size: 20px;")
        
        bg_color = QColor(properties.get('bg_color', '#FFFFFF'))
        if bg_color.isValid():
            self.bg_color = bg_color
            self.bg_color_label.setStyleSheet(
                f"color: {bg_color.name()}; background-color: {bg_color.name()}; "
                f"border: 1px solid black; font-size: 20px;")
        
        self.set_alignment(properties.get('alignment', 'left'))
        self.line_spacing_spin.setValue(properties.get('line_spacing', 1.0))

