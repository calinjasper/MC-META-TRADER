# Manual Setup Steps - Complete Guide

Follow these steps in order to set up the MT5 Indicator Export System.

## Step 1: Find Your MT5 Installation

### Option A: From MT5 Terminal
1. Open MetaTrader 5
2. Go to **File → Open Data Folder**
3. This opens: `C:\Users\YourName\AppData\Roaming\MetaQuotes\Terminal\...`
4. Navigate **UP** to find the installation folder
5. Look for: `C:\Program Files\MetaTrader 5\` or similar

### Option B: Check Common Locations
Open Windows Explorer and check:
- `C:\Program Files\MetaTrader 5\`
- `C:\Program Files (x86)\MetaTrader 5\`
- Any custom installation location

**Note the path** - you'll need it for Step 2.

---

## Step 2: Copy Indicator File

1. **Source file location:**
   ```
   C:\Users\Calin Jasper\Music\mc_meta\mt5_indicators\PythonIndicators.mq5
   ```

2. **Destination folder:**
   ```
   {Your MT5 Path}\MQL5\Indicators\
   ```
   Example: `C:\Program Files\MetaTrader 5\MQL5\Indicators\`

3. **Action:**
   - Copy `PythonIndicators.mq5` from source to destination
   - Verify the file exists in the Indicators folder

---

## Step 3: Compile the Indicator

1. **Open MetaEditor:**
   - In MT5, press **F4** (or Tools → MetaQuotes Language Editor)
   - Or find "MetaEditor" in Start Menu

2. **Open the file:**
   - File → Open
   - Navigate to: `MQL5\Indicators\PythonIndicators.mq5`
   - Click Open

3. **Compile:**
   - Press **F7** (or Tools → Compile)
   - Wait for compilation

4. **Check results:**
   - Look at bottom panel
   - Should see: **0 error(s), 0 warning(s)**
   - If errors, fix them before proceeding

5. **Verify compiled file:**
   - Check that `PythonIndicators.ex5` exists in the same folder
   - This is the compiled indicator MT5 uses

---

## Step 4: Verify Export Folder

1. **Find MT5 Files folder:**
   ```
   {Your MT5 Path}\MQL5\Files\
   ```
   Example: `C:\Program Files\MetaTrader 5\MQL5\Files\`

2. **Create PythonIndicators subfolder:**
   - Create folder: `PythonIndicators`
   - Full path: `C:\Program Files\MetaTrader 5\MQL5\Files\PythonIndicators\`

3. **Verify folder exists:**
   - Open Windows Explorer
   - Navigate to the folder
   - Should be empty (Python app will create JSON files here)

---

## Step 5: Run Python Application

1. **Start Python app:**
   ```bash
   python src/main.py
   ```

2. **Connect to MT5:**
   - Click "Connect to MT5" in the app
   - Wait for connection confirmation

3. **Add symbols:**
   - The app should auto-add symbols from config
   - Or manually add in Market Data tab
   - Verify symbols are being monitored

4. **Check Python logs:**
   - Look for: "MT5 Indicator Exporter initialized"
   - Should show export folder path
   - Example: "Export folder: C:\Program Files\MetaTrader 5\MQL5\Files\PythonIndicators"

---

## Step 6: Verify JSON Files Are Created

1. **Check export folder:**
   ```
   C:\Program Files\MetaTrader 5\MQL5\Files\PythonIndicators\
   ```

2. **Look for JSON files:**
   - Files named: `{Symbol}_{Timeframe}_indicators.json`
   - Example: `XAUUSDm_M1_indicators.json`
   - Example: `EURUSDm_M1_indicators.json`

3. **Check file contents:**
   - Right-click a JSON file → Open with Notepad
   - Should contain:
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
   - Check "Date modified"
   - Should update every few seconds
   - If not updating, Python app may not be running

---

## Step 7: Attach Indicator to MT5 Chart

1. **Open MT5 chart:**
   - Open a chart for a symbol you're monitoring
   - Example: XAUUSDm, EURUSDm
   - Set timeframe to match exported timeframe (e.g., M1)

2. **Attach indicator:**
   
   **Method 1: From Navigator**
   - Press **Ctrl+N** to open Navigator
   - Expand **Indicators → Custom**
   - Find **PythonIndicators**
   - Drag and drop onto chart
   
   **Method 2: From Menu**
   - Right-click chart
   - **Insert → Indicators → Custom → PythonIndicators**
   - Click OK

3. **Configure indicator:**
   - Properties dialog appears
   - Enable indicators you want to see:
     - ✅ Show EMA 50
     - ✅ Show EMA 200
     - ✅ Show VWAP
     - ✅ Show SuperTrend
   - Click **OK**

---

## Step 8: Verify Indicators Appear

1. **Check chart:**
   - You should see indicator lines on the chart
   - EMA 50: Orange line
   - EMA 200: Blue line
   - VWAP: Cyan line
   - SuperTrend: Green line

2. **Check chart legend:**
   - Bottom of chart shows indicator names
   - Should list: EMA(50), EMA(200), VWAP, SuperTrend

3. **Verify updates:**
   - Lines should update every 1-2 seconds
   - Values should change as new ticks arrive

---

## Step 9: Troubleshooting

### If indicators don't appear:

1. **Check compilation:**
   - Verify `PythonIndicators.ex5` exists
   - Recompile if needed (F7 in MetaEditor)

2. **Check JSON files:**
   - Verify files exist in export folder
   - Check file names match symbol/timeframe
   - Verify files are updating (check timestamp)

3. **Check symbol/timeframe match:**
   - Chart symbol must match JSON file symbol
   - Chart timeframe must match JSON file timeframe
   - Example: Chart XAUUSDm M1 needs `XAUUSDm_M1_indicators.json`

4. **Check MT5 logs:**
   - View → Toolbox → Experts tab
   - Look for file reading errors
   - Check for parsing errors

5. **Re-attach indicator:**
   - Remove indicator from chart
   - Re-attach from Navigator
   - This forces MT5 to re-read the file

---

## Quick Checklist

Before testing, verify:

- [ ] MT5 is installed and running
- [ ] `PythonIndicators.mq5` is in `MQL5\Indicators\` folder
- [ ] Indicator compiled successfully (`PythonIndicators.ex5` exists)
- [ ] Export folder exists: `MQL5\Files\PythonIndicators\`
- [ ] Python application is running
- [ ] Python app is connected to MT5
- [ ] JSON files are being created in export folder
- [ ] JSON files are updating (check timestamps)
- [ ] Indicator attached to chart
- [ ] Chart symbol/timeframe matches JSON file
- [ ] Indicator properties configured (indicators enabled)

---

## Expected Result

After completing all steps:

✅ Indicator lines visible on chart  
✅ Lines update in real-time  
✅ Multiple indicators display simultaneously  
✅ Values match Python calculations  

---

## Still Not Working?

If indicators still don't appear after following all steps:

1. **Check Python logs** for export errors
2. **Check MT5 Expert/Journal tabs** for file reading errors
3. **Verify file permissions** - Python needs write access
4. **Try running Python as Administrator** if permission issues
5. **Check antivirus** - may be blocking file access

The most common issue is **symbol/timeframe mismatch** - ensure chart matches exported file exactly!

