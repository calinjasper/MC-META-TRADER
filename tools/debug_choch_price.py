"""
Debug CHoCH Price Calculation
Compare system-calculated CHoCH prices with MT5
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
from src.config import Config
from src.strategy.strategy_persistence import StrategyPersistence
from src.strategy.smc_utils import extract_ohlc_arrays


def debug_choch_price():
    """Debug CHoCH price calculation"""
    print("=" * 70)
    print("  CHoCH Price Debug Analysis")
    print("=" * 70)
    print()
    
    # Load strategy
    strategy_file = project_root / "strategies" / "EURSELL.json"
    if not strategy_file.exists():
        print(f"[ERROR] Strategy file not found: {strategy_file}")
        return
    
    with open(strategy_file, 'r') as f:
        strategy_data = json.load(f)
    
    symbol = strategy_data['symbol']
    timeframe = strategy_data['timeframe']
    
    # Load config
    config = Config()
    mt5_config = config.get('mt5', {})
    
    # Initialize MT5
    print("Initializing MT5...")
    if not mt5.initialize(
        path=mt5_config.get('path', ''),
        login=mt5_config.get('login', 0),
        password=mt5_config.get('password', ''),
        server=mt5_config.get('server', ''),
        timeout=mt5_config.get('timeout', 10000)
    ):
        error = mt5.last_error()
        print(f"[ERROR] MT5 initialization failed: {error}")
        return
    
    print("[OK] MT5 connected")
    print()
    
    # Convert timeframe to MT5 constant
    timeframe_map = {
        1: mt5.TIMEFRAME_M1,
        5: mt5.TIMEFRAME_M5,
        15: mt5.TIMEFRAME_M15,
        30: mt5.TIMEFRAME_M30,
        60: mt5.TIMEFRAME_H1,
        240: mt5.TIMEFRAME_H4,
        1440: mt5.TIMEFRAME_D1
    }
    mt5_timeframe = timeframe_map.get(timeframe, mt5.TIMEFRAME_M15)
    
    # Get symbol info
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"[ERROR] Symbol {symbol} not found")
        mt5.shutdown()
        return
    
    mt5.symbol_select(symbol, True)
    
    # Get current tick
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        print(f"[ERROR] Could not get tick for {symbol}")
        mt5.shutdown()
        return
    
    current_price = (tick.bid + tick.ask) / 2.0
    current_bid = tick.bid
    current_ask = tick.ask
    
    # Get recent candles
    print(f"Fetching {symbol} M{timeframe} candles...")
    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, 500)
    if rates is None or len(rates) == 0:
        print(f"[ERROR] Could not get rates for {symbol}")
        mt5.shutdown()
        return
    
    print(f"[OK] Retrieved {len(rates)} candles")
    print()
    
    # Convert rates to dict format
    rates_dict = []
    for rate in rates:
        rates_dict.append({
            'time': rate[0],
            'open': float(rate[1]),
            'high': float(rate[2]),
            'low': float(rate[3]),
            'close': float(rate[4]),
            'tick_volume': int(rate[5]),
            'spread': int(rate[6]),
            'real_volume': int(rate[7]) if len(rate) > 7 else 0
        })
    
    # Extract OHLC arrays
    opens, highs, lows, closes = extract_ohlc_arrays(rates_dict)
    
    # Load strategy
    persistence = StrategyPersistence()
    strategy = persistence.load_strategy(strategy_file)
    
    if not strategy:
        print("[ERROR] Failed to load strategy")
        mt5.shutdown()
        return
    
    # Get market data for strategy
    market_data = {
        "tick": {
            "bid": current_bid,
            "ask": current_ask,
            "last": current_price
        },
        "rates": rates_dict,
        "ohlc": {
            "open": float(opens[-1]) if opens else None,
            "high": float(highs[-1]) if highs else None,
            "low": float(lows[-1]) if lows else None,
            "close": float(closes[-1]) if closes else None,
        }
    }
    
    # Update strategy to get SMC data
    signal = strategy.generate_signal(market_data)
    
    # Get all CHoCH events
    print("=" * 70)
    print("All CHoCH Events Detected:")
    print("=" * 70)
    print()
    
    choch_events = [e for e in strategy.all_events if e.event_type == "CHoCH"]
    
    if not choch_events:
        print("[WARNING] No CHoCH events found")
    else:
        print(f"Found {len(choch_events)} CHoCH events:")
        print()
        
        for i, event in enumerate(choch_events, 1):
            # Get candle info for this event
            event_index = event.index
            if event_index < len(rates_dict):
                candle = rates_dict[event_index]
                candle_time = mt5.symbol_info_tick(symbol).time if event_index == len(rates_dict) - 1 else candle['time']
                
                print(f"CHoCH Event {i}:")
                print(f"  Direction: {event.direction}")
                print(f"  Price: {event.price:.5f}")
                print(f"  Index: {event_index} (bar {len(rates_dict) - event_index - 1} bars ago)")
                print(f"  Candle Time: {candle['time']}")
                print(f"  Candle OHLC:")
                print(f"    Open: {candle['open']:.5f}")
                print(f"    High: {candle['high']:.5f}")
                print(f"    Low: {candle['low']:.5f}")
                print(f"    Close: {candle['close']:.5f}")
                print()
    
    # Show active CHoCH price
    print("=" * 70)
    print("Active CHoCH Price:")
    print("=" * 70)
    print()
    
    if strategy.active_choch_price:
        print(f"System CHoCH Price: {strategy.active_choch_price:.5f}")
        print(f"MT5 Expected: 183.359")
        diff = abs(strategy.active_choch_price - 183.359)
        print(f"Difference: {diff:.5f} ({diff / symbol_info.point if symbol_info.point > 0 else 0:.1f} pips)")
        print()
        
        # Find which event this corresponds to
        matching_event = None
        for event in choch_events:
            if abs(event.price - strategy.active_choch_price) < 0.0001:
                matching_event = event
                break
        
        if matching_event:
            print(f"This corresponds to CHoCH Event:")
            print(f"  Direction: {matching_event.direction}")
            print(f"  Index: {matching_event.index}")
            print(f"  Price: {matching_event.price:.5f}")
            
            # Show surrounding candles
            event_idx = matching_event.index
            if event_idx > 0 and event_idx < len(rates_dict) - 1:
                print()
                print("Surrounding Candles:")
                print(f"  Previous (index {event_idx - 1}): Close = {rates_dict[event_idx - 1]['close']:.5f}")
                print(f"  Event Candle (index {event_idx}): Close = {rates_dict[event_idx]['close']:.5f}")
                print(f"  Next (index {event_idx + 1}): Close = {rates_dict[event_idx + 1]['close']:.5f}")
    else:
        print("No active CHoCH price set")
    
    # Show recent candles for reference
    print()
    print("=" * 70)
    print("Recent Candles (last 10):")
    print("=" * 70)
    print()
    
    for i in range(max(0, len(rates_dict) - 10), len(rates_dict)):
        candle = rates_dict[i]
        bars_ago = len(rates_dict) - i - 1
        print(f"Bar {bars_ago} ago (index {i}):")
        print(f"  Time: {candle['time']}")
        print(f"  OHLC: O={candle['open']:.5f} H={candle['high']:.5f} L={candle['low']:.5f} C={candle['close']:.5f}")
        print()
    
    # Check if 183.359 appears in any candle
    print("=" * 70)
    print("Searching for MT5 CHoCH Price (183.359):")
    print("=" * 70)
    print()
    
    found_candles = []
    for i, candle in enumerate(rates_dict):
        # Check if 183.359 is close to any OHLC value
        for price_type, price in [('Open', candle['open']), ('High', candle['high']), 
                                   ('Low', candle['low']), ('Close', candle['close'])]:
            if abs(price - 183.359) < 0.001:
                found_candles.append((i, price_type, price, candle))
    
    if found_candles:
        print(f"Found {len(found_candles)} candles with price close to 183.359:")
        for idx, price_type, price, candle in found_candles:
            bars_ago = len(rates_dict) - idx - 1
            print(f"  Index {idx} (bar {bars_ago} ago): {price_type} = {price:.5f}")
            print(f"    OHLC: O={candle['open']:.5f} H={candle['high']:.5f} L={candle['low']:.5f} C={candle['close']:.5f}")
    else:
        print("No candles found with price exactly 183.359")
        print("Checking closest prices...")
        closest_candles = []
        for i, candle in enumerate(rates_dict):
            for price_type, price in [('Open', candle['open']), ('High', candle['high']), 
                                       ('Low', candle['low']), ('Close', candle['close'])]:
                diff = abs(price - 183.359)
                closest_candles.append((i, price_type, price, diff, candle))
        
        # Sort by difference and show top 5
        closest_candles.sort(key=lambda x: x[3])
        print("\nClosest prices to 183.359:")
        for idx, price_type, price, diff, candle in closest_candles[:5]:
            bars_ago = len(rates_dict) - idx - 1
            print(f"  Index {idx} (bar {bars_ago} ago): {price_type} = {price:.5f} (diff: {diff:.5f})")
    
    mt5.shutdown()
    print()


if __name__ == "__main__":
    debug_choch_price()
