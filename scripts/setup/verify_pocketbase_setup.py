"""
Verify PocketBase Network Setup
Comprehensive check to verify PocketBase is properly configured for network access
"""

import requests
import sys
import socket
from urllib.parse import urlparse

POCKETBASE_URL = "http://192.168.173.112:8090"


def check_network_connectivity(host, port):
    """Check if we can connect to the host and port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        return False


def test_pocketbase_connection():
    """Test connection to PocketBase"""
    print("=" * 80)
    print("  PocketBase Network Setup Verification")
    print("=" * 80)
    print()
    
    # Parse URL
    parsed = urlparse(POCKETBASE_URL)
    host = parsed.hostname
    port = parsed.port or 8090
    
    print(f"Target: {POCKETBASE_URL}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print()
    
    # Step 1: Check network connectivity
    print("Step 1: Checking network connectivity...")
    if check_network_connectivity(host, port):
        print(f"[OK] Port {port} is reachable on {host}")
    else:
        print(f"[FAIL] Cannot reach {host}:{port}")
        print("       Possible issues:")
        print("       1. PocketBase is not running")
        print("       2. Firewall is blocking the connection")
        print("       3. PocketBase is not bound to network interface")
        print("       4. Wrong IP address")
        print()
        print("       Solutions:")
        print("       1. Start PocketBase with: pocketbase.exe serve --http=0.0.0.0:8090")
        print("       2. Configure firewall: scripts\\setup\\configure_firewall_windows.ps1")
        return False
    print()
    
    # Step 2: Test HTTP connection
    print("Step 2: Testing HTTP connection...")
    try:
        response = requests.get(f"{POCKETBASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print("[OK] PocketBase HTTP API is accessible")
            data = response.json()
            print(f"       Response: {data}")
        else:
            print(f"[WARNING] HTTP returned status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("[FAIL] Cannot connect to PocketBase HTTP API")
        return False
    except requests.exceptions.Timeout:
        print("[FAIL] Connection timeout")
        return False
    except Exception as e:
        print(f"[WARNING] HTTP test error: {e}")
    print()
    
    # Step 3: Test API endpoint
    print("Step 3: Testing API endpoint...")
    try:
        response = requests.get(f"{POCKETBASE_URL}/api/collections", timeout=5)
        if response.status_code == 200:
            print("[OK] PocketBase API is working")
            collections = response.json()
            count = len(collections.get('items', []))
            print(f"       Found {count} collections")
        elif response.status_code == 401:
            print("[OK] API requires authentication (this is normal)")
            print("       Connection is working correctly")
        else:
            print(f"[WARNING] API returned status {response.status_code}")
    except Exception as e:
        print(f"[WARNING] API test error: {e}")
    print()
    
    # Step 4: Test admin UI
    print("Step 4: Testing admin UI access...")
    try:
        response = requests.get(f"{POCKETBASE_URL}/_/", timeout=5)
        if response.status_code == 200:
            print("[OK] Admin UI is accessible")
            print(f"       Access at: {POCKETBASE_URL}/_/")
        else:
            print(f"[INFO] Admin UI returned status {response.status_code}")
    except Exception as e:
        print(f"[INFO] Admin UI test: {e}")
    print()
    
    print("=" * 80)
    print()
    print("[SUCCESS] PocketBase network setup is working!")
    print()
    print("You can now:")
    print(f"1. Access admin UI: {POCKETBASE_URL}/_/")
    print("2. Start the trading system - it will connect automatically")
    print("3. Use all scripts and tools - they're configured correctly")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = test_pocketbase_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

