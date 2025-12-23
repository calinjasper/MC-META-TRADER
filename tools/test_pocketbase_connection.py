"""
Test PocketBase Connection
Quick script to verify connection to PocketBase at the new network IP
"""

import requests
import sys

POCKETBASE_URL = "http://192.168.173.112:8090"


def test_connection():
    """Test connection to PocketBase"""
    print("=" * 80)
    print("  Testing PocketBase Connection")
    print("=" * 80)
    print()
    print(f"Testing connection to: {POCKETBASE_URL}")
    print()
    
    # Test health endpoint
    try:
        response = requests.get(f"{POCKETBASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            print("[SUCCESS] PocketBase health check passed")
            print(f"          Response: {response.text}")
        else:
            print(f"[WARNING] Health check returned status {response.status_code}")
            print(f"          Response: {response.text}")
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to PocketBase")
        print("        Possible issues:")
        print("        1. PocketBase server is not running")
        print("        2. Firewall is blocking port 8090")
        print("        3. PocketBase is not configured to accept network connections")
        print("        4. IP address is incorrect")
        return False
    except requests.exceptions.Timeout:
        print("[ERROR] Connection timeout")
        print("        PocketBase server may be unreachable")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return False
    
    print()
    
    # Test API endpoint
    try:
        response = requests.get(f"{POCKETBASE_URL}/api/collections", timeout=5)
        if response.status_code == 200:
            print("[SUCCESS] PocketBase API is accessible")
            collections = response.json()
            print(f"          Found {len(collections.get('items', []))} collections")
        elif response.status_code == 401:
            print("[INFO] API requires authentication (this is normal)")
            print("       Connection is working, authentication needed for data access")
        else:
            print(f"[WARNING] API returned status {response.status_code}")
    except Exception as e:
        print(f"[WARNING] API test failed: {e}")
    
    print()
    print("=" * 80)
    print()
    print("Next steps:")
    print(f"1. Ensure PocketBase is running on {POCKETBASE_URL}")
    print("2. Configure PocketBase to accept network connections:")
    print("   - Start with: pocketbase.exe serve --http=0.0.0.0:8090")
    print("3. Check firewall rules allow port 8090")
    print("4. Verify you can access admin UI:")
    print(f"   {POCKETBASE_URL}/_/")
    print()
    
    return True


if __name__ == "__main__":
    try:
        test_connection()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

