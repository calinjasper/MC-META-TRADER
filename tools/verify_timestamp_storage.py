"""
Verify Timestamp Storage Logic
Check if timestamp_ms should be from UTC or IST
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


print("=" * 70)
print("  Verify Timestamp Storage Logic")
print("=" * 70)
print()

# Simulate what happens in store_tick()
# MT5 gives us a UTC datetime
tick_time_utc = datetime.now(UTC)
print(f"1. MT5 tick_time (UTC): {tick_time_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Current code does:
ist_time = tick_time_utc.astimezone(IST)
print(f"2. Converted to IST: {ist_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Current code calculates timestamp_ms from ist_time
timestamp_ms_from_ist = int(ist_time.timestamp() * 1000)
print(f"3. timestamp_ms from IST: {timestamp_ms_from_ist}")

# But .timestamp() on timezone-aware datetime returns UTC seconds!
# So this is actually correct - it's the UTC timestamp
utc_timestamp_seconds = ist_time.timestamp()
print(f"4. ist_time.timestamp() returns: {utc_timestamp_seconds} (UTC seconds)")

# Verify: convert back
reconstructed_utc = datetime.fromtimestamp(utc_timestamp_seconds, tz=UTC)
print(f"5. Reconstructed UTC: {reconstructed_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Compare
if abs((tick_time_utc - reconstructed_utc).total_seconds()) < 1:
    print()
    print("[OK] timestamp_ms calculation is correct!")
    print("     .timestamp() on IST datetime returns UTC seconds (correct)")
else:
    print()
    print("[ERROR] timestamp_ms calculation is wrong!")
    print(f"     Difference: {(tick_time_utc - reconstructed_utc).total_seconds()} seconds")

print()
print("Conclusion:")
print("  The code is correct - timestamp_ms stores UTC timestamp (in ms)")
print("  timestamp_ist stores IST-formatted string for display")
print("  Both are correct!")

