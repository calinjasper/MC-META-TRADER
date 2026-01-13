"""Check BTC_BUY strategy SL/TP calculation"""
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mt5_connector import MT5Connector

def main():
    # Load strategy config
    strategy_file = project_root / "strategies" / "BTC_BUY.json"
    with open(strategy_file, 'r') as f:
        strategy = json.load(f)
    
    print("=" * 60)
    print("BTC_BUY Strategy Configuration")
    print("=" * 60)
    print(f"Strategy: {strategy['name']}")
    print(f"Symbol: {strategy['symbol']}")
    print(f"SL Type: {strategy['sl_type']}")
    print(f"SL Value: {strategy['sl_value']}")
    print(f"TP Value: {strategy['tp_value']}")
    print(f"Use Ratio: {strategy['use_ratio']}")
    print()
    
    # Get symbol info
    mt5 = MT5Connector()
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return
    
    symbol_info = mt5.get_symbol_info('BTCUSDm')
    if not symbol_info:
        print("Failed to get symbol info")
        return
    
    point = symbol_info.get('point', 0.0001)
    digits = symbol_info.get('digits', 5)
    trade_stops_level = symbol_info.get('trade_stops_level', 0)
    min_distance = trade_stops_level * point if trade_stops_level > 0 else 0
    
    print("=" * 60)
    print("BTCUSDm Symbol Information")
    print("=" * 60)
    print(f"Point: {point}")
    print(f"Digits: {digits}")
    print(f"Trade Stops Level: {trade_stops_level}")
    print(f"Minimum Distance: {min_distance:.5f}")
    print()
    
    # Calculate expected SL/TP
    entry_price = 88896.73  # Example from logs
    sl_value = strategy['sl_value']
    tp_value = strategy['tp_value']
    
    # Calculate SL distance
    if "Points" in strategy['sl_type']:
        sl_distance = sl_value * point
    else:
        sl_distance = entry_price * (sl_value / 100.0)
    
    # Calculate TP distance
    if strategy['use_ratio']:
        tp_distance = sl_distance * 2.0
    else:
        if "Points" in strategy['sl_type']:
            tp_distance = tp_value * point
        else:
            tp_distance = entry_price * (tp_value / 100.0)
    
    # Calculate SL/TP prices
    sl_price = entry_price - sl_distance
    tp_price = entry_price + tp_distance
    
    print("=" * 60)
    print("Expected SL/TP Calculation")
    print("=" * 60)
    print(f"Entry Price: {entry_price:.5f}")
    print(f"SL Distance: {sl_distance:.5f} ({sl_value} points)")
    print(f"TP Distance: {tp_distance:.5f} ({tp_value} points)")
    print(f"SL Price: {sl_price:.5f}")
    print(f"TP Price: {tp_price:.5f}")
    print()
    
    # Validate against minimum distance
    print("=" * 60)
    print("Validation")
    print("=" * 60)
    sl_distance_actual = abs(entry_price - sl_price)
    tp_distance_actual = abs(tp_price - entry_price)
    
    print(f"SL Distance: {sl_distance_actual:.5f}")
    if min_distance > 0:
        if sl_distance_actual < min_distance:
            print(f"⚠️  SL distance ({sl_distance_actual:.5f}) is LESS than minimum ({min_distance:.5f})")
        else:
            print(f"✅ SL distance meets minimum requirement")
    
    print(f"TP Distance: {tp_distance_actual:.5f}")
    if min_distance > 0:
        if tp_distance_actual < min_distance:
            print(f"⚠️  TP distance ({tp_distance_actual:.5f}) is LESS than minimum ({min_distance:.5f})")
        else:
            print(f"✅ TP distance meets minimum requirement")
    
    # Check what was calculated in logs
    print()
    print("=" * 60)
    print("Issue from Logs")
    print("=" * 60)
    print("From logs (12:31:19):")
    print(f"  Entry: 88896.73")
    print(f"  Calculated SL: 88896.53 (WRONG - only 0.20 points!)")
    print(f"  Expected SL: {sl_price:.5f} ({sl_distance:.5f} points)")
    print(f"  Difference: {abs(88896.53 - sl_price):.5f} points")
    
    mt5.shutdown()

if __name__ == "__main__":
    main()
