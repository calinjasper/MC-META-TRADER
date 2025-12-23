"""
Add timestamp_ist Field to OHLC Collection
Adds timestamp_ist field to existing ohlc collection schema for IST-formatted display
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


def add_timestamp_ist_field(token):
    """Add timestamp_ist field to ohlc collection if it doesn't exist"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get current collection
    collection = get_collection(token, 'ohlc')
    if not collection:
        print("[ERROR] 'ohlc' collection does not exist")
        print("Please run: python setup_pocketbase_collections.py")
        return False
    
    # Check if timestamp_ist field already exists
    schema = collection.get('schema', [])
    has_timestamp_ist = any(field.get('name') == 'timestamp_ist' for field in schema)
    
    if has_timestamp_ist:
        print("[OK] 'ohlc' collection already has 'timestamp_ist' field")
        return True
    
    # Add timestamp_ist field to schema
    # Insert after 'timestamp' field for better organization
    timestamp_index = next((i for i, field in enumerate(schema) if field.get('name') == 'timestamp'), -1)
    if timestamp_index >= 0:
        schema.insert(timestamp_index + 1, {
            "name": "timestamp_ist",
            "type": "text",
            "required": False
        })
    else:
        schema.append({
            "name": "timestamp_ist",
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
            f"{POCKETBASE_URL}/api/collections/ohlc",
            headers=headers,
            json=update_data,
            timeout=10
        )
        if response.status_code == 200:
            print("[OK] Added 'timestamp_ist' field to 'ohlc' collection")
            return True
        else:
            print(f"[ERROR] Failed to update ohlc collection: Status {response.status_code}")
            print(f"       Response: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to update ohlc collection: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"       Response: {e.response.text}")
        return False


def main():
    print("=" * 70)
    print("  Add timestamp_ist Field to OHLC Collection")
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
    
    # Add timestamp_ist field
    print("Adding 'timestamp_ist' field to 'ohlc' collection...")
    if add_timestamp_ist_field(token):
        print()
        print("=" * 70)
        print("Update Complete!")
        print("=" * 70)
        print()
        print("The 'ohlc' collection now has the 'timestamp_ist' field.")
        print("This field will display IST-formatted timestamps (e.g., '2025-01-22 14:30:00 IST')")
        print("while the 'timestamp' field remains as milliseconds for efficient querying.")
        print()
        print("Next steps:")
        print("1. Restart your trading system (if running)")
        print("2. New M1 OHLC bars will include both 'timestamp' (milliseconds) and 'timestamp_ist' (IST format)")
        print("3. Use 'timestamp_ist' column in PocketBase UI for readable timestamps")
        print()
    else:
        print()
        print("[ERROR] Failed to update collection")
        print()
        print("You may need to add the field manually in PocketBase UI:")
        print("1. Go to http://192.168.173.112:8090/_/")
        print("2. Open 'ohlc' collection")
        print("3. Edit schema and add field:")
        print("   - Name: timestamp_ist")
        print("   - Type: text")
        print("   - Required: false")
        print()
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

