# SMC Indicator for MetaTrader 5

## Description

The SMC Indicator is a MetaTrader 5 custom indicator that visualizes Smart Money Concepts (SMC) elements on your charts. It detects and displays pivot points, Break of Structure (BOS) events, and Change of Character (CHoCH) events, helping you monitor market structure and verify trading conditions visually.

## Key Features

- **Pivot Detection**: Automatically detects fractal pivot highs and lows
- **Event Detection**: Identifies BOS and CHoCH events based on structure breaks
- **Bias Tracking**: Maintains and displays current market bias (BULLISH/BEARISH)
- **Flexible Line Drawing**: Draws horizontal lines at pivot points or event prices based on your selection
- **Visual Markers**: Shows event locations with colored markers
- **Structure Levels**: Displays last pivot high/low as reference levels

## Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `PivotLeft` | int | 2 | Number of bars to the left required for pivot confirmation |
| `PivotRight` | int | 2 | Number of bars to the right required for pivot confirmation |
| `EmitOn` | string | "NONE" | Line drawing mode: "NONE", "CHoCH", "BOS", or "BOTH" |
| `PivotHighColor` | color | Gold | Color for pivot high lines/markers |
| `PivotLowColor` | color | DodgerBlue | Color for pivot low lines/markers |
| `BOSColor` | color | Lime | Color for BOS event markers |
| `CHoCHColor` | color | Red | Color for CHoCH event markers |
| `PivotSize` | int | 3 | Size/width of pivot markers/lines |
| `EventSize` | int | 5 | Size of event markers |
| `ShowBiasLabel` | bool | true | Display bias label in top-left corner |
| `ShowStructureLevels` | bool | true | Display structure level lines (last pivot high/low) |
| `ShowDebugInfo` | bool | false | Show debug information in chart comments |
| `ShowUnconfirmedPivots` | bool | false | Show pivots immediately on M1 (without confirmation) |

## EmitOn Parameter - Line Drawing Modes

The `EmitOn` parameter controls where horizontal lines are drawn on the chart:

### "NONE" (Default)
- Draws horizontal lines at **pivot point prices**
- Gold lines for pivot highs
- Blue lines for pivot lows
- Each pivot creates a separate line segment with breaks between levels
- Best for: Identifying support/resistance levels

### "CHoCH"
- Draws horizontal lines at **CHoCH event prices only**
- Gold lines at each CHoCH event
- Each CHoCH event creates a separate line segment
- Best for: Identifying reversal points and bias changes

### "BOS"
- Draws horizontal lines at **BOS event prices only**
- Blue lines at each BOS event
- Each BOS event creates a separate line segment
- Best for: Identifying continuation points in trends

### "BOTH"
- Draws horizontal lines at **both BOS and CHoCH event prices**
- Gold lines for CHoCH events
- Blue lines for BOS events
- Both displayed simultaneously
- Best for: Complete structure analysis

## How It Works

### Pivot Detection

The indicator uses a fractal pivot algorithm:
1. Scans all bars for potential pivot points
2. A pivot high requires: higher than `PivotLeft` bars to the left AND higher/equal to `PivotRight` bars to the right
3. A pivot low requires: lower than `PivotLeft` bars to the left AND lower/equal to `PivotRight` bars to the right
4. Pivots are only confirmed after `PivotRight` bars have passed

### Event Detection

Events are detected chronologically (oldest to newest):

1. **For each bar**, the indicator finds the most recent pivot that occurred **before** that bar
2. **Checks if current bar breaks that pivot**:
   - Pivot High Break: `close > pivotHighPrice`
   - Pivot Low Break: `close < pivotLowPrice`
3. **Determines event type** based on current bias:
   - **BOS**: Break in direction of current bias (continuation)
   - **CHoCH**: Break opposite to current bias (reversal, flips bias)

### Bias Management

- Starts as "NONE"
- Changes to "BULLISH" on first upward BOS or CHoCH
- Changes to "BEARISH" on first downward BOS or CHoCH
- **Only CHoCH events flip the bias**
- BOS events maintain the current bias

### Event Classification Rules

#### When Price Breaks Above Pivot High:
```
IF currentBias == "BEARISH":
    → CHoCH (reversal, bias flips to BULLISH)
ELSE IF currentBias == "BULLISH":
    → BOS (continuation, bias stays BULLISH)
ELSE (bias is NONE):
    → BOS (establishes BULLISH bias)
```

#### When Price Breaks Below Pivot Low:
```
IF currentBias == "BULLISH":
    → CHoCH (reversal, bias flips to BEARISH)
ELSE IF currentBias == "BEARISH":
    → BOS (continuation, bias stays BEARISH)
ELSE (bias is NONE):
    → BOS (establishes BEARISH bias)
```

## Visual Elements

### Pivot Lines (EmitOn = "NONE")
- **Gold horizontal lines**: Pivot high levels
- **Blue horizontal lines**: Pivot low levels
- Each pivot creates its own line segment
- Lines extend from pivot point forward until next pivot
- Breaks appear between different pivot levels

