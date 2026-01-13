"""
Check XA_BUY Strategy Entry Conditions
Analyze when the XA_BUY strategy will enter trades
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
from src.strategy.strategy_persistence import StrategyPersistence
from src.strategy.smc_utils import extract_ohlc_arrays


def check_xa_buy_entry():
    """Check when XA_BUY strategy will enter trades"""
    print("=" * 70)
    print("  XA_BUY Strategy Entry Analysis")
    print("=" * 70)
    print()
    
    # Load strategy
    strategy_file = project_root / "strategies" / "XA_BUY.json"
    if not strategy_file.exists():
        print(f"[ERROR] Strategy file not found: {strategy_file}")
        return
    
    with open(strategy_file, 'r') as f:
        strategy_data = json.load(f)
    
    print(f"Strategy: {strategy_data['name']}")
    print(f"Symbol: {strategy_data['symbol']}")
    print(f"Timeframe: {strategy_data.get('timeframe', 'N/A')} minutes")
    print(f"Trade Direction: {strategy_data.get('trade_direction', 'both')}")
    print(f"Strategy Type: {strategy_data.get('strategy_type', 'N/A')}")
    
    if strategy_data.get('strategy_type') == 'smc':
        print(f"Emit On: {strategy_data.get('emit_on', 'NONE')}")
        print(f"Pivot Settings: Left={strategy_data.get('pivot_left', 2)}, Right={strategy_data.get('pivot_right', 2)}")
    print()
    
    # Display entry conditions
    buy_filters = strategy_data.get('buy_filters', [])
    sell_filters = strategy_data.get('sell_filters', [])
    
    if buy_filters:
        print("Entry Conditions (Buy Filters):")
        for i, filt in enumerate(buy_filters, 1):
            if filt.get('enabled', True):
                left = filt.get('left_operand', '')
                op = filt.get('operator', '')
                right = filt.get('right_operand', '')
                connector = filt.get('connector', 'AND')
                print(f"  {i}. {left} {op} {right} ({connector})")
        print()
    
    if sell_filters:
        print("Sell Filters (if any):")
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
    timeframe = strategy_data.get('timeframe', 15)
    
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
    
    # Get previous close (for cross detection)
    prev_close = float(closes[-2]) if len(closes) >= 2 else current_price
    
    print(f"Price Data:")
    print(f"  Current Close: {closes[-1]:.5f}")
    print(f"  Previous Close: {prev_close:.5f}")
    print(f"  Current Price (Live): {current_price:.5f}")
    print()
    
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
    
    # Get SMC pivots and prices
    smc_pivots = market_data.get('smc_pivots', {})
    if not smc_pivots:
        if hasattr(strategy, 'active_choch_price'):
            choch_price = strategy.active_choch_price
        else:
            choch_price = None
        if hasattr(strategy, 'active_pivot_high_price'):
            pivot_high = strategy.active_pivot_high_price
        else:
            pivot_high = None
        if hasattr(strategy, 'active_pivot_low_price'):
            pivot_low = strategy.active_pivot_low_price
        else:
            pivot_low = None
    else:
        choch_price = smc_pivots.get('choch_price')
        pivot_high = smc_pivots.get('pivot_high')
        pivot_low = smc_pivots.get('pivot_low')
    
    print("SMC Data:")
    if pivot_high:
        print(f"  Pivot High: {pivot_high:.5f}")
    else:
        print(f"  Pivot High: None")
    
    if pivot_low:
        print(f"  Pivot Low: {pivot_low:.5f}")
    else:
        print(f"  Pivot Low: None")
    
    if choch_price:
        print(f"  CHoCH Price: {choch_price:.5f}")
    else:
        print(f"  CHoCH Price: None")
    print()
    
    # Evaluate entry conditions
    if not buy_filters:
        print("[WARNING] No buy filters configured")
        mt5.shutdown()
        return
    
    print("Entry Condition Evaluation:")
    print("-" * 70)
    
    all_conditions_met = True
    condition_results = []
    
    for i, filt in enumerate(buy_filters, 1):
        if not filt.get('enabled', True):
            print(f"Filter {i}: DISABLED")
            condition_results.append(None)
            continue
        
        left_op = filt.get('left_operand', '')
        operator = filt.get('operator', '')
        right_op = filt.get('right_operand', '')
        connector = filt.get('connector', 'AND')
        
        print(f"\nFilter {i}: {left_op} {operator} {right_op} ({connector})")
        
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
        elif right_op == 'current_price':
            right_value = current_price
        else:
            right_value = None
            print(f"    [WARNING] Unknown right operand: {right_op}")
        
        if left_value is None or right_value is None:
            if right_value is None:
                print(f"    Status: [BLOCKER] {right_op} is not available")
                if right_op == 'smc_choch_price':
                    print(f"    Reason: No CHoCH event has been detected yet")
                elif right_op in ['smc_pivot_high', 'smc_pivot_low']:
                    print(f"    Reason: Not enough data to calculate pivots")
            else:
                print(f"    Status: [BLOCKER] Cannot evaluate condition")
            condition_results.append(False)
            all_conditions_met = False
            continue
        
        print(f"    Current Price: {left_value:.5f}")
        print(f"    {right_op}: {right_value:.5f}")
        print(f"    Previous Close: {prev_close:.5f}")
        
        # Evaluate condition
        condition_met = False
        
        if operator == 'crosses_above':
            # Crosses above: prev_price < right <= left
            condition_met = prev_close < right_value <= left_value
            print(f"\n    Cross Logic Check:")
            print(f"      Required: prev_close ({prev_close:.5f}) < {right_op} ({right_value:.5f}) <= current ({left_value:.5f})")
            print(f"      Check 1: prev_close < {right_op} = {prev_close:.5f} < {right_value:.5f} = {prev_close < right_value}")
            print(f"      Check 2: {right_op} <= current = {right_value:.5f} <= {left_value:.5f} = {right_value <= left_value}")
            
        elif operator == 'crosses_under':
            # Crosses under: prev_price > right >= left
            condition_met = prev_close > right_value >= left_value
            print(f"\n    Cross Logic Check:")
            print(f"      Required: prev_close ({prev_close:.5f}) > {right_op} ({right_value:.5f}) >= current ({left_value:.5f})")
            print(f"      Check 1: prev_close > {right_op} = {prev_close:.5f} > {right_value:.5f} = {prev_close > right_value}")
            print(f"      Check 2: {right_op} >= current = {right_value:.5f} >= {left_value:.5f} = {right_value >= left_value}")
            
        elif operator == '>':
            condition_met = left_value > right_value
            print(f"\n    Comparison: {left_value:.5f} > {right_value:.5f} = {condition_met}")
            
        elif operator == '<':
            condition_met = left_value < right_value
            print(f"\n    Comparison: {left_value:.5f} < {right_value:.5f} = {condition_met}")
            
        elif operator == '>=':
            condition_met = left_value >= right_value
            print(f"\n    Comparison: {left_value:.5f} >= {right_value:.5f} = {condition_met}")
            
        elif operator == '<=':
            condition_met = left_value <= right_value
            print(f"\n    Comparison: {left_value:.5f} <= {right_value:.5f} = {condition_met}")
            
        else:
            print(f"    [WARNING] Unknown operator: {operator}")
            condition_met = False
        
        condition_results.append(condition_met)
        
        if condition_met:
            print(f"    [CONDITION MET] OK")
        else:
            print(f"    [CONDITION NOT MET] FAILED")
            all_conditions_met = False
            
            # Provide guidance on what's needed
            if operator == 'crosses_above':
                if current_price < right_value:
                    distance = (right_value - current_price) / symbol_info.point if symbol_info.point > 0 else 0
                    print(f"    Action: Price needs to rise {distance:.1f} pips to {right_value:.5f} and cross above")
                elif prev_close >= right_value:
                    print(f"    Action: Price needs to drop below {right_value:.5f} first, then cross back above")
            elif operator == 'crosses_under':
                if current_price > right_value:
                    distance = (current_price - right_value) / symbol_info.point if symbol_info.point > 0 else 0
                    print(f"    Action: Price needs to drop {distance:.1f} pips to {right_value:.5f} and cross under")
                elif prev_close <= right_value:
                    print(f"    Action: Price needs to rise above {right_value:.5f} first, then drop below")
    
    print()
    print("=" * 70)
    print("Summary:")
    print("=" * 70)
    
    # Evaluate overall condition based on connectors
    if len(condition_results) > 1:
        # Check connectors
        overall_result = condition_results[0]
        for i in range(1, len(condition_results)):
            if condition_results[i] is None:  # Disabled condition
                continue
            connector = buy_filters[i].get('connector', 'AND')
            if connector == 'AND':
                overall_result = overall_result and condition_results[i]
            else:  # OR
                overall_result = overall_result or condition_results[i]
        
        if overall_result:
            print("[PRIMARY REASON] All entry conditions are MET!")
            print("  - BUY signal should be generated")
        else:
            print("[PRIMARY REASON] Entry conditions not met")
            print("  - Waiting for conditions to be satisfied")
    else:
        if condition_results[0]:
            print("[PRIMARY REASON] Entry condition is MET!")
            print("  - BUY signal should be generated")
        else:
            print("[PRIMARY REASON] Entry condition not met")
            print("  - Waiting for condition to be satisfied")
    
    mt5.shutdown()
    print()


if __name__ == "__main__":
    check_xa_buy_entry()
