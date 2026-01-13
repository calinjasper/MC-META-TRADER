"""
Check EURSELL Strategy Entry Conditions
Analyze when the EURSELL strategy will enter trades
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
from src.config import Config
from src.strategy.smc_strategy import SMCStrategy
from src.strategy.smc_utils import fractal_pivot_high, fractal_pivot_low, extract_ohlc_arrays


def check_eur_sell_entry():
    """Check when EURSELL strategy will enter trades"""
    print("=" * 70)
    print("  EURSELL Strategy Entry Analysis")
    print("=" * 70)
    print()
    
    # Load strategy
    strategy_file = project_root / "strategies" / "EURSELL.json"
    if not strategy_file.exists():
        print(f"[ERROR] Strategy file not found: {strategy_file}")
        return
    
    with open(strategy_file, 'r') as f:
        strategy_data = json.load(f)
    
    print(f"Strategy: {strategy_data['name']}")
    print(f"Symbol: {strategy_data['symbol']}")
    print(f"Timeframe: {strategy_data['timeframe']} minutes")
    print(f"Trade Direction: {strategy_data.get('trade_direction', 'both')}")
    print(f"Emit On: {strategy_data.get('emit_on', 'NONE')}")
    print(f"Pivot Settings: Left={strategy_data.get('pivot_left', 2)}, Right={strategy_data.get('pivot_right', 2)}")
    print()
    
    # Display entry condition
    sell_filters = strategy_data.get('sell_filters', [])
    if sell_filters:
        print("Entry Condition (Sell Filter):")
        for i, filt in enumerate(sell_filters, 1):
            if filt.get('enabled', True):
                left = filt.get('left_operand', '')
                op = filt.get('operator', '')
                right = filt.get('right_operand', '')
                print(f"  {i}. {left} {op} {right}")
        print()
    
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
    
    symbol = strategy_data['symbol']
    timeframe = strategy_data['timeframe']
    
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
    
    # Add to market watch
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
    
    print(f"Current Market Data:")
    print(f"  Current Price (Mid): {current_price:.5f}")
    print(f"  Bid: {current_bid:.5f}")
    print(f"  Ask: {current_ask:.5f}")
    print()
    
    # Get recent candles
    print(f"Fetching {symbol} M{timeframe} candles...")
    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, 500)
    if rates is None or len(rates) == 0:
        print(f"[ERROR] Could not get rates for {symbol}")
        mt5.shutdown()
        return
    
    print(f"[OK] Retrieved {len(rates)} candles")
    print()
    
    # Convert MT5 rates to dict format for extract_ohlc_arrays
    rates_dict = []
    for rate in rates:
        rates_dict.append({
            'open': float(rate[1]),
            'high': float(rate[2]),
            'low': float(rate[3]),
            'close': float(rate[4])
        })
    
    # Extract OHLC arrays
    opens, highs, lows, closes = extract_ohlc_arrays(rates_dict)
    
    # Get previous close (for cross detection)
    prev_close = float(closes[-2]) if len(closes) >= 2 else current_price
    
    print(f"Price Data:")
    print(f"  Current Close: {closes[-1]:.5f}")
    print(f"  Previous Close: {prev_close:.5f}")
    print(f"  Current Price (Live): {current_price:.5f}")
    print()
    
    # Create SMC strategy instance to get CHoCH price
    from src.strategy.strategy_persistence import StrategyPersistence
    persistence = StrategyPersistence()
    strategy = persistence.load_strategy(strategy_file)
    
    if not strategy:
        print("[ERROR] Failed to load strategy")
        mt5.shutdown()
        return
    
    # Convert rates to dict format for strategy
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
    
    # Get SMC pivots and CHoCH price
    smc_pivots = market_data.get('smc_pivots', {})
    if not smc_pivots:
        # Try to get from strategy directly
        if hasattr(strategy, 'active_choch_price'):
            choch_price = strategy.active_choch_price
        else:
            choch_price = None
    else:
        choch_price = smc_pivots.get('choch_price')
    
    pivot_high = smc_pivots.get('pivot_high') if smc_pivots else (strategy.active_pivot_high_price if hasattr(strategy, 'active_pivot_high_price') else None)
    pivot_low = smc_pivots.get('pivot_low') if smc_pivots else (strategy.active_pivot_low_price if hasattr(strategy, 'active_pivot_low_price') else None)
    
    print("SMC Data:")
    if pivot_high:
        print(f"  Pivot High: {pivot_high:.5f}")
    else:
        print(f"  Pivot High: None (not enough data)")
    
    if pivot_low:
        print(f"  Pivot Low: {pivot_low:.5f}")
    else:
        print(f"  Pivot Low: None (not enough data)")
    
    if choch_price:
        print(f"  CHoCH Price: {choch_price:.5f}")
    else:
        print(f"  CHoCH Price: None (no CHoCH event detected yet)")
    print()
    
    # Evaluate entry condition
    if not sell_filters:
        print("[WARNING] No sell filters configured")
        mt5.shutdown()
        return
    
    print("Entry Condition Evaluation:")
    print("-" * 70)
    
    for i, filt in enumerate(sell_filters, 1):
        if not filt.get('enabled', True):
            print(f"Filter {i}: DISABLED")
            continue
        
        left_op = filt.get('left_operand', '')
        operator = filt.get('operator', '')
        right_op = filt.get('right_operand', '')
        
        print(f"\nFilter {i}: {left_op} {operator} {right_op}")
        
        # Get left operand value
        if left_op == 'current_price':
            left_value = current_price
        else:
            left_value = None
            print(f"    [WARNING] Unknown left operand: {left_op}")
        
        # Get right operand value
        if right_op == 'smc_choch_price':
            right_value = choch_price
        elif right_op == 'smc_pivot_high':
            right_value = pivot_high
        elif right_op == 'smc_pivot_low':
            right_value = pivot_low
        else:
            right_value = None
            print(f"    [WARNING] Unknown right operand: {right_op}")
        
        if left_value is None or right_value is None:
            if right_value is None:
                print(f"    Status: [BLOCKER] {right_op} is not available")
                if right_op == 'smc_choch_price':
                    print(f"    Reason: No CHoCH event has been detected yet")
                    print(f"    Action: Wait for a CHoCH event to occur")
            else:
                print(f"    Status: [BLOCKER] Cannot evaluate condition")
            continue
        
        print(f"    Current Price: {left_value:.5f}")
        print(f"    CHoCH Price: {right_value:.5f}")
        print(f"    Previous Close: {prev_close:.5f}")
        
        # Evaluate condition
        if operator == 'crosses_under':
            # Crosses under: prev_price > right >= left
            # This means: price was above CHoCH, now at or below CHoCH
            has_crossed = prev_close > right_value >= left_value
            
            print(f"\n    Cross Logic Check:")
            print(f"      Required: prev_close ({prev_close:.5f}) > CHoCH ({right_value:.5f}) >= current ({left_value:.5f})")
            print(f"      Check 1: prev_close > CHoCH = {prev_close:.5f} > {right_value:.5f} = {prev_close > right_value}")
            print(f"      Check 2: CHoCH >= current = {right_value:.5f} >= {left_value:.5f} = {right_value >= left_value}")
            
            if has_crossed:
                print(f"\n    [TRIGGERED] ✅ SELL signal generated!")
                print(f"    The price has crossed under the CHoCH price")
            else:
                distance_to_choch = current_price - right_value
                distance_pips = distance_to_choch / symbol_info.point if symbol_info.point > 0 else 0
                
                if current_price > right_value:
                    print(f"\n    Status: [WAITING] Price is above CHoCH price")
                    print(f"    Required: Price must drop to {right_value:.5f} and cross under")
                    print(f"    Distance: {abs(distance_pips):.1f} pips above CHoCH")
                    print(f"    Action: Wait for price to drop below {right_value:.5f}")
                elif current_price < right_value:
                    print(f"\n    Status: [PARTIAL] Price is below CHoCH, but cross not confirmed")
                    print(f"    Required: prev_close ({prev_close:.5f}) > CHoCH ({right_value:.5f}) >= current ({left_value:.5f})")
                    if prev_close <= right_value:
                        print(f"    [BLOCKER] Previous close was not above CHoCH price")
                        print(f"    Action: Need price to rise above CHoCH first, then drop below")
        else:
            print(f"    [WARNING] Unknown operator: {operator}")
    
    print()
    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    
    if choch_price is None:
        print("[PRIMARY REASON] No CHoCH price available")
        print("  - Need a CHoCH (Change of Character) event to occur first")
        print("  - CHoCH events happen when market structure changes")
        print("  - Wait for market structure to change (bullish to bearish or vice versa)")
    else:
        if prev_close > choch_price >= current_price:
            print("[PRIMARY REASON] Entry condition is MET!")
            print("  - Price has crossed under CHoCH price")
            print("  - SELL signal should be generated")
        elif current_price > choch_price:
            print("[PRIMARY REASON] Price hasn't reached CHoCH yet")
            distance = (current_price - choch_price) / symbol_info.point if symbol_info.point > 0 else 0
            print(f"  - Need price to drop {abs(distance):.1f} pips to {choch_price:.5f}")
            print(f"  - Then price must cross under CHoCH (prev > CHoCH >= current)")
        elif current_price < choch_price:
            print("[PRIMARY REASON] Price is below CHoCH, but cross not confirmed")
            print(f"  - Current: {current_price:.5f}")
            print(f"  - CHoCH: {choch_price:.5f}")
            print(f"  - Previous: {prev_close:.5f}")
            print(f"  - Need: prev_close ({prev_close:.5f}) > CHoCH ({choch_price:.5f}) >= current ({current_price:.5f})")
            if prev_close <= choch_price:
                print(f"  - [BLOCKER] Previous close was not above CHoCH")
                print(f"  - Price needs to rise above CHoCH first, then drop below")
    
    mt5.shutdown()
    print()


if __name__ == "__main__":
    check_eur_sell_entry()
