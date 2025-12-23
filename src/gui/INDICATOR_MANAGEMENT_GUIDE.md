# Advanced Indicator Management UI - Implementation Guide

## Overview

The chart widget now features an advanced indicator management system that allows users to:
- Add multiple instances of the same indicator with different settings
- Configure each indicator independently through a settings dialog
- Toggle visibility of individual indicators
- Delete indicators individually
- View all active indicators in a management panel

## Architecture

### Components

1. **ChartWidget** (`src/gui/chart_widget.py`)
   - Main widget that manages the chart and indicators
   - Maintains a list of active indicator instances
   - Each indicator has: `id`, `type`, `visible`, `settings`

2. **IndicatorSettingsDialog** (`src/gui/indicator_settings_dialog.py`)
   - Modal dialog with tabbed interface
   - Three tabs: Inputs, Style, Visibility
   - Specific controls for each indicator type

3. **Indicator Types Supported**
   - EMA (Exponential Moving Average)
   - VWAP (Volume Weighted Average Price)
   - SuperTrend
   - SMC (Smart Money Concepts)

## User Interface

### Control Panel (Top Row)
```
[Symbol: ▼] [Timeframe: ▼] [Indicator: Add Indicator... ▼] [Refresh]
```

### Active Indicators Panel
```
Active Indicators:
┌─────────────────────────────────────────────────────┐
│ 👁 ⚙ 🗑 EMA (20, 50, 100, 200)                      │
│ 👁 ⚙ 🗑 VWAP (Bands: 1, 1.5, 2, Period: 10)         │
│ 👁 ⚙ 🗑 SuperTrend (Period: 10, Mult: 3.0, ...)     │
└─────────────────────────────────────────────────────┘
```

**Button Functions:**
- 👁 (Eye): Toggle indicator visibility
- ⚙ (Gear): Open settings dialog
- 🗑 (Trash): Remove indicator

## Adding Indicators

1. Click the "Add Indicator..." dropdown
2. Select an indicator type (EMA, VWAP, SuperTrend, or SMC)
3. The indicator is added with default settings
4. The indicator appears immediately on the chart and in the Active Indicators panel

## Configuring Indicators

### Opening Settings
1. Click the ⚙ button next to the indicator in the Active Indicators panel
2. The settings dialog opens with three tabs

### Inputs Tab

**EMA:**
- EMA 1 Period (default: 20)
- EMA 2 Period (default: 50)
- EMA 3 Period (default: 100)
- EMA 4 Period (default: 200)

**VWAP:**
- Standard Deviation Bands (default: "1, 1.5, 2")
- Swing Period in candles (default: 10)

**SuperTrend:**
- ATR Period (default: 10)
- ATR Multiplier (default: 3.0)
- ATR Method: "ATR (Wilder)" or "SMA(TR)"

**SMC:**
- Pivot Left Bars (default: 2)
- Pivot Right Bars (default: 2)
- Emit Signals On: "CHoCH only", "BOS only", or "Both"

### Style Tab

**Color Configuration:**
- Each indicator type has color pickers for its lines
- EMA: 4 separate colors for each period
- VWAP: Single line color
- SuperTrend: Uptrend and Downtrend colors
- SMC: Pivot High and Pivot Low colors

**Line Width:**
- Adjustable slider from 1 to 5 pixels (default: 2)

### Visibility Tab

- Single checkbox: "Show Indicator"
- Controls whether the indicator is rendered on the chart

## Default Settings

### EMA
```python
{
    'periods': [20, 50, 100, 200],
    'colors': ['#FFA726', '#42A5F5', '#AB47BC', '#66BB6A'],
    'line_width': 2,
    'visible': True
}
```

### VWAP
```python
{
    'bands': [1.0, 1.5, 2.0],
    'swing_period': 10,
    'color': '#00FFFF',
    'line_width': 2,
    'visible': True
}
```

### SuperTrend
```python
{
    'atr_period': 10,
    'atr_multiplier': 3.0,
    'atr_method': 'ATR (Wilder)',
    'up_color': '#00E676',
    'down_color': '#FF1744',
    'line_width': 2,
    'visible': True
}
```

### SMC
```python
{
    'pivot_left': 2,
    'pivot_right': 2,
    'emit_signals': 'CHoCH only (bias flips)',
    'high_color': '#FFCA28',
    'low_color': '#29B6F6',
    'line_width': 2,
    'visible': True
}
```

## Technical Implementation

### State Management

Each indicator instance is stored in `ChartWidget.active_indicators` as a dictionary:
```python
{
    'id': 'unique-uuid',          # UUID for identification
    'type': 'EMA',                # Indicator type
    'visible': True,              # Visibility state
    'settings': {...}             # Configuration settings
}
```

### Indicator Calculation Flow

