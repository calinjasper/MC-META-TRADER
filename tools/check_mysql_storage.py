"""
Diagnostic script to check MySQL tick storage
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import mysql.connector
from mysql.connector import Error
from src.config import Config

def check_mysql_connection():
    """Check MySQL connection"""
    config_loader = Config()
    mysql_config = config_loader.get('mysql', {})
    
    config = {
        'host': mysql_config.get('host', '127.0.0.1'),
        'port': mysql_config.get('port', 3306),
        'username': mysql_config.get('username', 'root'),
        'password': mysql_config.get('password', 'lokesh'),
        'database': mysql_config.get('database', 'forex')
    }
    
    print("=" * 70)
    print("MySQL Storage Diagnostic")
    print("=" * 70)
    print(f"Host: {config['host']}:{config['port']}")
    print(f"Database: {config['database']}")
    print(f"User: {config['username']}")
    print()
    
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        print("[OK] MySQL connection successful")
        
        # Check if tables exist
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\n[INFO] Found {len(tables)} tables in database:")
        for table in tables:
            print(f"  - {table}")
        
        # Check record counts for each symbol table
        allowed_symbols = ['XAUUSD', 'EURUSD', 'EURJPY', 'USDJPY', 'BTCUSD']
        print("\n[INFO] Record counts per symbol table:")
        for symbol in allowed_symbols:
            table_name = f"{symbol.lower()}_tick_level"
            if table_name in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"  - {table_name}: {count} records")
                
                # Get latest record
                if count > 0:
                    cursor.execute(f"SELECT timestamp, utc_time, bid, ask, last FROM {table_name} ORDER BY timestamp DESC LIMIT 1")
                    latest = cursor.fetchone()
                    if latest:
                        print(f"    Latest: timestamp={latest[0]}, UTC={latest[1]}, bid={latest[2]}, ask={latest[3]}, last={latest[4]}")
            else:
                print(f"  - {table_name}: TABLE NOT FOUND")
        
        cursor.close()
        conn.close()
        
        print("\n[INFO] Checking MySQL manager initialization...")
        from src.data.mysql_manager import MySQLManager
        
        mysql_manager = MySQLManager(**config)
        if mysql_manager.initialize():
            print("[OK] MySQL manager initialized successfully")
        else:
            print("[ERROR] MySQL manager initialization failed")
        
        return True
        
    except Error as e:
        print(f"[ERROR] MySQL connection failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_mysql_connection()

