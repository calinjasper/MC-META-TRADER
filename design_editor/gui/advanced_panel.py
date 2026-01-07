"""
Advanced Panel
Handles layers, text effects, and flexbox-like layout controls
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout,
                             QCheckBox, QSpinBox, QPushButton, QColorDialog,
                             QComboBox, QHBoxLayout, QLabel, QListWidget,
                             QListWidgetItem, QDoubleSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class AdvancedPanel(QWidget):
    """Panel for advanced features"""
    
    changed = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.current_properties = {}
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Layer Management
        layer_group = QGroupBox("Layers")
        layer_layout = QVBoxLayout()
        
        self.layer_list = QListWidget()
        self.layer_list.setMaximumHeight(100)
        self.layer_list.itemClicked.connect(self.on_layer_selected)
        layer_layout.addWidget(self.layer_list)
        
        layer_buttons_layout = QHBoxLayout()
        self.move_up_btn = QPushButton("↑")
        self.move_up_btn.clicked.connect(self.move_layer_up)
        layer_buttons_layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("↓")
        self.move_down_btn.clicked.connect(self.move_layer_down)
        layer_buttons_layout.addWidget(self.move_down_btn)
        
        layer_layout.addLayout(layer_buttons_layout)
        layer_group.setLayout(layer_layout)
        layout.addWidget(layer_group)
        
        # Text Shadow
        shadow_group = QGroupBox("Text Shadow")
        shadow_layout = QFormLayout()
        
        self.shadow_enabled_check = QCheckBox("Enable Shadow")
        self.shadow_enabled_check.toggled.connect(self.on_changed)
        shadow_layout.addRow(self.shadow_enabled_check)
        
        self.shadow_offset_x_spin = QSpinBox()
        self.shadow_offset_x_spin.setRange(-50, 50)
        self.shadow_offset_x_spin.setValue(2)
        self.shadow_offset_x_spin.valueChanged.connect(self.on_changed)
        shadow_layout.addRow("Offset X:", self.shadow_offset_x_spin)
        
        self.shadow_offset_y_spin = QSpinBox()
        self.shadow_offset_y_spin.setRange(-50, 50)
        self.shadow_offset_y_spin.setValue(2)
        self.shadow_offset_y_spin.valueChanged.connect(self.on_changed)
        shadow_layout.addRow("Offset Y:", self.shadow_offset_y_spin)
        
        self.shadow_blur_spin = QSpinBox()
        self.shadow_blur_spin.setRange(0, 20)
        self.shadow_blur_spin.setValue(4)
        self.shadow_blur_spin.valueChanged.connect(self.on_changed)
        shadow_layout.addRow("Blur:", self.shadow_blur_spin)
        
        self.shadow_color_btn = QPushButton("Shadow Color")
        self.shadow_color_btn.clicked.connect(self.choose_shadow_color)
        self.shadow_color_label = QLabel("■")
        self.shadow_color_label.setStyleSheet("color: black; font-size: 20px;")
        shadow_color_row = QHBoxLayout()
        shadow_color_row.addWidget(self.shadow_color_btn)
        shadow_color_row.addWidget(self.shadow_color_label)
        shadow_color_row.addStretch()
        shadow_layout.addRow("Color:", shadow_color_row)
        
        self.shadow_opacity_spin = QDoubleSpinBox()
        self.shadow_opacity_spin.setRange(0.0, 1.0)
        self.shadow_opacity_spin.setSingleStep(0.1)
        self.shadow_opacity_spin.setValue(0.5)
        self.shadow_opacity_spin.valueChanged.connect(self.on_changed)
        shadow_layout.addRow("Opacity:", self.shadow_opacity_spin)
        
        shadow_group.setLayout(shadow_layout)
        layout.addWidget(shadow_group)
        
        # Text Outline
        outline_group = QGroupBox("Text Outline")
        outline_layout = QFormLayout()
        
        self.outline_enabled_check = QCheckBox("Enable Outline")
        self.outline_enabled_check.toggled.connect(self.on_changed)
        outline_layout.addRow(self.outline_enabled_check)
        
        self.outline_width_spin = QSpinBox()
        self.outline_width_spin.setRange(1, 20)
        self.outline_width_spin.setValue(1)
        self.outline_width_spin.valueChanged.connect(self.on_changed)
        outline_layout.addRow("Width:", self.outline_width_spin)
        
        self.outline_color_btn = QPushButton("Outline Color")
        self.outline_color_btn.clicked.connect(self.choose_outline_color)
        self.outline_color_label = QLabel("■")
        self.outline_color_label.setStyleSheet("color: black; font-size: 20px;")
        outline_color_row = QHBoxLayout()
        outline_color_row.addWidget(self.outline_color_btn)
        outline_color_row.addWidget(self.outline_color_label)
        outline_color_row.addStretch()
        outline_layout.addRow("Color:", outline_color_row)
        
        outline_group.setLayout(outline_layout)
        layout.addWidget(outline_group)
        
        # Text Glow
        glow_group = QGroupBox("Text Glow")
        glow_layout = QFormLayout()
        
        self.glow_enabled_check = QCheckBox("Enable Glow")
        self.glow_enabled_check.toggled.connect(self.on_changed)
        glow_layout.addRow(self.glow_enabled_check)
        
        self.glow_radius_spin = QSpinBox()
        self.glow_radius_spin.setRange(0, 50)
        self.glow_radius_spin.setValue(10)
        self.glow_radius_spin.valueChanged.connect(self.on_changed)
        glow_layout.addRow("Radius:", self.glow_radius_spin)
        
        self.glow_color_btn = QPushButton("Glow Color")
        self.glow_color_btn.clicked.connect(self.choose_glow_color)
        self.glow_color_label = QLabel("■")
        self.glow_color_label.setStyleSheet("color: yellow; font-size: 20px;")
        glow_color_row = QHBoxLayout()
        glow_color_row.addWidget(self.glow_color_btn)
        glow_color_row.addWidget(self.glow_color_label)
        glow_color_row.addStretch()
        glow_layout.addRow("Color:", glow_color_row)
        
        self.glow_intensity_spin = QDoubleSpinBox()
        self.glow_intensity_spin.setRange(0.0, 1.0)
        self.glow_intensity_spin.setSingleStep(0.1)
        self.glow_intensity_spin.setValue(0.8)
        self.glow_intensity_spin.valueChanged.connect(self.on_changed)
        glow_layout.addRow("Intensity:", self.glow_intensity_spin)
        
        glow_group.setLayout(glow_layout)
        layout.addWidget(glow_group)
        
        # Flexbox-like Layout
        flexbox_group = QGroupBox("Layout Direction")
        flexbox_layout = QFormLayout()
        
        self.flex_direction_combo = QComboBox()
        self.flex_direction_combo.addItems([
            "Row (Horizontal)",
            "Column (Vertical)",
            "Row Reverse",
            "Column Reverse"
        ])
        self.flex_direction_combo.currentIndexChanged.connect(self.on_changed)
        flexbox_layout.addRow("Direction:", self.flex_direction_combo)
        
        self.justify_content_combo = QComboBox()
        self.justify_content_combo.addItems([
            "Flex Start",
            "Flex End",
            "Center",
            "Space Between",
            "Space Around",
            "Space Evenly"
        ])
        self.justify_content_combo.currentIndexChanged.connect(self.on_changed)
        flexbox_layout.addRow("Justify:", self.justify_content_combo)
        
        self.align_items_combo = QComboBox()
        self.align_items_combo.addItems([
            "Flex Start",
            "Flex End",
            "Center",
            "Stretch",
            "Baseline"
        ])
        self.align_items_combo.currentIndexChanged.connect(self.on_changed)
        flexbox_layout.addRow("Align Items:", self.align_items_combo)
        
        flexbox_group.setLayout(flexbox_layout)
        layout.addWidget(flexbox_group)
        
        layout.addStretch()
        
        # Initialize colors
        self.shadow_color = QColor(0, 0, 0)
        self.outline_color = QColor(0, 0, 0)
        self.glow_color = QColor(255, 255, 0)
    
    def choose_shadow_color(self):
        """Open color dialog for shadow color"""
        color = QColorDialog.getColor(self.shadow_color, self, "Choose Shadow Color")
        if color.isValid():
            self.shadow_color = color
            self.shadow_color_label.setStyleSheet(
                f"color: {color.name()}; font-size: 20px;")
            self.on_changed()
    
    def choose_outline_color(self):
        """Open color dialog for outline color"""
        color = QColorDialog.getColor(self.outline_color, self, "Choose Outline Color")
        if color.isValid():
            self.outline_color = color
            self.outline_color_label.setStyleSheet(
                f"color: {color.name()}; font-size: 20px;")
            self.on_changed()
    
    def choose_glow_color(self):
        """Open color dialog for glow color"""
        color = QColorDialog.getColor(self.glow_color, self, "Choose Glow Color")
        if color.isValid():
            self.glow_color = color
            self.glow_color_label.setStyleSheet(
                f"color: {color.name()}; font-size: 20px;")
            self.on_changed()
    
    def on_changed(self):
        """Emit changed signal with current properties"""
        properties = {
            'layer': self.current_properties.get('layer', 0),
            'shadow_enabled': self.shadow_enabled_check.isChecked(),
            'shadow_offset_x': self.shadow_offset_x_spin.value(),
            'shadow_offset_y': self.shadow_offset_y_spin.value(),
            'shadow_blur': self.shadow_blur_spin.value(),
            'shadow_color': self.shadow_color.name(),
            'shadow_opacity': self.shadow_opacity_spin.value(),
            'outline_enabled': self.outline_enabled_check.isChecked(),
            'outline_width': self.outline_width_spin.value(),
            'outline_color': self.outline_color.name(),
            'glow_enabled': self.glow_enabled_check.isChecked(),
            'glow_radius': self.glow_radius_spin.value(),
            'glow_color': self.glow_color.name(),
            'glow_intensity': self.glow_intensity_spin.value(),
            'flex_direction': self.flex_direction_combo.currentIndex(),
            'justify_content': self.justify_content_combo.currentIndex(),
            'align_items': self.align_items_combo.currentIndex()
        }
        self.current_properties.update(properties)
        self.changed.emit(properties)
    
    def on_layer_selected(self, item: QListWidgetItem):
        """Handle layer selection"""
        # This would be connected to canvas to select element by layer
        pass
    
    def move_layer_up(self):
        """Move selected layer up"""
        # This would move element up in z-order
        pass
    
    def move_layer_down(self):
        """Move selected layer down"""
        # This would move element down in z-order
        pass
    
    def update_layer_list(self, elements):
        """Update the layer list from canvas elements"""
        self.layer_list.clear()
        for i, element in enumerate(elements):
            text = element.get('text', f'Element {i+1}')
            item = QListWidgetItem(f"Layer {i+1}: {text[:20]}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.layer_list.addItem(item)
    
    def load_properties(self, properties):
        """Load properties from element"""
        if not properties:
            return
        
        self.shadow_enabled_check.setChecked(properties.get('shadow_enabled', False))
        self.shadow_offset_x_spin.setValue(properties.get('shadow_offset_x', 2))
        self.shadow_offset_y_spin.setValue(properties.get('shadow_offset_y', 2))
        self.shadow_blur_spin.setValue(properties.get('shadow_blur', 4))
        
        shadow_color = QColor(properties.get('shadow_color', '#000000'))
        if shadow_color.isValid():
            self.shadow_color = shadow_color
            self.shadow_color_label.setStyleSheet(
                f"color: {shadow_color.name()}; font-size: 20px;")
        
        self.shadow_opacity_spin.setValue(properties.get('shadow_opacity', 0.5))
        
        self.outline_enabled_check.setChecked(properties.get('outline_enabled', False))
        self.outline_width_spin.setValue(properties.get('outline_width', 1))
        
        outline_color = QColor(properties.get('outline_color', '#000000'))
        if outline_color.isValid():
            self.outline_color = outline_color
            self.outline_color_label.setStyleSheet(
                f"color: {outline_color.name()}; font-size: 20px;")
        
        self.glow_enabled_check.setChecked(properties.get('glow_enabled', False))
        self.glow_radius_spin.setValue(properties.get('glow_radius', 10))
        
        glow_color = QColor(properties.get('glow_color', '#FFFF00'))
        if glow_color.isValid():
            self.glow_color = glow_color
            self.glow_color_label.setStyleSheet(
                f"color: {glow_color.name()}; font-size: 20px;")
        
        self.glow_intensity_spin.setValue(properties.get('glow_intensity', 0.8))
        
        self.flex_direction_combo.setCurrentIndex(properties.get('flex_direction', 0))
        self.justify_content_combo.setCurrentIndex(properties.get('justify_content', 0))
        self.align_items_combo.setCurrentIndex(properties.get('align_items', 0))
        
        self.current_properties['layer'] = properties.get('layer', 0)

