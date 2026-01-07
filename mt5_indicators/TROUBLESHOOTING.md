# Troubleshooting: Indicator Lines Not Visible

If indicator lines are not appearing on your MT5 chart, follow these diagnostic steps:

## Step 1: Verify JSON Files Are Being Created

1. **Check the export folder:**
   ```
   C:\Program Files\MetaTrader 5\MQL5\Files\PythonIndicators\
   ```
   Or check your MT5 data folder path.

2. **Look for JSON files:**
   - Files should be named: `{Symbol}_{Timeframe}_indicators.json`
   - Example: `XAUUSDm_M1_indicators.json`

3. **Check file contents:**
   - Open a JSON file in Notepad
   - Verify it contains indicator values:
     ```json
     {
       "symbol": "XAUUSDm",
       "timeframe": "M1",
       "timestamp": 1234567890,
       "indicators": {
         "EMA_50": 2650.25,
         "EMA_200": 2645.50,
         "VWAP": 2651.00
       }
     }
     ```

4. **Check file updates:**
   - Right-click file → Properties
   - Check "Date modified" - should update every few seconds
   - If not updating, Python app may not be running or connected

## Step 2: Verify Indicator File Path

1. **Check indicator is looking for correct file:**
   - In MT5, open **Toolbox** (View → Toolbox)
   - Go to **Experts** tab
   - Look for errors like "Cannot open file" or "File not found"

2. **Verify file path matches:**
   - Chart symbol must match JSON file symbol
   - Chart timeframe must match JSON file timeframe
   - Example: Chart showing XAUUSDm M1 needs `XAUUSDm_M1_indicators.json`

3. **Check symbol name case:**
   - Some brokers use different cases (XAUUSDm vs xauusdm)
   - Ensure Python exports match exactly what MT5 expects

## Step 3: Check Indicator Compilation

1. **Verify compilation:**
   - Open MetaEditor (F4 in MT5)
   - Open `PythonIndicators.mq5`
   - Press F7 to compile
   - Check for errors in bottom panel

2. **Check compiled file exists:**
   - Look for `PythonIndicators.ex5` in `MQL5\Indicators\` folder
   - If missing, compilation failed

3. **Check for warnings:**
   - Even if compilation succeeds, warnings may indicate issues
   - Fix any warnings before proceeding

## Step 4: Verify Indicator Is Attached

1. **Check indicator list:**
   - Right-click chart → **Indicators List**
   - Verify **PythonIndicators** is listed
   - If not, attach it (drag from Navigator)

2. **Check indicator properties:**
   - Right-click chart → **Indicators List** → Select PythonIndicators → **Properties**
   - Verify indicators are enabled (checkboxes checked)
   - Check symbol and timeframe settings

3. **Check chart settings:**
   - Ensure chart is showing the correct symbol
   - Ensure chart timeframe matches exported timeframe

## Step 5: Debug File Reading

Add debug output to see what's happening:

1. **Check MT5 Journal:**
   - View → Toolbox → **Journal** tab
   - Look for file-related errors
   - Check if file is being read

2. **Check Expert Logs:**
   - View → Toolbox → **Experts** tab
   - Look for indicator errors
   - Check for parsing errors

3. **Test file manually:**
   - Try opening the JSON file in MT5's file viewer
   - Verify file is readable and not corrupted

## Step 6: Verify Indicator Values

1. **Check parsed values:**
   - The indicator should parse values from JSON
   - If all values are 0 or EMPTY_VALUE, parsing failed

2. **Check value ranges:**
   - EMA/VWAP values should be in price range
   - RSI should be 0-100
   - MACD can be negative
   - If values are outside expected ranges, parsing may be wrong

3. **Check buffer filling:**
   - Indicator fills all bars with same value (horizontal line)
   - If line doesn't appear, value may be EMPTY_VALUE

## Step 7: Common Issues and Fixes

### Issue: File Not Found
**Symptoms:** No indicator lines, "File not found" in logs

**Fixes:**
1. Verify export folder exists: `MQL5\Files\PythonIndicators\`
2. Check Python app is running and connected to MT5
3. Verify symbol/timeframe match between chart and file
4. Check file permissions (Python needs write access)

### Issue: All Values Are Zero
**Symptoms:** Indicator attached but no lines visible

**Fixes:**
1. Check JSON file contains valid indicator values
2. Verify JSON format is correct (valid JSON syntax)
3. Check indicator parsing logic (ParseJSONValue function)
4. Verify indicator keys match (EMA_50, VWAP, etc.)

### Issue: Lines Appear But Don't Update
**Symptoms:** Lines visible initially but don't change

**Fixes:**
1. Check JSON file is updating (check file modification time)
2. Verify Python app is calculating new values
3. Check indicator refresh interval (should check file every 1 second)
4. Try removing and re-attaching indicator

### Issue: Wrong Indicator Values
**Symptoms:** Lines visible but values don't match Python calculations

**Fixes:**
1. Verify chart symbol matches exported symbol
2. Check chart timeframe matches exported timeframe
3. Verify Python is calculating for correct symbol/timeframe
4. Check for symbol name mismatches (case sensitivity)

### Issue: Some Indicators Missing
**Symptoms:** Some indicators show, others don't

**Fixes:**
1. Check indicator checkboxes in properties (enabled/disabled)
2. Verify JSON contains all expected indicators
3. Check indicator parsing for specific indicators
4. Verify indicator values are valid (not null or 0)

## Step 8: Manual Testing

1. **Create test JSON file:**
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
       "SuperTrend_Lower": 2647.50
     }
   }
   ```

