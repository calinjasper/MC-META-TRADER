"""Verify minute data storage for all symbols"""
import mysql.connector
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")

conn = mysql.connector.connect(
    host='127.0.0.1',
    port=3306,
    user='root',
    password='lokesh',
    database='minute_data'
)

cursor = conn.cursor()

symbols = ['XAUUSD', 'EURUSD', 'EURJPY', 'USDJPY', 'BTCUSD']

print("=" * 80)
print("Minute Data Storage Verification")
print("=" * 80)
print()

for symbol in symbols:
    table_name = f"{symbol.lower()}_minute"
    
    try:
        # Count records
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        count = cursor.fetchone()[0]
        
        print(f"{symbol:8s} ({table_name:20s}): {count:6d} records", end="")
        
        if count > 0:
            # Get date range
            cursor.execute(f"""
                SELECT 
                    MIN(`timestamp`), 
                    MAX(`timestamp`),
                    MIN(CAST(`utc_time` AS CHAR(50))),
                    MAX(CAST(`utc_time` AS CHAR(50)))
                FROM `{table_name}`
            """)
            row = cursor.fetchone()
            min_ts, max_ts, min_utc, max_utc = row
            
            # Convert timestamps to readable format
            min_dt = datetime.fromtimestamp(min_ts / 1000, tz=UTC)
            max_dt = datetime.fromtimestamp(max_ts / 1000, tz=UTC)
            
            print(f" | Range: {min_dt.strftime('%Y-%m-%d %H:%M')} to {max_dt.strftime('%Y-%m-%d %H:%M')} UTC")
            
            # Get sample record
            cursor.execute(f"""
                SELECT `open`, `high`, `low`, `close`, `tick_count`
                FROM `{table_name}`
                ORDER BY `timestamp` DESC
                LIMIT 1
            """)
            sample = cursor.fetchone()
            if sample:
                print(f"         Latest OHLC: O={sample[0]}, H={sample[1]}, L={sample[2]}, C={sample[3]}, Ticks={sample[4]}")
        else:
            print(" | NO DATA")
            
    except Exception as e:
        print(f" | ERROR: {e}")

print()
print("=" * 80)

cursor.close()
conn.close()

