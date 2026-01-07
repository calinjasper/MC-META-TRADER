# DO THIS NOW - Step-by-Step Execution

Follow these steps **in order**. Check each box as you complete it.

## ✅ STEP 1: Copy Indicator File

**Easiest Method:**
- Double-click `COPY_INDICATOR.bat` in this folder
- It will copy the file automatically

**OR Manual:**
- Copy: `mt5_indicators\PythonIndicators.mq5`
- Paste to: `C:\Program Files\MetaTrader 5\MQL5\Indicators\`
- Verify file exists there

**Status:** ☐ Done

---

## ✅ STEP 2: Compile Indicator

1. Open **MetaTrader 5**
2. Press **F4** (opens MetaEditor)
3. **File → Open**
4. Navigate to: `MQL5\Indicators\PythonIndicators.mq5`
5. Click **Open**
6. Press **F7** (compile)
7. Check bottom panel: Should show **0 error(s), 0 warning(s)**
8. Verify: `PythonIndicators.ex5` file exists in same folder

**Status:** ☐ Done

---

## ✅ STEP 3: Create Export Folder

1. Open Windows Explorer
2. Navigate to: `C:\Program Files\MetaTrader 5\MQL5\Files\`
3. Create folder: `PythonIndicators`
4. Full path should be: `C:\Program Files\MetaTrader 5\MQL5\Files\PythonIndicators\`

**Status:** ☐ Done

---

## ✅ STEP 4: Run Python Application

1. Open terminal in project root: `C:\Users\Calin Jasper\Music\mc_meta`
2. Run: `python src/main.py`
3. In the app, click **"Connect to MT5"**
4. Wait for connection confirmation
5. Check that symbols are being monitored

**Status:** ☐ Done

---

## ✅ STEP 5: Verify JSON Files Are Created

1. Open Windows Explorer
2. Navigate to: `C:\Program Files\MetaTrader 5\MQL5\Files\PythonIndicators\`
3. You should see files like:
   - `XAUUSDm_M1_indicators.json`
   - `EURUSDm_M1_indicators.json`
   - etc.
4. Right-click a file → **Properties**
5. Check **"Date modified"** - should update every few seconds
6. Open file in Notepad to verify it contains indicator values

**Status:** ☐ Done (Files exist and updating)

---

## ✅ STEP 6: Attach Indicator to Chart

1. Open **MetaTrader 5**
2. Open a chart for a symbol you're monitoring (e.g., XAUUSDm)
3. Set timeframe to **M1** (or match your exported timeframe)
4. Press **Ctrl+N** (opens Navigator)
5. Expand **Indicators → Custom**
6. Find **PythonIndicators**
7. **Drag and drop** it onto the chart
8. In the properties dialog:
   - ✅ Check **Show EMA 50**
   - ✅ Check **Show EMA 200**
   - ✅ Check **Show VWAP**
   - ✅ Check **Show SuperTrend**
9. Click **OK**

**Status:** ☐ Done

---

## ✅ STEP 7: Verify Indicators Appear

Look at your MT5 chart. You should see:

- **EMA 50**: Orange horizontal line
- **EMA 200**: Blue horizontal line
- **VWAP**: Cyan horizontal line
- **SuperTrend**: Green horizontal line

**Check chart legend** (bottom of chart) - should list indicator names.

**Lines should update** every 1-2 seconds as new values arrive.

**Status:** ☐ Indicators visible and updating

---

## 🔧 If Indicators Don't Appear

### Quick Checks:

1. **Recompile indicator** (F7 in MetaEditor)
2. **Check JSON files exist** in export folder
3. **Verify symbol/timeframe match:**
   - Chart showing: XAUUSDm M1
   - JSON file: `XAUUSDm_M1_indicators.json`
4. **Remove and re-attach** indicator
5. **Check MT5 Toolbox:**
   - View → Toolbox → Experts tab
   - Look for file reading errors

### Common Issues:

| Problem | Solution |
|---------|----------|
| No lines visible | Recompile indicator, check JSON files |
| Lines not updating | Check Python app is running, verify file updates |
| Wrong values | Check symbol/timeframe match |
| File not found errors | Verify export folder path |

---

## 📝 Notes

- Indicator lines appear as **horizontal lines** across all bars
- This is normal - all bars show the same latest value
- Lines update in real-time as Python calculates new values
- Multiple indicators can be displayed simultaneously

---

## ✅ Final Checklist

Before considering setup complete:

- [ ] Indicator file copied to MT5
- [ ] Indicator compiled (0 errors)
- [ ] Export folder created
- [ ] Python app running and connected
- [ ] JSON files created and updating
- [ ] Indicator attached to chart
- [ ] Indicator lines visible
- [ ] Lines updating in real-time

**If all checked, setup is complete! 🎉**

---

## 🆘 Still Need Help?

1. Read **TROUBLESHOOTING.md** for detailed solutions
2. Check **QUICK_FIX.md** for recent fixes
3. Verify setup with **verify_setup.py**

