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

# Query timestamp from logs
query_ts = 1767095640000
dt = datetime.fromtimestamp(query_ts/1000, UTC)
print(f'Query timestamp: {query_ts}')
print(f'Represents: {dt} UTC = {dt.astimezone(IST)} IST')
print()

# Check what timestamps exist in database
cursor.execute('''
    SELECT timestamp, utc_time 
    FROM xauusd_minute 
    WHERE timestamp >= %s 
    ORDER BY timestamp ASC 
    LIMIT 20
''', (query_ts,))

rows = cursor.fetchall()
print(f'First 20 records (ASC order) after query timestamp:')
for r in rows:
    ts = r['timestamp']
    dt_utc = datetime.fromtimestamp(ts/1000, UTC)
    dt_ist = dt_utc.astimezone(IST)
    print(f'  TS: {ts}, UTC: {r["utc_time"]}, IST: {dt_ist}')

print()
print('What timestamp would 22:54 IST be?')
dt_2254_ist = datetime(2025, 12, 30, 22, 54, 0, tzinfo=IST)
ts_2254 = int(dt_2254_ist.timestamp() * 1000)
print(f'22:54 IST = {dt_2254_ist.astimezone(UTC)} UTC = timestamp {ts_2254}')

cursor.close()
conn.close()

