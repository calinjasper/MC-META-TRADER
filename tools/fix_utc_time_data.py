"""Fix existing UTC time data in database - convert timedelta to proper UTC format"""
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

# Get all tables
cursor.execute("SHOW TABLES LIKE '%_tick_level'")
tables = [row[0] for row in cursor.fetchall()]

print(f"Found {len(tables)} tick tables: {tables}")

for table_name in tables:
    print(f"\nProcessing table: {table_name}")
    
    # Get records with invalid utc_time (timedelta or time-only format)
    # Check all records, not just 100
    cursor.execute(f"""
        SELECT id, timestamp, utc_time 
        FROM `{table_name}` 
        WHERE LENGTH(utc_time) < 20 OR utc_time NOT LIKE '%-%-% %:%:% UTC'
        ORDER BY id DESC
    """)
    
    records = cursor.fetchall()
    print(f"  Found {len(records)} records with invalid utc_time format")
    
    updated = 0
    for record_id, timestamp_ms, utc_time_old in records:
        # Convert timestamp_ms to UTC datetime
        timestamp_sec = timestamp_ms / 1000
        dt_utc = datetime.fromtimestamp(timestamp_sec, tz=UTC)
        utc_time_new = dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Update the record
        update_sql = f"UPDATE `{table_name}` SET `utc_time` = %s WHERE `id` = %s"
        cursor.execute(update_sql, (utc_time_new, record_id))
        
        updated += 1
        if updated % 10 == 0:
            print(f"    Updated {updated} records...")
    
    conn.commit()
    print(f"  Updated {updated} records in {table_name}")

cursor.close()
conn.close()

print("\nDone! All invalid utc_time values have been fixed.")

