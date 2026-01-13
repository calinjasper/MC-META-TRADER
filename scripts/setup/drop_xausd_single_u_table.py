"""
Drop xausd_tick_level table (single 'u')
This is the incorrect table name that should be dropped
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import mysql.connector
from mysql.connector import Error
from src.config import Config

config_loader = Config()
mysql_config = config_loader.get('mysql', {})

config = {
    'host': mysql_config.get('host', '127.0.0.1'),
    'port': mysql_config.get('port', 3306),
    'user': mysql_config.get('username', 'root'),
    'password': mysql_config.get('password', 'lokesh'),
    'database': mysql_config.get('database', 'forex')
}

TABLE_NAME = 'xausd_tick_level'  # Single 'u'

print("=" * 70)
print("  Drop xausd_tick_level Table (single 'u')")
print("=" * 70)
print(f"Target Database: {config['database']}")
print(f"Target Table: {TABLE_NAME}")
print()

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute(f"SHOW TABLES LIKE '{TABLE_NAME}'")
    exists = cursor.fetchone() is not None
    
    if exists:
        print(f"[INFO] Table '{TABLE_NAME}' exists. Dropping...")
        cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        conn.commit()
        print(f"[OK] Table '{TABLE_NAME}' dropped successfully")
    else:
        print(f"[INFO] Table '{TABLE_NAME}' does not exist. Nothing to drop.")
    
    # List all tables to verify
    cursor.execute("SHOW TABLES")
    all_tables = [row[0] for row in cursor.fetchall()]
    xausd_tables = [t for t in all_tables if 'xausd' in t.lower()]
    
    print(f"\n[INFO] All XAUSD-related tables: {xausd_tables}")
    print(f"[INFO] Total tables in database: {len(all_tables)}")
    
    cursor.close()
    conn.close()
    
    print("\n[OK] Operation complete!")
    
except Error as e:
    print(f"[ERROR] Database error: {e}")
    sys.exit(1)

