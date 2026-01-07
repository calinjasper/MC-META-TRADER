# START HERE - Quick Setup Guide

## 🚀 Quick Setup (5 Minutes)

### Step 1: Copy Indicator File

**Option A: Use the batch script (Easiest)**
1. Double-click `COPY_INDICATOR.bat`
2. Follow the prompts
3. If it says "not found", use Option B

**Option B: Manual Copy**
1. Copy `PythonIndicators.mq5` from this folder
2. Paste to: `C:\Program Files\MetaTrader 5\MQL5\Indicators\`
   (Or `C:\Program Files (x86)\MetaTrader 5\MQL5\Indicators\` if 32-bit)

### Step 2: Compile Indicator

1. Open MT5
2. Press **F4** (opens MetaEditor)
3. File → Open → Navigate to `MQL5\Indicators\PythonIndicators.mq5`
4. Press **F7** (compile)
5. Verify: **0 error(s), 0 warning(s)**

### Step 3: Run Python App

1. Open terminal in project root
2. Run: `python src/main.py`
3. Click "Connect to MT5"
4. Wait for connection

### Step 4: Verify JSON Files

1. Check folder: `C:\Program Files\MetaTrader 5\MQL5\Files\PythonIndicators\`
2. Should see files like: `XAUUSDm_M1_indicators.json`
3. Files should update every few seconds

### Step 5: Attach to Chart

1. Open MT5 chart (e.g., XAUUSDm M1)
2. Press **Ctrl+N** (Navigator)
3. Drag **PythonIndicators** onto chart
4. Enable indicators in properties
5. Click OK

### Step 6: Verify

✅ Indicator lines should appear on chart  
✅ Lines update in real-time  
✅ Multiple indicators visible  

---

## 📋 Files in This Folder

- **PythonIndicators.mq5** - The MQL5 indicator (copy to MT5)
- **COPY_INDICATOR.bat** - Auto-copy script
- **MANUAL_SETUP_STEPS.md** - Detailed step-by-step guide
- **SETUP_GUIDE.md** - Complete setup documentation
- **TROUBLESHOOTING.md** - Fix common issues
- **QUICK_FIX.md** - Recent fixes applied
- **verify_setup.py** - Verification script

---

## ⚠️ Common Issues

### Indicators not showing?
1. Recompile indicator (F7 in MetaEditor)
2. Check JSON files exist and are updating
3. Verify symbol/timeframe match between chart and file
4. Remove and re-attach indicator

### Files not being created?
1. Check Python app is running
2. Verify MT5 connection in Python app
3. Check export folder exists: `MQL5\Files\PythonIndicators\`
4. Check Python logs for errors

### Compilation errors?
1. Ensure MT5 is up to date
2. Check for syntax errors in MetaEditor
3. Verify all required MQL5 functions are available

---

## 📞 Need Help?

1. Read **MANUAL_SETUP_STEPS.md** for detailed instructions
2. Check **TROUBLESHOOTING.md** for solutions
3. Verify setup with **verify_setup.py**

---

## ✅ Success Checklist

- [ ] Indicator file copied to MT5 Indicators folder
- [ ] Indicator compiled successfully (0 errors)
- [ ] Python app running and connected to MT5
- [ ] JSON files created in export folder
- [ ] JSON files updating (check timestamps)
- [ ] Indicator attached to chart
- [ ] Indicator lines visible on chart
- [ ] Lines updating in real-time

**If all checked, you're done! 🎉**

