"""
Historical State Checker for SMMA Strategy
Processes historical candles to see when signal candles occurred and entry conditions were met.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from datetime import datetime, timedelta
from src.mt5_connector import MT5Connector
from src.strategy.strategy_persistence import StrategyPersistence
from src.config import Config

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_smma_historical_state(strategy_name: str, lookback_bars: int = 50):
    """
    Check historical state of SMMA strategy by processing candles one by one.
    
    Args:
        strategy_name: Name of the strategy
        lookback_bars: Number of bars to look back
    """
    print(f"\n{'='*80}")
    print(f"Historical State Check: {strategy_name}")
    print(f"{'='*80}\n")
    
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
    
    # Load strategy
    persistence = StrategyPersistence()
    strategies = persistence.load_all_strategies()
    
    strategy = None
    for s in strategies:
        if s.name == strategy_name:
            s.set_mt5_connector(mt5)
            strategy = s
            break
    
    if not strategy:
        print(f"[ERROR] Strategy '{strategy_name}' not found")
        return
    
    if not hasattr(strategy, '_calculate_smma'):
        print(f"[ERROR] Strategy '{strategy_name}' is not an SMMA strategy")
        return
    
    print(f"Strategy: {strategy.name}")
    print(f"Symbol: {strategy.symbol}")
    print(f"Timeframe: {strategy.timeframe}")
    print(f"Length: {strategy.length}")
    print(f"Source Price: {strategy.source_price}")
    print(f"Trade Direction: {strategy.trade_direction}")
    print()
    
    # Get historical candles
    candles = strategy._get_candles(count=lookback_bars + strategy.length + 10)
    if not candles or len(candles) < strategy.length + 2:
        print(f"[ERROR] Not enough candles. Got {len(candles) if candles else 0}, need at least {strategy.length + 2}")
        return
    
    print(f"Loaded {len(candles)} candles")
    print(f"Processing last {lookback_bars} bars...\n")
    
    # Calculate SMMA for all candles
    smma_values = strategy._calculate_smma(candles)
    if not smma_values or len(smma_values) < 2:
        print("[ERROR] Could not calculate SMMA values")
        return
    
    # SMMA values start at index 'length' (first value is SMA of first 'length' candles)
    # So smma_values[0] corresponds to candles[strategy.length - 1]
    # smma_values[i] corresponds to candles[strategy.length - 1 + i]
    
    # Reset strategy state for clean simulation
    strategy.entry_high = 0.0
    strategy.entry_low = 0.0
    strategy.entry_high_s = 0.0
    strategy.entry_low_s = 0.0
    strategy.High = 0.0
    strategy.Low = 0.0
    strategy.High_s = 0.0
    strategy.Low_s = 0.0
    strategy.valid_buy = False
    strategy.valid_sell = False
    strategy.f1 = False
    strategy.f2 = False
    strategy.previous_price = None
    
    # Process candles from oldest to newest (simulating real-time)
    # Start from where we have SMMA values
    smma_start_idx = strategy.length - 1  # First SMMA value corresponds to this candle index
    start_idx = max(smma_start_idx + 1, len(candles) - lookback_bars)  # Need at least 2 candles for comparison
    
    events = []
    
    for i in range(start_idx, len(candles)):
        candle = candles[i]
        prev_candle = candles[i - 1] if i > 0 else candle
        
        current_close = candle['close']
        prev_close = prev_candle['close']
        current_high = candle['high']
        current_low = candle['low']
        
        # Map candle index to SMMA index
        smma_idx = i - smma_start_idx
        if smma_idx < 0 or smma_idx >= len(smma_values):
            continue
        
        current_smma = smma_values[smma_idx]
        prev_smma = smma_values[smma_idx - 1] if smma_idx > 0 else current_smma
        
        # Detect signal candles
        signal_candle = strategy._is_crossover(current_close, prev_close, current_smma, prev_smma)
        sig_candle = strategy._is_crossunder(current_close, prev_close, current_smma, prev_smma)
        
        # Store previous state
        prev_state = {
            'valid_buy': strategy.valid_buy,
            'valid_sell': strategy.valid_sell,
            'High': strategy.High,
            'Low': strategy.Low,
            'High_s': strategy.High_s,
            'Low_s': strategy.Low_s,
            'f1': strategy.f1,
            'f2': strategy.f2
        }
        
        # Handle buy signal candle
        if signal_candle and not strategy.f1:
            strategy.Low = current_low
            strategy.High = current_high
            strategy.valid_buy = True
            strategy.valid_sell = False
            events.append({
                'bar': i,
                'time': candle.get('time', 'N/A'),
                'type': 'BUY_SIGNAL_CANDLE',
                'price': current_close,
                'high': current_high,
                'low': current_low,
                'smma': current_smma
            })
        
        # Handle sell signal candle
        if sig_candle and not strategy.f2:
            strategy.High_s = current_high
            strategy.Low_s = current_low
            strategy.valid_buy = False
            strategy.valid_sell = True
            events.append({
                'bar': i,
                'time': candle.get('time', 'N/A'),
                'type': 'SELL_SIGNAL_CANDLE',
                'price': current_close,
                'high': current_high,
                'low': current_low,
                'smma': current_smma
            })
        
        # Check buy entry
        buy_entry = False
        if strategy.trade_direction in ("both", "long") and strategy.valid_buy and strategy.High > 0.0:
            buy_entry = strategy._is_crossover(current_close, prev_close, strategy.High, strategy.High)
            if buy_entry:
                strategy.f1 = True
                strategy.f2 = False
                strategy.entry_high = strategy.High
                strategy.entry_low = strategy.Low
                events.append({
                    'bar': i,
                    'time': candle.get('time', 'N/A'),
                    'type': 'BUY_ENTRY',
                    'price': current_close,
                    'entry_high': strategy.entry_high,
                    'entry_low': strategy.entry_low
                })
        
        # Check sell entry
        sell_entry = False
        if strategy.trade_direction in ("both", "short") and strategy.valid_sell and strategy.Low_s > 0.0:
            sell_entry = strategy._is_crossunder(current_close, prev_close, strategy.Low_s, strategy.Low_s)
            if sell_entry:
                strategy.f1 = False
                strategy.f2 = True
                strategy.entry_high_s = current_high
                strategy.entry_low_s = current_low
                events.append({
                    'bar': i,
                    'time': candle.get('time', 'N/A'),
                    'type': 'SELL_ENTRY',
                    'price': current_close,
                    'entry_high_s': strategy.entry_high_s,
                    'entry_low_s': strategy.entry_low_s
                })
        
        # Reset logic
        if strategy.entry_low > 0.0:
            if strategy._is_crossunder(current_close, prev_close, strategy.entry_low, strategy.entry_low):
                events.append({
                    'bar': i,
                    'time': candle.get('time', 'N/A'),
                    'type': 'BUY_RESET',
                    'price': current_close,
                    'entry_low': strategy.entry_low
                })
                strategy.High = 0.0
                strategy.Low = 0.0
                strategy.f1 = False
                strategy.valid_buy = False
        
        if strategy.entry_high_s > 0.0:
            if strategy._is_crossover(current_close, prev_close, strategy.entry_high_s, strategy.entry_high_s):
                events.append({
                    'bar': i,
                    'time': candle.get('time', 'N/A'),
                    'type': 'SELL_RESET',
                    'price': current_close,
                    'entry_high_s': strategy.entry_high_s
                })
                strategy.High_s = 0.0
                strategy.Low_s = 0.0
                strategy.f2 = False
                strategy.valid_sell = False
        
        strategy.previous_price = current_close
    
    # Display results
    print(f"{'='*80}")
    print(f"Events Found: {len(events)}")
    print(f"{'='*80}\n")
    
    if not events:
        print("No signal candles or entries found in the historical data.")
        print("\nCurrent State:")
        print(f"  valid_buy: {strategy.valid_buy}")
        print(f"  valid_sell: {strategy.valid_sell}")
        print(f"  High: {strategy.High if strategy.High > 0 else 'None'}")
        print(f"  Low: {strategy.Low if strategy.Low > 0 else 'None'}")
        print(f"  High_s: {strategy.High_s if strategy.High_s > 0 else 'None'}")
        print(f"  Low_s: {strategy.Low_s if strategy.Low_s > 0 else 'None'}")
        print(f"  f1: {strategy.f1}")
        print(f"  f2: {strategy.f2}")
    else:
        for event in events:
            event_type = event['type']
            bar = event['bar']
            time_str = event.get('time', 'N/A')
            if isinstance(time_str, datetime):
                time_str = time_str.strftime('%Y-%m-%d %H:%M:%S')
            
            if event_type == 'BUY_SIGNAL_CANDLE':
                print(f"Bar {bar} ({time_str}): [BUY SIGNAL CANDLE]")
                print(f"  Close={event['price']:.5f}, SMMA={event['smma']:.5f}")
                print(f"  High={event['high']:.5f}, Low={event['low']:.5f}")
                print(f"  -> Waiting for close to cross above High={event['high']:.5f}")
            elif event_type == 'SELL_SIGNAL_CANDLE':
                print(f"Bar {bar} ({time_str}): [SELL SIGNAL CANDLE]")
                print(f"  Close={event['price']:.5f}, SMMA={event['smma']:.5f}")
                print(f"  High_s={event['high']:.5f}, Low_s={event['low']:.5f}")
                print(f"  -> Waiting for close to cross below Low_s={event['low']:.5f}")
            elif event_type == 'BUY_ENTRY':
                print(f"Bar {bar} ({time_str}): [BUY ENTRY TRIGGERED]")
                print(f"  Close={event['price']:.5f} crossed above High={event['entry_high']:.5f}")
                print(f"  Entry High={event['entry_high']:.5f}, Entry Low={event['entry_low']:.5f}")
            elif event_type == 'SELL_ENTRY':
                print(f"Bar {bar} ({time_str}): [SELL ENTRY TRIGGERED]")
                print(f"  Close={event['price']:.5f} crossed below Low_s={event['entry_low_s']:.5f}")
                print(f"  Entry High_s={event['entry_high_s']:.5f}, Entry Low_s={event['entry_low_s']:.5f}")
            elif event_type == 'BUY_RESET':
                print(f"Bar {bar} ({time_str}): [BUY RESET] Stop loss hit")
                print(f"  Close={event['price']:.5f} crossed below entry_low={event['entry_low']:.5f}")
            elif event_type == 'SELL_RESET':
                print(f"Bar {bar} ({time_str}): [SELL RESET] Stop loss hit")
                print(f"  Close={event['price']:.5f} crossed above entry_high_s={event['entry_high_s']:.5f}")
            print()
        
        print(f"\nFinal State:")
        print(f"  valid_buy: {strategy.valid_buy}")
        print(f"  valid_sell: {strategy.valid_sell}")
        print(f"  High: {strategy.High if strategy.High > 0 else 'None'}")
        print(f"  Low: {strategy.Low if strategy.Low > 0 else 'None'}")
        print(f"  High_s: {strategy.High_s if strategy.High_s > 0 else 'None'}")
        print(f"  Low_s: {strategy.Low_s if strategy.Low_s > 0 else 'None'}")
        print(f"  f1: {strategy.f1}")
        print(f"  f2: {strategy.f2}")
        if strategy.entry_high > 0 or strategy.entry_low > 0:
            print(f"  Entry High: {strategy.entry_high:.5f}, Entry Low: {strategy.entry_low:.5f}")
        if strategy.entry_high_s > 0 or strategy.entry_low_s > 0:
            print(f"  Entry High_s: {strategy.entry_high_s:.5f}, Entry Low_s: {strategy.entry_low_s:.5f}")
    
    print(f"\n{'='*80}\n")
    
    # Cleanup
    mt5.shutdown()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_smma_historical_state.py <strategy_name> [lookback_bars]")
        print("\nExample:")
        print("  python check_smma_historical_state.py SELL_EUR 50")
        print("  python check_smma_historical_state.py SELL_EUR 100")
        sys.exit(1)
    
    strategy_name = sys.argv[1]
    lookback_bars = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    
    check_smma_historical_state(strategy_name, lookback_bars)
