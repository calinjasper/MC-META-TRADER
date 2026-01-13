"""Check XA_SELL strategy state"""
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.strategy.strategy_persistence import StrategyPersistence
from src.mt5_connector import MT5Connector

mt5 = MT5Connector()
if mt5.initialize():
    sp = StrategyPersistence()
    strategy = sp.load_strategy('strategies/XA_SELL.json')
    if strategy:
        strategy.set_mt5_connector(mt5)
        print(f"\nStrategy: {strategy.name}")
        print(f"Symbol: {strategy.symbol}")
        print(f"Enabled: {strategy.enabled}")
        print(f"Trade Direction: {getattr(strategy, 'trade_direction', 'both')}")
        print(f"\nState Variables:")
        print(f"  Valid Buy: {strategy.valid_buy}")
        print(f"  Valid Sell: {strategy.valid_sell}")
        print(f"  f1 (buy entered): {strategy.f1}")
        print(f"  f2 (sell entered): {strategy.f2}")
        print(f"\nEntry Levels:")
        high_val = strategy.high if strategy.high > 0 else 0.0
        low_val = strategy.low if strategy.low > 0 else 0.0
        high_s_val = strategy.high_s if strategy.high_s > 0 else 0.0
        low_s_val = strategy.low_s if strategy.low_s > 0 else 0.0
        print(f"  High: {high_val:.5f}")
        print(f"  Low: {low_val:.5f}")
        print(f"  High_s: {high_s_val:.5f}")
        print(f"  Low_s: {low_s_val:.5f}")
        print(f"\nEntry Tracking:")
        entry_high_val = strategy.entry_high if strategy.entry_high > 0 else 0.0
        entry_low_val = strategy.entry_low if strategy.entry_low > 0 else 0.0
        entry_high_s_val = strategy.entry_high_s if strategy.entry_high_s > 0 else 0.0
        entry_low_s_val = strategy.entry_low_s if strategy.entry_low_s > 0 else 0.0
        print(f"  entry_high: {entry_high_val:.5f}")
        print(f"  entry_low: {entry_low_val:.5f}")
        print(f"  entry_high_s: {entry_high_s_val:.5f}")
        print(f"  entry_low_s: {entry_low_s_val:.5f}")
        
        # Get current price
        tick = mt5.get_symbol_info_tick(strategy.symbol)
        if tick:
            current_price = (tick['bid'] + tick['ask']) / 2.0
            print(f"\nCurrent Market Price: {current_price:.5f}")
            if strategy.low_s > 0:
                print(f"  Low_s (sell entry level): {strategy.low_s:.5f}")
                print(f"  Price needs to cross below {strategy.low_s:.5f} for SELL entry")
                if current_price < strategy.low_s:
                    print(f"  [ALERT] Price is already below Low_s! Entry should trigger.")
                else:
                    print(f"  [WAITING] Price is above Low_s, waiting for cross below")
    else:
        print("Failed to load strategy")
    mt5.shutdown()
else:
    print("Failed to connect to MT5")
