"""
Diagnostic tool to check why strategies are not generating signals or trades.

Checks:
1. Strategy status (enabled/disabled)
2. Position status (if position exists, prevents new signals)
3. Strategy configuration
4. Signal generation test
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from src.mt5_connector import MT5Connector
from src.strategy.strategy_manager import StrategyManager
from src.strategy.strategy_persistence import StrategyPersistence
from src.trading.position_tracker import PositionTracker
from src.data_feed import DataFeed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def diagnose_strategy(strategy_name: str):
    """Diagnose a specific strategy"""
    print(f"\n{'='*60}")
    print(f"Diagnosing Strategy: {strategy_name}")
    print(f"{'='*60}\n")
    
    # Initialize MT5
    mt5 = MT5Connector()
    
    # Try to initialize MT5
    from src.config import Config
    config = Config()
    mt5_path = config.get('mt5.path', '')
    mt5_login = config.get('mt5.login', 0)
    mt5_password = config.get('mt5.password', '')
    mt5_server = config.get('mt5.server', '')
    
    if not mt5.initialize(mt5_path, mt5_login, mt5_password, mt5_server):
        print("[ERROR] MT5 not connected. Please connect MT5 from the application first.")
        return
    
    if not mt5.is_connected():
        print("[ERROR] MT5 initialization failed")
        return
    
    print("[OK] MT5 connected\n")
    
    # Initialize components
    position_tracker = PositionTracker()
    strategy_manager = StrategyManager(position_tracker=position_tracker)
    data_feed = DataFeed(mt5)
    
    # Load strategies
    persistence = StrategyPersistence()
    strategies = persistence.load_all_strategies()
    
    for strategy in strategies:
        if strategy.name == strategy_name:
            strategy.set_mt5_connector(mt5)
            strategy_manager.add_strategy(strategy)
            break
    else:
        print(f"[ERROR] Strategy '{strategy_name}' not found in saved strategies")
        print(f"\nAvailable strategies:")
        for s in strategies:
            print(f"  - {s.name} ({s.symbol})")
        return
    
    strategy = strategy_manager.get_strategy(strategy_name)
    if not strategy:
        print(f"[ERROR] Strategy '{strategy_name}' not found in strategy manager")
        return
    
    # Check 1: Strategy Status
    print("1. Strategy Status:")
    print(f"   Enabled: {'YES' if strategy.enabled else 'NO'}")
    print(f"   Symbol: {strategy.symbol}")
    print(f"   Type: {type(strategy).__name__}")
    if hasattr(strategy, 'timeframe'):
        print(f"   Timeframe: {strategy.timeframe}")
    print()
    
    # Check 2: Position Status
    print("2. Position Status:")
    has_buy = position_tracker.has_position(strategy.name, strategy.symbol, "BUY")
    has_sell = position_tracker.has_position(strategy.name, strategy.symbol, "SELL")
    print(f"   Has BUY position: {'YES (blocks new BUY signals)' if has_buy else 'NO'}")
    print(f"   Has SELL position: {'YES (blocks new SELL signals)' if has_sell else 'NO'}")
    
    if has_buy or has_sell:
        print(f"\n   [WARNING] Strategy has open position(s).")
        print(f"   This prevents new signals in the same direction.")
        print(f"   To allow multiple entries, disable 'Preserve Position' in strategy settings.")
        print(f"   Current preserve_position setting: {getattr(strategy, 'preserve_position', False)}")
    print()
    
    # Check 3: Strategy Configuration
    print("3. Strategy Configuration:")
    if hasattr(strategy, 'trade_direction'):
        print(f"   Trade Direction: {strategy.trade_direction}")
    if hasattr(strategy, 'pivot_left'):
        print(f"   SMC Pivot Left: {strategy.pivot_left}")
        print(f"   SMC Pivot Right: {strategy.pivot_right}")
        print(f"   SMC Emit On: {strategy.emit_on}")
    if hasattr(strategy, 'buy_filters'):
        print(f"   Buy Filters: {len(strategy.buy_filters) if strategy.buy_filters else 0}")
    if hasattr(strategy, 'sell_filters'):
        print(f"   Sell Filters: {len(strategy.sell_filters) if strategy.sell_filters else 0}")
    print()
    
    # Check 4: Test Signal Generation
    print("4. Testing Signal Generation:")
    data_feed.add_symbol(strategy.symbol)
    data_feed.start()
    
    # Wait a moment for data
    import time
    time.sleep(2)
    
    # Get market data
    tick = data_feed.get_latest_tick(strategy.symbol)
    if not tick:
        print(f"   [ERROR] No tick data available for {strategy.symbol}")
        print(f"   Make sure the symbol is available in MT5")
    else:
        print(f"   [OK] Got tick data: Bid={tick.get('bid')}, Ask={tick.get('ask')}")
        
        # Build market data
        market_data = {
            "tick": tick,
            "current_price": (tick.get('bid', 0) + tick.get('ask', 0)) / 2.0,
            "symbol": strategy.symbol
        }
        
        # Try to generate signal
        try:
            signal = strategy.generate_signal(market_data)
            if signal:
                print(f"   [OK] Signal Generated: {signal}")
            else:
                print(f"   [INFO] No signal generated (conditions not met)")
                print(f"   This is normal if entry conditions are not currently satisfied")
        except Exception as e:
            print(f"   [ERROR] Error generating signal: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    
    # Check 5: MT5 Connection
    print("5. MT5 Connection Status:")
    print(f"   Connected: {'YES' if mt5.is_connected() else 'NO'}")
    if mt5.is_connected():
        symbol_info = mt5.get_symbol_info(strategy.symbol)
        if symbol_info:
            print(f"   Symbol Available: YES")
            print(f"   Symbol Digits: {symbol_info.get('digits', 'N/A')}")
        else:
            print(f"   Symbol Available: NO")
            print(f"   [WARNING] Symbol '{strategy.symbol}' not found in MT5")
    
    print(f"\n{'='*60}\n")
    
    # Cleanup
    data_feed.stop()
    mt5.shutdown()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_strategy_signals.py <strategy_name>")
        print("\nExample:")
        print("  python diagnose_strategy_signals.py sell_btc")
        print("  python diagnose_strategy_signals.py SELL_EUR")
        sys.exit(1)
    
    strategy_name = sys.argv[1]
    diagnose_strategy(strategy_name)
