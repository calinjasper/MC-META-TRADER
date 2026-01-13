"""Debug BTC_BUY SL calculation issue"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.strategy.strategy_persistence import StrategyPersistence
from src.mt5_connector import MT5Connector

def main():
    # Load strategy
    persistence = StrategyPersistence()
    strategy = persistence.load_strategy("strategies/BTC_BUY.json")
    
    if not strategy:
        print("Failed to load strategy")
        return
    
    print("=" * 60)
    print("Strategy Object Attributes")
    print("=" * 60)
    print(f"Strategy Name: {strategy.name}")
    print(f"Strategy Type: {type(strategy).__name__}")
    print(f"Has sl_type: {hasattr(strategy, 'sl_type')}")
    print(f"sl_type value: {getattr(strategy, 'sl_type', 'NOT SET')}")
    print(f"Has sl_value: {hasattr(strategy, 'sl_value')}")
    print(f"sl_value value: {getattr(strategy, 'sl_value', 'NOT SET')}")
    print(f"Has sl_enabled: {hasattr(strategy, 'sl_enabled')}")
    print(f"sl_enabled value: {getattr(strategy, 'sl_enabled', 'NOT SET')}")
    print()
    
    # Check JSON directly
    with open("strategies/BTC_BUY.json", 'r') as f:
        json_data = json.load(f)
    
    print("=" * 60)
    print("JSON Configuration")
    print("=" * 60)
    print(f"sl_type in JSON: {json_data.get('sl_type')}")
    print(f"sl_value in JSON: {json_data.get('sl_value')}")
    print(f"sl_enabled in JSON: {json_data.get('sl_enabled')}")
    print()
    
    # Simulate calculation
    mt5 = MT5Connector()
    if mt5.initialize():
        symbol_info = mt5.get_symbol_info('BTCUSDm')
        if symbol_info:
            point = symbol_info.get('point', 0.0001)
            entry_price = 88896.73
            
            sl_value = getattr(strategy, 'sl_value', 20.0)
            sl_type = getattr(strategy, 'sl_type', None)
            
            print("=" * 60)
            print("SL Calculation Simulation")
            print("=" * 60)
            print(f"Entry Price: {entry_price}")
            print(f"Point: {point}")
            print(f"sl_type from object: {sl_type}")
            print(f"sl_value from object: {sl_value}")
            print()
            
            if sl_type and "Points" in sl_type:
                sl_distance = sl_value * point
                sl_price = entry_price - sl_distance
                print(f"SL Distance: {sl_distance:.5f} ({sl_value} * {point})")
                print(f"SL Price: {sl_price:.5f}")
                print(f"Expected from JSON (50.0): {entry_price - (50.0 * point):.5f}")
            else:
                print("SL type is None or not 'Points'")
        
        mt5.shutdown()

if __name__ == "__main__":
    main()
