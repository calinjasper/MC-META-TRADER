"""
Check if PocketBase server is running
"""
import requests
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from data_viewer.config import POCKETBASE_URL

def check_pocketbase():
    """Check if PocketBase is running"""
    print(f"Checking PocketBase at: {POCKETBASE_URL}")
    print("-" * 60)
    
    try:
        # Try to connect to PocketBase API
        response = requests.get(
            f"{POCKETBASE_URL}/api/health",
            timeout=3
        )
        
        if response.status_code == 200:
            print("[OK] PocketBase is RUNNING")
            print(f"   Status Code: {response.status_code}")
            return True
        else:
            print(f"[WARNING] PocketBase responded with status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] PocketBase is NOT RUNNING")
        print("   Error: Connection refused")
        print(f"   Please start PocketBase at: {POCKETBASE_URL}")
        return False
    except requests.exceptions.Timeout:
        print("[ERROR] PocketBase connection TIMEOUT")
        print("   Server may be slow or unreachable")
        return False
    except Exception as e:
        print(f"[ERROR] Error checking PocketBase: {e}")
        return False

if __name__ == "__main__":
    is_running = check_pocketbase()
    sys.exit(0 if is_running else 1)

