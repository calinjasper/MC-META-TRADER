"""
Test Timestamp Conversion
Debug the UTC to IST conversion to find the issue
"""

from datetime import datetime

# Setup timezones
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


# Test with the actual timestamp from the database
print("=" * 70)
print("  Timestamp Conversion Debug")
print("=" * 70)
print()

# The timestamp from database: 1766482586000 ms = 1766482586 seconds
test_timestamp_seconds = 1766482586
test_timestamp_ms = 1766482586000

print(f"Test timestamp (seconds): {test_timestamp_seconds}")
print(f"Test timestamp (ms): {test_timestamp_ms}")
print()

# Create UTC datetime from timestamp (as MT5 would)
utc_dt = datetime.fromtimestamp(test_timestamp_seconds, tz=UTC)
print(f"UTC datetime: {utc_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Convert to IST
ist_dt = _to_ist(utc_dt)
print(f"IST datetime: {ist_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Format as IST string
ist_str = _format_ist_timestamp(utc_dt)
print(f"IST formatted: {ist_str}")
print()

# Check what timestamp() returns
print("Timestamp values:")
print(f"  UTC timestamp: {utc_dt.timestamp()}")
print(f"  IST timestamp: {ist_dt.timestamp()}")
print(f"  (Note: .timestamp() always returns UTC seconds)")
print()

# Current time comparison
current_utc = datetime.now(UTC)
current_ist = datetime.now(IST)
print(f"Current UTC: {current_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Current IST: {current_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print()

# Calculate difference
time_diff = (current_utc.timestamp() - test_timestamp_seconds) / 3600
print(f"Time difference: {time_diff:.2f} hours between test timestamp and now")
print()

# Check if the stored IST time matches what we calculate
print("Verification:")
print(f"  Stored timestamp_ist: 2025-12-23 15:06:26 IST")
print(f"  Calculated IST:      {ist_str}")
print(f"  Match: {'YES' if ist_str == '2025-12-23 15:06:26 IST' else 'NO'}")
print()

# The issue: if current IST is 09:45 but stored is 15:06, that's 5.5 hours difference
# This suggests the timestamp is from 5.5 hours ago (which would be correct conversion)
# OR the system time is wrong
print("Analysis:")
if time_diff > 5:
    print(f"  The test timestamp is {time_diff:.1f} hours in the past")
    print(f"  This explains why stored IST (15:06) differs from current IST (09:45)")
    print(f"  The conversion appears to be working correctly!")
else:
    print("  The timestamp is recent, so there may be a conversion issue")

