"""Verify all tick tables are empty"""
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

print("Verifying tables are empty:")
all_empty = True
for table in tables:
    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
    count = cursor.fetchone()[0]
    status = "EMPTY" if count == 0 else f"{count} records"
    print(f"  {table}: {status}")
    if count > 0:
        all_empty = False

cursor.close()
conn.close()

if all_empty:
    print("\n[SUCCESS] All tables are empty!")
else:
    print("\n[WARNING] Some tables still have records")

