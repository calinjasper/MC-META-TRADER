"""
Check if strategies have existing positions that might be blocking new trades
"""

import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.strategy.strategy_persistence import StrategyPersistence
from src.mt5_connector import MT5Connector
from src.trading.order_manager import OrderManager
import MetaTrader5 as mt5

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_strategy_positions():
    """Check if strategies have positions that might block trades"""
    
    print("=" * 80)
    print("Strategy Position Check")
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
    
    # Initialize order manager
    from pathlib import Path
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    persistence_file = str(data_dir / "trade_history.json")
    order_manager = OrderManager(mt5_connector, persistence_file=persistence_file)
    
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
        
        symbol = strategy.symbol
        
        # Check MT5 positions
        positions = mt5.positions_get(symbol=symbol)
        if positions is None:
            positions = []
        
        print(f"\n[INFO] MT5 Positions for {symbol}:")
        if len(positions) == 0:
            print(f"  - No positions found")
        else:
            for pos in positions:
                print(f"  - Ticket: {pos.ticket}, Type: {'BUY' if pos.type == 0 else 'SELL'}, "
                      f"Volume: {pos.volume}, Price: {pos.price_open}")
        
        # Check position tracker
        print(f"\n[INFO] Position Tracker Status:")
        has_buy = order_manager.position_tracker.has_position(strategy.name, symbol, "BUY")
        has_sell = order_manager.position_tracker.has_position(strategy.name, symbol, "SELL")
        print(f"  - Has BUY position: {has_buy}")
        print(f"  - Has SELL position: {has_sell}")
        
        # Get strategy state
        if hasattr(strategy, 'get_smma_snapshot'):
            snapshot = strategy.get_smma_snapshot()
            if snapshot:
                print(f"\n[INFO] Strategy State:")
                print(f"  - Valid Buy: {snapshot.get('valid_buy')}")
                print(f"  - Valid Sell: {snapshot.get('valid_sell')}")
                print(f"  - High: {snapshot.get('high')}")
                print(f"  - Low: {snapshot.get('low')}")
                print(f"  - High_s: {snapshot.get('high_s')}")
                print(f"  - Low_s: {snapshot.get('low_s')}")
                
                # Check if entry should trigger
                tick_info = mt5.symbol_info_tick(symbol)
                if tick_info:
                    current_price = (tick_info.bid + tick_info.ask) / 2.0
                    
                    if snapshot.get('valid_buy') and snapshot.get('high', 0) > 0:
                        high = snapshot.get('high')
                        if current_price > high and not has_buy:
                            print(f"\n[OK] BUY Entry should trigger:")
                            print(f"  - Current Price: {current_price}")
                            print(f"  - Entry High: {high}")
                            print(f"  - No existing BUY position")
                        elif has_buy:
                            print(f"\n[BLOCKED] BUY Entry blocked - existing BUY position")
                    
                    if snapshot.get('valid_sell') and snapshot.get('low_s', 0) > 0:
                        low_s = snapshot.get('low_s')
                        if current_price < low_s and not has_sell:
                            print(f"\n[OK] SELL Entry should trigger:")
                            print(f"  - Current Price: {current_price}")
                            print(f"  - Entry Low: {low_s}")
                            print(f"  - No existing SELL position")
                        elif has_sell:
                            print(f"\n[BLOCKED] SELL Entry blocked - existing SELL position")
    
    print("\n" + "=" * 80)
    print("Check Complete")
    print("=" * 80)


if __name__ == "__main__":
    check_strategy_positions()
