# VWAP Indicator for MetaTrader 5

## Description

The VWAP Indicator is a MetaTrader 5 custom indicator that visualizes Volume Weighted Average Price (VWAP) with standard deviation bands on your charts. It calculates session-based VWAP and displays it along with configurable standard deviation bands, helping you monitor price relative to volume-weighted average and identify potential support/resistance levels.

## Key Features

- **Session-Based VWAP**: Calculates VWAP for specific trading sessions (NY, London, Asia) or continuous (All)
- **Standard Deviation Bands**: Displays up to 3 configurable standard deviation bands
- **Price Calculation Options**: Use typical price (H+L+C)/3 or close price
- **Session Reset**: Automatically resets VWAP calculation at session start times
- **Visual Bands**: Color-coded bands for easy identification of price levels

## Input Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `SessionType` | string | "NY" | Trading session: "NY", "London", "Asia", or "All" |
| `UseTypicalPrice` | bool | true | Use (H+L+C)/3 for calculation, else use Close price |
| `StdBands` | string | "1.0,1.5,2.0" | Standard deviation bands (comma-separated, up to 3 values) |
| `VWAPColor` | color | Yellow | Color for VWAP line |
| `VWAPWidth` | int | 2 | Width of VWAP line |
| `Band1Color` | color | DodgerBlue | Color for first standard deviation band |
| `Band2Color` | color | Orange | Color for second standard deviation band |
| `Band3Color` | color | Red | Color for third standard deviation band |
| `BandWidth` | int | 1 | Width of band lines |
| `ShowBands` | bool | true | Show/hide standard deviation bands |
| `ShowDebugInfo` | bool | false | Show debug information in chart comments |

## Session Types

### "NY" (New York Session)
- **Start Time**: 8:00 AM ET (13:00 UTC)
- **Reset**: Daily at session start
- **Best For**: US market hours trading

### "London" (London Session)
- **Start Time**: 8:00 AM GMT (8:00 UTC)
- **Reset**: Daily at session start
- **Best For**: European market hours trading

### "Asia" (Asian Session)
- **Start Time**: 00:00 JST (0:00 UTC, approximate)
- **Reset**: Daily at session start
- **Best For**: Asian market hours trading

### "All" (Continuous)
- **No Reset**: VWAP calculates continuously from first bar
- **Best For**: Overall market analysis without session boundaries

## How It Works

### VWAP Calculation

VWAP is calculated using the formula:
```
VWAP = Σ(Price × Volume) / Σ(Volume)
```

Where:
- **Price**: Either typical price `(High + Low + Close) / 3` or `Close` price
- **Volume**: Tick volume or real volume from each bar
- **Cumulative**: Summed from session start to current bar

### Standard Deviation Bands

Bands are calculated as:
```
Upper Band = VWAP + (StdDev × StandardDeviation)
Lower Band = VWAP - (StdDev × StandardDeviation)
```

Where:
- **StandardDeviation**: Standard deviation of prices from VWAP
- **StdDev**: Multiplier from `StdBands` parameter (e.g., 1.0, 1.5, 2.0)

### Session Reset

- VWAP resets at the start of each trading session
- Cumulative values (price×volume and volume) reset to zero
- New session VWAP calculation begins from session start
- For "All" session type, VWAP never resets (continuous calculation)

## Visual Elements

### VWAP Line
- **Yellow solid line** (default): Main VWAP line
- Shows volume-weighted average price for the session
- Updates in real-time as new bars form

### Standard Deviation Bands
- **Band 1** (Blue, default): First standard deviation level
- **Band 2** (Orange, default): Second standard deviation level
- **Band 3** (Red, default): Third standard deviation level
- Bands are drawn as dotted lines above and below VWAP
- Only visible when `ShowBands = true`

## Installation

1. Copy `vwap_indicator.mq5` to `MT5/MQL5/Indicators/`
2. Open MetaEditor (F4 in MT5)
3. Navigate to the indicator file
4. Compile (F7)
5. Attach to chart from Navigator panel

## Usage Examples

