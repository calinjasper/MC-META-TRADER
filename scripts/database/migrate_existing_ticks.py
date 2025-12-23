"""
Migrate Existing Ticks
Migrate tick data from the old mixed 'ticks' collection to symbol-specific collections
"""

import requests
import sys
from pathlib import Path
from collections import defaultdict
import time

POCKETBASE_URL = "http://192.168.173.112:8090"
ADMIN_EMAIL = "nrnnajith@gmail.com"
ADMIN_PASSWORD = "LokeshCalin"

OLD_COLLECTION = "ticks"


def get_admin_token():
    """Authenticate and get admin token"""
    try:
        response = requests.post(
            f"{POCKETBASE_URL}/api/admins/auth-with-password",
            json={"identity": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=5
        )
        response.raise_for_status()
        return response.json()['token']
    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        return None


def collection_exists(collection_name):
    """Check if a collection exists"""
    try:
        response = requests.get(
            f"{POCKETBASE_URL}/api/collections/{collection_name}",
            timeout=2
        )
        return response.status_code == 200
    except:
        return False


def get_all_records(collection_name, page=1, per_page=500):
    """
    Get all records from a collection (paginated)
    
    Yields:
        Record dictionaries
    """
    while True:
        url = f"{POCKETBASE_URL}/api/collections/{collection_name}/records"
        params = {
            'page': page,
            'perPage': per_page,
            'sort': 'timestamp'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                break
            
            for item in items:
                yield item
            
            # Check if more pages
            total_items = data.get('totalItems', 0)
            if page * per_page >= total_items:
                break
            
            page += 1
        except Exception as e:
            print(f"[ERROR] Failed to fetch records: {e}")
            break


def create_tick_collection(token, collection_name):
    """Create a new tick collection"""
    headers = {"Authorization": f"Bearer {token}"}
    
    schema = [
        {"name": "symbol", "type": "text", "required": True},
        {"name": "timestamp", "type": "number", "required": True},
        {"name": "bid", "type": "number", "required": True},
        {"name": "ask", "type": "number", "required": True},
        {"name": "last", "type": "number", "required": False},
        {"name": "volume", "type": "number", "required": False},
        {"name": "spread", "type": "number", "required": False}
    ]
    
    collection_data = {
        "name": collection_name,
        "type": "base",
        "schema": schema,
        "listRule": "",
        "viewRule": "",
        "createRule": "",
        "updateRule": "",
        "deleteRule": ""
    }
    
    try:
        response = requests.post(
            f"{POCKETBASE_URL}/api/collections",
            headers=headers,
            json=collection_data,
            timeout=5
        )
        response.raise_for_status()
        return True
    except Exception as e:
        if "already exists" in str(e).lower():
            return True
        print(f"[ERROR] Failed to create collection {collection_name}: {e}")
        return False


def insert_record(collection_name, record_data):
    """Insert a record into a collection"""
    url = f"{POCKETBASE_URL}/api/collections/{collection_name}/records"
    
    try:
        response = requests.post(url, json=record_data, timeout=5)
        response.raise_for_status()
        return True
    except Exception as e:
        return False


def delete_collection(token, collection_name):
    """Delete a collection"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.delete(
            f"{POCKETBASE_URL}/api/collections/{collection_name}",
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to delete collection: {e}")
        return False


def main():
    print("=" * 70)
    print("  Migrate Existing Ticks to Symbol-Specific Collections")
    print("=" * 70)
    print()
    print(f"Source: {OLD_COLLECTION} collection")
    print(f"Target: ticks_{{SYMBOL}} collections")
    print()
    
    # Check if old collection exists
    if not collection_exists(OLD_COLLECTION):
        print(f"[INFO] Old '{OLD_COLLECTION}' collection doesn't exist")
        print("Nothing to migrate. You're already using symbol-specific collections!")
        print()
        return
    
    # Authenticate
    print("Authenticating...")
    token = get_admin_token()
    if not token:
        print("[ERROR] Failed to authenticate")
        return
    print("[OK] Authenticated")
    print()
    
    # Fetch all records from old collection
    print(f"Fetching records from '{OLD_COLLECTION}' collection...")
    records_by_symbol = defaultdict(list)
    total_records = 0
    
    for record in get_all_records(OLD_COLLECTION):
        symbol = record.get('symbol', 'UNKNOWN')
        records_by_symbol[symbol].append(record)
        total_records += 1
        
        if total_records % 1000 == 0:
            print(f"  Fetched {total_records} records...")
    
    print(f"[OK] Fetched {total_records} records")
    print(f"[OK] Found {len(records_by_symbol)} unique symbols")
    print()
    
    # Show symbol breakdown
    print("Symbol breakdown:")
    for symbol, records in sorted(records_by_symbol.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {symbol}: {len(records)} records")
    print()
    
    # Confirm migration
    response = input("Proceed with migration? (yes/no): ").strip().lower()
    if response != 'yes':
        print("[CANCELLED] Migration cancelled by user")
        return
    print()
    
    # Migrate records
    print("Migrating records to symbol-specific collections...")
    print()
    
    migrated_count = 0
    error_count = 0
    
    for symbol, records in records_by_symbol.items():
        collection_name = f"ticks_{symbol}"
        
        print(f"Processing {symbol} ({len(records)} records)...")
        
        # Create collection if doesn't exist
        if not collection_exists(collection_name):
            if not create_tick_collection(token, collection_name):
                print(f"  [ERROR] Failed to create collection for {symbol}")
                error_count += len(records)
                continue
            print(f"  [OK] Created collection: {collection_name}")
        
        # Insert records
        success = 0
        for record in records:
            # Prepare record data (exclude PocketBase metadata)
            record_data = {
                'symbol': record.get('symbol'),
                'timestamp': record.get('timestamp'),
                'bid': record.get('bid'),
                'ask': record.get('ask'),
                'last': record.get('last'),
                'volume': record.get('volume'),
                'spread': record.get('spread')
            }
            
            if insert_record(collection_name, record_data):
                success += 1
                migrated_count += 1
            else:
                error_count += 1
            
            # Progress indicator
            if success % 100 == 0:
                print(f"  Migrated {success}/{len(records)}...", end='\r')
        
        print(f"  [OK] Migrated {success}/{len(records)} records")
    
    print()
    print("=" * 70)
    print("Migration Summary:")
    print(f"  Total records: {total_records}")
    print(f"  Migrated: {migrated_count}")
    print(f"  Errors: {error_count}")
    print("=" * 70)
    print()
    
    if migrated_count == total_records:
        print("[SUCCESS] All records migrated successfully!")
        print()
        
        # Ask if user wants to delete old collection
        response = input(f"Delete old '{OLD_COLLECTION}' collection? (yes/no): ").strip().lower()
        if response == 'yes':
            print(f"\nDeleting '{OLD_COLLECTION}' collection...")
            if delete_collection(token, OLD_COLLECTION):
                print(f"[OK] Deleted '{OLD_COLLECTION}' collection")
            else:
                print(f"[ERROR] Failed to delete '{OLD_COLLECTION}' collection")
                print("You can delete it manually from PocketBase UI if needed")
        else:
            print(f"\n[INFO] '{OLD_COLLECTION}' collection kept")
            print("You can delete it manually later from PocketBase UI")
    else:
        print("[WARNING] Some records failed to migrate")
        print(f"Please review errors and retry if needed")
    
    print()
    print("Next steps:")
    print("1. Verify data in PocketBase UI: http://192.168.173.112:8090/_/")
    print("2. Restart your trading system")
    print("3. New ticks will be stored in symbol-specific collections")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Migration cancelled by user")
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()

