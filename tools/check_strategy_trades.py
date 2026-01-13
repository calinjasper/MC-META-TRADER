"""
Diagnostic script to check why XA_BUY and BTC_SELL strategies aren't executing trades
"""

import sys
import json
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.strategy.strategy_persistence import StrategyPersistence
from src.mt5_connector import MT5Connector
import MetaTrader5 as mt5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_strategy_trades():
    """Check why strategies aren't executing trades"""
    
    print("=" * 80)
    print("Strategy Trade Diagnostic Tool")
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
        print(f"Checking Strategy: {strategy_name}")
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
        
        print(f"[OK] Strategy loaded: {strategy.name}")
        print(f"  - Symbol: {strategy.symbol}")
        print(f"  - Enabled: {strategy.enabled}")
        print(f"  - Trade Direction: {getattr(strategy, 'trade_direction', 'both')}")
        print(f"  - Strategy Type: {getattr(strategy, 'strategy_type', 'unknown')}")
        
        # Set MT5 connector
        if hasattr(strategy, 'set_mt5_connector'):
            strategy.set_mt5_connector(mt5_connector)
            print(f"  - MT5 Connector: Set")
        else:
            print(f"  - MT5 Connector: NOT SET (strategy doesn't have set_mt5_connector method)")
        
        # Check if symbol exists in MT5
        symbol = strategy.symbol
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"[ERROR] Symbol {symbol} not found in MT5")
            continue
        
        print(f"[OK] Symbol {symbol} found in MT5")
        print(f"  - Bid: {symbol_info.bid}")
        print(f"  - Ask: {symbol_info.ask}")
        
        # Get timeframe
        timeframe = getattr(strategy, 'timeframe', mt5.TIMEFRAME_M1)
        timeframe_name = {
            mt5.TIMEFRAME_M1: "M1",
            mt5.TIMEFRAME_M5: "M5",
            mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_M30: "M30",
            mt5.TIMEFRAME_H1: "H1",
            mt5.TIMEFRAME_H4: "H4",
            mt5.TIMEFRAME_D1: "D1"
        }.get(timeframe, f"TF{timeframe}")
        
        print(f"  - Timeframe: {timeframe_name} ({timeframe})")
        
        # Get candles
        if hasattr(strategy, '_get_candles'):
            candles = strategy._get_candles(count=200)
            if candles:
                print(f"[OK] Retrieved {len(candles)} candles")
                print(f"  - Latest candle: {candles[-1]}")
            else:
                print(f"[ERROR] Failed to retrieve candles")
                continue
        else:
            print(f"[ERROR] Strategy doesn't have _get_candles method")
            continue
        
        # Get current tick
        tick_info = mt5.symbol_info_tick(symbol)
        if tick_info:
            tick = {
                'bid': tick_info.bid,
                'ask': tick_info.ask,
                'time': tick_info.time
            }
            print(f"[OK] Current tick retrieved")
            print(f"  - Bid: {tick['bid']}")
            print(f"  - Ask: {tick['ask']}")
        else:
            print(f"[ERROR] Failed to retrieve current tick")
            continue
        
        # Prepare market data
        market_data = {
            'tick': tick,
            'rates': candles,
            'indicators': {}
        }
        
        # Generate signal
        print(f"\n[INFO] Generating signal...")
        signal = strategy.generate_signal(market_data)
        
        if signal:
            print(f"[OK] Signal generated: {signal}")
            
            # Check SMMA state if available
            if hasattr(strategy, 'get_smma_snapshot'):
                snapshot = strategy.get_smma_snapshot()
                if snapshot:
                    print(f"\n[INFO] SMMA Snapshot:")
                    print(f"  - SMMA Value: {snapshot.get('smma_value')}")
                    print(f"  - Valid Buy: {snapshot.get('valid_buy')}")
                    print(f"  - Valid Sell: {snapshot.get('valid_sell')}")
                    print(f"  - High: {snapshot.get('high')}")
                    print(f"  - Low: {snapshot.get('low')}")
                    print(f"  - High_s: {snapshot.get('high_s')}")
                    print(f"  - Low_s: {snapshot.get('low_s')}")
        else:
            print(f"[INFO] No signal generated (signal = None)")
            
            # Check SMMA state
            if hasattr(strategy, 'get_smma_snapshot'):
                snapshot = strategy.get_smma_snapshot()
                if snapshot:
                    print(f"\n[INFO] SMMA Snapshot:")
                    print(f"  - SMMA Value: {snapshot.get('smma_value')}")
                    print(f"  - Valid Buy: {snapshot.get('valid_buy')}")
                    print(f"  - Valid Sell: {snapshot.get('valid_sell')}")
                    print(f"  - High: {snapshot.get('high')}")
                    print(f"  - Low: {snapshot.get('low')}")
                    print(f"  - High_s: {snapshot.get('high_s')}")
                    print(f"  - Low_s: {snapshot.get('low_s')}")
                    
                    # Check if we're waiting for entry
                    if snapshot.get('valid_buy'):
                        current_price = (tick.get('bid', 0) + tick.get('ask', 0)) / 2.0
                        high = snapshot.get('high', 0)
                        print(f"\n[INFO] Buy Entry Status:")
                        print(f"  - Current Price: {current_price}")
                        print(f"  - Entry High: {high}")
                        print(f"  - Waiting for price to cross above {high}")
                        if current_price > high:
                            print(f"  - [OK] Price is above High - should trigger BUY entry")
                        else:
                            print(f"  - [WAITING] Price needs to cross above {high}")
                    
                    if snapshot.get('valid_sell'):
                        current_price = (tick.get('bid', 0) + tick.get('ask', 0)) / 2.0
                        low_s = snapshot.get('low_s', 0)
                        print(f"\n[INFO] Sell Entry Status:")
                        print(f"  - Current Price: {current_price}")
                        print(f"  - Entry Low: {low_s}")
                        print(f"  - Waiting for price to cross below {low_s}")
                        if current_price < low_s:
                            print(f"  - [OK] Price is below Low_s - should trigger SELL entry")
                        else:
                            print(f"  - [WAITING] Price needs to cross below {low_s}")
    
    print("\n" + "=" * 80)
    print("Diagnostic Complete")
    print("=" * 80)


if __name__ == "__main__":
    check_strategy_trades()
