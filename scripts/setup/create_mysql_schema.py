"""
Create MySQL Schema and Tables Script
Creates the 'forex' schema and tick_level tables for storing raw tick data
"""

import sys
import mysql.connector
from mysql.connector import Error
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# MySQL connection details
MYSQL_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'lokesh'
}

DATABASE_NAME = 'forex'

# Allowed symbols
ALLOWED_SYMBOLS = ['XAUSD', 'EURUSD', 'EURJPY', 'USDJPY', 'BTCUSD']


def create_schema():
    """Create the forex schema if it doesn't exist"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print(f"[OK] Schema '{DATABASE_NAME}' created/verified")
        
        cursor.close()
        conn.close()
        return True
    except Error as e:
        print(f"[ERROR] Failed to create schema: {e}")
        return False


def create_tables():
    """Create tick_level tables for all symbols to store raw tick data"""
    try:
        config = MYSQL_CONFIG.copy()
        config['database'] = DATABASE_NAME
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        for symbol in ALLOWED_SYMBOLS:
            table_name = f"{symbol.lower()}_tick_level"
            create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                timestamp BIGINT NOT NULL,
                utc_time VARCHAR(50),
                bid DECIMAL(20, 8) NOT NULL,
                ask DECIMAL(20, 8) NOT NULL,
                last DECIMAL(20, 8),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
            
            cursor.execute(create_table_sql)
            print(f"[OK] Table '{table_name}' created/verified for raw tick data")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        print(f"[ERROR] Failed to create tables: {e}")
        return False


def verify_connection():
    """Verify MySQL connection"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"[OK] Connected to MySQL Server version: {version[0]}")
        cursor.close()
        conn.close()
        return True
    except Error as e:
        print(f"[ERROR] Failed to connect to MySQL: {e}")
        print(f"       Please check your MySQL server is running and credentials are correct")
        return False


def verify_tables():
    """Verify all tables exist and show their structure"""
    try:
        config = MYSQL_CONFIG.copy()
        config['database'] = DATABASE_NAME
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        print("\n[INFO] Verifying tables...")
        for symbol in ALLOWED_SYMBOLS:
            table_name = f"{symbol}_tick_level"
            cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
            result = cursor.fetchone()
            if result:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"[OK] Table '{table_name}' exists with {count} records")
            else:
                print(f"[WARNING] Table '{table_name}' does not exist")
        
        cursor.close()
        conn.close()
        return True
    except Error as e:
        print(f"[ERROR] Failed to verify tables: {e}")
        return False


def main():
    """Main setup function"""
    print("=" * 70)
    print("  MySQL Database Setup - Forex Schema")
    print("=" * 70)
    print()
    
    # Verify connection
    if not verify_connection():
        print("\n[ERROR] Cannot proceed without database connection")
        sys.exit(1)
    
    # Create schema
    if not create_schema():
        print("\n[ERROR] Failed to create schema")
        sys.exit(1)
    
    # Create tables
    if not create_tables():
        print("\n[ERROR] Failed to create tables")
        sys.exit(1)
    
    # Verify tables
    verify_tables()
    
    print()
    print("=" * 70)
    print("[OK] MySQL database setup complete!")
    print("=" * 70)
    print()
    print(f"Schema: {DATABASE_NAME}")
    print(f"Tables created for symbols: {', '.join(ALLOWED_SYMBOLS)}")
    print()
    print("Table structure: id, timestamp, timestamp_ist, bid, ask, last")
    print("Each table stores raw tick data (not aggregated candles)")
    print()
    print("Next steps:")
    print("1. Start your trading system: python src/main_headless.py")
    print("2. Raw tick data will be stored in MySQL for the 5 allowed symbols")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Setup interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