2. **Save to export folder:**
   - Save as `XAUUSDm_M1_indicators.json`
   - Place in `MQL5\Files\PythonIndicators\`

3. **Attach indicator to XAUUSDm M1 chart:**
   - Should show horizontal lines at specified values
   - If not, indicator code has issues

## Step 9: Check Python Application

1. **Verify exporter is initialized:**
   - Check Python logs for: "MT5 Indicator Exporter initialized"
   - Verify export folder path is correct

2. **Check symbols are added:**
   - Verify symbols are added to exporter
   - Check logs for: "Added {symbol} to indicator export"

3. **Verify exports are happening:**
   - Check logs for: "Exported indicators for {symbol}"
   - Verify no export errors

4. **Check indicator calculations:**
   - Verify indicators are being calculated
   - Check for calculation errors in logs

## Step 10: Recompile and Restart

If nothing works:

1. **Recompile indicator:**
   - Open MetaEditor
   - Open `PythonIndicators.mq5`
   - Press F7 to recompile
   - Fix any errors

2. **Restart MT5:**
   - Close MT5 completely
   - Restart MT5
   - Re-attach indicator

3. **Restart Python app:**
   - Stop Python application
   - Restart Python application
   - Verify connection to MT5

4. **Clear and recreate:**
   - Delete JSON files in export folder
   - Let Python recreate them
   - Re-attach indicator

## Still Not Working?

If indicators still don't appear:

1. **Check MT5 version:**
   - Ensure MT5 is up to date
   - Some MQL5 features require newer versions

2. **Check file permissions:**
   - Run Python as Administrator if needed
   - Check Windows file permissions

3. **Check antivirus:**
   - Some antivirus may block file access
   - Add MT5 and Python folders to exclusions

4. **Check logs:**
   - Python application logs
   - MT5 Expert/Journal logs
   - Windows Event Viewer

5. **Test with simple indicator:**
   - Try with just one indicator (EMA_50)
   - If that works, add others one by one

## Quick Diagnostic Script

Add this to your Python app to test:

```python
# Test export manually
from src.indicators.mt5_indicator_exporter import MT5IndicatorExporter
exporter = MT5IndicatorExporter(mt5_connector, data_feed)
exporter.add_symbol("XAUUSDm", mt5.TIMEFRAME_M1)
exporter.export_indicators("XAUUSDm", mt5.TIMEFRAME_M1)

# Check if file exists
import os
file_path = os.path.join(exporter.get_export_folder(), "XAUUSDm_M1_indicators.json")
if os.path.exists(file_path):
    print(f"File exists: {file_path}")
    with open(file_path, 'r') as f:
        print(f"Content: {f.read()}")
else:
    print(f"File not found: {file_path}")
```

This will help identify if the issue is with file creation or indicator display.

