"""
Migration Script: Change timestamp_ist to utc_time
Alters all tick_level tables to rename timestamp_ist column to utc_time
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import mysql.connector
from mysql.connector import Error
from src.config import Config

ALLOWED_SYMBOLS = ['XAUUSD', 'EURUSD', 'EURJPY', 'USDJPY', 'BTCUSD']


def main():
    parser = argparse.ArgumentParser(description='Migrate timestamp_ist to utc_time in MySQL tables')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()
    
    print("=" * 70)
    print("  Migration: timestamp_ist to utc_time")
    print("=" * 70)
    print()
    
    # Load MySQL config
    config_loader = Config()
    mysql_config = config_loader.get('mysql', {})
    
    db_config = {
        'host': mysql_config.get('host', '127.0.0.1'),
        'port': mysql_config.get('port', 3306),
        'user': mysql_config.get('username', 'root'),
        'password': mysql_config.get('password', 'lokesh'),
        'database': mysql_config.get('database', 'forex')
    }
    
    print(f"Database: {db_config['database']}")
    print(f"Host: {db_config['host']}:{db_config['port']}")
    print()
    
    # Connect to MySQL
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        print("[OK] Connected to MySQL")
    except Error as e:
        print(f"[ERROR] Failed to connect: {e}")
        sys.exit(1)
    
    try:
        # Check which tables exist and have timestamp_ist column
        tables_to_migrate = []
        for symbol in ALLOWED_SYMBOLS:
            table_name = f"{symbol.lower()}_tick_level"
            
            # Check if table exists
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            if not cursor.fetchone():
                print(f"[SKIP] Table '{table_name}' does not exist")
                continue
            
            # Check if column exists
            cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE 'timestamp_ist'")
            if cursor.fetchone():
                tables_to_migrate.append(table_name)
                print(f"[INFO] Table '{table_name}' has timestamp_ist column")
            else:
                # Check if utc_time already exists
                cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE 'utc_time'")
                if cursor.fetchone():
                    print(f"[SKIP] Table '{table_name}' already has utc_time column")
                else:
                    print(f"[INFO] Table '{table_name}' does not have timestamp_ist column")
        
        if not tables_to_migrate:
            print("\n[INFO] No tables need migration. All tables are up to date.")
            return
        
        print(f"\n[INFO] Found {len(tables_to_migrate)} tables to migrate:")
        for table in tables_to_migrate:
            print(f"  - {table}")
        
        # Confirm migration (unless --yes flag is provided)
        if not args.yes:
            print("\n[WARNING] This will rename timestamp_ist to utc_time in the above tables.")
            try:
                response = input("Continue? (yes/no): ").strip().lower()
                if response not in ['yes', 'y']:
                    print("[INFO] Migration cancelled")
                    return
            except (EOFError, KeyboardInterrupt):
                print("\n[ERROR] Cannot read input. Use --yes flag for non-interactive mode.")
                sys.exit(1)
        
        # Perform migration
        print("\n[INFO] Starting migration...")
        success_count = 0
        
        for table_name in tables_to_migrate:
            try:
                # Use RENAME COLUMN (MySQL 8.0+ syntax - simpler and cleaner)
                alter_sql = f"ALTER TABLE `{table_name}` RENAME COLUMN `timestamp_ist` TO `utc_time`"
                cursor.execute(alter_sql)
                conn.commit()
                print(f"[OK] Migrated '{table_name}': timestamp_ist to utc_time")
                success_count += 1
            except Error as e:
                # Fallback: Use ADD COLUMN + UPDATE + DROP COLUMN approach
                try:
                    # Step 1: Add new column
                    cursor.execute(f"ALTER TABLE `{table_name}` ADD COLUMN `utc_time` VARCHAR(50) NULL AFTER `timestamp`")
                    
                    # Step 2: Copy data (for now, just copy as-is - will be updated by new code)
                    # Note: Existing IST data will remain, but new data will be UTC
                    cursor.execute(f"UPDATE `{table_name}` SET `utc_time` = `timestamp_ist` WHERE `timestamp_ist` IS NOT NULL")
                    
                    # Step 3: Drop old column
                    cursor.execute(f"ALTER TABLE `{table_name}` DROP COLUMN `timestamp_ist`")
                    
                    conn.commit()
                    print(f"[OK] Migrated '{table_name}' (using ADD/DROP): timestamp_ist to utc_time")
                    success_count += 1
                except Error as e2:
                    print(f"[ERROR] Failed to migrate '{table_name}': {e2}")
                    conn.rollback()
        
        print()
        print("=" * 70)
        print("  Migration Summary")
        print("=" * 70)
        print(f"Successfully migrated: {success_count}/{len(tables_to_migrate)} tables")
        
        if success_count == len(tables_to_migrate):
            print("[OK] All tables migrated successfully!")
        else:
            print("[WARNING] Some tables failed to migrate. Check errors above.")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()

