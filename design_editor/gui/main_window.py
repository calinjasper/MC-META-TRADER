"""
Main Window for Design Editor Application
"""

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QMenuBar, QStatusBar, QMessageBox, QFileDialog,
                             QSplitter, QToolBar, QMenu, QInputDialog)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from .text_controls_panel import TextControlsPanel
from .layout_controls_panel import LayoutControlsPanel
from .canvas_widget import CanvasWidget
from .advanced_panel import AdvancedPanel
import json
import os


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.undo_stack = []
        self.redo_stack = []
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Design Editor - Untitled")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create splitter for resizable panels
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Left panel - Controls
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Text Controls Panel
        self.text_controls = TextControlsPanel()
        left_splitter.addWidget(self.text_controls)
        
        # Layout Controls Panel
        self.layout_controls = LayoutControlsPanel()
        left_splitter.addWidget(self.layout_controls)
        
        # Advanced Panel
        self.advanced_panel = AdvancedPanel()
        left_splitter.addWidget(self.advanced_panel)
        
        left_splitter.setSizes([300, 300, 200])
        main_splitter.addWidget(left_splitter)
        
        # Center - Canvas
        self.canvas = CanvasWidget()
        main_splitter.addWidget(self.canvas)
        
        # Connect signals
        self.text_controls.changed.connect(self.on_text_changed)
        self.layout_controls.changed.connect(self.on_layout_changed)
        self.advanced_panel.changed.connect(self.on_advanced_changed)
        self.canvas.element_selected.connect(self.on_element_selected)
        
        # Add context menu to canvas
        self.canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self.show_canvas_context_menu)
        
        main_splitter.setSizes([400, 1000])
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create status bar
        self.create_status_bar()
    
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # File Menu
        file_menu = menubar.addMenu('&File')
        
        new_action = QAction('&New', self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction('&Open...', self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction('&Save', self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction('Save &As...', self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self.save_as_file)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        export_png_action = QAction('Export as &PNG...', self)
        export_png_action.triggered.connect(self.export_png)
        file_menu.addAction(export_png_action)
        
        export_svg_action = QAction('Export as &SVG...', self)
        export_svg_action.triggered.connect(self.export_svg)
        file_menu.addAction(export_svg_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('E&xit', self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit Menu
        edit_menu = menubar.addMenu('&Edit')
        
        undo_action = QAction('&Undo', self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction('&Redo', self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        copy_style_action = QAction('Copy &Style', self)
        copy_style_action.setShortcut('Ctrl+Shift+C')
        copy_style_action.triggered.connect(self.copy_style)
        edit_menu.addAction(copy_style_action)
        
        paste_style_action = QAction('&Paste Style', self)
        paste_style_action.setShortcut('Ctrl+Shift+V')
        paste_style_action.triggered.connect(self.paste_style)
        edit_menu.addAction(paste_style_action)
        
        # View Menu
        view_menu = menubar.addMenu('&View')
        
        zoom_in_action = QAction('Zoom &In', self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self.zoom_in)
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction('Zoom &Out', self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self.zoom_out)
        view_menu.addAction(zoom_out_action)
        
        reset_zoom_action = QAction('&Reset Zoom', self)
        reset_zoom_action.setShortcut('Ctrl+0')
        reset_zoom_action.triggered.connect(self.reset_zoom)
        view_menu.addAction(reset_zoom_action)
        
        view_menu.addSeparator()
        
        toggle_grid_action = QAction('Show &Grid', self)
        toggle_grid_action.setCheckable(True)
        toggle_grid_action.setChecked(True)
        toggle_grid_action.triggered.connect(self.toggle_grid)
        view_menu.addAction(toggle_grid_action)
        
        toggle_snap_action = QAction('&Snap to Grid', self)
        toggle_snap_action.setCheckable(True)
        toggle_snap_action.setChecked(True)
        toggle_snap_action.triggered.connect(self.toggle_snap)
        view_menu.addAction(toggle_snap_action)
        
        toggle_ruler_action = QAction('Show &Rulers', self)
        toggle_ruler_action.setCheckable(True)
        toggle_ruler_action.setChecked(True)
        toggle_ruler_action.triggered.connect(self.toggle_ruler)
        view_menu.addAction(toggle_ruler_action)
        
        # Help Menu
        help_menu = menubar.addMenu('&Help')
        
        help_action = QAction('&Documentation', self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)
        
        about_action = QAction('&About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Add common actions to toolbar
        new_action = QAction('New', self)
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
        
        open_action = QAction('Open', self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction('Save', self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        undo_action = QAction('Undo', self)
        undo_action.triggered.connect(self.undo)
        toolbar.addAction(undo_action)
        
        redo_action = QAction('Redo', self)
        redo_action.triggered.connect(self.redo)
        toolbar.addAction(redo_action)
    
    def create_status_bar(self):
        """Create the status bar"""
        self.statusBar().showMessage('Ready')
    
    def on_text_changed(self, properties):
        """Handle text property changes"""
        self.canvas.update_selected_element_text(properties)
        self.save_state()
    
    def on_layout_changed(self, properties):
        """Handle layout property changes"""
        self.canvas.update_selected_element_layout(properties)
        self.save_state()
    
    def on_advanced_changed(self, properties):
        """Handle advanced property changes"""
        self.canvas.update_selected_element_advanced(properties)
        self.save_state()
    
    def on_element_selected(self, element):
        """Handle element selection"""
        if element:
            self.text_controls.load_properties(element.get('text_properties', {}))
            self.layout_controls.load_properties(element.get('layout_properties', {}))
            self.advanced_panel.load_properties(element.get('advanced_properties', {}))
    
    def new_file(self):
        """Create a new file"""
        self.canvas.clear()
        self.current_file = None
        self.setWindowTitle("Design Editor - Untitled")
        self.undo_stack.clear()
        self.redo_stack.clear()
    
    def open_file(self):
        """Open a file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Design File", "", "Design Files (*.des);;All Files (*)")
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                self.canvas.load_data(data)
                self.current_file = filename
                self.setWindowTitle(f"Design Editor - {os.path.basename(filename)}")
                self.undo_stack.clear()
                self.redo_stack.clear()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
    
    def save_file(self):
        """Save the current file"""
        if self.current_file:
            self.save_as_file_path(self.current_file)
        else:
            self.save_as_file()
    
    def save_as_file(self):
        """Save file with a new name"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Design File", "", "Design Files (*.des);;All Files (*)")
        if filename:
            if not filename.endswith('.des'):
                filename += '.des'
            self.save_as_file_path(filename)
            self.current_file = filename
            self.setWindowTitle(f"Design Editor - {os.path.basename(filename)}")
    
    def save_as_file_path(self, filename):
        """Save to a specific file path"""
        try:
            data = self.canvas.save_data()
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            self.statusBar().showMessage(f'Saved: {filename}', 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
    
    def export_png(self):
        """Export canvas as PNG"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export as PNG", "", "PNG Files (*.png);;All Files (*)")
        if filename:
            if not filename.endswith('.png'):
                filename += '.png'
            self.canvas.export_png(filename)
            self.statusBar().showMessage(f'Exported: {filename}', 3000)
    
    def export_svg(self):
        """Export canvas as SVG"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export as SVG", "", "SVG Files (*.svg);;All Files (*)")
        if filename:
            if not filename.endswith('.svg'):
                filename += '.svg'
            self.canvas.export_svg(filename)
            self.statusBar().showMessage(f'Exported: {filename}', 3000)
    
    def undo(self):
        """Undo last action"""
        if self.undo_stack:
            state = self.undo_stack.pop()
            self.redo_stack.append(self.canvas.save_data())
            self.canvas.load_data(state)
    
    def redo(self):
        """Redo last undone action"""
        if self.redo_stack:
            state = self.redo_stack.pop()
            self.undo_stack.append(self.canvas.save_data())
            self.canvas.load_data(state)
    
    def copy_style(self):
        """Copy style of selected element"""
        element = self.canvas.get_selected_element()
        if element:
            self.copied_style = {
                'text': element.get('text_properties', {}),
                'layout': element.get('layout_properties', {}),
                'advanced': element.get('advanced_properties', {})
            }
            self.statusBar().showMessage('Style copied', 2000)
    
    def paste_style(self):
        """Paste copied style to selected element"""
        if hasattr(self, 'copied_style'):
            element = self.canvas.get_selected_element()
            if element:
                if 'text' in self.copied_style:
                    element['text_properties'].update(self.copied_style['text'])
                if 'layout' in self.copied_style:
                    element['layout_properties'].update(self.copied_style['layout'])
                if 'advanced' in self.copied_style:
                    element['advanced_properties'].update(self.copied_style['advanced'])
                self.canvas.update()
                self.save_state()
                self.statusBar().showMessage('Style pasted', 2000)
    
    def zoom_in(self):
        """Zoom in on canvas"""
        self.canvas.zoom_in()
    
    def zoom_out(self):
        """Zoom out on canvas"""
        self.canvas.zoom_out()
    
    def reset_zoom(self):
        """Reset zoom to 100%"""
        self.canvas.reset_zoom()
    
    def toggle_grid(self, checked):
        """Toggle grid display"""
        self.canvas.set_show_grid(checked)
    
    def toggle_snap(self, checked):
        """Toggle snap to grid"""
        self.canvas.set_snap_to_grid(checked)
    
    def toggle_ruler(self, checked):
        """Toggle ruler display"""
        self.canvas.set_show_ruler(checked)
    
    def save_state(self):
        """Save current state for undo"""
        state = self.canvas.save_data()
        self.undo_stack.append(state)
        if len(self.undo_stack) > 50:  # Limit undo history
            self.undo_stack.pop(0)
        self.redo_stack.clear()
    
    def show_help(self):
        """Show help documentation"""
        QMessageBox.information(
            self, "Help",
            "Design Editor Help\n\n"
            "• Click and drag to move elements\n"
            "• Use the control panels to adjust properties\n"
            "• Right-click for context menu\n"
            "• Use Ctrl+Z/Ctrl+Y for undo/redo\n"
            "• Export your designs as PNG or SVG"
        )
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About Design Editor",
            "Design Editor v1.0\n\n"
            "A comprehensive text and design element editor\n"
            "with advanced layout controls and effects."
        )
    
    def show_canvas_context_menu(self, pos):
        """Show context menu for canvas"""
        menu = QMenu(self)
        
        add_text_action = menu.addAction("Add Text Element")
        add_text_action.triggered.connect(self.add_text_element)
        
        if self.canvas.selected_element_index >= 0:
            menu.addSeparator()
            delete_action = menu.addAction("Delete Element")
            delete_action.triggered.connect(self.canvas.delete_selected_element)
        
        menu.exec(self.canvas.mapToGlobal(pos))
    
    def add_text_element(self):
        """Add a new text element"""
        text, ok = QInputDialog.getText(self, "Add Text Element", "Enter text:")
        if ok and text:
            self.canvas.add_text_element(text)
            self.save_state()

