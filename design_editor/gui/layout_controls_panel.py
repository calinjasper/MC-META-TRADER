"""
Layout Controls Panel
Handles dimensions, position, opacity, and margins
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout,
                             QSpinBox, QSlider, QHBoxLayout, QLabel, QDoubleSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal


class LayoutControlsPanel(QWidget):
    """Panel for layout and positioning controls"""
    
    changed = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.current_properties = {}
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Dimensions
        dim_group = QGroupBox("Dimensions")
        dim_layout = QFormLayout()
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 10000)
        self.width_spin.setValue(200)
        self.width_spin.valueChanged.connect(self.on_changed)
        dim_layout.addRow("Width:", self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 10000)
        self.height_spin.setValue(100)
        self.height_spin.valueChanged.connect(self.on_changed)
        dim_layout.addRow("Height:", self.height_spin)
        
        dim_group.setLayout(dim_layout)
        layout.addWidget(dim_group)
        
        # Position
        pos_group = QGroupBox("Position")
        pos_layout = QFormLayout()
        
        self.x_spin = QSpinBox()
        self.x_spin.setRange(-10000, 10000)
        self.x_spin.setValue(0)
        self.x_spin.valueChanged.connect(self.on_changed)
        pos_layout.addRow("X:", self.x_spin)
        
        self.y_spin = QSpinBox()
        self.y_spin.setRange(-10000, 10000)
        self.y_spin.setValue(0)
        self.y_spin.valueChanged.connect(self.on_changed)
        pos_layout.addRow("Y:", self.y_spin)
        
        pos_group.setLayout(pos_layout)
        layout.addWidget(pos_group)
        
        # Opacity
        opacity_group = QGroupBox("Opacity")
        opacity_layout = QVBoxLayout()
        
        opacity_control_layout = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        opacity_control_layout.addWidget(self.opacity_slider)
        
        self.opacity_label = QLabel("100%")
        self.opacity_label.setMinimumWidth(50)
        opacity_control_layout.addWidget(self.opacity_label)
        
        opacity_layout.addLayout(opacity_control_layout)
        opacity_group.setLayout(opacity_layout)
        layout.addWidget(opacity_group)
        
        # Margins
        margin_group = QGroupBox("Margins")
        margin_layout = QFormLayout()
        
        self.margin_top_spin = QSpinBox()
        self.margin_top_spin.setRange(0, 1000)
        self.margin_top_spin.setValue(0)
        self.margin_top_spin.valueChanged.connect(self.on_changed)
        margin_layout.addRow("Top:", self.margin_top_spin)
        
        self.margin_right_spin = QSpinBox()
        self.margin_right_spin.setRange(0, 1000)
        self.margin_right_spin.setValue(0)
        self.margin_right_spin.valueChanged.connect(self.on_changed)
        margin_layout.addRow("Right:", self.margin_right_spin)
        
        self.margin_bottom_spin = QSpinBox()
        self.margin_bottom_spin.setRange(0, 1000)
        self.margin_bottom_spin.setValue(0)
        self.margin_bottom_spin.valueChanged.connect(self.on_changed)
        margin_layout.addRow("Bottom:", self.margin_bottom_spin)
        
        self.margin_left_spin = QSpinBox()
        self.margin_left_spin.setRange(0, 1000)
        self.margin_left_spin.setValue(0)
        self.margin_left_spin.valueChanged.connect(self.on_changed)
        margin_layout.addRow("Left:", self.margin_left_spin)
        
        margin_group.setLayout(margin_layout)
        layout.addWidget(margin_group)
        
        layout.addStretch()
    
    def on_opacity_changed(self, value):
        """Handle opacity slider change"""
        self.opacity_label.setText(f"{value}%")
        self.on_changed()
    
    def on_changed(self):
        """Emit changed signal with current properties"""
        properties = {
            'width': self.width_spin.value(),
            'height': self.height_spin.value(),
            'x': self.x_spin.value(),
            'y': self.y_spin.value(),
            'opacity': self.opacity_slider.value() / 100.0,
            'margin_top': self.margin_top_spin.value(),
            'margin_right': self.margin_right_spin.value(),
            'margin_bottom': self.margin_bottom_spin.value(),
            'margin_left': self.margin_left_spin.value()
        }
        self.current_properties = properties
        self.changed.emit(properties)
    
    def load_properties(self, properties):
        """Load properties from element"""
        if not properties:
            return
        
        self.width_spin.setValue(properties.get('width', 200))
        self.height_spin.setValue(properties.get('height', 100))
        self.x_spin.setValue(properties.get('x', 0))
        self.y_spin.setValue(properties.get('y', 0))
        
        opacity = int(properties.get('opacity', 1.0) * 100)
        self.opacity_slider.setValue(opacity)
        self.opacity_label.setText(f"{opacity}%")
        
        self.margin_top_spin.setValue(properties.get('margin_top', 0))
        self.margin_right_spin.setValue(properties.get('margin_right', 0))
        self.margin_bottom_spin.setValue(properties.get('margin_bottom', 0))
        self.margin_left_spin.setValue(properties.get('margin_left', 0))

