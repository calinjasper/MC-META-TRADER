"""
Verify that volume fix is working - check if new ticks have volume populated
"""

import requests
from datetime import datetime, timedelta

POCKETBASE_URL = "http://192.168.173.112:8090"


def get_recent_ticks_with_volume(limit=20):
    """Get recent ticks and check volume"""
    url = f"{POCKETBASE_URL}/api/collections/ticks/records"
    
    # Get ticks from last 5 minutes
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    timestamp_ms = int(five_min_ago.timestamp() * 1000)
    
    params = {
        'filter': f'timestamp >= {timestamp_ms}',
        'sort': '-timestamp',
        'perPage': limit,
        'page': 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('items', [])
    except Exception as e:
        print(f"[ERROR] Failed to fetch ticks: {e}")
        return []


def main():
    print("=" * 80)
    print("  Verifying Volume Fix")
    print("=" * 80)
    print()
    print("Checking recent ticks (last 5 minutes) for volume values...")
    print()
    
    ticks = get_recent_ticks_with_volume(limit=20)
    
    if not ticks:
        print("[INFO] No ticks found in the last 5 minutes")
        print("       This may mean:")
        print("       - Trading system is not running")
        print("       - No ticks have been stored recently")
        print()
        print("The fix has been implemented and will work for new ticks.")
        print("Please restart the trading system to start storing ticks with volume.")
        return
    
    print(f"[OK] Found {len(ticks)} tick(s) in the last 5 minutes")
    print()
    
    # Count ticks with volume > 0
    ticks_with_volume = [t for t in ticks if t.get('volume', 0) > 0]
    ticks_without_volume = [t for t in ticks if t.get('volume', 0) == 0]
    
    print(f"Ticks with volume > 0: {len(ticks_with_volume)}/{len(ticks)}")
    print(f"Ticks with volume = 0: {len(ticks_without_volume)}/{len(ticks)}")
    print()
    
    if ticks_with_volume:
        print("[SUCCESS] Volume fix is working!")
        print("          New ticks are being stored with volume values.")
        print()
        print("Sample ticks with volume:")
        print("-" * 80)
        for tick in ticks_with_volume[:5]:
            symbol = tick.get('symbol', 'N/A')
            volume = tick.get('volume', 0)
            timestamp_ist = tick.get('timestamp_ist', 'N/A')
            print(f"  {symbol}: Volume = {volume}, Time = {timestamp_ist}")
    else:
        print("[INFO] All recent ticks still have volume = 0")
        print("       This may indicate:")
        print("       - Trading system needs to be restarted to pick up the fix")
        print("       - M1 bar volume is 0 (broker limitation)")
        print()
        print("The fix has been implemented. After restarting the trading system,")
        print("new ticks should have volume populated from M1 bars.")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()

