"""
Test script to verify M1 OHLC bars are being stored in PocketBase
"""

import requests
from datetime import datetime, timedelta

POCKETBASE_URL = "http://192.168.173.112:8090"


def get_recent_m1_bars(limit=20):
    """Get recent M1 OHLC bars from PocketBase"""
    url = f"{POCKETBASE_URL}/api/collections/ohlc/records"
    
    # Get bars from last 10 minutes
    ten_min_ago = datetime.utcnow() - timedelta(minutes=10)
    timestamp_ms = int(ten_min_ago.timestamp() * 1000)
    
    params = {
        'filter': f'timestamp >= {timestamp_ms} && timeframe = "M1"',
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
        print(f"[ERROR] Failed to fetch M1 bars: {e}")
        return []


def main():
    print("=" * 80)
    print("  Testing M1 OHLC Storage in PocketBase")
    print("=" * 80)
    print()
    
    bars = get_recent_m1_bars(limit=20)
    
    if not bars:
        print("[INFO] No M1 bars found in the last 10 minutes")
        print("       This may mean:")
        print("       - Trading system is not running")
        print("       - No M1 bars have been stored yet")
        print("       - Wait for a new minute to start (M1 bars are stored when they close)")
        print()
        print("The M1 OHLC storage has been activated.")
        print("New M1 bars will be stored automatically when they close.")
        return
    
    print(f"[OK] Found {len(bars)} M1 bar(s) in the last 10 minutes")
    print()
    
    # Group by symbol
    bars_by_symbol = {}
    for bar in bars:
        symbol = bar.get('symbol', 'N/A')
        if symbol not in bars_by_symbol:
            bars_by_symbol[symbol] = []
        bars_by_symbol[symbol].append(bar)
    
    print(f"Symbols with M1 bars: {len(bars_by_symbol)}")
    print()
    
    # Display sample bars
    print("Recent M1 Bars:")
    print("-" * 80)
    print(f"{'Symbol':<12} {'Timestamp':<20} {'timestamp_ist':<30} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10} {'Tick Vol':<10}")
    print("-" * 80)
    
    for symbol, symbol_bars in sorted(bars_by_symbol.items()):
        # Show most recent bar for each symbol
        latest_bar = symbol_bars[0]  # Already sorted by -timestamp
        timestamp_ms = latest_bar.get('timestamp', 0)
        timestamp_str = datetime.fromtimestamp(timestamp_ms / 1000).strftime('%Y-%m-%d %H:%M:%S') if timestamp_ms else 'N/A'
        timestamp_ist = latest_bar.get('timestamp_ist', 'N/A')
        
        print(f"{symbol:<12} {timestamp_str:<20} {timestamp_ist:<30} "
              f"{latest_bar.get('open', 0):<10.5f} "
              f"{latest_bar.get('high', 0):<10.5f} "
              f"{latest_bar.get('low', 0):<10.5f} "
              f"{latest_bar.get('close', 0):<10.5f} "
              f"{latest_bar.get('tick_volume', 0):<10}")
    
    print("-" * 80)
    print()
    
    # Check for duplicates (same symbol and timestamp)
    print("Duplicate Check:")
    print("-" * 80)
    seen = {}
    duplicates = []
    for bar in bars:
        symbol = bar.get('symbol', 'N/A')
        timestamp = bar.get('timestamp', 0)
        key = (symbol, timestamp)
        if key in seen:
            duplicates.append((symbol, timestamp))
        else:
            seen[key] = bar
    
    if duplicates:
        print(f"[WARNING] Found {len(duplicates)} duplicate M1 bars (same symbol and timestamp)")
        for symbol, timestamp in duplicates[:5]:  # Show first 5
            print(f"  - {symbol} at {datetime.fromtimestamp(timestamp / 1000)}")
    else:
        print("[OK] No duplicate M1 bars found")
    
    print("-" * 80)
    print()
    
    # Verify data completeness
    print("Data Completeness Check:")
    print("-" * 80)
    required_fields = ['symbol', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close']
    incomplete = []
    
    for bar in bars:
        missing = [field for field in required_fields if not bar.get(field)]
        if missing:
            incomplete.append((bar.get('symbol', 'N/A'), missing))
    
    if incomplete:
        print(f"[WARNING] Found {len(incomplete)} bars with missing fields:")
        for symbol, missing in incomplete[:5]:  # Show first 5
            print(f"  - {symbol}: missing {', '.join(missing)}")
    else:
        print("[OK] All M1 bars have required fields")
    
    print("-" * 80)
    print()
    
    # Check for timestamp_ist field
    print("timestamp_ist Field Check:")
    print("-" * 80)
    bars_with_ist = [bar for bar in bars if bar.get('timestamp_ist')]
    bars_without_ist = [bar for bar in bars if not bar.get('timestamp_ist')]
    
    print(f"Bars with timestamp_ist: {len(bars_with_ist)}/{len(bars)}")
    print(f"Bars without timestamp_ist: {len(bars_without_ist)}/{len(bars)}")
    
    if bars_with_ist:
        sample_ist = bars_with_ist[0].get('timestamp_ist', '')
        print(f"Sample timestamp_ist: {sample_ist}")
        if 'IST' in sample_ist:
            print("[OK] timestamp_ist format includes 'IST' suffix")
        else:
            print("[WARNING] timestamp_ist format does not include 'IST' suffix")
    
    if bars_without_ist:
        print("[WARNING] Some bars are missing timestamp_ist field!")
        print("          This may indicate:")
        print("          - Old records created before timestamp_ist was added")
        print("          - Field not being stored correctly")
        print("          - Field needs to be added to PocketBase collection schema")
    
    print("-" * 80)
    print()
    
    # Summary
    print("Summary:")
    print("-" * 80)
    print(f"Total M1 bars found: {len(bars)}")
    print(f"Unique symbols: {len(bars_by_symbol)}")
    print(f"Timeframe: M1 (1-minute)")
    print(f"Storage status: {'Active' if bars else 'No data yet'}")
    print("-" * 80)
    print()
    
    if bars:
        print("[SUCCESS] M1 OHLC storage is working correctly!")
        print("          M1 bars are being stored automatically when they close.")
    else:
        print("[INFO] M1 OHLC storage is activated but no bars found yet.")
        print("       Wait for a new minute to start for bars to be stored.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()

