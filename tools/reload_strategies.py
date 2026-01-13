"""
Reload Strategies Tool
Removes and re-adds strategies from JSON files to pick up changes.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from src.mt5_connector import MT5Connector
from src.strategy.strategy_manager import StrategyManager
from src.strategy.strategy_persistence import StrategyPersistence
from src.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def reload_strategies(strategy_names=None):
    """
    Reload specified strategies or all strategies.
    
    Args:
        strategy_names: List of strategy names to reload, or None to reload all
    """
    print(f"\n{'='*70}")
    print("Reloading Strategies")
    print(f"{'='*70}\n")
    
    # Initialize MT5
    mt5 = MT5Connector()
    config = Config()
    mt5_path = config.get('mt5.path', '')
    mt5_login = config.get('mt5.login', 0)
    mt5_password = config.get('mt5.password', '')
    mt5_server = config.get('mt5.server', '')
    
    if not mt5.initialize(mt5_path, mt5_login, mt5_password, mt5_server):
        print("[ERROR] MT5 not connected")
        return
    
    if not mt5.is_connected():
        print("[ERROR] MT5 initialization failed")
        return
    
    print("[OK] MT5 connected\n")
    
    # Initialize strategy manager
    strategy_manager = StrategyManager()
    
    # Load persistence
    persistence = StrategyPersistence()
    
    # Get list of strategies to reload
    if strategy_names is None:
        # Reload all strategies
        all_strategies = persistence.load_all_strategies()
        strategy_names = [s.name for s in all_strategies]
        print(f"Reloading all {len(strategy_names)} strategies...\n")
    else:
        print(f"Reloading {len(strategy_names)} strategy(ies)...\n")
    
    # Reload each strategy
    reloaded = 0
    failed = 0
    
    for strategy_name in strategy_names:
        print(f"Reloading: {strategy_name}...")
        
        # Remove existing strategy if present
        if strategy_manager.get_strategy(strategy_name):
            strategy_manager.remove_strategy(strategy_name)
            print(f"  Removed existing strategy from memory")
        
        # Load from JSON
        strategy_file = persistence.strategies_dir / f"{strategy_name}.json"
        if not strategy_file.exists():
            print(f"  [ERROR] Strategy file not found: {strategy_file}")
            failed += 1
            continue
        
        strategy = persistence.load_strategy(str(strategy_file))
        if not strategy:
            print(f"  [ERROR] Failed to load strategy from file")
            failed += 1
            continue
        
        # Set MT5 connector
        if hasattr(strategy, 'set_mt5_connector'):
            strategy.set_mt5_connector(mt5)
        
        # Add to strategy manager
        if strategy_manager.add_strategy(strategy):
            print(f"  [OK] Strategy reloaded successfully")
            print(f"      Type: {type(strategy).__name__}")
            print(f"      Symbol: {strategy.symbol}")
            print(f"      Enabled: {strategy.enabled}")
            
            # Show strategy-specific info
            if hasattr(strategy, 'length'):
                print(f"      SMMA Length: {strategy.length}")
            if hasattr(strategy, 'pivot_left'):
                print(f"      SMC Pivot: {strategy.pivot_left}/{strategy.pivot_right}")
            if hasattr(strategy, 'buy_filters'):
                print(f"      Buy Filters: {len(strategy.buy_filters) if strategy.buy_filters else 0}")
            if hasattr(strategy, 'sell_filters'):
                print(f"      Sell Filters: {len(strategy.sell_filters) if strategy.sell_filters else 0}")
            
            reloaded += 1
        else:
            print(f"  [ERROR] Failed to add strategy to manager")
            failed += 1
        
        print()
    
    print(f"{'='*70}")
    print(f"Reload Complete: {reloaded} succeeded, {failed} failed")
    print(f"{'='*70}\n")
    
    # Cleanup
    mt5.shutdown()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Reload specific strategies
        strategy_names = sys.argv[1:]
        reload_strategies(strategy_names)
    else:
        # Reload all strategies
        print("Reloading all strategies...")
        print("(To reload specific strategies, provide names as arguments)")
        print()
        reload_strategies()
