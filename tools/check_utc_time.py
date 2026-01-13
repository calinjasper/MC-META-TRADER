"""Check UTC time format in database"""
import mysql.connector
from datetime import datetime
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")

# Connect to database
conn = mysql.connector.connect(
    host='127.0.0.1',
    port=3306,
    user='root',
    password='lokesh',
    database='forex'
)

cursor = conn.cursor()

# Get latest record
cursor.execute('SELECT timestamp, utc_time, LENGTH(utc_time) as len FROM xauusd_tick_level ORDER BY timestamp DESC LIMIT 1')
row = cursor.fetchone()

if row:
    timestamp_ms = row[0]
    utc_time_stored = row[1]
    length = row[2]
    
    print(f"Latest record:")
    print(f"  timestamp_ms: {timestamp_ms}")
    print(f"  utc_time stored: '{utc_time_stored}'")
    print(f"  length: {length}")
    
    # Convert timestamp back to datetime
    ts_sec = timestamp_ms / 1000
    dt = datetime.fromtimestamp(ts_sec, tz=UTC)
    expected_format = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    print(f"\nExpected format for this timestamp:")
    print(f"  '{expected_format}'")
    print(f"  length: {len(expected_format)}")
    
    print(f"\nCurrent UTC time:")
    print(f"  {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Check if stored matches expected
    if utc_time_stored == expected_format:
        print("\n✓ Stored format matches expected format")
    else:
        print(f"\n✗ MISMATCH: Stored format does not match expected")
        print(f"  Difference: '{utc_time_stored}' vs '{expected_format}'")
else:
    print("No records found")

cursor.close()
conn.close()

