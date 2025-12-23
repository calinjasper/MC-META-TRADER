"""
Update Ticks Collection Schema
Adds 'created' field to the existing ticks collection
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


def update_ticks_collection(token):
    """Add 'created' field to ticks collection if it doesn't exist"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get current collection
    collection = get_collection(token, 'ticks')
    if not collection:
        print("[ERROR] 'ticks' collection does not exist")
        print("Please run: python setup_pocketbase_collections.py")
        return False
    
    # Check if 'created' field already exists
    schema = collection.get('schema', [])
    has_created = any(field.get('name') == 'created' for field in schema)
    
    if has_created:
        print("[OK] 'ticks' collection already has 'created' field")
        return True
    
    # Add 'created' field to schema
    schema.append({
        "name": "created",
        "type": "text",
        "required": False
    })
    
    # Update collection with full collection data
    update_data = {
        "name": collection.get('name'),
        "type": collection.get('type'),
        "schema": schema,
        "listRule": collection.get('listRule', ''),
        "viewRule": collection.get('viewRule', ''),
        "createRule": collection.get('createRule', ''),
        "updateRule": collection.get('updateRule', ''),
        "deleteRule": collection.get('deleteRule', '')
    }
    
    try:
        response = requests.patch(
            f"{POCKETBASE_URL}/api/collections/ticks",
            headers=headers,
            json=update_data,
            timeout=10
        )
        response.raise_for_status()
        print("[OK] Added 'created' field to 'ticks' collection")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update ticks collection: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"       Response: {e.response.text}")
        return False


def main():
    print("=" * 70)
    print("  Update Ticks Collection Schema")
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
    
    # Update ticks collection
    print("Updating 'ticks' collection...")
    if update_ticks_collection(token):
        print()
        print("=" * 70)
        print("Update Complete!")
        print("=" * 70)
        print()
        print("The 'ticks' collection now has the 'created' field for IST timestamps.")
        print("All new ticks will include IST-formatted timestamps in the 'created' field.")
        print()
    else:
        print()
        print("[ERROR] Failed to update collection")
        sys.exit(1)


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

