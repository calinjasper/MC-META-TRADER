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

# What timestamp should 17:24 IST have?
dt_1724_ist = datetime(2025, 12, 30, 17, 24, 0, tzinfo=IST)
ts_1724_ist_correct = int(dt_1724_ist.timestamp() * 1000)
print(f'17:24 IST should have timestamp: {ts_1724_ist_correct}')
print(f'Which represents: {datetime.fromtimestamp(ts_1724_ist_correct/1000, UTC)} UTC = {dt_1724_ist} IST')
print()

# Check for data with this timestamp
cursor.execute('''
    SELECT timestamp, utc_time, open, high, low, close 
    FROM xauusd_minute 
    WHERE timestamp = %s
''', (ts_1724_ist_correct,))
rows = cursor.fetchall()
print(f'Records with timestamp {ts_1724_ist_correct} (17:24 IST): {len(rows)}')
for r in rows:
    print(f'  TS: {r["timestamp"]}, UTC: {r["utc_time"]}')

print()

# Check what timestamp the database has for utc_time showing 17:24
cursor.execute('''
    SELECT timestamp, utc_time 
    FROM xauusd_minute 
    WHERE utc_time LIKE '2025-12-30 17:24%' 
    ORDER BY timestamp ASC 
    LIMIT 5
''')
rows = cursor.fetchall()
print('Records with utc_time showing "2025-12-30 17:24":')
for r in rows:
    ts = r['timestamp']
    dt_utc = datetime.fromtimestamp(ts/1000, UTC)
    dt_ist = dt_utc.astimezone(IST)
    print(f'  TS: {ts}, UTC: {r["utc_time"]}, IST: {dt_ist}')

print()

# Check range around 17:24 IST
ts_start = ts_1724_ist_correct - 60000  # 1 minute before
ts_end = ts_1724_ist_correct + 60000    # 1 minute after
cursor.execute('''
    SELECT timestamp, utc_time 
    FROM xauusd_minute 
    WHERE timestamp >= %s AND timestamp <= %s
    ORDER BY timestamp ASC
''', (ts_start, ts_end))
rows = cursor.fetchall()
print(f'Records in range [{ts_start}, {ts_end}] (around 17:24 IST):')
for r in rows:
    ts = r['timestamp']
    dt_utc = datetime.fromtimestamp(ts/1000, UTC)
    dt_ist = dt_utc.astimezone(IST)
    print(f'  TS: {ts}, UTC: {r["utc_time"]}, IST: {dt_ist}')

cursor.close()
conn.close()

