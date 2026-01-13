"""
Debug SMMA signal detection to see why crossover/crossunder isn't being detected
"""

import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.strategy.strategy_persistence import StrategyPersistence
from src.mt5_connector import MT5Connector
import MetaTrader5 as mt5

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def debug_smma_signals():
    """Debug SMMA signal detection"""
    
    print("=" * 80)
    print("SMMA Signal Detection Debug")
    print("=" * 80)
    
    # Initialize MT5
    mt5_connector = MT5Connector()
    config_path = project_root / "config" / "config.json"
    
    if config_path.exists():
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
            mt5_config = config.get('mt5', {})
            path = mt5_config.get('path', '')
            login = mt5_config.get('login', 0)
            password = mt5_config.get('password', '')
            server = mt5_config.get('server', '')
            timeout = mt5_config.get('timeout', 10000)
            
            if path and login and password and server:
                if not mt5_connector.initialize(path, login, password, server, timeout):
                    print("[ERROR] Failed to connect to MT5")
                    return
            else:
                if not mt5_connector.initialize():
                    print("[ERROR] Failed to connect to MT5")
                    return
    else:
        if not mt5_connector.initialize():
            print("[ERROR] Failed to connect to MT5")
            return
    
    print(f"[OK] Connected to MT5")
    
    # Load strategies
    persistence = StrategyPersistence()
    
    strategies_to_check = ["XA_BUY", "BTC_SELL"]
    
    for strategy_name in strategies_to_check:
        print("\n" + "=" * 80)
        print(f"Debugging Strategy: {strategy_name}")
        print("=" * 80)
        
        strategy_file = persistence.strategies_dir / f"{strategy_name}.json"
        if not strategy_file.exists():
            print(f"[ERROR] Strategy file not found: {strategy_file}")
            continue
        
        # Load strategy
        strategy = persistence.load_strategy(str(strategy_file))
        if not strategy:
            print(f"[ERROR] Failed to load strategy from {strategy_file}")
            continue
        
        # Set MT5 connector
        if hasattr(strategy, 'set_mt5_connector'):
            strategy.set_mt5_connector(mt5_connector)
        
        symbol = strategy.symbol
        timeframe = getattr(strategy, 'timeframe', mt5.TIMEFRAME_M1)
        
        # Get candles
        candles = strategy._get_candles(count=200)
        if not candles or len(candles) < 10:
            print(f"[ERROR] Not enough candles")
            continue
        
        print(f"[OK] Retrieved {len(candles)} candles")
        
        # Show last 10 candles with SMMA values
        print(f"\n[INFO] Last 10 Candles Analysis:")
        print(f"{'Index':<8} {'Time':<20} {'Close':<12} {'High':<12} {'Low':<12} {'SMMA':<12} {'Crossover':<12} {'Crossunder':<12}")
        print("-" * 100)
        
        # Compute SMMA for all candles
        smma_values = strategy._compute_smma_values(candles)
        
        # Check last 10 candles
        for i in range(max(0, len(candles) - 10), len(candles)):
            candle = candles[i]
            smma_val = smma_values[i] if i < len(smma_values) and smma_values[i] is not None else None
            
            # Check for crossover/crossunder
            if i > 0:
                prev_candle = candles[i-1]
                prev_smma = smma_values[i-1] if (i-1) < len(smma_values) and smma_values[i-1] is not None else None
                
                current_close = float(candle['close'])
                prev_close = float(prev_candle['close'])
                
                crossover = False
                crossunder = False
                
                if smma_val is not None and prev_smma is not None:
                    # Crossover: current > smma AND previous <= prev_smma
                    crossover = current_close > smma_val and prev_close <= prev_smma
                    # Crossunder: current < smma AND previous >= prev_smma
                    crossunder = current_close < smma_val and prev_close >= prev_smma
                
                time_str = str(candle['time'])[:19] if candle.get('time') else 'N/A'
                close_str = f"{current_close:.5f}"
                high_str = f"{float(candle['high']):.5f}"
                low_str = f"{float(candle['low']):.5f}"
                smma_str = f"{smma_val:.5f}" if smma_val is not None else "N/A"
                cross_str = "YES" if crossover else "NO"
                under_str = "YES" if crossunder else "NO"
                
                marker = ""
                if crossover:
                    marker = " <-- CROSSOVER!"
                elif crossunder:
                    marker = " <-- CROSSUNDER!"
                
                print(f"{i:<8} {time_str:<20} {close_str:<12} {high_str:<12} {low_str:<12} {smma_str:<12} {cross_str:<12} {under_str:<12}{marker}")
            else:
                time_str = str(candle['time'])[:19] if candle.get('time') else 'N/A'
                close_str = f"{float(candle['close']):.5f}"
                high_str = f"{float(candle['high']):.5f}"
                low_str = f"{float(candle['low']):.5f}"
                smma_str = f"{smma_val:.5f}" if smma_val is not None else "N/A"
                print(f"{i:<8} {time_str:<20} {close_str:<12} {high_str:<12} {low_str:<12} {smma_str:<12} {'N/A':<12} {'N/A':<12}")
        
        # Check current state
        print(f"\n[INFO] Current Strategy State:")
        print(f"  - High: {strategy.high}")
        print(f"  - Low: {strategy.low}")
        print(f"  - High_s: {strategy.high_s}")
        print(f"  - Low_s: {strategy.low_s}")
        print(f"  - Valid Buy: {strategy.valid_buy}")
        print(f"  - Valid Sell: {strategy.valid_sell}")
        print(f"  - f1: {strategy.f1}")
        print(f"  - f2: {strategy.f2}")
        
        # Get current price
        tick_info = mt5.symbol_info_tick(symbol)
        if tick_info:
            current_price = (tick_info.bid + tick_info.ask) / 2.0
            print(f"\n[INFO] Current Market Price: {current_price}")
            
            if strategy.valid_buy and strategy.high > 0:
                print(f"  - Waiting for price to cross above {strategy.high} for BUY entry")
                if current_price > strategy.high:
                    print(f"  - [OK] Price ({current_price}) is above High ({strategy.high}) - BUY entry should trigger!")
                else:
                    print(f"  - [WAITING] Price needs to cross above {strategy.high}")
            
            if strategy.valid_sell and strategy.low_s > 0:
                print(f"  - Waiting for price to cross below {strategy.low_s} for SELL entry")
                if current_price < strategy.low_s:
                    print(f"  - [OK] Price ({current_price}) is below Low_s ({strategy.low_s}) - SELL entry should trigger!")
                else:
                    print(f"  - [WAITING] Price needs to cross below {strategy.low_s}")
    
    print("\n" + "=" * 80)
    print("Debug Complete")
    print("=" * 80)


if __name__ == "__main__":
    debug_smma_signals()
