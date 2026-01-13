"""
Debug SELL Strategy Cross Detection
Check why the strategy didn't enter when cross happened
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
import json
from src.config import Config
from src.strategy.smc_strategy import SMCStrategy

def debug_sell_cross():
    """Debug why SELL strategy didn't enter on cross"""
    
    print("=" * 70)
    print("  SELL Strategy Cross Detection Debug")
    print("=" * 70)
    print()
    
    # Load strategy
    strategy_file = project_root / "strategies" / "SELL.json"
    with open(strategy_file, 'r') as f:
        strategy_data = json.load(f)
    
    symbol = strategy_data.get('symbol')
    timeframe = strategy_data.get('timeframe', 5)
    
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
        error = mt5.last_error()
        print(f"[ERROR] MT5 initialization failed: {error}")
        return
    
    # Get more historical data to see when pivot was formed
    timeframe_enum = getattr(mt5, f"TIMEFRAME_M{timeframe}", mt5.TIMEFRAME_M5)
    rates = mt5.copy_rates_from_pos(symbol, timeframe_enum, 0, 500)
    
    if rates is None or len(rates) == 0:
        print(f"[ERROR] Failed to get rates for {symbol}")
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
    
    # Create strategy
    strategy = SMCStrategy(
        name=strategy_data.get('name'),
        symbol=symbol,
        timeframe=timeframe,
        pivot_left=strategy_data.get('pivot_left', 2),
        pivot_right=strategy_data.get('pivot_right', 2),
        emit_on=strategy_data.get('emit_on', 'NONE'),
        sell_filters=strategy_data.get('sell_filters', [])
    )
    
    # Update strategy with all candles
    print("Updating strategy with historical data...")
    strategy.update(candles)
    
    print(f"\nCurrent State:")
    print(f"  Active Pivot Low: {strategy.active_pivot_low_price}")
    print(f"  Active Pivot High: {strategy.active_pivot_high_price}")
    print(f"  Total Pivots: {len(strategy.all_pivot_lows)} lows, {len(strategy.all_pivot_highs)} highs")
    print()
    
    # Show recent pivots
    if strategy.all_pivot_lows:
        print("Recent Pivot Lows:")
        for i, pivot in enumerate(strategy.all_pivot_lows[-5:], 1):
            print(f"  {i}. Price: {pivot.price:.5f}, Index: {pivot.index}")
    print()
    
    # Check current price vs pivot low
    current_price = (mt5.symbol_info_tick(symbol).bid + mt5.symbol_info_tick(symbol).ask) / 2.0
    print(f"Current Price: {current_price:.5f}")
    
    if strategy.active_pivot_low_price:
        print(f"Pivot Low: {strategy.active_pivot_low_price:.5f}")
        print(f"Price vs Pivot: {current_price:.5f} vs {strategy.active_pivot_low_price:.5f}")
        print(f"Difference: {current_price - strategy.active_pivot_low_price:.5f}")
        print()
        
        # Check if price is below pivot
        if current_price < strategy.active_pivot_low_price:
            print("Price IS below pivot low")
            
            # Check previous close
            prev_close = candles[-2]['close'] if len(candles) >= 2 else current_price
            print(f"Previous Close: {prev_close:.5f}")
            
            # Check cross condition
            # crosses_under: prev_price > right >= left
            # prev_price > pivot_low >= current_price
            check1 = prev_close > strategy.active_pivot_low_price
            check2 = strategy.active_pivot_low_price >= current_price
            
            print(f"\nCross Condition Check:")
            print(f"  Required: prev_close > pivot_low >= current_price")
            print(f"  Check 1: {prev_close:.5f} > {strategy.active_pivot_low_price:.5f} = {check1}")
            print(f"  Check 2: {strategy.active_pivot_low_price:.5f} >= {current_price:.5f} = {check2}")
            
            if check1 and check2:
                print(f"\n  [CROSS DETECTED] Condition should be TRUE!")
            else:
                if not check1:
                    print(f"\n  [BLOCKER] Previous close ({prev_close:.5f}) was NOT above pivot low")
                    print(f"  This means price was already below pivot when strategy checked")
                if not check2:
                    print(f"\n  [BLOCKER] Pivot low ({strategy.active_pivot_low_price:.5f}) is NOT >= current ({current_price:.5f})")
        else:
            print("Price is ABOVE pivot low - waiting for cross")
    
    # Test signal generation
    print("\n" + "=" * 70)
    print("Testing Signal Generation")
    print("=" * 70)
    
    ohlc = {
        'open': float(candles[-1]['open']),
        'high': float(candles[-1]['high']),
        'low': float(candles[-1]['low']),
        'close': float(candles[-1]['close'])
    }
    
    market_data = {
        'symbol': symbol,
        'timeframe': timeframe,
        'current_price': current_price,
        'ohlc': ohlc
    }
    
    signal = strategy.generate_signal(market_data)
    print(f"\nGenerated Signal: {signal}")
    
    # Check _prev_filter_price
    print(f"\nPrevious Filter Price: {strategy._prev_filter_price}")
    
    # Manually check the condition
    if strategy.sell_filters:
        filt = strategy.sell_filters[0]
        left_op = filt.get("left_operand", "")
        operator = filt.get("operator", "")
        right_op = filt.get("right_operand", "")
        
        print(f"\nManual Condition Check:")
        print(f"  Condition: {left_op} {operator} {right_op}")
        
        from src.strategy.unified_indicator_resolver import resolve_operand
        context = {
            'price': current_price,
            'ohlc': ohlc,
            'smc_pivots': {}
        }
        
        if strategy.active_pivot_low_price:
            context['smc_pivots']['pivot_low'] = strategy.active_pivot_low_price
        
        left_val = resolve_operand(left_op, context)
        right_val = resolve_operand(right_op, context)
        
        print(f"  Left Value: {left_val}")
        print(f"  Right Value: {right_val}")
        print(f"  Previous Price: {strategy._prev_filter_price}")
        
        if operator == 'crosses_under' and left_val and right_val:
            prev = strategy._prev_filter_price if strategy._prev_filter_price else prev_close
            result = prev > right_val >= left_val
            print(f"  Cross Check: {prev:.5f} > {right_val:.5f} >= {left_val:.5f} = {result}")
    
    mt5.shutdown()

if __name__ == "__main__":
    debug_sell_cross()
