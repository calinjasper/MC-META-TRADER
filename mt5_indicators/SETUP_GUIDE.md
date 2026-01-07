# MT5 Python Indicators - Complete Setup Guide

This guide will walk you through setting up the MT5 Indicator Export System step by step.

## Prerequisites

- MetaTrader 5 installed and running
- Python application codebase ready
- Basic knowledge of MT5 file structure

---

## Step 1: Find Your MT5 Installation Folder

### Method 1: Check Common Locations

MT5 is typically installed in one of these locations:
- `C:\Program Files\MetaTrader 5\`
- `C:\Program Files (x86)\MetaTrader 5\`

### Method 2: Find from MT5 Terminal

1. Open MetaTrader 5
2. Go to **File → Open Data Folder**
3. This opens the MT5 data folder (usually `C:\Users\YourName\AppData\Roaming\MetaQuotes\Terminal\...`)
4. Navigate up to find the installation folder, or note the path structure

### Method 3: Check Registry (Advanced)

1. Press `Win + R`, type `regedit`, press Enter
2. Navigate to: `HKEY_LOCAL_MACHINE\SOFTWARE\MetaQuotes\MetaTrader 5`
3. Check the "Path" value

### What You Need

You need to find the **MQL5** folder inside your MT5 installation:
```
C:\Program Files\MetaTrader 5\MQL5\
```

Inside this folder, you should see:
- `Indicators\` - Where custom indicators go
- `Files\` - Where data files are stored (Python will write here)

---

## Step 2: Copy the Indicator File

1. **Locate the indicator file** in your project:
   ```
   mt5_indicators/PythonIndicators.mq5
   ```

2. **Copy the file** to MT5's Indicators folder:
   ```
   C:\Program Files\MetaTrader 5\MQL5\Indicators\PythonIndicators.mq5
   ```

   **OR** if you have multiple MT5 installations, copy to the correct one:
   ```
   C:\Program Files (x86)\MetaTrader 5\MQL5\Indicators\PythonIndicators.mq5
   ```

3. **Verify the file** exists in the Indicators folder

---

## Step 3: Compile the Indicator

### Option A: Using MetaEditor (Recommended)

1. **Open MetaEditor:**
   - In MT5, press `F4` (or go to **Tools → MetaQuotes Language Editor**)
   - Or find "MetaEditor" in your Start Menu

2. **Open the indicator file:**
   - In MetaEditor, go to **File → Open**
   - Navigate to: `MQL5\Indicators\PythonIndicators.mq5`
   - Click Open

3. **Compile the indicator:**
   - Press `F7` (or click the **Compile** button)
   - Or go to **Tools → Compile**

4. **Check for errors:**
   - Look at the bottom panel for compilation results
   - If successful, you'll see: `0 error(s), 0 warning(s)`
   - If there are errors, they will be listed - fix them before proceeding

5. **Verify compilation:**
   - After successful compilation, you should see `PythonIndicators.ex5` in the same folder
   - This is the compiled indicator file that MT5 uses

### Option B: Using MT5 Terminal

1. In MT5, go to **View → Navigator** (or press `Ctrl+N`)
2. Find **Indicators → Custom**
3. Right-click on **PythonIndicators** (if it appears)
4. Select **Compile**
5. Check the **Toolbox** tab (View → Toolbox) for compilation results

---

## Step 4: Verify Python Application Setup

Before running the Python app, verify it can find MT5:

1. **Check MT5 path in config:**
   - Open `config/config.json`
   - Verify the `mt5.path` is correct:
     ```json
     "mt5": {
       "path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
     }
     ```

2. **Test MT5 connection:**
   - The Python application should automatically detect MT5
   - When you run the app, check the logs for:
     ```
     MT5 Indicator Exporter initialized. Export folder: C:\Program Files\MetaTrader 5\MQL5\Files\PythonIndicators
     ```

3. **Verify export folder exists:**
   - The Python app will create: `MQL5\Files\PythonIndicators\`
   - If it doesn't exist, create it manually:
     ```
     C:\Program Files\MetaTrader 5\MQL5\Files\PythonIndicators\
     ```

---

## Step 5: Run the Python Application

1. **Start MT5 first:**
   - Make sure MetaTrader 5 is running
   - Log in to your account

2. **Run the Python application:**
   ```bash
   python src/main.py
   ```

3. **Connect to MT5:**
   - In the Python app, click **Connect to MT5** (or it may auto-connect)
   - Wait for connection confirmation

4. **Add symbols:**
   - The app should automatically add symbols from your config
   - Or manually add symbols in the **Market Data** tab
   - Check that symbols are being monitored

5. **Verify indicator export:**
   - Check the export folder for JSON files:
     ```
     C:\Program Files\MetaTrader 5\MQL5\Files\PythonIndicators\
     ```
   - You should see files like:
     - `XAUUSDm_M1_indicators.json`
     - `EURUSDm_M1_indicators.json`
   - These files should update every few seconds

---

## Step 6: Attach Indicator to MT5 Chart

1. **Open a chart in MT5:**
   - Open MT5 terminal
   - Open a chart for a symbol you're monitoring (e.g., XAUUSDm, EURUSDm)
   - Make sure the timeframe matches (e.g., M1 if you're exporting M1 data)

2. **Attach the indicator:**
   
   **Method 1: From Navigator**
   - Press `Ctrl+N` to open Navigator
   - Expand **Indicators → Custom**
   - Find **PythonIndicators**
   - Drag and drop it onto your chart
   
   **Method 2: From Menu**
   - Right-click on the chart
   - Go to **Insert → Indicators → Custom → PythonIndicators**
   - Click OK

3. **Configure indicator settings:**
   - A properties dialog will appear
   - Configure which indicators to show:
     - ✅ Show EMA 50
     - ✅ Show EMA 200
     - ✅ Show VWAP
     - ✅ Show SuperTrend
     - (Optional) Show RSI, MACD, BB, Stochastic
   - Click **OK**

4. **Verify indicators appear:**
   - You should see indicator lines on your chart
   - EMA lines (orange and blue)
   - VWAP line (cyan)
   - SuperTrend line (green)
   - Check the chart legend to see indicator names

---

## Step 7: Verify Real-Time Updates

1. **Watch the chart:**
   - Indicators should update as new ticks arrive
   - The indicator checks for file updates every 100ms

2. **Check file updates:**
   - Open the export folder in Windows Explorer
   - Watch the JSON files - their "Date modified" should update every few seconds
   - Open a JSON file to see the latest indicator values

3. **Monitor Python logs:**
   - Check the Python application console/logs
   - You should see messages like:
     ```
     Exported indicators for XAUUSDm M1: 8 indicators
     ```

---

## Troubleshooting

### Problem: Indicator doesn't appear on chart

**Solutions:**
1. **Check compilation:**
   - Verify `PythonIndicators.ex5` exists in `MQL5\Indicators\`
   - Recompile if needed (F7 in MetaEditor)

2. **Check file path:**
   - Ensure JSON files exist in `MQL5\Files\PythonIndicators\`
   - File name must match: `{Symbol}_{Timeframe}_indicators.json`
   - Example: `XAUUSDm_M1_indicators.json`

3. **Check symbol/timeframe match:**
   - Chart symbol must match the exported symbol (case-sensitive in some cases)
   - Chart timeframe must match the exported timeframe

4. **Check indicator is attached:**
   - In MT5, right-click chart → **Indicators List**
   - Verify **PythonIndicators** is listed

### Problem: Indicators not updating

**Solutions:**
1. **Check Python app is running:**
   - Verify Python application is connected to MT5
   - Check that symbols are being monitored

2. **Check file updates:**
   - Open the JSON file in Notepad
   - Watch for timestamp changes
   - If not updating, check Python logs for errors

3. **Check MT5 permissions:**
   - Ensure Python has write access to `MQL5\Files\`
   - Try running Python as Administrator if needed

4. **Restart indicator:**
   - Remove indicator from chart
   - Re-attach it
   - This forces MT5 to re-read the file

### Problem: "File not found" errors

**Solutions:**
1. **Verify export folder:**
   - Check `MQL5\Files\PythonIndicators\` exists
   - Create it manually if needed

2. **Check Python logs:**
   - Look for: `MT5 data folder not found`
   - This means Python couldn't find MT5 installation
   - Verify MT5 path in config.json

3. **Check file names:**
   - Symbol name must match exactly
   - Timeframe string must match (M1, M5, H1, etc.)
   - Check for typos or case mismatches

### Problem: Wrong indicator values

**Solutions:**
1. **Check timeframe:**
   - Ensure chart timeframe matches exported timeframe
   - Python exports for the timeframe specified in strategy/config

2. **Check symbol:**
   - Verify you're looking at the correct symbol
   - Different symbols have different indicator files

3. **Check Python calculation:**
   - Verify indicators are calculating correctly in Python
   - Check Python logs for calculation errors

### Problem: Compilation errors

**Common errors and fixes:**

1. **"Undeclared identifier"**
   - Make sure you're using MT5 build 3815 or later
   - Some functions may not be available in older versions

2. **"Cannot open file"**
   - Check file path is correct
   - Ensure file is in `MQL5\Indicators\` folder

3. **"Function not defined"**
   - Check MQL5 version compatibility
   - Update MT5 to latest version

---

## Quick Verification Checklist

Before using the system, verify:

- [ ] MT5 is installed and running
- [ ] `PythonIndicators.mq5` is in `MQL5\Indicators\` folder
- [ ] Indicator compiled successfully (`PythonIndicators.ex5` exists)
- [ ] Python application can find MT5 (check logs)
- [ ] Export folder exists: `MQL5\Files\PythonIndicators\`
- [ ] JSON files are being created in export folder
- [ ] JSON files are updating (check timestamps)
- [ ] Indicator attached to chart
- [ ] Indicator lines visible on chart
- [ ] Indicators updating in real-time

---

## Advanced Configuration

### Custom Indicator Colors

To change indicator colors, edit `PythonIndicators.mq5`:

1. Open in MetaEditor
2. Find the `OnInit()` function
3. Look for `PlotIndexSetInteger(..., PLOT_LINE_COLOR, ...)`
4. Change color values (e.g., `clrOrange` to `clrRed`)
5. Recompile (F7)

### Multiple Timeframes

The system supports multiple timeframes:
- Export indicators for M1, M5, H1, etc.
- Each timeframe has its own JSON file
- Attach indicator to chart with matching timeframe

### Custom Indicator Selection

In the indicator properties dialog:
- Enable/disable specific indicators
- Configure symbol and timeframe filters
- Adjust update frequency (in code)

---

## Support

If you encounter issues:

1. **Check logs:**
   - Python application logs
   - MT5 Expert/Journal tabs
   - MetaEditor compilation output

2. **Verify setup:**
   - Go through this guide step by step
   - Check each requirement

3. **Test components:**
   - Test Python → File export (check JSON files)
   - Test File → MT5 indicator (check chart display)

---

## Next Steps

Once everything is working:

1. **Monitor multiple symbols** - Add more symbols to your Python app
2. **Use different timeframes** - Export indicators for M5, H1, etc.
3. **Customize display** - Adjust colors and styles in MQL5 code
4. **Add more indicators** - Extend the system with additional indicators

Enjoy monitoring your Python-calculated indicators directly in MT5!

