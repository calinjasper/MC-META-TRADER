"""
Delete all records from all tick_level tables in the forex database.
This script will empty all tables but keep the table structures intact.
"""
import mysql.connector
from mysql.connector import Error
import sys
import argparse

# Database configuration
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'lokesh',
    'database': 'forex'
}

def get_all_tick_tables(conn):
    """Get all tick_level tables from the database"""
    try:
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES LIKE '%_tick_level'")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables
    except Error as e:
        print(f"[ERROR] Failed to get tables: {e}")
        return []

def get_table_record_count(conn, table_name):
    """Get the number of records in a table"""
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
        count = cursor.fetchone()[0]
        cursor.close()
        return count
    except Error as e:
        print(f"[ERROR] Failed to get count for {table_name}: {e}")
        return 0

def delete_all_records(conn, table_name):
    """Delete all records from a table"""
    try:
        cursor = conn.cursor()
        delete_sql = f"DELETE FROM `{table_name}`"
        cursor.execute(delete_sql)
        deleted_count = cursor.rowcount
        conn.commit()
        cursor.close()
        return deleted_count
    except Error as e:
        print(f"[ERROR] Failed to delete records from {table_name}: {e}")
        conn.rollback()
        return 0

def reset_auto_increment(conn, table_name):
    """Reset AUTO_INCREMENT to 1 for a table"""
    try:
        cursor = conn.cursor()
        reset_sql = f"ALTER TABLE `{table_name}` AUTO_INCREMENT = 1"
        cursor.execute(reset_sql)
        conn.commit()
        cursor.close()
        return True
    except Error as e:
        print(f"[WARNING] Failed to reset AUTO_INCREMENT for {table_name}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Delete all records from all tick_level tables')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()
    
    print("=" * 70)
    print("Delete All Records from Tick Tables")
    print("=" * 70)
    print()
    
    # Connect to database
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("[OK] Connected to MySQL database")
    except Error as e:
        print(f"[ERROR] Failed to connect to database: {e}")
        sys.exit(1)
    
    # Get all tick tables
    tables = get_all_tick_tables(conn)
    if not tables:
        print("[INFO] No tick_level tables found")
        conn.close()
        sys.exit(0)
    
    print(f"[INFO] Found {len(tables)} tables:")
    total_records = 0
    for table in tables:
        count = get_table_record_count(conn, table)
        total_records += count
        print(f"  - {table}: {count:,} records")
    print()
    print(f"[INFO] Total records to delete: {total_records:,}")
    print()
    
    # Confirmation
    if not args.yes:
        response = input("Are you sure you want to delete ALL records from ALL tables? (yes/no): ").strip().lower()
        if response != 'yes':
            print("[INFO] Operation cancelled.")
            conn.close()
            sys.exit(0)
    
    print()
    print("[INFO] Deleting records...")
    print()
    
    # Delete records from each table
    total_deleted = 0
    for table in tables:
        count_before = get_table_record_count(conn, table)
        if count_before == 0:
            print(f"[SKIP] {table}: Already empty")
            continue
        
        deleted = delete_all_records(conn, table)
        count_after = get_table_record_count(conn, table)
        
        if deleted > 0 and count_after == 0:
            print(f"[OK] {table}: Deleted {deleted:,} records")
            total_deleted += deleted
            # Reset AUTO_INCREMENT
            if reset_auto_increment(conn, table):
                print(f"      Reset AUTO_INCREMENT to 1")
        else:
            print(f"[ERROR] {table}: Expected to delete {count_before:,}, but {count_after:,} records remain")
    
    print()
    print("=" * 70)
    print(f"Summary: Deleted {total_deleted:,} records from {len(tables)} tables")
    print("=" * 70)
    
    # Verify all tables are empty
    print()
    print("[INFO] Verifying all tables are empty...")
    all_empty = True
    for table in tables:
        count = get_table_record_count(conn, table)
        if count > 0:
            print(f"[ERROR] {table}: Still has {count:,} records")
            all_empty = False
        else:
            print(f"[OK] {table}: Empty")
    
    if all_empty:
        print()
        print("[SUCCESS] All tables are now empty!")
    else:
        print()
        print("[WARNING] Some tables still have records. Please check manually.")
    
    conn.close()
    print()
    print("[INFO] Database connection closed")

if __name__ == "__main__":
    main()

