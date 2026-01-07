# MT5 Python Indicators

This folder contains MQL5 indicators that display Python-calculated indicator values directly on MT5 charts.

## Installation

1. **Copy the indicator file to MT5:**
   - Copy `PythonIndicators.mq5` to your MT5 installation's `MQL5/Indicators/` folder
   - Example: `C:\Program Files\MetaTrader 5\MQL5\Indicators\PythonIndicators.mq5`

2. **Compile the indicator:**
   - Open MetaEditor (F4 in MT5)
   - Open `PythonIndicators.mq5`
   - Press F7 to compile
   - Ensure there are no compilation errors

3. **Verify Python application is running:**
   - The Python application must be running and connected to MT5
   - The application will automatically write indicator values to `MQL5/Files/PythonIndicators/` folder

## Usage

1. **Open a chart** in MT5 for the symbol you want to monitor

2. **Attach the indicator:**
   - Right-click on the chart → Insert → Indicators → Custom → PythonIndicators
   - Or drag `PythonIndicators` from Navigator to the chart

3. **Configure indicators:**
   - In the indicator properties, you can:
     - Select which indicators to display (EMA, VWAP, SuperTrend, RSI, MACD, Bollinger Bands, Stochastic)
     - Customize colors and styles (in the indicator code)
     - Set symbol and timeframe filters (optional)

4. **Monitor indicators:**
   - Indicators will update in real-time as Python calculates new values
   - The indicator reads JSON files from `MQL5/Files/PythonIndicators/` folder
   - Files are named: `{Symbol}_{Timeframe}_indicators.json`

## Supported Indicators

- **EMA (50, 200)**: Exponential Moving Averages
- **VWAP**: Volume Weighted Average Price
- **SuperTrend**: SuperTrend indicator with upper/lower bands
- **RSI**: Relative Strength Index
- **MACD**: Moving Average Convergence Divergence (with signal and histogram)
- **Bollinger Bands**: Upper, Middle, and Lower bands
- **Stochastic**: %K and %D lines

## File Format

The Python application writes JSON files with the following structure:

```json
{
  "symbol": "XAUUSDm",
  "timeframe": "M1",
  "timestamp": 1234567890,
  "indicators": {
    "EMA_50": 2650.25,
    "EMA_200": 2645.50,
    "VWAP": 2651.00,
    "SuperTrend": 2648.75,
    "SuperTrend_Upper": 2650.00,
    "SuperTrend_Lower": 2647.50,
    "RSI": 65.5,
    "MACD": {
      "macd": 0.5,
      "signal": 0.3,
      "histogram": 0.2
    },
    "BB_Upper": 2655.0,
    "BB_Middle": 2650.0,
    "BB_Lower": 2645.0,
    "Stochastic_K": 75.5,
    "Stochastic_D": 70.2
  }
}
```

## Troubleshooting

### Indicators not appearing:
1. **Check Python application is running** and connected to MT5
2. **Verify files are being created** in `MQL5/Files/PythonIndicators/` folder
3. **Check file names match** your chart symbol and timeframe
4. **Ensure indicator is compiled** without errors

### Indicators not updating:
1. **Check file modification time** - files should update every few seconds
2. **Verify Python application is receiving ticks** for the symbol
3. **Check MT5 data folder path** - ensure Python can write to `MQL5/Files/`

### File not found errors:
1. **Verify MT5 data folder** is correctly detected by Python application
2. **Check folder permissions** - Python needs write access to `MQL5/Files/`
3. **Ensure symbol name matches** exactly (case-sensitive in some cases)

## Notes

- The indicator displays the **latest** indicator value across all bars (simplified implementation)
- For historical indicator lines, the Python application would need to export full time series
- The indicator checks for file updates every 100ms to balance performance and responsiveness
- Multiple indicators can be displayed simultaneously on the same chart

## Customization

To customize indicator colors and styles, edit `PythonIndicators.mq5` and modify the `PlotIndexSetInteger` calls in the `OnInit()` function.

