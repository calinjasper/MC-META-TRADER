import mysql.connector
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo('Asia/Kolkata')
UTC = ZoneInfo('UTC')

conn = mysql.connector.connect(
    host='127.0.0.1',
    port=3306,
    user='root',
    password='lokesh',
    database='minute_data'
)
cursor = conn.cursor(dictionary=True)

# Check the exact format of utc_time
cursor.execute('''
    SELECT timestamp, utc_time, CAST(utc_time AS CHAR(50)) as utc_time_str
    FROM xauusd_minute 
    WHERE timestamp = 1767115440000
''')
row = cursor.fetchone()
if row:
    print(f'Record with timestamp 1767115440000:')
    print(f'  Timestamp: {row["timestamp"]}')
    print(f'  utc_time (raw): {row["utc_time"]}')
    print(f'  utc_time (string): {row["utc_time_str"]}')
    print(f'  Type: {type(row["utc_time"])}')
    
    # Convert timestamp to see what it represents
    ts = row['timestamp']
    dt_utc = datetime.fromtimestamp(ts/1000, UTC)
    dt_ist = dt_utc.astimezone(IST)
    print(f'  Represents: {dt_utc} UTC = {dt_ist} IST')
else:
    print('No record found with timestamp 1767115440000')

# Check all records with timestamp around 17:24 UTC
cursor.execute('''
    SELECT timestamp, utc_time 
    FROM xauusd_minute 
    WHERE timestamp >= 1767115400000 AND timestamp <= 1767115500000
    ORDER BY timestamp ASC
    LIMIT 10
''')
rows = cursor.fetchall()
print(f'\nRecords around timestamp 1767115440000 (17:24 UTC):')
for r in rows:
    ts = r['timestamp']
    dt_utc = datetime.fromtimestamp(ts/1000, UTC)
    dt_ist = dt_utc.astimezone(IST)
    print(f'  TS: {ts}, UTC: {r["utc_time"]}, IST: {dt_ist}')

cursor.close()
conn.close()

