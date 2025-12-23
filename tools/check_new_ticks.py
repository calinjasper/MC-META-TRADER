"""
Check for New Ticks
Verify if new ticks are being created with correct timestamps
"""

import requests
from datetime import datetime, timedelta

POCKETBASE_URL = "http://192.168.173.112:8090"


def get_recent_ticks(limit=5, minutes_ago=5):
    """Get recent ticks from last N minutes"""
    try:
        # Calculate timestamp for N minutes ago
        cutoff_time = datetime.now() - timedelta(minutes=minutes_ago)
        cutoff_timestamp_ms = int(cutoff_time.timestamp() * 1000)
        
        url = f"{POCKETBASE_URL}/api/collections/ticks/records"
        params = {
            'filter': f'timestamp >= {cutoff_timestamp_ms}',
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
    print("  Check for New Ticks (Last 5 Minutes)")
    print("=" * 70)
    print()
    
    # Get current time
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
    
    # Get ticks from last 5 minutes
    print("Fetching ticks from last 5 minutes...")
    ticks = get_recent_ticks(limit=10, minutes_ago=5)
    
    if not ticks:
        print("[WARNING] No ticks found in last 5 minutes!")
        print("This could mean:")
        print("1. Trading system is not running")
        print("2. No market activity")
        print("3. Ticks are not being stored")
        print()
        
        # Try getting any recent ticks
        print("Trying to get any recent ticks...")
        try:
            url = f"{POCKETBASE_URL}/api/collections/ticks/records"
            params = {
                'sort': '-timestamp',
                'perPage': 5,
                'page': 1
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            recent = data.get('items', [])
            
            if recent:
                latest = recent[0]
                latest_timestamp_ms = latest.get('timestamp', 0)
                latest_timestamp_ist = latest.get('timestamp_ist', 'N/A')
                
                # Convert to datetime
                latest_dt = datetime.fromtimestamp(latest_timestamp_ms / 1000)
                time_diff = (datetime.now() - latest_dt).total_seconds() / 3600
                
                print(f"Latest tick:")
                print(f"  Timestamp (ms): {latest_timestamp_ms}")
                print(f"  timestamp_ist: {latest_timestamp_ist}")
                print(f"  Time difference: {time_diff:.2f} hours ago")
                print()
                
                if time_diff > 1:
                    print(f"[WARNING] Latest tick is {time_diff:.1f} hours old!")
                    print("         Trading system may not be storing new ticks")
        except Exception as e:
            print(f"[ERROR] {e}")
        
        return
    
    print(f"[OK] Found {len(ticks)} tick(s) in last 5 minutes")
    print()
    print("Recent Ticks:")
    print("-" * 70)
    print(f"{'Symbol':<12} {'timestamp_ist':<25} {'Time Diff':<15}")
    print("-" * 70)
    
    for tick in ticks:
        symbol = tick.get('symbol', 'N/A')
        timestamp_ist = tick.get('timestamp_ist', 'N/A')
        timestamp_ms = tick.get('timestamp', 0)
        
        # Calculate time difference
        if timestamp_ms:
            tick_dt = datetime.fromtimestamp(timestamp_ms / 1000)
            time_diff_seconds = (datetime.now() - tick_dt).total_seconds()
            time_diff_str = f"{time_diff_seconds/60:.1f} min ago"
        else:
            time_diff_str = "N/A"
        
        print(f"{symbol:<12} {timestamp_ist:<25} {time_diff_str:<15}")
    
    print("-" * 70)
    print()
    
    # Check if timestamps match current IST
    print("Verification:")
    for tick in ticks[:3]:  # Check first 3
        timestamp_ist = tick.get('timestamp_ist', '')
        if timestamp_ist:
            # Parse the timestamp
            try:
                tick_time_str = timestamp_ist.replace(' IST', '')
                tick_dt = datetime.strptime(tick_time_str, '%Y-%m-%d %H:%M:%S')
                # Compare with current IST (within 5 minutes)
                time_diff = abs((current_ist - tick_dt).total_seconds())
                if time_diff < 300:  # 5 minutes
                    print(f"  ✓ {tick.get('symbol')}: timestamp_ist matches current time")
                else:
                    print(f"  ✗ {tick.get('symbol')}: timestamp_ist is {time_diff/60:.1f} min off")
            except Exception as e:
                print(f"  ? {tick.get('symbol')}: Could not parse timestamp_ist")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

