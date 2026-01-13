"""Analyze BTC_SELL strategy entry conditions"""
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
    strategy = persistence.load_strategy("strategies/BTC_SELL.json")
    
    if not strategy:
        print("Failed to load BTC_SELL strategy")
        return
    
    print("=" * 70)
    print("BTC_SELL Strategy Configuration")
    print("=" * 70)
    print(f"Strategy Name: {strategy.name}")
    print(f"Symbol: {strategy.symbol}")
    print(f"Timeframe: {strategy.timeframe}")
    print(f"Enabled: {strategy.enabled}")
    print(f"Emit On: {strategy.emit_on}")
    print(f"Pivot Left: {strategy.pivot_left}")
    print(f"Pivot Right: {strategy.pivot_right}")
    print()
    
    # Check sell filters
    if hasattr(strategy, 'sell_filters') and strategy.sell_filters:
        print("=" * 70)
        print("SELL Entry Conditions (Sell Filters)")
        print("=" * 70)
        for i, filter_cond in enumerate(strategy.sell_filters, 1):
            enabled = filter_cond.get("enabled", True)
            left = filter_cond.get("left_operand", "")
            operator = filter_cond.get("operator", "")
            right = filter_cond.get("right_operand", "")
            connector = filter_cond.get("connector", "OR")
            
            status = "✅ ENABLED" if enabled else "❌ DISABLED"
            print(f"\nFilter {i} ({status}):")
            print(f"  Condition: {left} {operator} {right}")
            if i < len(strategy.sell_filters):
                print(f"  Connector: {connector}")
            
            # Explain the condition
            if operator == "crosses_below" or operator == "crosses under":
                print(f"  Meaning: Price crosses BELOW {right}")
                print(f"  Logic: prev_price > {right} >= current_price")
            elif operator == "crosses_above" or operator == "crosses above":
                print(f"  Meaning: Price crosses ABOVE {right}")
                print(f"  Logic: prev_price < {right} <= current_price")
            elif operator == "<":
                print(f"  Meaning: {left} is less than {right}")
            elif operator == ">":
                print(f"  Meaning: {left} is greater than {right}")
    else:
        print("=" * 70)
        print("No SELL filters configured!")
        print("=" * 70)
    
    # Check SL/TP
    print()
    print("=" * 70)
    print("Risk Management")
    print("=" * 70)
    print(f"SL Type: {getattr(strategy, 'sl_type', 'N/A')}")
    print(f"SL Value: {getattr(strategy, 'sl_value', 'N/A')}")
    print(f"SL Enabled: {getattr(strategy, 'sl_enabled', 'N/A')}")
    print(f"TP Value: {getattr(strategy, 'tp_value', 'N/A')}")
    print(f"TP Enabled: {getattr(strategy, 'tp_enabled', 'N/A')}")
    
    # Get current market data if MT5 is available
    mt5 = MT5Connector()
    if mt5.initialize():
        symbol_info = mt5.get_symbol_info('BTCUSDm')
        if symbol_info:
            tick = mt5.get_symbol_info_tick('BTCUSDm')
            if tick:
                current_price = (tick.get('bid', 0) + tick.get('ask', 0)) / 2.0
                print()
                print("=" * 70)
                print("Current Market State")
                print("=" * 70)
                print(f"Current Price (Bid/Ask Avg): {current_price:.2f}")
                print(f"Bid: {tick.get('bid', 0):.2f}")
                print(f"Ask: {tick.get('ask', 0):.2f}")
                
                # Note: We can't get SMC data without running the strategy update
                print()
                print("Note: To see SMC prices (CHoCH, BOS, pivots), check the application logs")
                print("      when the strategy is running and receiving market data updates.")
        
        mt5.shutdown()
    
    print()
    print("=" * 70)
    print("When Will It Enter?")
    print("=" * 70)
    print("The strategy will enter a SELL trade when:")
    print("1. The sell filter condition(s) are met")
    print("2. The strategy is enabled")
    print("3. Trading hours allow (if configured)")
    print()
    print("Check the application logs for detailed evaluation of conditions.")

if __name__ == "__main__":
    main()