1. `refresh_chart()` is called (automatically or manually)
2. `get_indicator_data()` loops through `active_indicators`
3. For each visible indicator:
   - Calls the appropriate calculation method
   - Passes custom settings from the indicator instance
   - Gets back line series data with unique names
4. All indicator data is sent to JavaScript via QWebChannel
5. TradingView Lightweight Charts renders the lines

### Unique Naming

Each indicator series gets a unique name to prevent conflicts:
- EMA: `EMA(20)_<uuid>`
- VWAP: `VWAP_<uuid>`
- SuperTrend: `SuperTrend_UP_<uuid>`, `SuperTrend_DOWN_<uuid>`

This allows multiple instances of the same indicator type to be displayed simultaneously with different settings.

## Usage Examples

### Example 1: Multiple EMA Configurations
1. Add EMA indicator with default settings (20, 50, 100, 200)
2. Add another EMA indicator
3. Open settings on the second EMA
4. Change periods to (8, 21, 55, 89) for Fibonacci EMAs
5. Change colors to differentiate from the first set
6. Now both EMA sets are visible on the chart simultaneously

### Example 2: Comparing SuperTrend Settings
1. Add SuperTrend with default settings (ATR: 10, Mult: 3.0)
2. Add another SuperTrend
3. Open settings on the second SuperTrend
4. Change to (ATR: 14, Mult: 2.5)
5. Compare which parameters work better for the current market

### Example 3: Temporary Hide Indicator
1. Click the 👁 button to toggle visibility
2. The indicator remains in the list but is not rendered
3. Click again to show it

### Example 4: Remove Unused Indicator
1. Click the 🗑 button
2. The indicator is permanently removed
3. The chart is refreshed automatically

## Code Structure

### Key Methods in ChartWidget

- `add_indicator(indicator_type)` - Create new indicator instance
- `remove_indicator(indicator_id)` - Delete indicator
- `toggle_indicator_visibility(indicator_id)` - Show/hide indicator
- `open_indicator_settings(indicator_id)` - Open settings dialog
- `update_indicator_list_ui()` - Refresh the indicator panel UI
- `get_default_indicator_settings(indicator_type)` - Get default config
- `get_indicator_label(indicator)` - Format display label
- `get_indicator_data()` - Calculate all visible indicators
- `_calculate_ema_indicator(times, rates, settings, ind_id)` - EMA calculation
- `_calculate_vwap_indicator(times, rates, settings, ind_id)` - VWAP calculation
- `_calculate_supertrend_indicator(times, rates, settings, ind_id)` - SuperTrend calculation
- `_calculate_smc_indicator(times, rates, settings, ind_id)` - SMC calculation

### Key Classes

**IndicatorSettingsDialog**
- `__init__(indicator_type, current_settings, parent)` - Initialize dialog
- `setup_ui()` - Create tabbed interface
- `create_inputs_tab()` - Build inputs controls
- `create_style_tab()` - Build style controls
- `create_visibility_tab()` - Build visibility controls
- `load_settings()` - Load current settings into UI
- `get_settings()` - Extract settings from UI
- `choose_color(button, index)` - Color picker handler
- Indicator-specific input methods: `ema_inputs()`, `vwap_inputs()`, etc.

## Future Enhancements

### SMC Rendering
Currently, SMC indicators return empty data as they require marker/shape rendering rather than line series. Future implementation could:
1. Add marker support to the HTML/JS chart
2. Implement pivot detection algorithm
3. Render CHoCH and BOS signals as markers on the chart

### Additional Features
- Save/load indicator configurations
- Copy settings from one indicator to another
- Indicator templates/presets
- Export indicator data to CSV
- Alert conditions based on indicator values

## Troubleshooting

### Indicator Not Showing on Chart
1. Check that the indicator is visible (👁 button should show open eye)
2. Verify that there is candle data available for the symbol
3. Check the log for calculation errors
4. Try refreshing the chart manually

### Settings Not Applying
1. Ensure you clicked "OK" in the settings dialog (not "Cancel")
2. Check the Active Indicators panel to see if the label updated
3. Try toggling visibility off and on

### Multiple Instances Not Working
1. Verify that each indicator has a unique ID in the active_indicators list
2. Check that indicator names include the UUID suffix
3. Look for JavaScript console errors in the log

## Migration Notes

The old checkbox-based system has been completely replaced. The following changes were made:

**Removed:**
- Individual checkboxes for VWAP, EMA, SuperTrend, SMC
- Boolean state variables: `show_vwap`, `show_ema`, `show_supertrend`, `show_smc`
- Toggle handler methods: `on_vwap_toggled()`, `on_ema_toggled()`, etc.

**Added:**
- Dropdown for adding indicators
- Active indicators list (`self.active_indicators`)
- Indicator management panel with scroll area
- Individual indicator row widgets with buttons
- Settings dialog integration
- UUID-based indicator identification
- Custom settings support in calculation methods

All functionality has been preserved and enhanced with the new system.

