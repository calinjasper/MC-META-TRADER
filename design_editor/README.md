# Design Editor

A comprehensive PyQt6-based text and design element editor with advanced layout controls, text effects, and precise positioning tools.

## Features

### Text Controls
- **Font Selection**: Choose from multiple font families
- **Font Size**: Adjustable from 6pt to 200pt
- **Text Styles**: Bold, Italic, and Underline toggles
- **Colors**: Text and background color pickers
- **Alignment**: Left, Center, Right, and Justify options
- **Line Spacing**: Adjustable from 0.5x to 5.0x

### Layout Controls
- **Dimensions**: Width and height adjustment (1-10000px)
- **Position**: X/Y coordinate controls with snap-to-grid
- **Opacity**: Slider control from 0% to 100%
- **Margins**: Individual controls for top, right, bottom, and left margins

### Canvas Features
- **Movable Elements**: Click and drag to reposition elements
- **Grid Display**: Toggleable grid overlay for alignment
- **Snap to Grid**: Automatic alignment to grid points
- **Rulers**: Horizontal and vertical rulers with measurements
- **Real-time Preview**: Instant visual feedback of all changes
- **Keyboard Navigation**: Arrow keys to move selected elements
- **Zoom Controls**: Mouse wheel (Ctrl) or menu options

### Advanced Features
- **Layer Management**: Visual layer list with reordering
- **Text Effects**:
  - **Shadow**: Configurable offset, blur, color, and opacity
  - **Outline**: Adjustable width and color
  - **Glow**: Radius, color, and intensity controls
- **Flexbox-like Layout**: Direction, justify content, and align items controls

### Menu System
- **File Operations**:
  - New, Open, Save, Save As
  - Export as PNG or SVG
- **Edit Functions**:
  - Undo/Redo (Ctrl+Z/Ctrl+Y)
  - Copy/Paste Style (Ctrl+Shift+C/V)
- **View Controls**:
  - Zoom In/Out/Reset
  - Toggle Grid, Snap, and Rulers
- **Help**: Documentation and About dialog

## Installation

### Requirements
- Python 3.8+
- PyQt6

### Install Dependencies

```bash
pip install PyQt6
```

## Usage

### Running the Application

```bash
python main.py
```

### Basic Workflow

1. **Add Text Element**: Right-click on canvas → "Add Text Element" or use context menu
2. **Select Element**: Click on any element to select it
3. **Adjust Properties**: Use the control panels on the left to modify:
   - Text formatting (font, size, style, colors)
   - Layout (position, size, opacity, margins)
   - Advanced effects (shadow, outline, glow)
4. **Move Elements**: Click and drag, or use arrow keys
5. **Save Your Work**: File → Save or Ctrl+S
6. **Export**: File → Export as PNG/SVG

### Keyboard Shortcuts

- **Ctrl+N**: New file
- **Ctrl+O**: Open file
- **Ctrl+S**: Save file
- **Ctrl+Shift+S**: Save As
- **Ctrl+Z**: Undo
- **Ctrl+Y**: Redo
- **Ctrl+Shift+C**: Copy style
- **Ctrl+Shift+V**: Paste style
- **Ctrl++**: Zoom in
- **Ctrl+-**: Zoom out
- **Ctrl+0**: Reset zoom
- **Delete**: Delete selected element
- **Arrow Keys**: Move selected element (hold Shift for grid snap)

### Mouse Controls

- **Left Click**: Select element
- **Left Click + Drag**: Move element
- **Right Click**: Context menu
- **Ctrl + Mouse Wheel**: Zoom in/out

## File Format

Design files are saved as JSON (`.des` extension) with the following structure:

```json
{
  "elements": [
    {
      "type": "text",
      "text": "Your text here",
      "text_properties": {
        "font_family": "Arial",
        "font_size": 12,
        "bold": false,
        "italic": false,
        "underline": false,
        "text_color": "#000000",
        "bg_color": "#FFFFFF",
        "alignment": "left",
        "line_spacing": 1.0
      },
      "layout_properties": {
        "x": 50,
        "y": 50,
        "width": 200,
        "height": 100,
        "opacity": 1.0,
        "margin_top": 0,
        "margin_right": 0,
        "margin_bottom": 0,
        "margin_left": 0
      },
      "advanced_properties": {
        "layer": 0,
        "shadow_enabled": false,
        "outline_enabled": false,
        "glow_enabled": false
      }
    }
  ],
  "zoom_level": 1.0,
  "show_grid": true,
  "snap_to_grid": true,
  "show_ruler": true
}
```

## Project Structure

```
design_editor/
├── main.py                 # Application entry point
├── gui/
│   ├── __init__.py
│   ├── main_window.py     # Main window with menus
│   ├── text_controls_panel.py    # Text formatting controls
│   ├── layout_controls_panel.py  # Layout and positioning
│   ├── canvas_widget.py           # Drawing canvas
│   └── advanced_panel.py          # Advanced features
└── README.md
```

## Features in Detail

### Text Controls Panel
- Font family dropdown with 12+ fonts
- Font size spinner (6-200pt)
- Style checkboxes (Bold, Italic, Underline)
- Color pickers with visual preview
- Alignment buttons (Left, Center, Right, Justify)
- Line spacing control

### Layout Controls Panel
- Width/Height spinners
- X/Y position controls
- Opacity slider with percentage display
- Individual margin controls (top, right, bottom, left)

### Canvas Widget
- Custom painting with QPainter
- Grid overlay with configurable size
- Rulers with measurement ticks
- Element selection and dragging
- Snap-to-grid functionality
- Zoom support with scaling
- Export to PNG and SVG

### Advanced Panel
- Layer list widget
- Text shadow effects (offset, blur, color, opacity)
- Text outline effects (width, color)
- Text glow effects (radius, color, intensity)
- Flexbox-like layout controls

## Future Enhancements

Potential features for future versions:
- Multiple element types (shapes, images, etc.)
- Gradient fills
- Text on path
- Animation support
- Template library
- Plugin system
- Collaborative editing

## License

This project is provided as-is for educational and development purposes.

## Contributing

Feel free to extend this application with additional features and improvements!

