"""
PocketBase Collections Auto-Setup Script
Automatically creates all required collections for the trading system
"""

import requests
import json
import sys
import time

POCKETBASE_URL = "http://192.168.173.112:8090"

# Hardcoded admin credentials
ADMIN_EMAIL = "nrnnajith@gmail.com"
ADMIN_PASSWORD = "LokeshCalin"

def create_collection(admin_token, collection_data):
    """Create a collection in PocketBase"""
    headers = {
        'Content-Type': 'application/json',
        'Authorization': admin_token
    }
    
    response = requests.post(
        f"{POCKETBASE_URL}/api/collections",
        headers=headers,
        json=collection_data
    )
    
    if response.status_code in [200, 201]:
        print(f"[OK] Created collection: {collection_data['name']}")
        return True
    else:
        print(f"[ERROR] Failed to create {collection_data['name']}: {response.text}")
        return False

def get_admin_token(email, password):
    """Authenticate as admin and get token"""
    response = requests.post(
        f"{POCKETBASE_URL}/api/admins/auth-with-password",
        json={
            "identity": email,
            "password": password
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data['token']
    else:
        print(f"[ERROR] Authentication failed: {response.text}")
        return None

def main():
    print("=" * 60)
    print("  PocketBase Collections Auto-Setup")
    print("=" * 60)
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
    
    # Use hardcoded admin credentials
    print("Authenticating with admin account...")
    print(f"Admin Email: {ADMIN_EMAIL}")
    print()
    
    admin_token = get_admin_token(ADMIN_EMAIL, ADMIN_PASSWORD)
    
    if not admin_token:
        print("[ERROR] Failed to authenticate. Please check your credentials.")
        sys.exit(1)
    
    print("[OK] Authenticated successfully!")
    print()
    print("Creating collections...")
    print()
    
    # Define all collections
    collections = [
        # 1. Trades Collection
        {
            "name": "trades",
            "type": "base",
            "schema": [
                {"name": "ticket", "type": "number", "required": True, "options": {"min": None, "max": None}},
                {"name": "symbol", "type": "text", "required": True},
                {"name": "direction", "type": "text", "required": True},
                {"name": "entry_time", "type": "date", "required": True},
                {"name": "entry_price", "type": "number", "required": True, "options": {"min": None, "max": None}},
                {"name": "exit_time", "type": "date", "required": False},
                {"name": "exit_price", "type": "number", "required": False, "options": {"min": None, "max": None}},
                {"name": "volume", "type": "number", "required": True, "options": {"min": None, "max": None}},
                {"name": "sl", "type": "number", "required": False, "options": {"min": None, "max": None}},
                {"name": "tp", "type": "number", "required": False, "options": {"min": None, "max": None}},
                {"name": "profit", "type": "number", "required": False, "options": {"min": None, "max": None}},
                {"name": "exit_reason", "type": "text", "required": False},
                {"name": "strategy_name", "type": "text", "required": False},
                {"name": "comment", "type": "text", "required": False},
                {"name": "created", "type": "text", "required": False}
            ],
            "indexes": ["CREATE UNIQUE INDEX idx_ticket ON trades (ticket)"]
        },
        
        # 2. Signals Collection
        {
            "name": "signals",
            "type": "base",
            "schema": [
                {"name": "symbol", "type": "text", "required": True},
                {"name": "timestamp", "type": "date", "required": True},
                {"name": "signal_type", "type": "text", "required": True},
                {"name": "strategy_name", "type": "text", "required": True},
                {"name": "conditions", "type": "json", "required": False, "options": {"maxSize": 2000000}},
                {"name": "price", "type": "number", "required": False, "options": {"min": None, "max": None}},
                {"name": "created", "type": "text", "required": False}
            ],
            "indexes": ["CREATE INDEX idx_signals_symbol_time ON signals (symbol, timestamp)"]
        },
        
        # 3. OHLC Collection
        {
            "name": "ohlc",
            "type": "base",
            "schema": [
                {"name": "symbol", "type": "text", "required": True},
                {"name": "timeframe", "type": "text", "required": True},
                {"name": "timestamp", "type": "number", "required": True, "options": {"min": None, "max": None}},
                {"name": "timestamp_ist", "type": "text", "required": False},
                {"name": "open", "type": "number", "required": True, "options": {"min": None, "max": None}},
                {"name": "high", "type": "number", "required": True, "options": {"min": None, "max": None}},
                {"name": "low", "type": "number", "required": True, "options": {"min": None, "max": None}},
                {"name": "close", "type": "number", "required": True, "options": {"min": None, "max": None}},
                {"name": "tick_volume", "type": "number", "required": False, "options": {"min": None, "max": None}},
                {"name": "real_volume", "type": "number", "required": False, "options": {"min": None, "max": None}},
                {"name": "created", "type": "text", "required": False}
            ],
            "indexes": ["CREATE INDEX idx_ohlc_symbol_tf_time ON ohlc (symbol, timeframe, timestamp)"]
        },
        
        # 4. Ticks Collection (Single collection for all symbols)
        {
            "name": "ticks",
            "type": "base",
            "schema": [
                {"name": "symbol", "type": "text", "required": True},
                {"name": "timestamp", "type": "number", "required": True, "options": {"min": None, "max": None}},
                {"name": "timestamp_ist", "type": "text", "required": False},
                {"name": "bid", "type": "number", "required": True, "options": {"min": None, "max": None}},
                {"name": "ask", "type": "number", "required": True, "options": {"min": None, "max": None}},
                {"name": "last", "type": "number", "required": False, "options": {"min": None, "max": None}},
                {"name": "volume", "type": "number", "required": False, "options": {"min": None, "max": None}},
                {"name": "spread", "type": "number", "required": False, "options": {"min": None, "max": None}},
                {"name": "created", "type": "text", "required": False}
            ],
            "indexes": ["CREATE INDEX idx_ticks_symbol_time ON ticks (symbol, timestamp)"]
        },
        
        # 4. Indicators Collection
        {
            "name": "indicators",
            "type": "base",
            "schema": [
                {"name": "symbol", "type": "text", "required": True},
                {"name": "timeframe", "type": "text", "required": True},
                {"name": "timestamp", "type": "date", "required": True},
                {"name": "indicator_name", "type": "text", "required": True},
                {"name": "value", "type": "number", "required": False, "options": {"min": None, "max": None}},
                {"name": "metadata", "type": "json", "required": False, "options": {"maxSize": 2000000}},
                {"name": "created", "type": "text", "required": False}
            ],
            "indexes": ["CREATE INDEX idx_indicators_symbol_time ON indicators (symbol, timeframe, timestamp)"]
        }
    ]
    
    # Create each collection
    success_count = 0
    for collection in collections:
        if create_collection(admin_token, collection):
            success_count += 1
        time.sleep(0.5)  # Small delay between requests
    
    print()
    print("=" * 60)
    print(f"[OK] Setup Complete! Created {success_count}/{len(collections)} collections")
    print("=" * 60)
    print()
    print("Your PocketBase database is ready!")
    print()
    print("Note: All tick data will be stored in the single 'ticks' collection")
    print("      with IST timestamps and 'created' field.")
    print()
    print("Next steps:")
    print("1. View your collections: http://192.168.173.112:8090/_/")
    print("2. Start your trading system: python src\\main.py")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Error: {e}")
        sys.exit(1)

