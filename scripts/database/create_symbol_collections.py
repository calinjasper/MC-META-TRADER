"""
Create Symbol-Specific Tick Collections
Automatically creates ticks_{SYMBOL} collections for all active trading symbols
"""

import requests
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

POCKETBASE_URL = "http://192.168.173.112:8090"
ADMIN_EMAIL = "nrnnajith@gmail.com"
ADMIN_PASSWORD = "LokeshCalin"

# Active symbols - you can modify this list or import from your trading system
ACTIVE_SYMBOLS = [
    'XAUUSDm', 'EURUSDm', 'GBPUSDm', 'USDJPYm', 'USDCADm',
    'AUDUSDm', 'NZDUSDm', 'EURJPYm', 'GBPJPYm', 'AUDJPYm',
    'EURGBPm', 'EURAUDm', 'EURCADm', 'EURCHFm', 'EURNZDm',
    'GBPAUDm', 'GBPCADm', 'GBPCHFm', 'GBPNZDm', 'AUDCADm',
    'AUDCHFm', 'AUDNZDm', 'CADCHFm', 'CADJPYm', 'CHFJPYm',
    'NZDCADm', 'NZDCHFm', 'NZDJPYm', 'AAPLm', 'AMZNm',
    'GOOGLm', 'MSFTm', 'TSLAm', 'BILIm', 'US30m',
    'EURZARm', 'EURMXNm', 'EURSEKm', 'AUDZARm', 'XAGAUDm',
    'BTCTHBm', 'AUDDKKm', 'AMDm', 'AMGNm', 'ABTm',
    'ABBVm', 'EBAYm', 'STOXX50m'
]


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


def collection_exists(token, collection_name):
    """Check if a collection already exists"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{POCKETBASE_URL}/api/collections/{collection_name}",
            headers=headers,
            timeout=2
        )
        return response.status_code == 200
    except:
        return False


def create_tick_collection(token, symbol):
    """
    Create a tick collection for a specific symbol
    
    Args:
        token: Admin authentication token
        symbol: Trading symbol (e.g., XAUUSDm)
    
    Returns:
        True if successful, False otherwise
    """
    collection_name = f"ticks_{symbol}"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Check if already exists
    if collection_exists(token, collection_name):
        print(f"[SKIP] Collection already exists: {collection_name}")
        return True
    
    # Define schema
    schema = [
        {"name": "symbol", "type": "text", "required": True},
        {"name": "timestamp", "type": "number", "required": True, "options": {"min": None, "max": None}},
        {"name": "bid", "type": "number", "required": True, "options": {"min": None, "max": None}},
        {"name": "ask", "type": "number", "required": True, "options": {"min": None, "max": None}},
        {"name": "last", "type": "number", "required": False, "options": {"min": None, "max": None}},
        {"name": "volume", "type": "number", "required": False, "options": {"min": None, "max": None}},
        {"name": "spread", "type": "number", "required": False, "options": {"min": None, "max": None}},
        {"name": "created", "type": "text", "required": False}
    ]
    
    collection_data = {
        "name": collection_name,
        "type": "base",
        "schema": schema,
        "listRule": "",      # Allow all
        "viewRule": "",      # Allow all
        "createRule": "",    # Allow unauthenticated writes
        "updateRule": "",    # Allow all
        "deleteRule": ""     # Allow all
    }
    
    try:
        response = requests.post(
            f"{POCKETBASE_URL}/api/collections",
            headers=headers,
            json=collection_data,
            timeout=5
        )
        response.raise_for_status()
        print(f"[OK] Created collection: {collection_name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create {collection_name}: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"       Response: {e.response.text}")
        return False


def main():
    print("=" * 70)
    print("  Create Symbol-Specific Tick Collections")
    print("=" * 70)
    print()
    print(f"PocketBase URL: {POCKETBASE_URL}")
    print(f"Symbols to process: {len(ACTIVE_SYMBOLS)}")
    print()
    
    # Authenticate
    print("Authenticating...")
    token = get_admin_token()
    if not token:
        print("[ERROR] Failed to authenticate with PocketBase")
        print("Make sure PocketBase is running and admin account exists")
        return
    
    print("[OK] Authenticated successfully")
    print()
    
    # Create collections
    print(f"Creating collections for {len(ACTIVE_SYMBOLS)} symbols...")
    print()
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for symbol in ACTIVE_SYMBOLS:
        result = create_tick_collection(token, symbol)
        if result:
            if collection_exists(token, f"ticks_{symbol}"):
                success_count += 1
            else:
                skip_count += 1
        else:
            fail_count += 1
    
    print()
    print("=" * 70)
    print("Summary:")
    print(f"  Created:  {success_count}")
    print(f"  Skipped:  {skip_count} (already existed)")
    print(f"  Failed:   {fail_count}")
    print("=" * 70)
    print()
    
    if success_count > 0:
        print("Collections created successfully!")
        print()
        print("Next steps:")
        print("1. View collections in PocketBase UI: http://192.168.173.112:8090/_/")
        print("2. Restart your trading system to start using symbol-specific collections")
        print()
    elif skip_count > 0:
        print("All collections already exist. You're ready to go!")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()

