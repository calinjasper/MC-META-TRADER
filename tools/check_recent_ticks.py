"""
Check Recent Tick Data
Check if recent ticks have timestamp_ist field populated correctly
"""

import requests
from datetime import datetime

POCKETBASE_URL = "http://192.168.173.112:8090"


def get_recent_ticks(limit=10):
    """Get recent ticks from PocketBase"""
    try:
        url = f"{POCKETBASE_URL}/api/collections/ticks/records"
        params = {
            'sort': '-timestamp',
            'perPage': limit,
            'page': 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('items', [])
    except Exception as e:
        print(f"[ERROR] Failed to fetch ticks: {e}")
        return []


def main():
    print("=" * 70)
    print("  Check Recent Tick Data")
    print("=" * 70)
    print()
    
    print("Fetching recent ticks...")
    ticks = get_recent_ticks(10)
    
    if not ticks:
        print("[ERROR] No ticks found")
        print("Make sure PocketBase is running and trading system is active")
        return
    
    print(f"[OK] Found {len(ticks)} recent tick(s)")
    print()
    
    print("Recent Tick Data:")
    print("-" * 70)
    print(f"{'Symbol':<12} {'Timestamp (ms)':<18} {'timestamp_ist':<25} {'Has IST?':<10}")
    print("-" * 70)
    
    for tick in ticks:
        symbol = tick.get('symbol', 'N/A')
        timestamp = tick.get('timestamp', 0)
        timestamp_ist = tick.get('timestamp_ist', 'MISSING')
        has_ist = 'YES' if timestamp_ist and timestamp_ist != 'MISSING' else 'NO'
        
        print(f"{symbol:<12} {timestamp:<18} {timestamp_ist:<25} {has_ist:<10}")
    
    print("-" * 70)
    print()
    
    # Check current IST time for comparison
    try:
        from zoneinfo import ZoneInfo
        IST = ZoneInfo("Asia/Kolkata")
    except ImportError:
        try:
            import pytz
            IST = pytz.timezone("Asia/Kolkata")
        except ImportError:
            from datetime import timezone, timedelta
            IST = timezone(timedelta(hours=5, minutes=30))
    
    current_ist = datetime.now(IST)
    print(f"Current IST time: {current_ist.strftime('%Y-%m-%d %H:%M:%S IST')}")
    print()
    
    # Analyze
    ticks_with_ist = sum(1 for t in ticks if t.get('timestamp_ist'))
    print(f"Ticks with timestamp_ist: {ticks_with_ist}/{len(ticks)}")
    
    if ticks_with_ist == 0:
        print()
        print("[WARNING] No ticks have timestamp_ist field populated!")
        print("Possible issues:")
        print("1. Trading system may not be using updated code")
        print("2. timestamp_ist field may not exist in schema")
        print("3. Conversion may be failing silently")
    else:
        print()
        print("[OK] Some ticks have timestamp_ist field")
        print("Check if the timestamps match current IST time above")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

