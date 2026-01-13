"""Check tick data count in all tables"""
import mysql.connector

conn = mysql.connector.connect(
    host='127.0.0.1',
    port=3306,
    user='root',
    password='lokesh',
    database='forex'
)

cursor = conn.cursor()
tables = ['btcusd_tick_level', 'eurjpy_tick_level', 'eurusd_tick_level', 'usdjpy_tick_level', 'xauusd_tick_level']

print('Checking for tick data:')
total = 0
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
    count = cursor.fetchone()[0]
    total += count
    print(f"  {table}: {count:,} records")

print(f"\nTotal records: {total:,}")

cursor.close()
conn.close()

