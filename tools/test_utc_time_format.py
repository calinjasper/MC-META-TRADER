"""
Test script to verify UTC time format matches MetaTrader 5 format
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from zoneinfo import ZoneInfo
from src.data.mysql_manager import MySQLManager

UTC = ZoneInfo("UTC")

def test_utc_format():
    """Test that UTC time format matches MT5 format"""
    print("=" * 70)
    print("Testing UTC Time Format")
    print("=" * 70)
    print()
    
    # Initialize MySQL manager
    try:
        mysql_manager = MySQLManager('127.0.0.1', 3306, 'root', 'lokesh', 'forex')
        mysql_manager.initialize()
    except Exception as e:
        print(f"Error initializing MySQL manager: {e}")
        return False
    
    # Test 1: Format current UTC time
    print("Test 1: Format current UTC time")
    now_utc = datetime.now(UTC)
    formatted = mysql_manager._format_utc_timestamp(now_utc)
    print(f"  Current UTC: {now_utc}")
    print(f"  Formatted:   '{formatted}'")
    print(f"  Length:      {len(formatted)} (expected: 23)")
    is_valid = len(formatted) == 23 and formatted.endswith(' UTC')
    print(f"  Valid:       {'YES' if is_valid else 'NO'}")
    print()
    
    # Test 2: Format a specific UTC time (matching MT5 format)
    print("Test 2: Format specific UTC time (2025-12-30 16:50:00 UTC)")
    test_time = datetime(2025, 12, 30, 16, 50, 0, tzinfo=UTC)
    formatted = mysql_manager._format_utc_timestamp(test_time)
    expected = "2025-12-30 16:50:00 UTC"
    print(f"  Test time:   {test_time}")
    print(f"  Formatted:   '{formatted}'")
    print(f"  Expected:    '{expected}'")
    matches = formatted == expected
    print(f"  Match:       {'YES' if matches else 'NO'}")
    print()
    
    # Test 3: Test with tick data structure (simulating MT5 tick)
    print("Test 3: Test with simulated MT5 tick data")
    tick_time = datetime.now(UTC)
    tick_data = {
        'time': tick_time,
        'bid': 2650.5,
        'ask': 2650.6,
        'last': 2650.55
    }
    
    # Format the time
    formatted = mysql_manager._format_utc_timestamp(tick_time)
    print(f"  Tick time:   {tick_time}")
    print(f"  Formatted:   '{formatted}'")
    print(f"  Length:      {len(formatted)}")
    print(f"  Type:        {type(formatted)}")
    is_valid = isinstance(formatted, str) and len(formatted) == 23
    print(f"  Valid:       {'YES' if is_valid else 'NO'}")
    print()
    
    # Test 4: Verify format matches MT5's UTC time display
    print("Test 4: Verify format matches MT5 UTC time")
    print("  MT5 displays UTC time as: 'YYYY-MM-DD HH:MM:SS UTC'")
    print(f"  Our format:                '{formatted}'")
    format_ok = formatted.endswith(' UTC') and len(formatted.split()) == 3
    print(f"  Format check:              {'YES' if format_ok else 'NO'}")
    print()
    
    # Test 5: Check database storage (if possible)
    print("Test 5: Check latest database record")
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host='127.0.0.1',
            port=3306,
            user='root',
            password='lokesh',
            database='forex'
        )
        cursor = conn.cursor()
        cursor.execute('SELECT id, timestamp, utc_time, LENGTH(utc_time) as len FROM xauusd_tick_level ORDER BY id DESC LIMIT 1')
        row = cursor.fetchone()
        if row:
            print(f"  Latest record ID: {row[0]}")
            print(f"  Timestamp (ms):   {row[1]}")
            print(f"  UTC time stored:   '{row[2]}'")
            print(f"  Length:           {row[3]}")
            is_valid_format = row[3] == 23 and isinstance(row[2], str)
            print(f"  Valid format:      {'YES' if is_valid_format else 'NO'}")
            
            # Convert timestamp back to UTC
            ts_sec = row[1] / 1000
            dt_from_ts = datetime.fromtimestamp(ts_sec, tz=UTC)
            expected_format = mysql_manager._format_utc_timestamp(dt_from_ts)
            print(f"  Expected format:  '{expected_format}'")
            matches = str(row[2]) == expected_format
            print(f"  Matches:          {'YES' if matches else 'NO'}")
        else:
            print("  No records found in database")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"  Error checking database: {e}")
    print()
    
    print("=" * 70)
    print("Test Complete")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    test_utc_format()

