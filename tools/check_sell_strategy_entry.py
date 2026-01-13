"""
Check SELL Strategy Entry Conditions
Analyze when the SELL strategy will enter trades
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
import json
from src.strategy.strategy_persistence import StrategyPersistence
from src.strategy.smc_strategy import SMCStrategy
from src.mt5_connector import MT5Connector
from src.strategy.unified_indicator_resolver import resolve_operand

def check_sell_strategy_entry():
    """Check when SELL strategy will enter trades"""
    
    print("=" * 70)
    print("  SELL Strategy Entry Analysis")
    print("=" * 70)
    print()
    
    # Load strategy
    persistence = StrategyPersistence()
    strategy_file = project_root / "strategies" / "SELL.json"
    
    if not strategy_file.exists():
        print(f"[ERROR] Strategy file not found: {strategy_file}")
        return
    
    with open(strategy_file, 'r') as f:
        strategy_data = json.load(f)
    
    print("Strategy Configuration:")
    print(f"  Name: {strategy_data.get('name')}")
    print(f"  Symbol: {strategy_data.get('symbol')}")
    print(f"  Timeframe: M{strategy_data.get('timeframe')}")
    print(f"  Strategy Type: {strategy_data.get('strategy_type')}")
    print(f"  Enabled: {strategy_data.get('enabled')}")
    print(f"  Trade Direction: {strategy_data.get('trade_direction')}")
    print()
    
    # SMC Settings
    print("SMC Settings:")
    print(f"  Pivot Left: {strategy_data.get('pivot_left')}")
    print(f"  Pivot Right: {strategy_data.get('pivot_right')}")
    print(f"  Emit On: {strategy_data.get('emit_on')}")
    print()
    
    # Check sell filters
    sell_filters = strategy_data.get('sell_filters', [])
    if sell_filters:
        print("Entry Condition (Sell Filter):")
        for i, filt in enumerate(sell_filters, 1):
            enabled = filt.get("enabled", True)
            left = filt.get("left_operand", "")
            operator = filt.get("operator", "")
            right = filt.get("right_operand", "")
            connector = filt.get("connector", "AND")
            
            status = "ENABLED" if enabled else "DISABLED"
            print(f"\n  Filter {i} ({status}):")
            print(f"    Condition: {left} {operator} {right}")
            if i < len(sell_filters):
                print(f"    Connector: {connector}")
    else:
        print("[WARNING] No sell filters configured!")
        return
    
    print()
    print("=" * 70)
    print("Current Market State")
    print("=" * 70)
    
    # Initialize MT5
    from src.config import Config
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
    
    symbol = strategy_data.get('symbol')
    timeframe = strategy_data.get('timeframe', 5)
    
    # Get symbol info
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"[ERROR] Symbol {symbol} not found")
        mt5.shutdown()
        return
    
    # Get current price
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"[ERROR] Failed to get tick data for {symbol}")
        mt5.shutdown()
        return
    
    current_price = (tick.bid + tick.ask) / 2.0
    
    # Get recent candles
    timeframe_enum = getattr(mt5, f"TIMEFRAME_M{timeframe}", mt5.TIMEFRAME_M5)
    rates = mt5.copy_rates_from_pos(symbol, timeframe_enum, 0, 500)
    
    if rates is None or len(rates) == 0:
        print(f"[ERROR] Failed to get rates for {symbol}")
        mt5.shutdown()
        return
    
    # Get previous close
    prev_close = rates[-2]['close'] if len(rates) >= 2 else current_price
    
    print(f"  Current Price: {current_price:.5f}")
    print(f"  Previous Close: {prev_close:.5f}")
    print()
    
    # Create strategy instance to get SMC data
    strategy = SMCStrategy(
        name=strategy_data.get('name'),
        symbol=symbol,
        timeframe=timeframe,
        pivot_left=strategy_data.get('pivot_left', 2),
        pivot_right=strategy_data.get('pivot_right', 2),
        emit_on=strategy_data.get('emit_on', 'NONE'),
        sell_filters=sell_filters
    )
    
    # Update strategy with market data
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
    
    strategy.update(candles)
    
    # Get SMC pivots
    from src.strategy.unified_indicator_resolver import resolve_operand
    
    ohlc = {
        'open': float(rates[-1]['open']),
        'high': float(rates[-1]['high']),
        'low': float(rates[-1]['low']),
        'close': float(rates[-1]['close'])
    }
    
    context = {
        'price': current_price,
        'ohlc': ohlc,
        'smc_pivots': {}
    }
    
    # Add SMC pivots
    if strategy.active_pivot_high_price is not None:
        context['smc_pivots']['pivot_high'] = strategy.active_pivot_high_price
    if strategy.active_pivot_low_price is not None:
        context['smc_pivots']['pivot_low'] = strategy.active_pivot_low_price
    if strategy.active_choch_price is not None:
        context['smc_pivots']['choch_price'] = strategy.active_choch_price
    if strategy.active_bos_price is not None:
        context['smc_pivots']['bos_price'] = strategy.active_bos_price
    
    print("SMC Pivot Levels:")
    if strategy.active_pivot_high_price:
        print(f"  Pivot High: {strategy.active_pivot_high_price:.5f}")
    else:
        print(f"  Pivot High: None")
    
    if strategy.active_pivot_low_price:
        print(f"  Pivot Low: {strategy.active_pivot_low_price:.5f}")
    else:
        print(f"  Pivot Low: None")
    
    if strategy.active_choch_price:
        print(f"  CHoCH Price: {strategy.active_choch_price:.5f}")
    else:
        print(f"  CHoCH Price: None")
    
    print()
    
    # Evaluate sell conditions
    print("=" * 70)
    print("Entry Condition Evaluation")
    print("=" * 70)
    
    for i, filt in enumerate(sell_filters, 1):
        if not filt.get("enabled", True):
            print(f"\nFilter {i}: DISABLED - Skipping")
            continue
        
        left_op = filt.get("left_operand", "")
        operator = filt.get("operator", "")
        right_op = filt.get("right_operand", "")
        
        print(f"\nFilter {i}: {left_op} {operator} {right_op}")
        
        # Resolve operands
        left_value = resolve_operand(left_op, context)
        right_value = resolve_operand(right_op, context)
        
        if left_value is None:
            print(f"  [ERROR] Could not resolve left operand: {left_op}")
            continue
        
        if right_value is None:
            print(f"  [ERROR] Could not resolve right operand: {right_op}")
            if right_op == 'smc_pivot_low':
                print(f"    Reason: No pivot low has been detected yet")
                print(f"    Action: Wait for a pivot low to form")
            elif right_op == 'smc_choch_price':
                print(f"    Reason: No CHoCH event has been detected yet")
                print(f"    Action: Wait for a CHoCH event to occur")
            continue
        
        print(f"    Left Value ({left_op}): {left_value:.5f}")
        print(f"    Right Value ({right_op}): {right_value:.5f}")
        print(f"    Previous Close: {prev_close:.5f}")
        
        # Evaluate condition
        if operator == 'crosses_under':
            # Crosses under: prev_price > right >= left
            # This means: price was above pivot low, now at or below pivot low
            has_crossed = prev_close > right_value >= left_value
            
            print(f"\n    Cross Logic Check:")
            print(f"      Required: prev_close ({prev_close:.5f}) > {right_op} ({right_value:.5f}) >= current ({left_value:.5f})")
            print(f"      Check 1: prev_close > {right_op} = {prev_close:.5f} > {right_value:.5f} = {prev_close > right_value}")
            print(f"      Check 2: {right_op} >= current = {right_value:.5f} >= {left_value:.5f} = {right_value >= left_value}")
            
            if has_crossed:
                print(f"\n    [TRIGGERED] ✅ SELL signal generated!")
                print(f"    The price has crossed under the {right_op}")
            else:
                distance_to_level = current_price - right_value
                distance_pips = distance_to_level / symbol_info.point if symbol_info.point > 0 else 0
                
                if current_price > right_value:
                    print(f"\n    Status: [WAITING] Price is above {right_op}")
                    print(f"    Required: Price must drop to {right_value:.5f} and cross under")
                    print(f"    Distance: {abs(distance_pips):.1f} pips above {right_op}")
                    print(f"    Action: Wait for price to drop below {right_value:.5f}")
                elif current_price < right_value:
                    print(f"\n    Status: [PARTIAL] Price is below {right_op}, but cross not confirmed")
                    print(f"    Required: prev_close ({prev_close:.5f}) > {right_op} ({right_value:.5f}) >= current ({left_value:.5f})")
                    if prev_close <= right_value:
                        print(f"    [BLOCKER] Previous close was not above {right_op}")
                        print(f"    Action: Need price to rise above {right_op} first, then drop below")
        elif operator == '<':
            # Simple less than
            is_below = left_value < right_value
            print(f"\n    Simple Comparison:")
            print(f"      {left_value:.5f} < {right_value:.5f} = {is_below}")
            if is_below:
                print(f"\n    [TRIGGERED] ✅ SELL signal generated!")
            else:
                distance = right_value - left_value
                print(f"\n    Status: [WAITING] Price is above {right_op}")
                print(f"    Required: Price must drop below {right_value:.5f}")
                print(f"    Distance: {distance / symbol_info.point:.1f} pips above")
        else:
            print(f"    [WARNING] Unknown operator: {operator}")
    
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    
    # Check if strategy would generate signal
    market_data = {
        'symbol': symbol,
        'timeframe': timeframe,
        'current_price': current_price,
        'ohlc': ohlc
    }
    
    signal = strategy.generate_signal(market_data)
    
    if signal == "SELL":
        print("[PRIMARY REASON] SELL entry conditions are MET!")
        print(f"  - {strategy_data.get('name')} should generate a SELL signal NOW")
    else:
        print("[PRIMARY REASON] SELL entry conditions not met")
        print(f"  - {strategy_data.get('name')} is waiting for SELL conditions to be satisfied")
        if not strategy.active_pivot_low_price:
            print("  - No pivot low available yet (need more price action)")
    
    mt5.shutdown()

if __name__ == "__main__":
    check_sell_strategy_entry()
