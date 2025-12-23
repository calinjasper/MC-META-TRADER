"""
Debug MT5 Timestamp Issue
Check if MT5 timestamps are being interpreted correctly
"""

from datetime import datetime
import time

# Setup UTC timezone
try:
    from zoneinfo import ZoneInfo
    UTC = ZoneInfo("UTC")
except ImportError:
    try:
        import pytz
        UTC = pytz.UTC
    except ImportError:
        from datetime import timezone
        UTC = timezone.utc

print("=" * 70)
print("  Debug MT5 Timestamp Issue")
print("=" * 70)
print()

# The stored timestamp from database
stored_timestamp_ms = 1766482586000
stored_timestamp_sec = stored_timestamp_ms / 1000

print(f"Stored timestamp (ms): {stored_timestamp_ms}")
print(f"Stored timestamp (sec): {stored_timestamp_sec}")
print()

# Method 1: Current code - datetime.fromtimestamp with UTC
dt_utc = datetime.fromtimestamp(stored_timestamp_sec, tz=UTC)
print(f"Method 1 - fromtimestamp(ts, tz=UTC):")
print(f"  Result: {dt_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print()

# Method 2: datetime.utcfromtimestamp (deprecated but might work differently)
dt_utc2 = datetime.utcfromtimestamp(stored_timestamp_sec)
print(f"Method 2 - utcfromtimestamp(ts):")
print(f"  Result: {dt_utc2.strftime('%Y-%m-%d %H:%M:%S')} (naive)")
print()

# Current system time
current_utc = datetime.now(UTC)
current_timestamp = time.time()
print(f"Current system time:")
print(f"  UTC: {current_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"  Timestamp: {current_timestamp}")
print()

# Calculate difference
time_diff_seconds = stored_timestamp_sec - current_timestamp
time_diff_hours = time_diff_seconds / 3600
print(f"Time difference:")
print(f"  Stored timestamp is {time_diff_hours:.2f} hours {'ahead' if time_diff_hours > 0 else 'behind'} current time")
print()

# Check if this is a timezone issue
# Maybe the timestamp was created using local time instead of UTC?
import time
local_time = datetime.fromtimestamp(stored_timestamp_sec)
print(f"If interpreted as local time (no timezone):")
print(f"  Result: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
print()

# The issue: if MT5 gives us a timestamp that's actually in local timezone
# but we treat it as UTC, we get wrong results
print("Analysis:")
if abs(time_diff_hours) > 4:
    print(f"  [WARNING] Timestamp is {abs(time_diff_hours):.1f} hours off!")
    print(f"  This suggests a timezone interpretation issue.")
    print()
    print("  Possible causes:")
    print("  1. MT5 timestamp is in local timezone, not UTC")
    print("  2. System clock was wrong when timestamp was created")
    print("  3. MT5 server time is wrong")
else:
    print("  [OK] Timestamp is close to current time")

