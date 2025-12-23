# Single Ticks Collection - Implementation Complete

## Overview

Your trading system now uses a **single `ticks` collection** with powerful filtering capabilities. This is the industry-standard approach that's simpler to manage while still providing easy symbol-specific views.

---

## What Changed

### System Reverted to Single Collection
- ✅ All ticks stored in one `ticks` collection
- ✅ Filter by symbol in PocketBase UI
- ✅ Export tool groups by symbol automatically
- ✅ Simpler management (1 collection vs 30+)

---

## Quick Start

### 1. Consolidate Existing Data (If Needed)

If you have data in separate `ticks_*` collections:

```bash
python consolidate_ticks.py
```

This will:
- Move all data from `ticks_XAUUSDm`, `ticks_EURUSDm`, etc. → single `ticks`
- Verify data integrity
- Optionally delete old collections

### 2. Restart Trading System

```bash
# Stop current system
taskkill /F /IM python.exe

# Start with new configuration
python src\main.py
```

**Or use batch file:**
```bash
start_trading_system.bat
```

### 3. Verify Data Flow

Open PocketBase:
```
http://127.0.0.1:8090/_/
```

- Click `ticks` collection
- You should see ticks from all symbols flowing in
- Use the filter box to view specific symbols

---

## Viewing Symbol-Specific Data

### Method 1: PocketBase UI Filtering

**In PocketBase UI:**
1. Go to `http://127.0.0.1:8090/_/`
2. Click `ticks` collection
3. In the filter box, enter:
   ```
   symbol = "XAUUSDm"
   ```
4. See only XAUUSD ticks!

**More filters:**
```
symbol = "EURUSDm"           # EUR/USD only
symbol ~ "USD"                # All USD pairs
symbol = "XAUUSDm" && bid > 4400  # XAUUSD above price
timestamp >= 1734900000000    # Recent ticks
```

**📖 See [`FILTERING_TICKS_GUIDE.md`](FILTERING_TICKS_GUIDE.md) for complete filtering guide!**

### Method 2: Quick View Script

```bash
# View last 100 XAUUSD ticks
python view_symbol_ticks.py --symbol XAUUSD

# View with stats
python view_symbol_ticks.py --symbol EURUSD --stats

# View specific date range
python view_symbol_ticks.py --symbol GBPUSD --from 2025-12-22 --to 2025-12-23

# Custom limit
python view_symbol_ticks.py --symbol XAUUSD --limit 500
```

**Output:**
- Formatted table of ticks
- Statistics (min/max/avg bid/ask/spread)
- Date range support

---

## Exporting Data

### Export All Symbols (Separate Files)

```bash
python export_ticks_to_csv.py
```

**Creates:**
- `exports/ticks_XAUUSDm_20251222_235959.csv`
- `exports/ticks_EURUSDm_20251222_235959.csv`
- `exports/ticks_GBPUSDm_20251222_235959.csv`
- ... (one per symbol)

### Export Specific Symbol

```bash
python export_ticks_to_csv.py --symbol XAUUSD
```

### Export Date Range

```bash
# Today only
python export_ticks_to_csv.py --from 2025-12-22 --to 2025-12-22

# Last week
python export_ticks_to_csv.py --from 2025-12-15 --to 2025-12-22

# Specific symbol + date range
python export_ticks_to_csv.py --symbol EURUSD --from 2025-12-20 --to 2025-12-22
```

### List Available Symbols

```bash
python export_ticks_to_csv.py --list
```

---

## Benefits vs Separate Collections

| Feature | Separate Collections | Single Collection ✅ |
|---------|---------------------|---------------------|
| **Management** | 30+ collections | 1 collection |
| **View one symbol** | Click collection | Use filter |
| **Export** | Manual per collection | Auto-grouped |
| **Cross-symbol queries** | Very difficult | Easy |
| **Performance** | Slower UI loading | Faster |
| **Standard practice** | No | Yes |
| **Backups** | 30+ collections | 1 collection |
| **New symbols** | Create collection | Auto-handled |

---

## Tools & Scripts

### 1. Export Tool
**File:** [`export_ticks_to_csv.py`](export_ticks_to_csv.py)
- Queries single collection
- Groups by symbol
- Exports to CSV files

### 2. Quick View Tool  
**File:** [`view_symbol_ticks.py`](view_symbol_ticks.py)
- Command-line ticker viewer
- Statistics calculator
- Fast symbol lookup

### 3. Consolidation Tool
**File:** [`consolidate_ticks.py`](consolidate_ticks.py)
- Moves data from `ticks_*` → `ticks`
- One-time migration
- Optional cleanup

### 4. Filtering Guide
**File:** [`FILTERING_TICKS_GUIDE.md`](FILTERING_TICKS_GUIDE.md)
- Complete filter syntax
- Examples for all scenarios
- Tips & tricks

