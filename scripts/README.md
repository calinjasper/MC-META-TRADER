# Scripts Directory

This directory contains utility scripts organized by purpose.

## Structure

### `setup/`
Scripts for setting up and configuring PocketBase collections:
- `setup_pocketbase_collections.py` - Main setup script to create all collections
- `add_timestamp_ist_field.py` - Add timestamp_ist field to ticks collection
- `add_timestamp_ist_to_ohlc.py` - Add timestamp_ist field to OHLC collection
- `update_collections_for_ist.py` - Update collections for IST timestamp support

### `database/`
Scripts for database operations and migrations:
- `migrate_existing_ticks.py` - Migrate existing tick data
- `consolidate_ticks.py` - Consolidate tick collections
- `create_symbol_collections.py` - Create symbol-specific collections (legacy)
- `delete_tick_collections.py` - Delete symbol-specific tick collections
- `update_ticks_collection.py` - Update ticks collection schema

### `export/`
Scripts for exporting and viewing data:
- `export_ticks_to_csv.py` - Export tick data to CSV format
- `view_symbol_ticks.py` - Quick CLI tool to view tick data for a symbol

### `legacy/`
Legacy scripts and old code:
- `Python Code – Profit Lock + Trailing Logic.py`
- `Python Code Trailing Stop-Loss System.py`

## Usage

All scripts should be run from the project root directory:

```bash
# Setup PocketBase collections
python scripts/setup/setup_pocketbase_collections.py

# View ticks for a symbol
python scripts/export/view_symbol_ticks.py --symbol XAUUSDm

# Export ticks to CSV
python scripts/export/export_ticks_to_csv.py
```

