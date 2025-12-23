# Tests Directory

This directory contains test scripts for verifying functionality and debugging issues.

## Test Scripts

- `test_ist_conversion.py` - Test IST timezone conversion logic
- `test_volume_fix.py` - Test volume population in tick data
- `test_m1_ohlc_storage.py` - Test M1 OHLC bar storage in PocketBase
- `test_timestamp_conversion.py` - Test timestamp conversion
- `test_mt5_timezone.py` - Test MT5 timezone handling
- `test_live_conversion.py` - Test live timestamp conversion
- `test_chart_import.py` - Test chart import functionality

## Usage

Run tests from the project root directory:

```bash
# Test IST conversion
python tests/test_ist_conversion.py

# Test volume fix
python tests/test_volume_fix.py

# Test M1 OHLC storage
python tests/test_m1_ohlc_storage.py
```

## Note

These are functional test scripts, not unit tests. They verify that features work correctly by checking actual data in PocketBase or testing conversion logic.

