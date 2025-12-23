"""
Verify Ticks Collection Setup
Checks that single ticks collection exists and is properly configured
"""

import requests
import sys

POCKETBASE_URL = "http://192.168.173.112:8090"
ADMIN_EMAIL = "nrnnajith@gmail.com"
ADMIN_PASSWORD = "LokeshCalin"


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


def list_all_collections(token):
    """List all collections"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{POCKETBASE_URL}/api/collections",
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        collections = response.json().get('items', [])
        return [c['name'] for c in collections]
    except Exception as e:
        print(f"[ERROR] Failed to list collections: {e}")
        return []


def get_collection_details(token, collection_name):
    """Get collection schema details"""
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


def main():
    print("=" * 70)
    print("  Verify Ticks Collection Setup")
    print("=" * 70)
    print()
    
    # Check if PocketBase is running
    try:
        response = requests.get(f"{POCKETBASE_URL}/api/health", timeout=2)
        if response.status_code != 200:
            print("[ERROR] PocketBase is not running!")
            sys.exit(1)
    except:
        print("[ERROR] Cannot connect to PocketBase")
        sys.exit(1)
    
    print("[OK] PocketBase is running")
    print()
    
    # Authenticate
    token = get_admin_token()
    if not token:
        print("[ERROR] Failed to authenticate")
        sys.exit(1)
    
    print("[OK] Authenticated")
    print()
    
    # List all collections
    print("Checking collections...")
    all_collections = list_all_collections(token)
    
    # Check for ticks_* collections
    tick_collections = [c for c in all_collections if c.startswith('ticks_')]
    
    if tick_collections:
        print(f"[WARNING] Found {len(tick_collections)} symbol-specific tick collection(s):")
        for coll in sorted(tick_collections):
            print(f"  - {coll}")
        print()
        print("These should be deleted. Run: python delete_tick_collections.py --yes")
        print()
    else:
        print("[OK] No symbol-specific tick collections found")
        print()
    
    # Check ticks collection
    print("Checking 'ticks' collection...")
    if 'ticks' in all_collections:
        print("[OK] 'ticks' collection exists")
        
        # Get collection details
        ticks_collection = get_collection_details(token, 'ticks')
        if ticks_collection:
            schema = ticks_collection.get('schema', [])
            field_names = [f.get('name') for f in schema]
            
            print(f"  Fields: {', '.join(field_names)}")
            
            # Check for required fields
            required_fields = ['symbol', 'timestamp', 'bid', 'ask']
            missing_fields = [f for f in required_fields if f not in field_names]
            
            if missing_fields:
                print(f"[WARNING] Missing required fields: {', '.join(missing_fields)}")
            else:
                print("[OK] All required fields present")
            
            # Check for created field
            if 'created' in field_names:
                print("[OK] 'created' field exists for IST timestamps")
            else:
                print("[WARNING] 'created' field missing - IST timestamps won't be stored")
                print("          Add it manually in PocketBase UI or run update_ticks_collection.py")
        else:
            print("[ERROR] Could not get collection details")
    else:
        print("[ERROR] 'ticks' collection does not exist!")
        print("        Run: python setup_pocketbase_collections.py")
    
    print()
    print("=" * 70)
    print("Verification Complete")
    print("=" * 70)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED]")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

