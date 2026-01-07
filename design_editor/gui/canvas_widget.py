"""
Canvas Widget
Main drawing area with movable elements, grid, snap, and rulers
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMenu, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QSize
from PyQt6.QtGui import (QPainter, QColor, QFont, QPen, QBrush, QPaintEvent,
                         QMouseEvent, QKeyEvent, QWheelEvent, QTextOption)
import math


class CanvasWidget(QWidget):
    """Canvas for drawing and manipulating design elements"""
    
    element_selected = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.elements = []
        self.selected_element_index = -1
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.drag_element_start_pos = QPoint()
        
        # View settings
        self.zoom_level = 1.0
        self.show_grid = True
        self.snap_to_grid = True
        self.show_ruler = True
        self.grid_size = 20
        
        # Ruler settings
        self.ruler_size = 30
        
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet("background-color: #f5f5f5;")
    
    def paintEvent(self, event: QPaintEvent):
        """Paint the canvas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Apply zoom
        painter.scale(self.zoom_level, self.zoom_level)
        
        # Draw rulers
        if self.show_ruler:
            self.draw_rulers(painter)
        
        # Draw grid
        if self.show_grid:
            self.draw_grid(painter)
        
        # Draw elements
        for i, element in enumerate(self.elements):
            self.draw_element(painter, element, i == self.selected_element_index)
    
    def draw_rulers(self, painter: QPainter):
        """Draw horizontal and vertical rulers"""
        painter.save()
        
        # Horizontal ruler
        ruler_rect = QRect(0, 0, int(self.width() / self.zoom_level), self.ruler_size)
        painter.fillRect(ruler_rect, QColor(240, 240, 240))
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRect(ruler_rect)
        
        # Vertical ruler
        ruler_rect = QRect(0, 0, self.ruler_size, int(self.height() / self.zoom_level))
        painter.fillRect(ruler_rect, QColor(240, 240, 240))
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawRect(ruler_rect)
        
        # Draw ruler ticks
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        # Horizontal ticks
        step = self.grid_size
        for x in range(self.ruler_size, int(self.width() / self.zoom_level), step):
            painter.drawLine(x, 0, x, self.ruler_size)
            if x % (step * 5) == 0:
                painter.drawText(x - 10, 0, 20, self.ruler_size, 
                                Qt.AlignmentFlag.AlignCenter, str(x))
        
        # Vertical ticks
        for y in range(self.ruler_size, int(self.height() / self.zoom_level), step):
            painter.drawLine(0, y, self.ruler_size, y)
            if y % (step * 5) == 0:
                painter.drawText(0, y - 10, self.ruler_size, 20,
                                Qt.AlignmentFlag.AlignCenter, str(y))
        
        painter.restore()
    
    def draw_grid(self, painter: QPainter):
        """Draw grid lines"""
        painter.save()
        painter.setPen(QPen(QColor(220, 220, 220), 1))
        
        width = int(self.width() / self.zoom_level)
        height = int(self.height() / self.zoom_level)
        
        # Vertical lines
        for x in range(self.ruler_size, width, self.grid_size):
            painter.drawLine(x, self.ruler_size, x, height)
        
        # Horizontal lines
        for y in range(self.ruler_size, height, self.grid_size):
            painter.drawLine(self.ruler_size, y, width, y)
        
        painter.restore()
    
    def draw_element(self, painter: QPainter, element: dict, selected: bool):
        """Draw a design element"""
        layout = element.get('layout_properties', {})
        text_props = element.get('text_properties', {})
        advanced = element.get('advanced_properties', {})
        
        x = layout.get('x', 0) + self.ruler_size
        y = layout.get('y', 0) + self.ruler_size
        width = layout.get('width', 200)
        height = layout.get('height', 100)
        opacity = layout.get('opacity', 1.0)
        
        painter.save()
        painter.setOpacity(opacity)
        
        # Apply margins
        margin_top = layout.get('margin_top', 0)
        margin_right = layout.get('margin_right', 0)
        margin_bottom = layout.get('margin_bottom', 0)
        margin_left = layout.get('margin_left', 0)
        
        content_rect = QRect(
            x + margin_left,
            y + margin_top,
            width - margin_left - margin_right,
            height - margin_top - margin_bottom
        )
        
        # Draw background
        bg_color = QColor(text_props.get('bg_color', '#FFFFFF'))
        if bg_color.alpha() > 0:
            painter.fillRect(content_rect, bg_color)
        
        # Draw text effects (shadow, outline, etc.)
        if advanced.get('shadow_enabled', False):
            self.draw_text_shadow(painter, element, content_rect)
        
        if advanced.get('outline_enabled', False):
            self.draw_text_outline(painter, element, content_rect)
        
        # Draw text
        text = element.get('text', 'Text Element')
        self.draw_text(painter, text, text_props, content_rect)
        
        # Draw selection border
        if selected:
            painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRect(x, y, width, height))
            
            # Draw resize handles
            handle_size = 8
            handles = [
                QRect(x - handle_size//2, y - handle_size//2, handle_size, handle_size),  # Top-left
                QRect(x + width - handle_size//2, y - handle_size//2, handle_size, handle_size),  # Top-right
                QRect(x - handle_size//2, y + height - handle_size//2, handle_size, handle_size),  # Bottom-left
                QRect(x + width - handle_size//2, y + height - handle_size//2, handle_size, handle_size),  # Bottom-right
            ]
            painter.setBrush(QBrush(QColor(0, 120, 215)))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            for handle in handles:
                painter.drawRect(handle)
        
        painter.restore()
    
    def draw_text(self, painter: QPainter, text: str, props: dict, rect: QRect):
        """Draw text with formatting"""
        font_family = props.get('font_family', 'Arial')
        font_size = props.get('font_size', 12)
        bold = props.get('bold', False)
        italic = props.get('italic', False)
        underline = props.get('underline', False)
        
        font = QFont(font_family, font_size)
        font.setBold(bold)
        font.setItalic(italic)
        font.setUnderline(underline)
        painter.setFont(font)
        
        text_color = QColor(props.get('text_color', '#000000'))
        painter.setPen(QPen(text_color))
        
        alignment_map = {
            'left': Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            'center': Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            'right': Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            'justify': Qt.AlignmentFlag.AlignJustify | Qt.AlignmentFlag.AlignTop
        }
        alignment = alignment_map.get(props.get('alignment', 'left'), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        
        text_option = QTextOption(alignment)
        text_option.setWrapMode(QTextOption.WrapMode.WordWrap)
        
        painter.drawText(rect, text, text_option)
    
    def draw_text_shadow(self, painter: QPainter, element: dict, rect: QRect):
        """Draw text shadow effect"""
        advanced = element.get('advanced_properties', {})
        shadow_offset_x = advanced.get('shadow_offset_x', 2)
        shadow_offset_y = advanced.get('shadow_offset_y', 2)
        shadow_blur = advanced.get('shadow_blur', 4)
        shadow_color = QColor(advanced.get('shadow_color', '#000000'))
        shadow_opacity = advanced.get('shadow_opacity', 0.5)
        
        shadow_color.setAlphaF(shadow_opacity)
        painter.setPen(QPen(shadow_color, shadow_blur))
        
        # Simplified shadow rendering
        text = element.get('text', '')
        text_props = element.get('text_properties', {})
        shadow_rect = rect.translated(shadow_offset_x, shadow_offset_y)
        self.draw_text(painter, text, text_props, shadow_rect)
    
    def draw_text_outline(self, painter: QPainter, element: dict, rect: QRect):
        """Draw text outline effect"""
        advanced = element.get('advanced_properties', {})
        outline_width = advanced.get('outline_width', 1)
        outline_color = QColor(advanced.get('outline_color', '#000000'))
        
        painter.setPen(QPen(outline_color, outline_width))
        # Outline is drawn as part of text rendering in simplified form
        # Full implementation would require more complex text path rendering
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = self.screen_to_canvas(event.pos())
            self.selected_element_index = self.find_element_at(pos)
            
            if self.selected_element_index >= 0:
                element = self.elements[self.selected_element_index]
                self.element_selected.emit(element)
                self.dragging = True
                self.drag_start_pos = pos
                layout = element.get('layout_properties', {})
                self.drag_element_start_pos = QPoint(layout.get('x', 0), layout.get('y', 0))
            
            self.update()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move"""
        pos = self.screen_to_canvas(event.pos())
        
        if self.dragging and self.selected_element_index >= 0:
            element = self.elements[self.selected_element_index]
            layout = element.get('layout_properties', {})
            
            dx = pos.x() - self.drag_start_pos.x()
            dy = pos.y() - self.drag_start_pos.y()
            
            new_x = self.drag_element_start_pos.x() + dx
            new_y = self.drag_element_start_pos.y() + dy
            
            # Snap to grid
            if self.snap_to_grid:
                new_x = round(new_x / self.grid_size) * self.grid_size
                new_y = round(new_y / self.grid_size) * self.grid_size
            
            layout['x'] = new_x
            layout['y'] = new_y
            self.update()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press"""
        if self.selected_element_index >= 0:
            element = self.elements[self.selected_element_index]
            layout = element.get('layout_properties', {})
            
            step = self.grid_size if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            
            if event.key() == Qt.Key.Key_Left:
                layout['x'] = max(0, layout.get('x', 0) - step)
                self.update()
            elif event.key() == Qt.Key.Key_Right:
                layout['x'] = layout.get('x', 0) + step
                self.update()
            elif event.key() == Qt.Key.Key_Up:
                layout['y'] = max(0, layout.get('y', 0) - step)
                self.update()
            elif event.key() == Qt.Key.Key_Down:
                layout['y'] = layout.get('y', 0) + step
                self.update()
            elif event.key() == Qt.Key.Key_Delete:
                self.delete_selected_element()
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zoom"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)
    
    def screen_to_canvas(self, pos: QPoint) -> QPoint:
        """Convert screen coordinates to canvas coordinates"""
        return QPoint(
            int(pos.x() / self.zoom_level) - self.ruler_size,
            int(pos.y() / self.zoom_level) - self.ruler_size
        )
    
    def find_element_at(self, pos: QPoint) -> int:
        """Find element at given position"""
        for i in range(len(self.elements) - 1, -1, -1):  # Check from top to bottom
            element = self.elements[i]
            layout = element.get('layout_properties', {})
            x = layout.get('x', 0)
            y = layout.get('y', 0)
            width = layout.get('width', 200)
            height = layout.get('height', 100)
            
            if x <= pos.x() <= x + width and y <= pos.y() <= y + height:
                return i
        return -1
    
    def add_text_element(self, text: str = "New Text"):
        """Add a new text element"""
        element = {
            'type': 'text',
            'text': text,
            'text_properties': {
                'font_family': 'Arial',
                'font_size': 12,
                'bold': False,
                'italic': False,
                'underline': False,
                'text_color': '#000000',
                'bg_color': '#FFFFFF',
                'alignment': 'left',
                'line_spacing': 1.0
            },
            'layout_properties': {
                'x': 50,
                'y': 50,
                'width': 200,
                'height': 100,
                'opacity': 1.0,
                'margin_top': 0,
                'margin_right': 0,
                'margin_bottom': 0,
                'margin_left': 0
            },
            'advanced_properties': {
                'layer': len(self.elements),
                'shadow_enabled': False,
                'outline_enabled': False,
                'glow_enabled': False
            }
        }
        self.elements.append(element)
        self.selected_element_index = len(self.elements) - 1
        self.element_selected.emit(element)
        self.update()
    
    def delete_selected_element(self):
        """Delete the selected element"""
        if self.selected_element_index >= 0:
            self.elements.pop(self.selected_element_index)
            self.selected_element_index = -1
            self.element_selected.emit({})
            self.update()
    
    def get_selected_element(self) -> dict:
        """Get the currently selected element"""
        if 0 <= self.selected_element_index < len(self.elements):
            return self.elements[self.selected_element_index]
        return {}
    
    def update_selected_element_text(self, properties: dict):
        """Update text properties of selected element"""
        if self.selected_element_index >= 0:
            self.elements[self.selected_element_index]['text_properties'].update(properties)
            self.update()
    
    def update_selected_element_layout(self, properties: dict):
        """Update layout properties of selected element"""
        if self.selected_element_index >= 0:
            self.elements[self.selected_element_index]['layout_properties'].update(properties)
            self.update()
    
    def update_selected_element_advanced(self, properties: dict):
        """Update advanced properties of selected element"""
        if self.selected_element_index >= 0:
            self.elements[self.selected_element_index]['advanced_properties'].update(properties)
            self.update()
    
    def clear(self):
        """Clear all elements"""
        self.elements.clear()
        self.selected_element_index = -1
        self.update()
    
    def save_data(self) -> dict:
        """Save canvas data to dictionary"""
        return {
            'elements': self.elements,
            'zoom_level': self.zoom_level,
            'show_grid': self.show_grid,
            'snap_to_grid': self.snap_to_grid,
            'show_ruler': self.show_ruler
        }
    
    def load_data(self, data: dict):
        """Load canvas data from dictionary"""
        self.elements = data.get('elements', [])
        self.zoom_level = data.get('zoom_level', 1.0)
        self.show_grid = data.get('show_grid', True)
        self.snap_to_grid = data.get('snap_to_grid', True)
        self.show_ruler = data.get('show_ruler', True)
        self.selected_element_index = -1
        self.update()
    
    def zoom_in(self):
        """Zoom in"""
        self.zoom_level = min(self.zoom_level * 1.2, 5.0)
        self.update()
    
    def zoom_out(self):
        """Zoom out"""
        self.zoom_level = max(self.zoom_level / 1.2, 0.1)
        self.update()
    
    def reset_zoom(self):
        """Reset zoom to 100%"""
        self.zoom_level = 1.0
        self.update()
    
    def set_show_grid(self, show: bool):
        """Set grid visibility"""
        self.show_grid = show
        self.update()
    
    def set_snap_to_grid(self, snap: bool):
        """Set snap to grid"""
        self.snap_to_grid = snap
    
    def set_show_ruler(self, show: bool):
        """Set ruler visibility"""
        self.show_ruler = show
        self.update()
    
    def export_png(self, filename: str):
        """Export canvas as PNG"""
        from PyQt6.QtGui import QImage
        img = QImage(self.size(), QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.white)
        painter = QPainter(img)
        self.render(painter)
        painter.end()
        img.save(filename)
    
    def export_svg(self, filename: str):
        """Export canvas as SVG"""
        try:
            from PyQt6.QtSvg import QSvgGenerator
            generator = QSvgGenerator()
            generator.setFileName(filename)
            generator.setSize(self.size())
            generator.setViewBox(QRect(QPoint(0, 0), self.size()))
            painter = QPainter(generator)
            self.render(painter)
            painter.end()
        except ImportError:
            # SVG export requires QtSvg module
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Export Error", 
                              "SVG export requires PyQt6 with QtSvg support")

