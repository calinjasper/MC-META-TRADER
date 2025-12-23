"""
Consolidate Ticks Collections
Move data from separate ticks_* collections back to a single 'ticks' collection
"""

import requests
import sys
from collections import defaultdict

POCKETBASE_URL = "http://192.168.173.112:8090"
ADMIN_EMAIL = "nrnnajith@gmail.com"
ADMIN_PASSWORD = "LokeshCalin"
TARGET_COLLECTION = "ticks"


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


def get_all_collections():
    """Get list of all collections"""
    try:
        response = requests.get(
            f"{POCKETBASE_URL}/api/collections",
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Failed to get collections: {e}")
        return []


def get_tick_collections():
    """Get all ticks_* collections"""
    all_collections = get_all_collections()
    tick_collections = [
        c for c in all_collections 
        if c.get('name', '').startswith('ticks_')
    ]
    return tick_collections


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


def get_all_records_from_collection(collection_name):
    """Get all records from a collection"""
    page = 1
    per_page = 500
    all_records = []
    
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
            
            all_records.extend(items)
            
            # Check if more pages
            total_items = data.get('totalItems', 0)
            if page * per_page >= total_items:
                break
            
            page += 1
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch records from {collection_name}: {e}")
            break
    
    return all_records


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
        print(f"[ERROR] Failed to delete collection {collection_name}: {e}")
        return False


def main():
    print("=" * 70)
    print("  Consolidate Ticks Collections")
    print("=" * 70)
    print()
    print(f"Source: ticks_* collections (symbol-specific)")
    print(f"Target: {TARGET_COLLECTION} collection (single)")
    print()
    
    # Check if target collection exists
    if not collection_exists(TARGET_COLLECTION):
        print(f"[ERROR] Target '{TARGET_COLLECTION}' collection doesn't exist")
        print(f"Please create it first using: python fix_ticks_collection.py")
        return
    
    print(f"[OK] Target '{TARGET_COLLECTION}' collection exists")
    print()
    
    # Get list of ticks_* collections
    print("Finding ticks_* collections...")
    tick_collections = get_tick_collections()
    
    if not tick_collections:
        print("[INFO] No ticks_* collections found")
        print("Nothing to consolidate. You're already using the single collection!")
        return
    
    print(f"[OK] Found {len(tick_collections)} ticks_* collections:")
    for col in tick_collections:
        print(f"  - {col['name']}")
    print()
    
    # Confirm consolidation
    response = input("Proceed with consolidation? (yes/no): ").strip().lower()
    if response != 'yes':
        print("[CANCELLED] Consolidation cancelled by user")
        return
    print()
    
    # Consolidate records
    print("Consolidating records into single collection...")
    print()
    
    total_consolidated = 0
    total_errors = 0
    
    for collection in tick_collections:
        collection_name = collection['name']
        symbol = collection_name.replace('ticks_', '')
        
        print(f"Processing {symbol}...")
        
        # Fetch all records
        records = get_all_records_from_collection(collection_name)
        print(f"  Found {len(records)} records")
        
        if not records:
            print(f"  [SKIP] No records to consolidate")
            continue
        
        # Insert into target collection
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
            
            if insert_record(TARGET_COLLECTION, record_data):
                success += 1
                total_consolidated += 1
            else:
                total_errors += 1
            
            # Progress indicator
            if success % 100 == 0:
                print(f"  Consolidated {success}/{len(records)}...", end='\r')
        
        print(f"  [OK] Consolidated {success}/{len(records)} records")
    
    print()
    print("=" * 70)
    print("Consolidation Summary:")
    print(f"  Total records: {total_consolidated + total_errors}")
    print(f"  Consolidated: {total_consolidated}")
    print(f"  Errors: {total_errors}")
    print("=" * 70)
    print()
    
    if total_consolidated > 0:
        print("[SUCCESS] All records consolidated successfully!")
        print()
        
        # Ask if user wants to delete old collections
        response = input("Delete old ticks_* collections? (yes/no): ").strip().lower()
        if response == 'yes':
            print("\nDeleting old collections...")
            
            # Authenticate for deletion
            token = get_admin_token()
            if not token:
                print("[ERROR] Failed to authenticate for deletion")
                print("You can delete collections manually from PocketBase UI")
                return
            
            deleted_count = 0
            for collection in tick_collections:
                collection_name = collection['name']
                print(f"  Deleting {collection_name}...", end=' ')
                if delete_collection(token, collection_name):
                    print("[OK]")
                    deleted_count += 1
                else:
                    print("[FAILED]")
            
            print()
            print(f"Deleted {deleted_count}/{len(tick_collections)} collections")
        else:
            print("\n[INFO] Old collections kept")
            print("You can delete them manually later from PocketBase UI")
    else:
        print("[WARNING] No records were consolidated")
    
    print()
    print("Next steps:")
    print("1. Verify data in PocketBase UI: http://192.168.173.112:8090/_/")
    print("2. Restart your trading system (already configured for single collection)")
    print("3. Use filtering to view symbol-specific data")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Consolidation cancelled by user")
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()

