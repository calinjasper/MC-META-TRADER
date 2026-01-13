"""Check XAUUSD symbol info and minimum stop levels"""
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.mt5_connector import MT5Connector

mt5 = MT5Connector()
if mt5.initialize():
    info = mt5.get_symbol_info('XAUUSDm')
    if info:
        point = info.get('point', 0)
        digits = info.get('digits', 2)
        stops_level = info.get('trade_stops_level', 0)
        min_distance = stops_level * point if stops_level > 0 else 10 * point
        
        print(f"XAUUSDm Symbol Info:")
        print(f"  Point: {point}")
        print(f"  Digits: {digits}")
        print(f"  Trade Stops Level: {stops_level} points")
        print(f"  Minimum Distance: {min_distance:.5f} price units")
        print(f"\nCurrent Strategy Settings:")
        print(f"  SL Value: 20.0 points")
        print(f"  SL Distance: {20.0 * point:.5f} price units")
        print(f"  TP Value: 40.0 points")
        print(f"  TP Distance: {40.0 * point:.5f} price units")
        
        if 20.0 * point < min_distance:
            print(f"\n⚠️  PROBLEM: SL distance ({20.0 * point:.5f}) is less than minimum ({min_distance:.5f})")
            print(f"   Recommended SL: {int(min_distance / point) + 10} points")
        else:
            print(f"\n✅ SL distance is valid")
    else:
        print("Failed to get symbol info")
else:
    print("Failed to connect to MT5")
