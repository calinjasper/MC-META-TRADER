"""
Test IST Timezone Conversion
Verifies that UTC timestamps from MT5 are correctly converted to IST
"""

from datetime import datetime

# Test the conversion logic
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


# Test: Current time in UTC, convert to IST
print("=" * 70)
print("  IST Timezone Conversion Test")
print("=" * 70)
print()

# Get current UTC time
current_utc = datetime.now(UTC)
print(f"Current UTC time:  {current_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Convert to IST
current_ist = _to_ist(current_utc)
print(f"Current IST time:  {current_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")

# Format as IST string
ist_string = _format_ist_timestamp(current_utc)
print(f"IST formatted:     {ist_string}")

print()
print("Expected: IST should be UTC + 5:30 hours")
print(f"Difference: {current_ist.hour - current_utc.hour} hours, {current_ist.minute - current_utc.minute} minutes")
print()

# Test with a specific UTC timestamp (simulating MT5)
test_timestamp = 1766448469  # Example Unix timestamp
test_utc = datetime.fromtimestamp(test_timestamp, tz=UTC)
test_ist = _to_ist(test_utc)
test_ist_str = _format_ist_timestamp(test_utc)

print(f"Test UTC time:     {test_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Test IST time:     {test_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Test IST formatted: {test_ist_str}")
print()

print("=" * 70)
print("If IST time shows current time in India, conversion is working correctly!")
print("=" * 70)

