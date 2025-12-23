"""
Test script to verify that volume is now populated in tick data
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.mt5_connector import MT5Connector
import MetaTrader5 as mt5
from datetime import datetime

def test_volume_population():
    """Test that get_tick() now returns non-zero volume values"""
    print("=" * 80)
    print("  Testing Volume Population in Tick Data")
    print("=" * 80)
    print()
    
    # Initialize MT5 connector
    connector = MT5Connector()
    
    # Try to initialize (may fail if MT5 not running, that's OK for testing structure)
    if not connector.initialize():
        print("[WARNING] Could not connect to MT5. Testing code structure only.")
        print("          Please ensure MT5 is running to test actual volume retrieval.")
        print()
        return
    
    print("[OK] Connected to MT5")
    print()
    
    # Get a test symbol (try common ones)
    test_symbols = ["XAUUSDm", "EURUSDm", "GBPUSDm", "USDJPYm"]
    symbol = None
    
    for test_symbol in test_symbols:
        symbol_info = connector.get_symbol_info(test_symbol)
        if symbol_info:
            symbol = test_symbol
            break
    
    if not symbol:
        print("[ERROR] Could not find any test symbol")
        return
    
    print(f"Testing with symbol: {symbol}")
    print()
    
    # Get tick data
    print("Fetching tick data...")
    tick = connector.get_tick(symbol)
    
    if not tick:
        print("[ERROR] Could not retrieve tick data")
        return
    
    print("[OK] Retrieved tick data")
    print()
    print("Tick Data:")
    print("-" * 80)
    print(f"Symbol:     {tick['symbol']}")
    print(f"Time:       {tick['time']}")
    print(f"Bid:        {tick['bid']:.5f}")
    print(f"Ask:        {tick['ask']:.5f}")
    print(f"Last:       {tick['last']:.5f}")
    print(f"Volume:     {tick['volume']}")
    print(f"Spread:     {tick['spread']:.5f}")
    print("-" * 80)
    print()
    
    # Check volume
    if tick['volume'] > 0:
        print(f"[SUCCESS] Volume is populated: {tick['volume']}")
        print("          Volume is now being retrieved from M1 bar tick_volume")
    else:
        print("[WARNING] Volume is still 0")
        print("          This may indicate:")
        print("          - M1 bar fetch failed")
        print("          - M1 bar tick_volume is 0 (broker limitation)")
        print("          - Cache not working correctly")
    
    print()
    
    # Test multiple ticks to verify caching works
    print("Testing cache (fetching 5 ticks in quick succession)...")
    volumes = []
    for i in range(5):
        tick = connector.get_tick(symbol)
        if tick:
            volumes.append(tick['volume'])
            print(f"  Tick {i+1}: Volume = {tick['volume']}")
    
    if len(set(volumes)) == 1 and volumes[0] > 0:
        print("[OK] Cache working correctly - same volume returned (same M1 bar)")
    elif len(set(volumes)) > 1:
        print("[INFO] Different volumes detected - may indicate new M1 bar started")
    else:
        print("[WARNING] All volumes are 0")
    
    print()
    print("=" * 80)
    
    # Cleanup
    connector.shutdown()


if __name__ == "__main__":
    try:
        test_volume_population()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Cancelled by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()