---

## PocketBase Filtering Examples

### Basic Filters

```
symbol = "XAUUSDm"              # Exact match
symbol ~ "USD"                  # Contains USD
symbol ~ "EUR"                  # All EUR pairs
```

### Time-Based Filters

```
timestamp >= 1734900000000      # After timestamp
timestamp >= 1734900000000 && timestamp <= 1734912000000  # Range
```

### Price Filters

```
bid > 4400                      # XAUUSD above 4400
spread > 0.001                  # Large spread
bid > 1.10 && symbol ~ "EUR"    # EUR pairs above 1.10
```

### Combined Filters

```
symbol = "XAUUSDm" && bid > 4400 && timestamp >= 1734900000000
```

**📖 See [`FILTERING_TICKS_GUIDE.md`](FILTERING_TICKS_GUIDE.md) for 50+ examples!**

---

## Common Tasks

### View Today's XAUUSD Ticks

**PocketBase UI:**
```
symbol = "XAUUSDm" && timestamp >= 1734825600000
```

**Command Line:**
```bash
python view_symbol_ticks.py --symbol XAUUSD --from 2025-12-22
```

### Export Week's Data

```bash
python export_ticks_to_csv.py --from 2025-12-15 --to 2025-12-22
```

### Check Symbol Statistics

```bash
python view_symbol_ticks.py --symbol EURUSD --stats --limit 1000
```

### Find High-Volatility Periods

**PocketBase UI:**
```
spread > 0.002 && timestamp >= 1734900000000
```

---

## Migration Path

### If You Have Separate Collections

**Step 1: Consolidate Data**
```bash
python consolidate_ticks.py
```

**Step 2: Verify in PocketBase**
- Check `ticks` collection has all data
- Verify record counts match

**Step 3: Delete Old Collections**
- Prompted by consolidation script
- Or manually in PocketBase UI

**Step 4: Restart System**
```bash
python src\main.py
```

---

## Troubleshooting

### No Ticks Appearing

**Check:**
1. Trading system is running
2. MT5 is connected
3. Markets are open
4. View PocketBase: `http://127.0.0.1:8090/_/`

### Filter Not Working

**Common issues:**
1. Missing quotes: `symbol = XAUUSDm` ❌ → `symbol = "XAUUSDm"` ✅
2. Wrong operator: `symbol == "XAUUSDm"` ❌ → `symbol = "XAUUSDm"` ✅
3. Case sensitivity: Symbols are case-sensitive

### Export Shows Wrong Symbol

**Solution:**
- Symbol names must match exactly (e.g., `XAUUSDm` not `XAUUSD`)
- Use `--list` flag to see available symbols:
  ```bash
  python export_ticks_to_csv.py --list
  ```

---

## Performance Tips

### 1. Add Indexes

For faster filtering, PocketBase automatically indexes:
- `symbol` field
- `timestamp` field

### 2. Use Time Filters

When browsing large datasets:
```
timestamp >= 1734900000000  # Last 24 hours
```

### 3. Export for Analysis

For heavy analysis, export to CSV:
```bash
python export_ticks_to_csv.py --symbol XAUUSD
```

Then analyze in Excel/Python/R.

---

## Files Created/Modified

### Modified Files
- ✅ `src/data/pocketbase_manager.py` - Reverted to single collection
- ✅ `export_ticks_to_csv.py` - Updated for single collection

### New Files  
- ✅ `consolidate_ticks.py` - Migration tool
- ✅ `view_symbol_ticks.py` - Quick view tool
- ✅ `FILTERING_TICKS_GUIDE.md` - Complete filtering guide
- ✅ `SINGLE_COLLECTION_README.md` - This file

### Deprecated Files
- `create_symbol_collections.py` - No longer needed
- `migrate_existing_ticks.py` - Replaced by `consolidate_ticks.py`
- `SYMBOL_WISE_TICKS_README.md` - Old approach

---

## Summary

✅ **Single Collection** = Industry standard, simpler management  
✅ **Powerful Filtering** = View any symbol instantly  
✅ **Auto-Grouped Export** = CSV files organized by symbol  
✅ **Better Performance** = Faster queries, easier backups  
✅ **Cross-Symbol Analysis** = Correlation, statistics, etc.  

**Your tick storage is now optimized and easy to use!** 🎯

---

## Next Steps

1. **Consolidate** (if you have separate collections):
   ```bash
   python consolidate_ticks.py
   ```

2. **Restart system**:
   ```bash
   python src\main.py
   ```

3. **Try filtering** in PocketBase:
   ```
   http://127.0.0.1:8090/_/
   ```

4. **Export data** when needed:
   ```bash
   python export_ticks_to_csv.py
   ```

**Enjoy your simplified, powerful tick storage system!** 🚀

