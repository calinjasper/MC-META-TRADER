"""
Check All Strategies - List all strategies and their trade direction
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

def check_all_strategies():
    """List all strategies and their configurations"""
    print("=" * 80)
    print("  All Strategies Configuration")
    print("=" * 80)
    print()
    
    strategies_dir = project_root / "strategies"
    
    if not strategies_dir.exists():
        print(f"[ERROR] Strategies directory not found: {strategies_dir}")
        return
    
    strategy_files = list(strategies_dir.glob("*.json"))
    
    if not strategy_files:
        print("No strategy files found in strategies directory")
        return
    
    print(f"Found {len(strategy_files)} strategy file(s):\n")
    
    for strategy_file in sorted(strategy_files):
        try:
            with open(strategy_file, 'r') as f:
                strategy_data = json.load(f)
            
            name = strategy_data.get('name', 'N/A')
            symbol = strategy_data.get('symbol', 'N/A')
            strategy_type = strategy_data.get('strategy_type', 'N/A')
            trade_direction = strategy_data.get('trade_direction', 'both')
            enabled = strategy_data.get('enabled', False)
            
            print(f"Strategy: {name}")
            print(f"  File: {strategy_file.name}")
            print(f"  Symbol: {symbol}")
            print(f"  Type: {strategy_type}")
            print(f"  Trade Direction: {trade_direction}")
            print(f"  Enabled: {enabled}")
            
            # Show what trades it will take
            if trade_direction == "long":
                print(f"  [BUY ONLY] Will take: BUY trades only")
                print(f"  [IGNORED] Will ignore: SELL trades")
            elif trade_direction == "short":
                print(f"  [SELL ONLY] Will take: SELL trades only")
                print(f"  [IGNORED] Will ignore: BUY trades")
            else:  # both
                print(f"  [BOTH] Will take: Both BUY and SELL trades")
            
            # Additional info for SMMA strategies
            if strategy_type == "smma":
                length = strategy_data.get('length', 7)
                source_price = strategy_data.get('source_price', 'close')
                print(f"  SMMA Length: {length}")
                print(f"  Source Price: {source_price}")
            
            print()
            
        except Exception as e:
            print(f"[ERROR] Failed to read {strategy_file.name}: {e}")
            print()
    
    print("=" * 80)

if __name__ == "__main__":
    check_all_strategies()
