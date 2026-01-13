"""Debug UTC time storage issue"""
import sys
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

UTC = ZoneInfo("UTC")

# Simulate what should happen
tick_time = datetime.now(UTC)
print(f"Tick time (datetime): {tick_time}")
print(f"Tick time type: {type(tick_time)}")
print(f"Tick time tzinfo: {tick_time.tzinfo}")

# Format as UTC
if tick_time.tzinfo is None:
    tick_time = tick_time.replace(tzinfo=UTC)
utc_time = tick_time.astimezone(UTC) if tick_time.tzinfo != UTC else tick_time
formatted = utc_time.strftime("%Y-%m-%d %H:%M:%S UTC")

print(f"\nFormatted UTC time: '{formatted}'")
print(f"Length: {len(formatted)}")

# Check what happens if we convert to string directly
direct_str = str(tick_time)
print(f"\nDirect string conversion: '{direct_str}'")

# Check time() method (this would give just time)
time_only = tick_time.time()
print(f"\nTime only (time() method): '{time_only}'")
print(f"Time only as string: '{str(time_only)}'")