### Example 1: NY Session VWAP
```
SessionType = "NY"
StdBands = "1.0,1.5,2.0"
ShowBands = true
```
- VWAP resets daily at 8:00 AM ET
- Shows 3 standard deviation bands
- Best for US market trading

### Example 2: London Session VWAP
```
SessionType = "London"
StdBands = "1.0,2.0"
ShowBands = true
```
- VWAP resets daily at 8:00 AM GMT
- Shows 2 standard deviation bands
- Best for European market trading

### Example 3: Continuous VWAP
```
SessionType = "All"
StdBands = "1.5,2.0"
ShowBands = true
```
- VWAP never resets (continuous)
- Shows 2 standard deviation bands
- Best for overall market analysis

### Example 4: Close Price VWAP
```
SessionType = "NY"
UseTypicalPrice = false
StdBands = "1.0,1.5,2.0"
```
- Uses close price instead of typical price
- May be more responsive to price changes
- Useful for specific trading strategies

## Recommended Settings

### For Day Trading (M1, M5)
- SessionType: "NY" or "London" (depending on trading hours)
- UseTypicalPrice: true
- StdBands: "1.0,1.5,2.0"
- ShowBands: true

### For Swing Trading (H1, H4)
- SessionType: "All" (continuous)
- UseTypicalPrice: true
- StdBands: "1.5,2.0"
- ShowBands: true

### For Scalping (M1)
- SessionType: "NY" or current active session
- UseTypicalPrice: false (close price for faster response)
- StdBands: "1.0,1.5"
- ShowBands: true

## Trading Applications

### Mean Reversion
- Price above upper band → potential sell signal
- Price below lower band → potential buy signal
- Price returns to VWAP → mean reversion opportunity

### Trend Following
- Price above VWAP → bullish trend
- Price below VWAP → bearish trend
- Price breaks bands → strong trend continuation

### Support/Resistance
- VWAP line acts as dynamic support/resistance
- Standard deviation bands provide additional levels
- Price reactions at these levels indicate significance

## Troubleshooting

### VWAP Not Showing
- **Check**: Chart has enough bars (need at least 2 bars)
- **Check**: Volume data is available
- **Solution**: Increase chart history
- **Enable**: `ShowDebugInfo = true` to see calculation status

### Bands Not Appearing
- **Check**: `ShowBands = true`
- **Check**: At least 2 bars of data (needed for standard deviation)
- **Check**: `StdBands` parameter is correctly formatted (comma-separated numbers)

### VWAP Not Resetting
- **Check**: SessionType is not "All"
- **Check**: Chart has data from session start time
- **Verify**: Session start time matches your timezone

### Incorrect VWAP Values
- **Check**: Volume data is correct (some symbols may have zero volume)
- **Check**: SessionType matches your trading hours
- **Enable**: `ShowDebugInfo = true` to see cumulative values

## Technical Notes

### Volume Handling
- Uses tick_volume if available, falls back to volume
- If both are zero, uses 1.0 as minimum volume
- Zero volume bars use previous VWAP value

### Standard Deviation Calculation
- Calculated from all prices in current session
- Requires at least 2 bars of data
- Updates as new bars are added to session

### Session Time Handling
- Session times are in UTC
- Automatically adjusts for timezone differences
- Handles day transitions correctly

## Integration with Python Strategy

This indicator uses the **same logic** as your Python `VWAP` indicator:
- Identical session types and start times
- Identical price calculation (typical vs close)
- Identical standard deviation band calculation
- Identical session reset logic

This ensures visual consistency between:
- **MT5 Indicator**: Visual monitoring and verification
- **Python Strategy**: Automated signal generation and execution

## Version Information

- **Version**: 1.00
- **File**: `vwap_indicator.mq5`
- **Platform**: MetaTrader 5
- **Language**: MQL5

## Support

For issues or questions:
1. Check MT5 Experts tab for errors
2. Verify compilation succeeded (0 errors, 0 warnings)
3. Enable `ShowDebugInfo = true` for diagnostics
4. Ensure sufficient chart history is loaded
5. Verify volume data is available for your symbol

---

**Created for Volume Weighted Average Price (VWAP) Trading System**
