"""
Grid Layout Helper
Utility functions for fixing grid layout alignment issues
"""

from PyQt6.QtWidgets import QGridLayout, QPushButton, QWidget
from PyQt6.QtCore import Qt


def fix_grid_alignment(grid_layout: QGridLayout, num_columns: int = 5, num_rows: int = 5):
    """
    Fix alignment issues in a QGridLayout with buttons
    
    Args:
        grid_layout: The QGridLayout to fix
        num_columns: Number of columns in the grid
        num_rows: Number of rows in the grid
    """
    # Set consistent spacing
    grid_layout.setSpacing(5)
    
    # Set consistent margins
    grid_layout.setContentsMargins(10, 10, 10, 10)
    
    # Set column stretch to ensure equal distribution
    for col in range(num_columns):
        grid_layout.setColumnStretch(col, 1)
        grid_layout.setColumnMinimumWidth(col, 60)
    
    # Set row stretch to ensure equal distribution
    for row in range(num_rows):
        grid_layout.setRowStretch(row, 1)
        grid_layout.setRowMinimumHeight(row, 30)
    
    # Ensure all buttons have consistent sizing
    for i in range(grid_layout.count()):
        item = grid_layout.itemAt(i)
        if item and item.widget():
            widget = item.widget()
            if isinstance(widget, QPushButton):
                # Set consistent button sizing
                widget.setMinimumSize(60, 30)
                widget.setMaximumSize(200, 50)
                widget.setSizePolicy(widget.sizePolicy().horizontalPolicy(), 
                                    widget.sizePolicy().verticalPolicy())


def create_aligned_action_grid(parent: QWidget, num_columns: int = 5, num_rows: int = 5) -> QGridLayout:
    """
    Create a properly aligned grid layout for action buttons
    
    Args:
        parent: Parent widget
        num_columns: Number of columns
        num_rows: Number of rows
        
    Returns:
        QGridLayout with proper alignment settings
    """
    grid = QGridLayout(parent)
    grid.setSpacing(5)
    grid.setContentsMargins(10, 10, 10, 10)
    
    # Set equal column stretch
    for col in range(num_columns):
        grid.setColumnStretch(col, 1)
        grid.setColumnMinimumWidth(col, 60)
    
    # Set equal row stretch
    for row in range(num_rows):
        grid.setRowStretch(row, 1)
        grid.setRowMinimumHeight(row, 30)
    
    return grid

