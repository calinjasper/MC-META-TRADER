"""
Check IST Timestamps in PocketBase
Quick script to verify IST conversion is working correctly
"""

import requests
from datetime import datetime

POCKETBASE_URL = "http://192.168.173.112:8090"


def get_recent_ticks(limit=10):
    """Get recent ticks from PocketBase"""
    url = f"{POCKETBASE_URL}/api/collections/ticks/records"
    
    params = {
        'sort': '-timestamp',  # Newest first
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
    print("  Checking IST Timestamps in PocketBase")
    print("=" * 80)
    print()
    
    ticks = get_recent_ticks(limit=10)
    
    if not ticks:
        print("[ERROR] No ticks found in PocketBase")
        return
    
    print(f"[OK] Found {len(ticks)} recent tick(s)")
    print()
    print("Recent Ticks (showing timestamp conversion):")
    print("-" * 80)
    print(f"{'Symbol':<12} {'Timestamp (ms)':<18} {'timestamp_ist':<30} {'created':<30} {'Bid':<10} {'Ask':<10} {'Volume':<10}")
    print("-" * 80)
    
    for tick in ticks:
        symbol = tick.get('symbol', 'N/A')
        timestamp_ms = tick.get('timestamp', 0)
        timestamp_ist = tick.get('timestamp_ist', 'N/A')
        created = tick.get('created', 'N/A')
        bid = tick.get('bid', 0)
        ask = tick.get('ask', 0)
        volume = tick.get('volume', 0)
        
        # Convert timestamp_ms to readable format for comparison
        if timestamp_ms:
            dt_utc = datetime.utcfromtimestamp(timestamp_ms / 1000)
            dt_local = datetime.fromtimestamp(timestamp_ms / 1000)
            timestamp_readable = dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')
        else:
            timestamp_readable = 'N/A'
        
        print(f"{symbol:<12} {timestamp_ms:<18} {timestamp_ist:<30} {created:<30} {bid:<10.5f} {ask:<10.5f} {volume:<10}")
        if timestamp_ms:
            print(f"             (UTC: {timestamp_readable})")
    
    print("-" * 80)
    print()
    
    # Check if timestamp_ist is populated
    ticks_with_ist = [t for t in ticks if t.get('timestamp_ist')]
    ticks_without_ist = [t for t in ticks if not t.get('timestamp_ist')]
    
    print(f"Ticks with timestamp_ist: {len(ticks_with_ist)}/{len(ticks)}")
    print(f"Ticks without timestamp_ist: {len(ticks_without_ist)}/{len(ticks)}")
    
    if ticks_without_ist:
        print()
        print("[WARNING] Some ticks are missing timestamp_ist field!")
        print("This may indicate:")
        print("  - Old records created before IST conversion was implemented")
        print("  - Conversion logic is not executing")
        print("  - Field not being stored correctly")
    
    # Verify IST format
    print()
    print("IST Format Verification:")
    print("-" * 80)
    current_utc = datetime.utcnow()
    current_ist_expected = current_utc.replace(hour=current_utc.hour + 5, minute=current_utc.minute + 30)
    if current_ist_expected.minute >= 60:
        current_ist_expected = current_ist_expected.replace(hour=current_ist_expected.hour + 1, minute=current_ist_expected.minute - 60)
    
    print(f"Current UTC time:  {current_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Expected IST time: {current_utc.strftime('%Y-%m-%d %H:%M:%S')} + 5:30 = {current_ist_expected.strftime('%Y-%m-%d %H:%M:%S')} IST")
    
    if ticks_with_ist:
        sample_ist = ticks_with_ist[0].get('timestamp_ist', '')
        print(f"Sample stored IST:  {sample_ist}")
        
        # Check if format matches expected pattern
        if 'IST' in sample_ist:
            print("[OK] IST format includes 'IST' suffix")
        else:
            print("[WARNING] IST format does not include 'IST' suffix")
        
        # Check if time difference is approximately 5:30
        if timestamp_ms:
            stored_dt = datetime.fromtimestamp(timestamp_ms / 1000)
            # Parse IST string to compare
            try:
                ist_parts = sample_ist.replace(' IST', '').split(' ')
                if len(ist_parts) == 2:
                    date_part, time_part = ist_parts
                    ist_dt_str = f"{date_part} {time_part}"
                    ist_dt = datetime.strptime(ist_dt_str, '%Y-%m-%d %H:%M:%S')
                    # Compare with UTC timestamp
                    utc_dt = datetime.utcfromtimestamp(timestamp_ms / 1000)
                    time_diff = ist_dt - utc_dt
                    hours_diff = time_diff.total_seconds() / 3600
                    print(f"Time difference: {hours_diff:.2f} hours (expected: 5.50 hours)")
                    if 5.4 <= hours_diff <= 5.6:
                        print("[OK] IST conversion appears correct (5:30 offset)")
                    else:
                        print(f"[WARNING] IST conversion offset is {hours_diff:.2f} hours, expected 5.50 hours")
            except Exception as e:
                print(f"[ERROR] Could not parse IST timestamp for comparison: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()

