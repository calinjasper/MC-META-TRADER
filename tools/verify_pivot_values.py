"""
Verify Pivot High/Low Values
Compare system-calculated pivots with MT5 values
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mt5_connector import MT5Connector
from src.strategy.smc_utils import fractal_pivot_high, fractal_pivot_low, extract_ohlc_arrays

def verify_pivots(symbol: str = "EURUSD", timeframe: int = 15, pivot_left: int = 2, pivot_right: int = 2):
    """Verify pivot calculations against MT5 values"""
    
    print(f"Verifying pivots for {symbol} on M{timeframe}")
    print(f"Pivot settings: left={pivot_left}, right={pivot_right}")
    print("-" * 60)
    
    # Connect to MT5
    connector = MT5Connector()
    if not connector.initialize():
        print("[ERROR] Failed to connect to MT5")
        return
    
    # Get recent candles
    rates = connector.get_rates(symbol, timeframe, 500)
    if not rates:
        print(f"[ERROR] Failed to get rates for {symbol}")
        return
    
    print(f"[OK] Retrieved {len(rates)} candles")
    
    # Extract OHLC arrays
    opens, highs, lows, closes = extract_ohlc_arrays(rates)
    
    # Find all pivot highs and lows
    pivot_highs = []
    pivot_lows = []
    
    start = pivot_left
    end = len(highs) - pivot_right
    
    for i in range(start, end):
        if fractal_pivot_high(highs, i, pivot_left, pivot_right):
            pivot_highs.append({'index': i, 'price': highs[i], 'bar': len(highs) - i - 1})
        if fractal_pivot_low(lows, i, pivot_left, pivot_right):
            pivot_lows.append({'index': i, 'price': lows[i], 'bar': len(lows) - i - 1})
    
    print(f"\n[OK] Found {len(pivot_highs)} pivot highs, {len(pivot_lows)} pivot lows")
    
    # Find most recent (active) pivots
    if pivot_highs:
        most_recent_high = max(pivot_highs, key=lambda x: x['index'])
        print(f"\nMost Recent Pivot High:")
        print(f"  Price: {most_recent_high['price']:.5f}")
        print(f"  Index: {most_recent_high['index']} (bar {most_recent_high['bar']} bars ago)")
        print(f"  MT5 Expected: 156.992")
        diff = abs(most_recent_high['price'] - 156.992)
        if diff < 0.001:
            print(f"  [MATCH] ✓ Values match!")
        else:
            print(f"  [DIFF] ✗ Difference: {diff:.5f}")
            print(f"  [INFO] System: {most_recent_high['price']:.5f}, MT5: 156.992")
    else:
        print("\n[WARNING] No pivot highs found")
    
    if pivot_lows:
        most_recent_low = max(pivot_lows, key=lambda x: x['index'])
        print(f"\nMost Recent Pivot Low:")
        print(f"  Price: {most_recent_low['price']:.5f}")
        print(f"  Index: {most_recent_low['index']} (bar {most_recent_low['bar']} bars ago)")
        print(f"  MT5 Expected: 156.826")
        diff = abs(most_recent_low['price'] - 156.826)
        if diff < 0.001:
            print(f"  [MATCH] ✓ Values match!")
        else:
            print(f"  [DIFF] ✗ Difference: {diff:.5f}")
            print(f"  [INFO] System: {most_recent_low['price']:.5f}, MT5: 156.826")
    else:
        print("\n[WARNING] No pivot lows found")
    
    # Show recent pivots for context
    print(f"\n--- Recent Pivot Highs (last 5) ---")
    for ph in sorted(pivot_highs, key=lambda x: x['index'], reverse=True)[:5]:
        print(f"  {ph['price']:.5f} (bar {ph['bar']} ago)")
    
    print(f"\n--- Recent Pivot Lows (last 5) ---")
    for pl in sorted(pivot_lows, key=lambda x: x['index'], reverse=True)[:5]:
        print(f"  {pl['price']:.5f} (bar {pl['bar']} ago)")
    
    # Check if MT5 values exist in our pivots
    print(f"\n--- Checking for MT5 Values ---")
    mt5_high = 156.992
    mt5_low = 156.826
    
    found_high = any(abs(ph['price'] - mt5_high) < 0.001 for ph in pivot_highs)
    found_low = any(abs(pl['price'] - mt5_low) < 0.001 for pl in pivot_lows)
    
    if found_high:
        matching_high = next(ph for ph in pivot_highs if abs(ph['price'] - mt5_high) < 0.001)
        print(f"  Pivot High 156.992: ✓ Found at index {matching_high['index']} (bar {matching_high['bar']} ago)")
    else:
        print(f"  Pivot High 156.992: ✗ Not found in calculated pivots")
        # Find closest
        if pivot_highs:
            closest = min(pivot_highs, key=lambda x: abs(x['price'] - mt5_high))
            print(f"    Closest: {closest['price']:.5f} (diff: {abs(closest['price'] - mt5_high):.5f})")
    
    if found_low:
        matching_low = next(pl for pl in pivot_lows if abs(pl['price'] - mt5_low) < 0.001)
        print(f"  Pivot Low 156.826: ✓ Found at index {matching_low['index']} (bar {matching_low['bar']} ago)")
    else:
        print(f"  Pivot Low 156.826: ✗ Not found in calculated pivots")
        # Find closest
        if pivot_lows:
            closest = min(pivot_lows, key=lambda x: abs(x['price'] - mt5_low))
            print(f"    Closest: {closest['price']:.5f} (diff: {abs(closest['price'] - mt5_low):.5f})")
    
    connector.shutdown()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Verify pivot values against MT5")
    parser.add_argument("--symbol", default="EURUSD", help="Symbol to check")
    parser.add_argument("--timeframe", type=int, default=15, help="Timeframe (minutes)")
    parser.add_argument("--pivot-left", type=int, default=2, help="Pivot left bars")
    parser.add_argument("--pivot-right", type=int, default=2, help="Pivot right bars")
    
    args = parser.parse_args()
    verify_pivots(args.symbol, args.timeframe, args.pivot_left, args.pivot_right)
