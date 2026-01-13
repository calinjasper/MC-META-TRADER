"""
Check Pivot Timing Issue
The pivot needs pivot_right bars after it to be confirmed
If price crosses before confirmation, the pivot isn't available yet
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
import json
from src.config import Config
from src.strategy.smc_strategy import SMCStrategy
from src.strategy.smc_utils import fractal_pivot_low

def check_pivot_timing():
    """Check when pivots are confirmed vs when crosses happen"""
    
    print("=" * 70)
    print("  Pivot Timing Issue Analysis")
    print("=" * 70)
    print()
    
    # Load strategy
    strategy_file = project_root / "strategies" / "SELL.json"
    with open(strategy_file, 'r') as f:
        strategy_data = json.load(f)
    
    symbol = strategy_data.get('symbol')
    timeframe = strategy_data.get('timeframe', 5)
    pivot_left = strategy_data.get('pivot_left', 2)
    pivot_right = strategy_data.get('pivot_right', 2)
    
    print(f"Strategy Settings:")
    print(f"  Pivot Left: {pivot_left}")
    print(f"  Pivot Right: {pivot_right}")
    print(f"  A pivot needs {pivot_right} bars AFTER it to be confirmed")
    print()
    
    # Initialize MT5
    config = Config()
    mt5_config = config.get('mt5', {})
    
    if not mt5.initialize(
        path=mt5_config.get('path', ''),
        login=mt5_config.get('login', 0),
        password=mt5_config.get('password', ''),
        server=mt5_config.get('server', ''),
        timeout=mt5_config.get('timeout', 10000)
    ):
        print(f"[ERROR] MT5 initialization failed")
        return
    
    # Get historical data
    timeframe_enum = getattr(mt5, f"TIMEFRAME_M{timeframe}", mt5.TIMEFRAME_M5)
    rates = mt5.copy_rates_from_pos(symbol, timeframe_enum, 0, 500)
    
    if rates is None:
        print(f"[ERROR] Failed to get rates")
        mt5.shutdown()
        return
    
    # Convert to candles
    candles = []
    for rate in rates:
        candles.append({
            'time': int(rate['time']),
            'open': float(rate['open']),
            'high': float(rate['high']),
            'low': float(rate['low']),
            'close': float(rate['close']),
            'volume': int(rate['tick_volume'])
        })
    
    # Extract lows
    lows = [c['low'] for c in candles]
    
    # Find all potential pivot lows (even unconfirmed)
    print("Checking for pivot lows...")
    print()
    
    # Check each bar to see if it could be a pivot
    potential_pivots = []
    for i in range(pivot_left, len(lows) - pivot_right):
        if fractal_pivot_low(lows, i, pivot_left, pivot_right):
            potential_pivots.append((i, lows[i]))
            print(f"  Confirmed Pivot Low at bar {i}: {lows[i]:.5f}")
            print(f"    - Confirmed at bar {i + pivot_right} (needs {pivot_right} bars after)")
    
    # Check unconfirmed pivots (last pivot_right bars)
    print()
    print("Checking last few bars for unconfirmed pivots...")
    for i in range(len(lows) - pivot_right, len(lows)):
        # Check if this could be a pivot (but not confirmed yet)
        if i >= pivot_left:
            # Check left side only
            is_potential = True
            for j in range(i - pivot_left, i):
                if lows[i] >= lows[j]:
                    is_potential = False
                    break
            
            if is_potential:
                print(f"  Potential (unconfirmed) Pivot Low at bar {i}: {lows[i]:.5f}")
                print(f"    - Will be confirmed at bar {i + pivot_right} (in {i + pivot_right - len(lows) + 1} bars)")
                print(f"    - Current bar: {len(lows) - 1}")
    
    # Check if 156.677 is in the data
    print()
    print("Searching for price level 156.677...")
    target_price = 156.677
    tolerance = 0.01
    
    for i, candle in enumerate(candles):
        if abs(candle['low'] - target_price) < tolerance:
            print(f"  Found price {candle['low']:.5f} at bar {i}")
            print(f"    - Can be confirmed: {i < len(candles) - pivot_right}")
            if i < len(candles) - pivot_right:
                print(f"    - Confirmed at bar {i + pivot_right}")
                print(f"    - Current bar: {len(candles) - 1}")
                if i + pivot_right <= len(candles) - 1:
                    print(f"    - Status: CONFIRMED")
                else:
                    print(f"    - Status: NOT YET CONFIRMED")
            else:
                print(f"    - Status: NOT YET CONFIRMED (needs {i + pivot_right - len(candles) + 1} more bars)")
    
    mt5.shutdown()

if __name__ == "__main__":
    check_pivot_timing()
