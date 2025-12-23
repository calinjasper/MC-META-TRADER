"""
Check if timestamp_ist is being stored in OHLC records
"""

import requests
from datetime import datetime, timedelta

POCKETBASE_URL = "http://192.168.173.112:8090"


def get_latest_m1_bar():
    """Get the most recent M1 bar from PocketBase"""
    url = f"{POCKETBASE_URL}/api/collections/ohlc/records"
    
    params = {
        'filter': 'timeframe = "M1"',
        'sort': '-timestamp',
        'perPage': 1,
        'page': 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        items = data.get('items', [])
        return items[0] if items else None
    except Exception as e:
        print(f"[ERROR] Failed to fetch M1 bar: {e}")
        return None


def main():
    print("=" * 80)
    print("  Checking timestamp_ist in OHLC Storage")
    print("=" * 80)
    print()
    
    bar = get_latest_m1_bar()
    
    if not bar:
        print("[INFO] No M1 bars found in PocketBase")
        return
    
    print("Most Recent M1 Bar:")
    print("-" * 80)
    print(f"Symbol:        {bar.get('symbol', 'N/A')}")
    print(f"Timeframe:     {bar.get('timeframe', 'N/A')}")
    print(f"Timestamp:     {bar.get('timestamp', 'N/A')}")
    print(f"timestamp_ist: {bar.get('timestamp_ist', 'N/A')}")
    print(f"Created:       {bar.get('created', 'N/A')}")
    print(f"Open:          {bar.get('open', 'N/A')}")
    print(f"High:          {bar.get('high', 'N/A')}")
    print(f"Low:           {bar.get('low', 'N/A')}")
    print(f"Close:         {bar.get('close', 'N/A')}")
    print(f"Tick Volume:   {bar.get('tick_volume', 'N/A')}")
    print("-" * 80)
    print()
    
    # Check timestamp_ist
    timestamp_ist = bar.get('timestamp_ist')
    if timestamp_ist:
        print(f"[SUCCESS] timestamp_ist is present: {timestamp_ist}")
        if 'IST' in timestamp_ist:
            print("[OK] timestamp_ist format includes 'IST' suffix")
        else:
            print("[WARNING] timestamp_ist format does not include 'IST' suffix")
    else:
        print("[WARNING] timestamp_ist field is missing")
        print("          This may indicate:")
        print("          - Field needs to be added to PocketBase collection schema")
        print("          - Old record created before timestamp_ist was added")
        print("          - Wait for a new M1 bar to be stored after code update")
    
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

