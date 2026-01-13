# SMA Indicator for MetaTrader 5

## Description

The SMA Indicator is a MetaTrader 5 custom indicator that visualizes Simple Moving Average (SMA) on your charts. It calculates the average of closing prices over a specified period, providing a smooth line that helps identify trends and potential support/resistance levels.

## Key Features

- **Simple Moving Average**: Calculates average of closing prices over specified period
- **Configurable Period**: Adjustable period from 1 to any value
- **Customizable Appearance**: Color, line width, and line style options
- **Real-time Updates**: Updates automatically as new bars form
- **Standard Calculation**: Uses standard SMA formula (sum of closes / period)

## Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `SMAPeriod` | int | 14 | Number of periods for SMA calculation |
| `SMAColor` | color | Yellow | Color for SMA line |
| `SMAWidth` | int | 2 | Width of SMA line in pixels |
| `SMAStyle` | int | 0 (Solid) | Line style: 0=Solid, 1=Dash, 2=Dot, 3=DashDot, 4=DashDotDot |
| `ShowDebugInfo` | bool | false | Show debug information in chart comments |

## How It Works

### SMA Calculation

SMA is calculated using the formula:
```
SMA = (Close[0] + Close[1] + ... + Close[Period-1]) / Period
```

Where:
- **Close[0]**: Current bar's close price
- **Close[1]**: Previous bar's close price
- **Close[Period-1]**: Close price from (Period-1) bars ago
- **Period**: Number of periods to average

### Calculation Method

- Uses closing prices from each bar
- Calculates sum of closes over the period
- Divides by period to get average
- Updates in real-time as new bars form

## Visual Elements

### SMA Line
- **Yellow solid line** (default): Main SMA line
- Shows average price over the specified period
- Smooths out price fluctuations
- Updates in real-time

## Installation

1. Copy `sma_indicator.mq5` to `MT5/MQL5/Indicators/`
2. Open MetaEditor (F4 in MT5)
3. Navigate to the indicator file
4. Compile (F7)
5. Attach to chart from Navigator panel

## Usage Examples

### Example 1: Standard SMA(14)
```
Period = 14
SMAColor = Yellow
SMAWidth = 2
SMAStyle = 0 (Solid)
```
- Common default setting
- Good for general trend identification
- Works well on most timeframes

### Example 2: Fast SMA(20)
```
SMAPeriod = 20
SMAColor = Blue
SMAWidth = 2
SMAStyle = 0 (Solid)
```
- Faster response to price changes
- Good for shorter-term trading
- Useful for entry signals

### Example 3: Slow SMA(50)
```
SMAPeriod = 50
SMAColor = Red
SMAWidth = 2
SMAStyle = 0 (Solid)
```
- Slower response to price changes
- Good for longer-term trend identification
- Useful for trend confirmation

### Example 4: Multiple SMAs
Attach multiple instances with different periods:
- SMA(20) - Fast trend
- SMA(50) - Medium trend
- SMA(200) - Long-term trend

## Recommended Settings

### For Day Trading (M1, M5)
- Period: 20-50
- Color: Bright color for visibility
- Width: 2-3 pixels
- Style: Solid

### For Swing Trading (H1, H4)
- Period: 50-200
- Color: Distinct from price bars
- Width: 2 pixels
- Style: Solid

### For Position Trading (D1)
- Period: 100-200
- Color: Subtle color
- Width: 2 pixels
- Style: Solid

## Trading Applications

### Trend Identification
- Price above SMA → Uptrend
- Price below SMA → Downtrend
- SMA slope direction → Trend strength

### Support/Resistance
- SMA acts as dynamic support/resistance
- Price bounces off SMA → Significant level
- Multiple touches → Stronger level

### Entry Signals
- Price crosses above SMA → Potential buy signal
- Price crosses below SMA → Potential sell signal
- Use with other indicators for confirmation

### Multiple SMA Crossover
- Fast SMA crosses above slow SMA → Golden cross (bullish)
- Fast SMA crosses below slow SMA → Death cross (bearish)
- Common pairs: SMA(20)/SMA(50), SMA(50)/SMA(200)

## Common Periods

### Short-term
- **SMA(9)**: Very fast, for scalping
- **SMA(20)**: Fast, for day trading
- **SMA(21)**: Common short-term period

### Medium-term
- **SMA(50)**: Medium-term trend
- **SMA(55)**: Alternative medium period
- **SMA(100)**: Longer medium-term

### Long-term
- **SMA(200)**: Long-term trend (very popular)
- **SMA(250)**: Alternative long-term period

## Troubleshooting

### SMA Not Showing
- **Check**: Chart has enough bars (need at least `Period` bars)
- **Check**: Period is valid (>= 1)
- **Solution**: Increase chart history
- **Enable**: `ShowDebugInfo = true` to see calculation status

### Incorrect SMA Values
- **Check**: Period matches your expectation
- **Check**: Indicator is using correct symbol/timeframe
- **Verify**: Compare with built-in MT5 SMA indicator

### SMA Too Slow/Fast
- **Adjust**: Decrease period for faster response
- **Adjust**: Increase period for slower response
- **Note**: Shorter periods = more responsive, more noise
- **Note**: Longer periods = less responsive, smoother

## Technical Notes

### Calculation Method
- Uses standard SMA formula
- Calculates from close prices only
- Updates on each new bar
- No lag in calculation (uses current and past bars)

### Performance
- Efficient calculation
- Minimal computational overhead
- Suitable for all timeframes
- Works with any symbol

### Line Styles
- **0 (STYLE_SOLID)**: Continuous solid line (default)
- **1 (STYLE_DASH)**: Dashed line
- **2 (STYLE_DOT)**: Dotted line
- **3 (STYLE_DASHDOT)**: Dash-dot line
- **4 (STYLE_DASHDOTDOT)**: Dash-dot-dot line

## Integration with Python Strategy

This indicator uses the **same logic** as your Python `SMA` indicator:
- Identical period calculation
- Identical formula (sum of closes / period)
- Identical update method

This ensures visual consistency between:
- **MT5 Indicator**: Visual monitoring and verification
- **Python Strategy**: Automated signal generation and execution

## Comparison with Built-in MT5 SMA

This custom indicator provides:
- **Same calculation** as built-in SMA
- **More customization** options (color, width, style)
- **Debug information** option
- **Consistency** with your Python implementation

## Version Information

- **Version**: 1.00
- **File**: `sma_indicator.mq5`
- **Platform**: MetaTrader 5
- **Language**: MQL5

## Support

For issues or questions:
1. Check MT5 Experts tab for errors
2. Verify compilation succeeded (0 errors, 0 warnings)
3. Enable `ShowDebugInfo = true` for diagnostics
4. Ensure sufficient chart history is loaded (at least `SMAPeriod` bars)
5. Compare values with built-in MT5 SMA indicator to verify accuracy

---

**Created for Simple Moving Average (SMA) Trading System**
