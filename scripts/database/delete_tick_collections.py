"""
Delete Tick Collections from PocketBase
Deletes symbol-specific tick collections (ticks_*)
"""

import requests
import sys
import argparse

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


def delete_collection(token, collection_name):
    """Delete a collection"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.delete(
            f"{POCKETBASE_URL}/api/collections/{collection_name}",
            headers=headers,
            timeout=10
        )
        if response.status_code == 204:
            return True
        else:
            print(f"[ERROR] Failed to delete {collection_name}: Status {response.status_code}")
            print(f"       Response: {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Error deleting {collection_name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Delete tick collections from PocketBase')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt')
    parser.add_argument('--symbol', help='Delete only collections for specific symbol (e.g., XAUUSDm)')
    args = parser.parse_args()
    
    print("=" * 70)
    print("  Delete Tick Collections from PocketBase")
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
    
    # List tick collections
    print("Finding tick collections...")
    tick_collections = list_tick_collections(token)
    
    if not tick_collections:
        print("[INFO] No tick collections found")
        return
    
    # Filter by symbol if specified
    if args.symbol:
        symbol_upper = args.symbol.upper()
        if not symbol_upper.endswith('M'):
            symbol_upper += 'M'
        tick_collections = [
            coll for coll in tick_collections
            if coll.upper().endswith(symbol_upper)
        ]
        if not tick_collections:
            print(f"[INFO] No collections found for symbol: {args.symbol}")
            return
    
    print(f"[OK] Found {len(tick_collections)} tick collection(s):")
    for coll in sorted(tick_collections):
        print(f"  - {coll}")
    print()
    
    # Confirm deletion
    if not args.yes:
        print("WARNING: This will permanently delete all tick collections and their data!")
        try:
            response = input("Are you sure you want to delete all tick collections? (yes/no): ").strip().lower()
            if response != 'yes':
                print("[CANCELLED] Deletion cancelled")
                return
        except (EOFError, KeyboardInterrupt):
            print("\n[CANCELLED] Deletion cancelled (use --yes to skip confirmation)")
            return
    
    print()
    print("Deleting collections...")
    print()
    
    deleted_count = 0
    failed_count = 0
    
    for collection_name in sorted(tick_collections):
        print(f"Deleting {collection_name}...", end=' ')
        if delete_collection(token, collection_name):
            print("[OK]")
            deleted_count += 1
        else:
            print("[FAILED]")
            failed_count += 1
    
    print()
    print("=" * 70)
    print("Deletion Complete!")
    print("=" * 70)
    print(f"Deleted: {deleted_count}")
    print(f"Failed:  {failed_count}")
    print()
    
    if deleted_count > 0:
        print("All tick collections have been deleted.")
        print("New collections will be created automatically when ticks arrive.")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Deletion cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

