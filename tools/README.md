# Tools Directory

This directory contains diagnostic and verification tools for checking system status and data integrity.

## Diagnostic Tools

### Verification Scripts
- `verify_ticks_setup.py` - Verify ticks collection setup
- `verify_timestamp_storage.py` - Verify timestamp storage
- `verify_volume_fix.py` - Verify volume fix implementation
- `verify_fix_summary.py` - Summary of fixes and verifications

### Check Scripts
- `check_ist_timestamps.py` - Check IST timestamps in PocketBase
- `check_ohlc_timestamp_ist.py` - Check timestamp_ist in OHLC records
- `check_recent_ticks.py` - Check recent tick data
- `check_new_ticks.py` - Check for new ticks

### Debug Scripts
- `debug_mt5_timestamp.py` - Debug MT5 timestamp issues

## Usage

Run tools from the project root directory:

```bash
# Check IST timestamps
python tools/check_ist_timestamps.py

# Verify ticks setup
python tools/verify_ticks_setup.py

# Check OHLC timestamp_ist
python tools/check_ohlc_timestamp_ist.py
```

## Purpose

These tools help:
- Diagnose issues with data storage
- Verify that fixes are working correctly
- Check data integrity in PocketBase
- Debug timestamp and timezone issues

