"""
Test Live Timestamp Conversion
Simulate what happens when a tick comes in from MT5
"""

from datetime import datetime

# Setup timezones (same as in code)
try:
    from zoneinfo import ZoneInfo
    UTC = ZoneInfo("UTC")
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    try:
        import pytz
        UTC = pytz.UTC
        IST = pytz.timezone("Asia/Kolkata")
    except ImportError:
        from datetime import timezone, timedelta
        UTC = timezone.utc
        IST = timezone(timedelta(hours=5, minutes=30))


def _to_ist(dt):
    """Convert datetime to IST timezone"""
    if dt.tzinfo is None:
        try:
            from zoneinfo import ZoneInfo
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        except ImportError:
            import pytz
            dt = pytz.UTC.localize(dt)
    
    if hasattr(IST, 'normalize'):
        return IST.normalize(dt.astimezone(IST))
    else:
        return dt.astimezone(IST)


def _format_ist_timestamp(dt):
    """Format datetime as IST timestamp string"""
    ist_dt = _to_ist(dt)
    return ist_dt.strftime("%Y-%m-%d %H:%M:%S IST")


print("=" * 70)
print("  Live Timestamp Conversion Test")
print("=" * 70)
print()

# Simulate: MT5 gives us current time as UTC timestamp
current_utc_time = datetime.now(UTC)
print(f"Step 1 - MT5 gives UTC time: {current_utc_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Step 2 - Convert to IST (as store_tick does)
ist_time = _to_ist(current_utc_time)
print(f"Step 2 - Converted to IST: {ist_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Step 3 - Calculate timestamp_ms (as store_tick does on line 170)
timestamp_ms = int(ist_time.timestamp() * 1000)
print(f"Step 3 - timestamp_ms: {timestamp_ms}")

# Step 4 - Format IST string (as store_tick does on line 171)
created_str = _format_ist_timestamp(current_utc_time)
print(f"Step 4 - timestamp_ist: {created_str}")
print()

# Verify
print("Verification:")
print(f"  Current UTC: {current_utc_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"  Current IST: {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"  Stored IST:  {created_str}")
print()

# Check if they match
current_ist_str = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
if created_str == current_ist_str or abs((datetime.strptime(created_str, "%Y-%m-%d %H:%M:%S IST") - datetime.strptime(current_ist_str, "%Y-%m-%d %H:%M:%S IST")).total_seconds()) < 2:
    print("[OK] Conversion is working correctly!")
else:
    print("[ERROR] Conversion mismatch!")
    print(f"  Expected: {current_ist_str}")
    print(f"  Got:      {created_str}")

