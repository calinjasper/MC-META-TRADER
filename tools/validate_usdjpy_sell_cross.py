"""
USDJPYm M5 SELL Strategy Validator
Compares MT5 indicator pivot/cross logic with Python strategy to prove 1:1 behavior
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
import json
import logging
from datetime import datetime
from src.config import Config
from src.strategy.smc_strategy import SMCStrategy
from src.strategy.smc_utils import fractal_pivot_low, extract_ohlc_arrays

# Enable debug logging for SMC strategy
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('src.strategy.smc_strategy')

def validate_usdjpy_sell():
    """Validate USDJPYm M5 SELL strategy cross detection"""
    
    print("=" * 80)
    print("  USDJPYm M5 SELL Strategy Validator")
    print("  Comparing MT5 Indicator vs Python Strategy")
    print("=" * 80)
    print()
    
    # Load strategy
    strategy_file = project_root / "strategies" / "SELL.json"
    with open(strategy_file, 'r') as f:
        strategy_data = json.load(f)
    
    symbol = strategy_data.get('symbol')
    timeframe = strategy_data.get('timeframe', 5)
    
    print(f"Strategy: {strategy_data.get('name')}")
    print(f"Symbol: {symbol}")
    print(f"Timeframe: M{timeframe}")
    print(f"Pivot Left: {strategy_data.get('pivot_left', 2)}")
    print(f"Pivot Right: {strategy_data.get('pivot_right', 2)}")
    print(f"Emit On: {strategy_data.get('emit_on', 'NONE')}")
    print()
    
    # Initialize MT5
    config = Config()
    mt5_config = config.get('mt5', {})
    
    if not mt5.initialize(
        path=mt5_config.get('path', ''),
        login=mt5_config.get('login', 0),
        password=mt5_config.get('password', ''),
        server=mt5_config.get('server', ''),
        timeout=mt5_config.get('timeout', 10000)
    ):
        print(f"[ERROR] MT5 initialization failed: {mt5.last_error()}")
        return
    
    # Get current tick
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"[ERROR] Failed to get tick for {symbol}")
        mt5.shutdown()
        return
    
    current_ltp = (tick.bid + tick.ask) / 2.0
    
    print("=" * 80)
    print("MT5 Current State")
    print("=" * 80)
    print(f"Current LTP: {current_ltp:.5f}")
    print(f"Bid: {tick.bid:.5f}")
    print(f"Ask: {tick.ask:.5f}")
    print()
    
    # Get historical data
    timeframe_enum = getattr(mt5, f"TIMEFRAME_M{timeframe}", mt5.TIMEFRAME_M5)
    rates = mt5.copy_rates_from_pos(symbol, timeframe_enum, 0, 500)
    
    if rates is None or len(rates) == 0:
        print(f"[ERROR] Failed to get rates")
        mt5.shutdown()
        return
    
    # Convert to candles
    candles = []
    for rate in rates:
        candles.append({
            'time': int(rate['time']),
            'open': float(rate['open']),
            'high': float(rate['high']),
            'low': float(rate['low']),
            'close': float(rate['close']),
            'volume': int(rate['tick_volume'])
        })
    
    # Show last few candles
    print("Last 5 M5 Candles:")
    for i in range(-5, 0):
        c = candles[i]
        dt = datetime.fromtimestamp(c['time'])
        print(f"  {dt.strftime('%Y-%m-%d %H:%M')} | O:{c['open']:.5f} H:{c['high']:.5f} L:{c['low']:.5f} C:{c['close']:.5f}")
    print()
    
    # Create strategy instance
    strategy = SMCStrategy(
        name=strategy_data.get('name'),
        symbol=symbol,
        timeframe=timeframe,
        pivot_left=strategy_data.get('pivot_left', 2),
        pivot_right=strategy_data.get('pivot_right', 2),
        emit_on=strategy_data.get('emit_on', 'NONE'),
        sell_filters=strategy_data.get('sell_filters', [])
    )
    
    # Set MT5 connector for the strategy
    from src.mt5_connector import MT5Connector
    connector = MT5Connector()
    connector.connected = True  # Assume connected since we initialized MT5
    strategy.set_mt5_connector(connector)
    
    print("=" * 80)
    print("Python Strategy State (After Processing Historical Data)")
    print("=" * 80)
    
    # Simulate signal generation to update pivots
    market_data = {
        'symbol': symbol,
        'timeframe': timeframe,
        'current_price': current_ltp,
        'ohlc': {
            'open': candles[-1]['open'],
            'high': candles[-1]['high'],
            'low': candles[-1]['low'],
            'close': candles[-1]['close']
        }
    }
    
    # Generate signal (this will update pivots and check conditions)
    signal = strategy.generate_signal(market_data)
    
    print(f"Active Pivot Low: {strategy.active_pivot_low_price}")
    print(f"Active Pivot High: {strategy.active_pivot_high_price}")
    print(f"Total Pivot Lows: {len(strategy.all_pivot_lows)}")
    print(f"Total Pivot Highs: {len(strategy.all_pivot_highs)}")
    print(f"Previous Filter Price: {strategy._prev_filter_price}")
    print(f"Last Bar Time: {strategy._last_bar_time}")
    print()
    
    # Show recent pivot lows
    if strategy.all_pivot_lows:
        print("Recent Pivot Lows (last 5):")
        for pivot in strategy.all_pivot_lows[-5:]:
            bar_time = datetime.fromtimestamp(candles[pivot.index]['time'])
            print(f"  Index {pivot.index}: {pivot.price:.5f} at {bar_time.strftime('%Y-%m-%d %H:%M')}")
        print()
    
    # Check entry condition
    print("=" * 80)
    print("Entry Condition Analysis")
    print("=" * 80)
    
    if strategy.sell_filters:
        filt = strategy.sell_filters[0]
        left_op = filt.get("left_operand", "")
        operator = filt.get("operator", "")
        right_op = filt.get("right_operand", "")
        
        print(f"Condition: {left_op} {operator} {right_op}")
        print()
        
        if strategy.active_pivot_low_price:
            print(f"Current LTP: {current_ltp:.5f}")
            print(f"Active Pivot Low: {strategy.active_pivot_low_price:.5f}")
            print(f"Previous Price: {strategy._prev_filter_price}")
            print()
            
            # Check cross condition
            if operator == 'crosses_under':
                # crosses_under: prev_price > right >= left
                if strategy._prev_filter_price is not None:
                    check1 = strategy._prev_filter_price > strategy.active_pivot_low_price
                    check2 = strategy.active_pivot_low_price >= current_ltp
                    
                    print(f"Cross Under Logic:")
                    print(f"  Required: prev_price > pivot_low >= current_ltp")
                    print(f"  Check 1: {strategy._prev_filter_price:.5f} > {strategy.active_pivot_low_price:.5f} = {check1}")
                    print(f"  Check 2: {strategy.active_pivot_low_price:.5f} >= {current_ltp:.5f} = {check2}")
                    print(f"  Result: {check1 and check2}")
                    print()
                    
                    if check1 and check2:
                        print("[CROSS DETECTED] Strategy should generate SELL signal!")
                    elif not check1:
                        print("[NO CROSS] Previous price was not above pivot low")
                        print(f"  Action: Price needs to rise above {strategy.active_pivot_low_price:.5f} first")
                    elif not check2:
                        print("[NO CROSS] Current price is not at or below pivot low")
                        print(f"  Action: Price needs to drop to {strategy.active_pivot_low_price:.5f}")
                else:
                    print("[NO PREVIOUS PRICE] Cannot detect cross on first tick")
                    print(f"  Current LTP will be saved as previous price for next tick")
            
            # Check distance
            distance = current_ltp - strategy.active_pivot_low_price
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info:
                distance_pips = distance / symbol_info.point if symbol_info.point > 0 else 0
                print(f"\nDistance from Pivot Low: {distance_pips:.1f} pips")
                if distance > 0:
                    print(f"  Price is ABOVE pivot low")
                elif distance < 0:
                    print(f"  Price is BELOW pivot low")
                else:
                    print(f"  Price is AT pivot low")
        else:
            print("[NO PIVOT LOW] No pivot low detected yet")
            print("  Need more price action to form a confirmed pivot")
    
    print()
    print("=" * 80)
    print("Signal Generation Result")
    print("=" * 80)
    print(f"Generated Signal: {signal if signal else 'None'}")
    
    if signal == "SELL":
        print("[SUCCESS] Strategy generated SELL signal!")
    elif signal is None:
        print("[WAITING] Strategy is waiting for entry conditions")
    
    print()
    
    # Test with simulated tick movement
    print("=" * 80)
    print("Simulated Tick Test (if pivot exists)")
    print("=" * 80)
    
    if strategy.active_pivot_low_price:
        # Simulate price above pivot (same bar, just tick update)
        test_price_above = strategy.active_pivot_low_price + 0.01
        print(f"\nTest 1: Price moves to {test_price_above:.5f} (above pivot)")
        test_market_data = market_data.copy()
        test_market_data['current_price'] = test_price_above
        signal1 = strategy.generate_signal(test_market_data)
        print(f"  Signal: {signal1 if signal1 else 'None'}")
        print(f"  Previous price saved: {strategy._prev_filter_price:.5f}")
        print(f"  Check: prev={strategy._prev_filter_price:.5f} > pivot={strategy.active_pivot_low_price:.5f} = {strategy._prev_filter_price > strategy.active_pivot_low_price}")
        
        # Simulate price crossing below pivot (same bar, next tick)
        test_price_below = strategy.active_pivot_low_price - 0.01
        print(f"\nTest 2: Price crosses to {test_price_below:.5f} (below pivot)")
        print(f"  Previous price BEFORE call: {strategy._prev_filter_price:.5f}")
        test_market_data2 = market_data.copy()
        test_market_data2['current_price'] = test_price_below
        signal2 = strategy.generate_signal(test_market_data2)
        print(f"  Signal: {signal2 if signal2 else 'None'}")
        print(f"  Previous price AFTER call: {strategy._prev_filter_price:.5f}")
        print(f"  Check 1: prev > pivot = {strategy._prev_filter_price:.5f} > {strategy.active_pivot_low_price:.5f} = {strategy._prev_filter_price > strategy.active_pivot_low_price}")
        print(f"  Check 2: pivot >= current = {strategy.active_pivot_low_price:.5f} >= {test_price_below:.5f} = {strategy.active_pivot_low_price >= test_price_below}")
        
        if signal2 == "SELL":
            print("  [SUCCESS] Cross detected and SELL signal generated!")
        else:
            print("  [ISSUE] Cross should have been detected")
            # Check why it didn't trigger
            if strategy._prev_filter_price <= strategy.active_pivot_low_price:
                print(f"  Reason: Previous price ({strategy._prev_filter_price:.5f}) was not above pivot ({strategy.active_pivot_low_price:.5f})")
            elif strategy.active_pivot_low_price < test_price_below:
                print(f"  Reason: Current price ({test_price_below:.5f}) is not at or below pivot ({strategy.active_pivot_low_price:.5f})")
    
    mt5.shutdown()

if __name__ == "__main__":
    validate_usdjpy_sell()
