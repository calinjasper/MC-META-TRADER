"""
Detailed diagnostic tool to check strategy conditions and state.
Shows current market data, indicator values, and why signals are/aren't generated.
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
from src.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def diagnose_strategy_detailed(strategy_name: str):
    """Detailed diagnosis of a specific strategy"""
    print(f"\n{'='*70}")
    print(f"Detailed Diagnosis: {strategy_name}")
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
    
    # Initialize components
    position_tracker = PositionTracker()
    strategy_manager = StrategyManager(position_tracker=position_tracker)
    data_feed = DataFeed(mt5)
    
    # Load strategies
    persistence = StrategyPersistence()
    strategies = persistence.load_all_strategies()
    
    strategy = None
    for s in strategies:
        if s.name == strategy_name:
            s.set_mt5_connector(mt5)
            strategy_manager.add_strategy(s)
            strategy = s
            break
    
    if not strategy:
        print(f"[ERROR] Strategy '{strategy_name}' not found")
        print(f"\nAvailable strategies:")
        for s in strategies:
            print(f"  - {s.name} ({s.symbol})")
        return
    
    print(f"Strategy: {strategy.name}")
    print(f"Type: {type(strategy).__name__}")
    print(f"Symbol: {strategy.symbol}")
    print(f"Enabled: {strategy.enabled}")
    print()
    
    # Get market data
    data_feed.add_symbol(strategy.symbol)
    data_feed.start()
    import time
    time.sleep(2)
    
    tick = data_feed.get_latest_tick(strategy.symbol)
    if not tick:
        print(f"[ERROR] No tick data for {strategy.symbol}")
        return
    
    current_price = (tick.get('bid', 0) + tick.get('ask', 0)) / 2.0
    print(f"Current Price (LTP): {current_price:.5f}")
    print(f"Bid: {tick.get('bid'):.5f}, Ask: {tick.get('ask'):.5f}")
    print()
    
    # Strategy-specific diagnostics
    if isinstance(strategy, type(strategy_manager.get_strategy(strategy_name))):
        strategy_type = type(strategy).__name__
        
        if strategy_type == "SMCStrategy":
            print("SMC Strategy Details:")
            print(f"  Pivot Left: {strategy.pivot_left}")
            print(f"  Pivot Right: {strategy.pivot_right}")
            print(f"  Emit On: {strategy.emit_on}")
            print(f"  Trade Direction: {strategy.trade_direction}")
            print()
            
            # Get candles
            candles = strategy._get_candles(count=100)
            if candles:
                print(f"  Latest Candle: O={candles[-1]['open']:.5f}, H={candles[-1]['high']:.5f}, "
                      f"L={candles[-1]['low']:.5f}, C={candles[-1]['close']:.5f}")
                print()
            
            # Check active SMC prices
            market_data = {
                "tick": tick,
                "current_price": current_price,
                "symbol": strategy.symbol
            }
            
            # Force update to get current SMC values
            test_signal = strategy.generate_signal(market_data)
            
            print("  Active SMC Prices:")
            print(f"    Pivot High: {strategy.active_pivot_high_price}")
            print(f"    Pivot Low: {strategy.active_pivot_low_price}")
            print(f"    CHoCH Price: {strategy.active_choch_price}")
            print(f"    BOS Price: {strategy.active_bos_price}")
            print(f"    Bias: {strategy.bias}")
            print()
            
            # Check buy filters
            if strategy.buy_filters:
                print(f"  Buy Filters ({len(strategy.buy_filters)}):")
                for i, filt in enumerate(strategy.buy_filters, 1):
                    enabled = filt.get('enabled', True)
                    left = filt.get('left_operand', 'N/A')
                    op = filt.get('operator', 'N/A')
                    right = filt.get('right_operand', 'N/A')
                    print(f"    {i}. {'[ENABLED]' if enabled else '[DISABLED]'} {left} {op} {right}")
            
            # Check sell filters
            if strategy.sell_filters:
                print(f"  Sell Filters ({len(strategy.sell_filters)}):")
                for i, filt in enumerate(strategy.sell_filters, 1):
                    enabled = filt.get('enabled', True)
                    left = filt.get('left_operand', 'N/A')
                    op = filt.get('operator', 'N/A')
                    right = filt.get('right_operand', 'N/A')
                    print(f"    {i}. {'[ENABLED]' if enabled else '[DISABLED]'} {left} {op} {right}")
            
            print()
            print(f"  Signal Generated: {test_signal if test_signal else 'None'}")
            
        # SMMA strategy has been removed
        # elif strategy_type == "SMMAStrategy":
            print("SMMA Strategy Details:")
            print(f"  Length: {strategy.length}")
            print(f"  Source Price: {strategy.source_price}")
            print(f"  Trade Direction: {strategy.trade_direction}")
            print()
            
            # Get candles
            candles = strategy._get_candles(count=100)
            if candles and len(candles) >= strategy.length:
                print(f"  Latest Candle: O={candles[-1]['open']:.5f}, H={candles[-1]['high']:.5f}, "
                      f"L={candles[-1]['low']:.5f}, C={candles[-1]['close']:.5f}")
                print()
                
                # Calculate SMMA
                smma_values = strategy._calculate_smma(candles)
                if smma_values:
                    current_smma = smma_values[-1]
                    prev_smma = smma_values[-2] if len(smma_values) > 1 else None
                    print(f"  Current SMMA: {current_smma:.5f}")
                    if prev_smma:
                        print(f"  Previous SMMA: {prev_smma:.5f}")
                    print()
                    
                    # Check signal candle state
                    print("  Signal Candle State:")
                    print(f"    valid_buy: {strategy.valid_buy}")
                    print(f"    valid_sell: {strategy.valid_sell}")
                    print(f"    High (buy signal): {strategy.High if strategy.High > 0 else 'None'}")
                    print(f"    Low (buy signal): {strategy.Low if strategy.Low > 0 else 'None'}")
                    print(f"    High_s (sell signal): {strategy.High_s if strategy.High_s > 0 else 'None'}")
                    print(f"    Low_s (sell signal): {strategy.Low_s if strategy.Low_s > 0 else 'None'}")
                    print(f"    f1 (buy flag): {strategy.f1}")
                    print(f"    f2 (sell flag): {strategy.f2}")
                    print()
                    
                    # Check entry levels
                    print("  Entry Levels:")
                    print(f"    entry_high: {strategy.entry_high if strategy.entry_high > 0 else 'None'}")
                    print(f"    entry_low: {strategy.entry_low if strategy.entry_low > 0 else 'None'}")
                    print(f"    entry_high_s: {strategy.entry_high_s if strategy.entry_high_s > 0 else 'None'}")
                    print(f"    entry_low_s: {strategy.entry_low_s if strategy.entry_low_s > 0 else 'None'}")
                    print()
                    
                    # Check current conditions
                    current_close = candles[-1]['close']
                    prev_close = candles[-2]['close'] if len(candles) > 1 else current_close
                    
                    print("  Current Conditions:")
                    # Check for signal candle
                    signal_candle = strategy._is_crossover(current_close, prev_close, current_smma, prev_smma)
                    sig_candle = strategy._is_crossunder(current_close, prev_close, current_smma, prev_smma)
                    print(f"    Close crossed above SMMA: {signal_candle}")
                    print(f"    Close crossed below SMMA: {sig_candle}")
                    
                    # Check for buy entry
                    if strategy.valid_buy and strategy.High > 0:
                        buy_entry = strategy._is_crossover(current_close, prev_close, strategy.High, strategy.High)
                        print(f"    Close crossed above High ({strategy.High:.5f}): {buy_entry}")
                    
                    # Check for sell entry
                    if strategy.valid_sell and strategy.Low_s > 0:
                        sell_entry = strategy._is_crossunder(current_close, prev_close, strategy.Low_s, strategy.Low_s)
                        print(f"    Close crossed below Low_s ({strategy.Low_s:.5f}): {sell_entry}")
            
            # Test signal generation
            market_data = {
                "tick": tick,
                "current_price": current_price,
                "symbol": strategy.symbol
            }
            test_signal = strategy.generate_signal(market_data)
            print()
            print(f"  Signal Generated: {test_signal if test_signal else 'None'}")
    
    print(f"\n{'='*70}\n")
    
    # Cleanup
    data_feed.stop()
    mt5.shutdown()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_strategy_detailed.py <strategy_name>")
        sys.exit(1)
    
    strategy_name = sys.argv[1]
    diagnose_strategy_detailed(strategy_name)
