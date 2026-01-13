"""
Drop XAUSD Tick Level Table Script
Drops the xausd_tick_level table from the MySQL forex database
"""

import sys
import argparse
import mysql.connector
from mysql.connector import Error
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import Config

# Load MySQL configuration from config.json
config_loader = Config()
mysql_config_data = config_loader.get('mysql', {})

MYSQL_CONFIG = {
    'host': mysql_config_data.get('host', '127.0.0.1'),
    'port': mysql_config_data.get('port', 3306),
    'user': mysql_config_data.get('username', 'root'),
    'password': mysql_config_data.get('password', 'lokesh')
}
DATABASE_NAME = mysql_config_data.get('database', 'forex')
# Drop xausd_tick_level (single 'u') - the incorrect table name
TABLE_NAME = 'xausd_tick_level'


def verify_connection():
    """Verify MySQL connection"""
    try:
        config = MYSQL_CONFIG.copy()
        config['database'] = DATABASE_NAME
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchall()  # Consume the result
        cursor.close()
        conn.close()
        print(f"[OK] MySQL connection successful: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{DATABASE_NAME}")
        return True
    except Error as e:
        print(f"[ERROR] MySQL connection failed: {e}")
        return False


def check_table_exists():
    """Check if the table exists"""
    try:
        config = MYSQL_CONFIG.copy()
        config['database'] = DATABASE_NAME
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        cursor.execute(f"SHOW TABLES LIKE '{TABLE_NAME}'")
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            print(f"[INFO] Table '{TABLE_NAME}' exists")
            return True
        else:
            print(f"[INFO] Table '{TABLE_NAME}' does not exist")
            return False
    except Error as e:
        print(f"[ERROR] Failed to check table existence: {e}")
        return False


def drop_table():
    """Drop the xausd_tick_level table"""
    try:
        config = MYSQL_CONFIG.copy()
        config['database'] = DATABASE_NAME
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # Drop the table
        cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        conn.commit()
        
        print(f"[OK] Table '{TABLE_NAME}' dropped successfully")
        
        cursor.close()
        conn.close()
        return True
    except Error as e:
        print(f"[ERROR] Failed to drop table: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Drop XAUSD tick level table from MySQL')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    args = parser.parse_args()
    
    print("=" * 70)
    print("  Drop XAUSD Tick Level Table")
    print("=" * 70)
    print(f"Target Database: {DATABASE_NAME}")
    print(f"Target Table: {TABLE_NAME}")
    print(f"Target Host: {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}")
    print()
    
    # Verify connection
    if not verify_connection():
        print("\n[ERROR] Cannot proceed without database connection")
        sys.exit(1)
    
    # Check if table exists
    table_exists = check_table_exists()
    
    if not table_exists:
        print(f"\n[INFO] Table '{TABLE_NAME}' does not exist. Nothing to drop.")
        sys.exit(0)
    
    # Confirm deletion (unless --yes flag is provided)
    if not args.yes:
        print(f"\n[WARNING] This will permanently delete the table '{TABLE_NAME}' and all its data!")
        try:
            response = input("Are you sure you want to continue? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print("[INFO] Operation cancelled by user")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print("\n[ERROR] Cannot read input. Use --yes flag for non-interactive mode.")
            sys.exit(1)
    
    # Drop the table
    if not drop_table():
        print("\n[ERROR] Failed to drop table")
        sys.exit(1)
    
    # Verify deletion
    if not check_table_exists():
        print(f"\n[OK] Table '{TABLE_NAME}' successfully deleted and verified")
    else:
        print(f"\n[WARNING] Table '{TABLE_NAME}' may still exist (verification failed)")
    
    print()
    print("=" * 70)
    print("[OK] Operation complete!")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()

