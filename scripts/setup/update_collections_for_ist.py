"""
Update PocketBase Collections for IST Timestamps
Adds 'created' field to existing collections and verifies setup
"""

import requests
import sys
import json

POCKETBASE_URL = "http://192.168.173.112:8090"
ADMIN_EMAIL = "nrnnajith@gmail.com"
ADMIN_PASSWORD = "LokeshCalin"

# Collections that need the 'created' field
COLLECTIONS_TO_UPDATE = ["trades", "signals", "ohlc", "indicators"]


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


def get_collection(token, collection_name):
    """Get collection details"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{POCKETBASE_URL}/api/collections/{collection_name}",
            headers=headers,
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"[ERROR] Failed to get collection {collection_name}: {e}")
        return None


def update_collection_schema(token, collection_name):
    """Add 'created' field to collection schema if it doesn't exist"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get current collection
    collection = get_collection(token, collection_name)
    if not collection:
        print(f"[SKIP] Collection {collection_name} does not exist")
        return False
    
    # Check if 'created' field already exists
    schema = collection.get('schema', [])
    has_created = any(field.get('name') == 'created' for field in schema)
    
    if has_created:
        print(f"[SKIP] Collection {collection_name} already has 'created' field")
        return True
    
    # Add 'created' field to schema
    schema.append({
        "name": "created",
        "type": "text",
        "required": False
    })
    
    # Update collection
    update_data = {
        "schema": schema
    }
    
    try:
        response = requests.patch(
            f"{POCKETBASE_URL}/api/collections/{collection_name}",
            headers=headers,
            json=update_data,
            timeout=10
        )
        response.raise_for_status()
        print(f"[OK] Added 'created' field to {collection_name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update {collection_name}: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"       Response: {e.response.text}")
        return False


def list_tick_collections(token):
    """List all tick collections"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{POCKETBASE_URL}/api/collections",
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        collections = response.json().get('items', [])
        tick_collections = [
            c['name'] for c in collections
            if c.get('name', '').startswith('ticks_')
        ]
        return tick_collections
    except Exception as e:
        print(f"[ERROR] Failed to list collections: {e}")
        return []


def check_tick_collection_schema(token, collection_name):
    """Check if tick collection has 'created' field"""
    collection = get_collection(token, collection_name)
    if not collection:
        return False
    
    schema = collection.get('schema', [])
    has_created = any(field.get('name') == 'created' for field in schema)
    return has_created


def main():
    print("=" * 70)
    print("  Update PocketBase Collections for IST Timestamps")
    print("=" * 70)
    print()
    
    # Check if PocketBase is running
    try:
        response = requests.get(f"{POCKETBASE_URL}/api/health", timeout=2)
        if response.status_code != 200:
            print("[ERROR] PocketBase is not running!")
            print("Please start PocketBase first: pocketbase.exe serve")
            sys.exit(1)
    except:
        print("[ERROR] Cannot connect to PocketBase at", POCKETBASE_URL)
        print("Please start PocketBase first: pocketbase.exe serve")
        sys.exit(1)
    
    print("[OK] PocketBase is running")
    print()
    
    # Authenticate
    print("Authenticating...")
    token = get_admin_token()
    if not token:
        print("[ERROR] Failed to authenticate")
        sys.exit(1)
    
    print("[OK] Authenticated successfully")
    print()
    
    # Update main collections
    print("Updating main collections...")
    print()
    success_count = 0
    for collection_name in COLLECTIONS_TO_UPDATE:
        if update_collection_schema(token, collection_name):
            success_count += 1
    
    print()
    print(f"[OK] Updated {success_count}/{len(COLLECTIONS_TO_UPDATE)} main collections")
    print()
    
    # Check tick collections
    print("Checking tick collections...")
    tick_collections = list_tick_collections(token)
    
    if tick_collections:
        print(f"[OK] Found {len(tick_collections)} tick collection(s)")
        
        # Check which ones need updating
        needs_update = []
        for coll_name in tick_collections:
            if not check_tick_collection_schema(token, coll_name):
                needs_update.append(coll_name)
        
        if needs_update:
            print(f"[INFO] {len(needs_update)} tick collection(s) need 'created' field:")
            for coll_name in needs_update[:10]:  # Show first 10
                print(f"  - {coll_name}")
            if len(needs_update) > 10:
                print(f"  ... and {len(needs_update) - 10} more")
            print()
            print("Updating tick collections...")
            
            tick_success = 0
            for coll_name in needs_update:
                if update_collection_schema(token, coll_name):
                    tick_success += 1
            
            print(f"[OK] Updated {tick_success}/{len(needs_update)} tick collections")
        else:
            print("[OK] All tick collections already have 'created' field")
    else:
        print("[INFO] No tick collections found yet")
        print("       They will be created automatically when first tick arrives")
    
    print()
    print("=" * 70)
    print("Update Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Restart your trading system to use the new code")
    print("2. New ticks will be stored in symbol-specific collections (ticks_XAUUSDm, etc.)")
    print("3. All timestamps will be in IST format with 'created' field")
    print()
    print("To verify:")
    print("  - Check PocketBase UI: http://192.168.173.112:8090/_/")
    print("  - Look for 'created' field in collection schemas")
    print("  - Check that new ticks go to ticks_{SYMBOL} collections")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Update cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

