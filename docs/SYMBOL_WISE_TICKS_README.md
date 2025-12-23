# Symbol-Wise Tick Storage - Implementation Complete

## Overview

Your trading system now stores ticks in **symbol-specific collections** for easier viewing and exporting. Instead of one mixed `ticks` collection, each symbol gets its own collection (e.g., `ticks_XAUUSDm`, `ticks_EURUSDm`).

---

## What Changed

### 1. PocketBase Manager
- **File**: `src/data/pocketbase_manager.py`
- **Changes**: 
  - `store_tick()` now routes ticks to symbol-specific collections
  - Auto-creates collections as needed
  - Caches collection existence to avoid repeated API calls

### 2. New Scripts

#### `create_symbol_collections.py`
Pre-create collections for all active symbols

#### `export_ticks_to_csv.py`
Export tick data to CSV files, grouped by symbol

#### `migrate_existing_ticks.py`
Migrate existing data from old mixed collection to symbol-specific collections

---

## Getting Started

### Step 1: Create Collections for Active Symbols

```bash
python create_symbol_collections.py
```

This will:
- Connect to PocketBase
- Create `ticks_{SYMBOL}` collections for all active symbols
- Set appropriate API rules

**Expected output:**
```
Created collection: ticks_XAUUSDm
Created collection: ticks_EURUSDm
...
```

### Step 2: Migrate Existing Data (Optional)

If you already have tick data in the old `ticks` collection:

```bash
python migrate_existing_ticks.py
```

This will:
- Read all records from the old `ticks` collection
- Group by symbol
- Create symbol-specific collections
- Insert records into appropriate collections
- Optionally delete the old collection

**Note**: This is a one-time operation. Skip if you're starting fresh.

### Step 3: Restart Trading System

Stop your current trading system and restart it:

```bash
# Stop
taskkill /F /IM python.exe

# Start
python src\main.py
```

**Or use the batch file:**
```bash
start_trading_system.bat
```

New ticks will now be automatically stored in symbol-specific collections!

---

## Viewing Data in PocketBase

### Open PocketBase Admin UI
```
http://127.0.0.1:8090/_/
```

### Navigate to Collections

You'll see:
- `ticks_XAUUSDm` - Gold ticks
- `ticks_EURUSDm` - EUR/USD ticks
- `ticks_GBPUSDm` - GBP/USD ticks
- ... (one per symbol)

### View Symbol Data

Click any collection to see only that symbol's ticks:
- Clean, organized view
- Easy filtering and searching
- No mixed data

---

## Exporting Data to CSV

### Export All Symbols

```bash
python export_ticks_to_csv.py
```

Creates CSV files in `exports/` folder:
- `ticks_XAUUSDm_20251222_235959.csv`
- `ticks_EURUSDm_20251222_235959.csv`
- ...

### Export Specific Symbol

```bash
python export_ticks_to_csv.py --symbol XAUUSD
```

### Export Date Range

```bash
# Export today's data
python export_ticks_to_csv.py --from 2025-12-22 --to 2025-12-22

# Export last week
python export_ticks_to_csv.py --from 2025-12-15 --to 2025-12-22

# Export specific symbol with date range
python export_ticks_to_csv.py --symbol EURUSD --from 2025-12-20 --to 2025-12-22
```

### List Available Symbols

```bash
python export_ticks_to_csv.py --list
```

### CSV Format

Exported CSV files contain:
- `id` - Record ID
- `symbol` - Trading symbol
- `timestamp` - Unix timestamp (milliseconds)
- `datetime` - Human-readable datetime
- `bid` - Bid price
- `ask` - Ask price
- `last` - Last price
- `volume` - Tick volume
- `spread` - Bid-ask spread
- `created` - Record creation time
- `updated` - Last update time

---

## Benefits

### Easy Viewing
✅ Each symbol has its own collection  
✅ No mixed data to filter through  
✅ Clear organization in PocketBase UI

### Easy Exporting
✅ Export one symbol or all symbols  
✅ CSV format ready for Excel/analysis  
✅ Date range filtering support

### Performance
✅ Smaller collections = faster queries  
✅ No need to filter by symbol  
✅ Optimized storage per symbol

---

## Technical Details

### Collection Naming
- Format: `ticks_{SYMBOL}`
- Examples: `ticks_XAUUSDm`, `ticks_EURUSDm`

### Auto-Creation
- Collections are created automatically when first tick arrives
- No manual intervention needed for new symbols

### Schema (Per Collection)
```
symbol    (text)   - Trading symbol
timestamp (number) - Unix timestamp in milliseconds
bid       (number) - Bid price
ask       (number) - Ask price
last      (number) - Last price (optional)
volume    (number) - Tick volume (optional)
spread    (number) - Bid-ask spread (optional)
```

### API Rules
All collections have open API rules for development:
- List: Allow all
- View: Allow all
- Create: Allow all (unauthenticated writes)
- Update: Allow all
- Delete: Allow all

**For production**, you should restrict these rules!

---

## Troubleshooting

### "Collection doesn't exist" error
**Solution**: Run `python create_symbol_collections.py` to pre-create collections

### Export shows 0 records
**Possible causes**:
- Trading system not running
- Symbol name mismatch
- Date range too narrow

**Solution**: Check PocketBase UI to verify data exists

### Migration fails
**Possible causes**:
- PocketBase not running
- Authentication failed
- Insufficient permissions

**Solution**: 
1. Ensure PocketBase is running
2. Verify admin credentials in script
3. Check PocketBase logs

---

## Maintenance

### Backup
Each collection needs separate backup. Use PocketBase's built-in backup or export all to CSV regularly.

### Cleanup
Old ticks can be deleted per symbol for better management:
1. Open PocketBase UI
2. Navigate to specific symbol collection
3. Filter by date
4. Delete old records

### Adding New Symbols
New symbol collections are created automatically when first tick arrives. No manual intervention needed!

---

## Support

If you encounter issues:
1. Check PocketBase is running: `http://127.0.0.1:8090`
2. Verify collections exist in admin UI
3. Check trading system logs for errors
4. Review `exports/` folder for CSV files

---

**Enjoy your organized, symbol-wise tick storage!** 🚀