### Event Lines (EmitOn = "CHoCH", "BOS", or "BOTH")
- **Gold horizontal lines**: CHoCH event prices (when enabled)
- **Blue horizontal lines**: BOS event prices (when enabled)
- Each event creates its own line segment
- Lines extend from event point forward until next event
- Breaks appear between different events

### Event Markers
- **Green markers**: BOS events (when EmitOn = "BOS" or "BOTH")
- **Red markers**: CHoCH events (when EmitOn = "CHoCH" or "BOTH")
- Markers appear at the exact bar where event occurred

### Structure Levels
- **Yellow dotted line**: Last pivot high level (resistance)
- **Cyan dotted line**: Last pivot low level (support)
- Only visible when `ShowStructureLevels = true`

### Bias Label
- **Top-left corner**: Shows current market bias
- **Green "BULLISH"**: Uptrend bias
- **Red "BEARISH"**: Downtrend bias
- **White "NONE"**: No bias established
- Only visible when `ShowBiasLabel = true`

## Installation

1. Copy `smc_indicator.mq5` to `MT5/MQL5/Indicators/`
2. Open MetaEditor (F4 in MT5)
3. Navigate to the indicator file
4. Compile (F7)
5. Attach to chart from Navigator panel

## Usage Examples

### Example 1: View Pivot Levels
```
EmitOn = "NONE"
```
- See all pivot high/low levels as horizontal lines
- Identify key support/resistance areas
- Monitor price reactions at pivot levels

### Example 2: Monitor Reversals
```
EmitOn = "CHoCH"
```
- See only CHoCH event levels (where bias changes)
- Identify reversal points
- Use for counter-trend entries

### Example 3: Monitor Continuations
```
EmitOn = "BOS"
```
- See only BOS event levels (trend continuation)
- Identify structure breaks in trend direction
- Use for trend-following entries

### Example 4: Complete Analysis
```
EmitOn = "BOTH"
```
- See all structure breaks (both BOS and CHoCH)
- Understand complete market structure evolution
- Get full picture of market dynamics

## Recommended Settings by Timeframe

### Higher Timeframes (H1, H4, D1)
- PivotLeft: 2-3
- PivotRight: 2-3
- EmitOn: "CHoCH" or "NONE"
- More stable, clearer structure

### Medium Timeframes (M15, M30)
- PivotLeft: 3-4
- PivotRight: 3-4
- EmitOn: "BOTH" or "NONE"
- Balanced view of structure

### Lower Timeframes (M5, M15)
- PivotLeft: 3-5
- PivotRight: 3-5
- EmitOn: "BOTH"
- More events, faster structure changes

### M1 Timeframe
- PivotLeft: 3-5
- PivotRight: 3-5
- EmitOn: "BOTH"
- ShowUnconfirmedPivots: true
- More noise, requires careful analysis

## Troubleshooting

### No Lines Appearing
- **Check**: Chart has enough bars (need at least `PivotLeft + PivotRight + 5`)
- **Solution**: Increase chart history (Properties → Common → Max bars in history)
- **Enable**: `ShowDebugInfo = true` to see what's happening

### Events Not Detected
- **Check**: Pivots are being detected (set `EmitOn = "NONE"` to verify)
- **Check**: Price has broken pivot levels
- **Enable**: `ShowDebugInfo = true` to see pivot and bias status

### Lines Not Drawing at Events
- **Verify**: EmitOn setting matches what you want to see
- **Check**: Events are being detected (look for event markers)
- **Enable**: `ShowDebugInfo = true` to diagnose

## Technical Notes

### Pivot Confirmation
- Pivots require `PivotRight` bars to pass before being confirmed
- Most recent `PivotRight` bars cannot show pivots (not yet confirmed)
- Enable `ShowUnconfirmedPivots = true` on M1 to see pivots immediately

### Event Detection Order
- Events are detected chronologically (oldest to newest)
- Bias state is maintained correctly as events are processed
- Each bar is checked against the most recent pivot that occurred before it

### Line Drawing
- Lines are drawn as horizontal segments
- Each pivot/event gets its own segment
- Breaks appear between different levels/events
- Lines extend forward from pivot/event point

## Integration with Python Strategy

This indicator uses the **same logic** as your Python `SMCStrategy`:
- Identical pivot detection algorithm
- Identical BOS/CHoCH detection logic
- Identical bias management rules

This ensures visual consistency between:
- **MT5 Indicator**: Visual monitoring and verification
- **Python Strategy**: Automated signal generation and execution

## Version Information

- **Version**: 1.01
- **File**: `smc_indicator.mq5`
- **Platform**: MetaTrader 5
- **Language**: MQL5

## Support

For issues or questions:
1. Check MT5 Experts tab for errors
2. Verify compilation succeeded (0 errors, 0 warnings)
3. Enable `ShowDebugInfo = true` for diagnostics
4. Ensure sufficient chart history is loaded

---

**Created for Smart Money Concepts (SMC) Trading System**
