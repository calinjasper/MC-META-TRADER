# Project Reorganization Summary

## Date: December 23, 2025

This document summarizes the reorganization of the MC-META-TRADER project directory structure.

## Changes Made

### New Directory Structure

1. **`scripts/`** - Utility scripts organized by purpose
   - `setup/` - Setup and configuration scripts (4 files)
   - `database/` - Database operations and migrations (5 files)
   - `export/` - Data export and viewing scripts (2 files)
   - `legacy/` - Legacy scripts (2 files)

2. **`tests/`** - Test scripts (7 files)
   - All test_*.py files moved here

3. **`tools/`** - Diagnostic and verification tools (9 files)
   - All check_*.py, verify_*.py, and debug_*.py files moved here

4. **`docs/`** - Documentation files (6 files)
   - All .md files (except main README.md) moved here

### Files Moved

#### Setup Scripts → `scripts/setup/`
- `setup_pocketbase_collections.py`
- `add_timestamp_ist_field.py`
- `add_timestamp_ist_to_ohlc.py`
- `update_collections_for_ist.py`

#### Database Scripts → `scripts/database/`
- `migrate_existing_ticks.py`
- `consolidate_ticks.py`
- `create_symbol_collections.py`
- `delete_tick_collections.py`
- `update_ticks_collection.py`

#### Export Scripts → `scripts/export/`
- `export_ticks_to_csv.py`
- `view_symbol_ticks.py`

#### Test Scripts → `tests/`
- `test_ist_conversion.py`
- `test_volume_fix.py`
- `test_m1_ohlc_storage.py`
- `test_timestamp_conversion.py`
- `test_mt5_timezone.py`
- `test_live_conversion.py`
- `test_chart_import.py`

#### Diagnostic Tools → `tools/`
- `check_ist_timestamps.py`
- `check_ohlc_timestamp_ist.py`
- `check_recent_ticks.py`
- `check_new_ticks.py`
- `verify_ticks_setup.py`
- `verify_timestamp_storage.py`
- `verify_volume_fix.py`
- `verify_fix_summary.py`
- `debug_mt5_timestamp.py`

#### Documentation → `docs/`
- `README_POCKETBASE.md`
- `POCKETBASE_INTEGRATION_COMPLETE.md`
- `FILTERING_TICKS_GUIDE.md`
- `SINGLE_COLLECTION_README.md`
- `SYMBOL_WISE_TICKS_README.md`

#### Legacy Scripts → `scripts/legacy/`
- `Python Code – Profit Lock + Trailing Logic.py`
- `Python Code Trailing Stop-Loss System.py`

### Files Kept in Root

- `README.md` - Main project README
- `requirements.txt` - Python dependencies
- `start_trading_system.bat` - Windows startup script
- `start_trading_system.sh` - Linux/Mac startup script
- `PROJECT_STRUCTURE.md` - This reorganization summary

### Directories Unchanged

- `src/` - Main application code (unchanged)
- `config/` - Configuration files (unchanged)
- `data/` - Data files (unchanged)
- `logs/` - Log files (unchanged)
- `pocketbase/` - PocketBase database (unchanged)
- `examples/` - Example code (unchanged)

## New Documentation Created

1. **`scripts/README.md`** - Documentation for scripts directory
2. **`tests/README.md`** - Documentation for tests directory
3. **`tools/README.md`** - Documentation for tools directory
4. **`docs/README.md`** - Documentation index
5. **`PROJECT_STRUCTURE.md`** - Complete project structure documentation

## Usage After Reorganization

All scripts should still be run from the project root directory:

```bash
# Setup PocketBase (new path)
python scripts/setup/setup_pocketbase_collections.py

# View ticks (new path)
python scripts/export/view_symbol_ticks.py --symbol XAUUSDm

# Run tests (new path)
python tests/test_volume_fix.py

# Check data (new path)
python tools/check_ist_timestamps.py
```

## Benefits

1. **Better Organization** - Related files are grouped together
2. **Easier Navigation** - Clear directory structure
3. **Improved Maintainability** - Easier to find and update scripts
4. **Documentation** - Each directory has its own README
5. **Cleaner Root** - Root directory is less cluttered

## Notes

- All scripts maintain their original functionality
- Import paths remain unchanged (scripts use relative imports or absolute paths from project root)
- No code changes were required
- All file references in documentation have been updated

