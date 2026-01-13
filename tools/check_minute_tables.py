"""Check minute tables for data"""
import mysql.connector

conn = mysql.connector.connect(
    host='127.0.0.1',
    port=3306,
    user='root',
    password='lokesh',
    database='minute_data'
)

cursor = conn.cursor()

# Check all minute tables
tables = ['xauusd_minute', 'eurusd_minute', 'eurjpy_minute', 'usdjpy_minute', 'btcusd_minute']

print("=" * 70)
print("Minute Tables Data Count")
print("=" * 70)

for table in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = cursor.fetchone()[0]
        print(f"{table:20s}: {count:6d} records")
        
        # Get latest timestamp if any records exist
        if count > 0:
            cursor.execute(f"SELECT MAX(`timestamp`), MAX(CAST(`utc_time` AS CHAR(50))) FROM `{table}`")
            row = cursor.fetchone()
            print(f"  Latest: timestamp={row[0]}, utc_time={row[1]}")
    except Exception as e:
        print(f"{table:20s}: ERROR - {e}")

cursor.close()
conn.close()

