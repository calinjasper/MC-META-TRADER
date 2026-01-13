"""
Analyze Why EUR_PIV Didn't Enter Trade
Check all possible reasons why the strategy didn't trigger
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


def analyze_eur_piv_no_entry():
    """Analyze why EUR_PIV didn't enter a trade"""
    print("=" * 70)
    print("  EUR_PIV Trade Entry Analysis")
    print("=" * 70)
    print()
    
    # Load strategy
    strategy_file = project_root / "strategies" / "EUR_PIV.json"
    if not strategy_file.exists():
        print(f"[ERROR] Strategy file not found: {strategy_file}")
        return
    
    with open(strategy_file, 'r') as f:
        strategy_data = json.load(f)
    
    print(f"Strategy: {strategy_data['name']}")
    print(f"Symbol: {strategy_data['symbol']}")
    print(f"Enabled: {strategy_data.get('enabled', False)}")
    print(f"Timeframe: {strategy_data['timeframe']} minutes")
    print(f"Trade Direction: {strategy_data.get('trade_direction', 'both')}")
    print()
    
    # Check if strategy is enabled
    if not strategy_data.get('enabled', False):
        print("=" * 70)
        print("  REASON: Strategy is DISABLED")
        print("=" * 70)
        print("The strategy is not enabled, so it won't enter trades.")
        print("Enable it in the strategy settings to allow trade entries.")
        return
    
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
    
    print(f"Current Market Price:")
    print(f"  Bid: {current_bid:.5f}")
    print(f"  Ask: {current_ask:.5f}")
    print(f"  Mid: {current_price:.5f}")
    print()
    
    # Get rates
    print(f"Fetching {timeframe}-minute candles...")
    rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, 500)
    
    if rates is None or len(rates) == 0:
        print(f"[ERROR] Could not get rates for {symbol}")
        mt5.shutdown()
        return
    
    print(f"[OK] Got {len(rates)} bars")
    print()
    
    # Extract OHLC arrays
    import numpy as np
    if isinstance(rates, np.ndarray):
        highs = [float(r['high']) for r in rates]
        lows = [float(r['low']) for r in rates]
        closes = [float(r['close']) for r in rates]
        opens = [float(r['open']) for r in rates]
    else:
        opens, highs, lows, closes = extract_ohlc_arrays(rates)
    
    # Calculate pivots
    pivot_left = strategy_data.get('pivot_left', 2)
    pivot_right = strategy_data.get('pivot_right', 2)
    
    print("Calculating SMC pivots...")
    pivot_highs = []
    pivot_lows = []
    
    start = pivot_left
    end = len(highs) - pivot_right
    
    for i in range(start, end):
        if fractal_pivot_high(highs, i, pivot_left, pivot_right):
            pivot_highs.append({'index': i, 'price': highs[i]})
        if fractal_pivot_low(lows, i, pivot_left, pivot_right):
            pivot_lows.append({'index': i, 'price': lows[i]})
    
    # Find active pivot low (most recent)
    active_pivot_low = None
    if pivot_lows:
        most_recent_pivot_low = pivot_lows[-1]  # Last one is most recent
        active_pivot_low = most_recent_pivot_low['price']
    
    print(f"[OK] Found {len(pivot_highs)} pivot highs, {len(pivot_lows)} pivot lows")
    if active_pivot_low:
        print(f"Active Pivot Low: {active_pivot_low:.5f}")
    else:
        print("Active Pivot Low: None (not enough data)")
    print()
    
    # Analyze entry conditions
    print("=" * 70)
    print("  ENTRY CONDITION ANALYSIS")
    print("=" * 70)
    print()
    
    trade_direction = strategy_data.get('trade_direction', 'both')
    sell_filters = strategy_data.get('sell_filters', [])
    
    # Check SELL conditions (since trade_direction is "short")
    if trade_direction in ('short', 'both') and sell_filters:
        print("SELL Entry Condition:")
        print("-" * 70)
        
        for i, filter_cond in enumerate(sell_filters, 1):
            if not filter_cond.get('enabled', True):
                print(f"  Condition {i}: DISABLED - This condition is turned off")
                continue
            
            left_op = filter_cond.get('left_operand', filter_cond.get('left_field', ''))
            operator = filter_cond.get('operator', '')
            right_op = filter_cond.get('right_operand', filter_cond.get('right_field', ''))
            
            print(f"  Condition {i}: {left_op} {operator} {right_op}")
            
            # Evaluate condition
            if operator == 'crosses_under' and right_op == 'smc_pivot_low':
                if active_pivot_low is None:
                    print(f"    [BLOCKER] No pivot low available yet")
                    print(f"    Reason: Need more bars to confirm pivot low")
                    print(f"    Action: Wait for more {timeframe}-minute candles")
                else:
                    # Check if price has crossed under pivot low
                    prev_close = closes[-2] if len(closes) >= 2 else current_price
                    current_close = closes[-1] if closes else current_price
                    
                    # Cross under: prev_price > pivot_low >= current_price
                    has_crossed = prev_close > active_pivot_low >= current_close
                    
                    distance_to_pivot = current_price - active_pivot_low
                    distance_pips = distance_to_pivot / symbol_info.point if symbol_info.point > 0 else 0
                    
                    print(f"    Active Pivot Low: {active_pivot_low:.5f}")
                    print(f"    Previous Close: {prev_close:.5f}")
                    print(f"    Current Close: {current_close:.5f}")
                    print(f"    Current Price: {current_price:.5f}")
                    print(f"    Distance to Pivot: {distance_to_pivot:.5f} ({distance_pips:.1f} points)")
                    print()
                    
                    if has_crossed:
                        print(f"    [CONDITION MET] Price has crossed under pivot low!")
                        print(f"    This should trigger a SELL entry")
                        print()
                        print("    [CHECKING OTHER FACTORS...]")
                    elif current_price < active_pivot_low:
                        print(f"    [PARTIAL] Price is below pivot low, but cross not confirmed")
                        print(f"    Required: prev_close ({prev_close:.5f}) > pivot ({active_pivot_low:.5f}) >= current_close ({current_close:.5f})")
                        print(f"    Status: prev_close > pivot = {prev_close > active_pivot_low}")
                        print(f"    Status: pivot >= current_close = {active_pivot_low >= current_close}")
                        if prev_close <= active_pivot_low:
                            print(f"    [BLOCKER] Previous close was not above pivot low")
                        if active_pivot_low < current_close:
                            print(f"    [BLOCKER] Current close is above pivot low (needs to be at or below)")
                    else:
                        print(f"    [BLOCKER] Price is above pivot low")
                        print(f"    Required: Price must drop to {active_pivot_low:.5f} and cross under")
                        print(f"    Required Drop: {abs(distance_pips):.1f} points")
        
        print()
    
    # Check for other potential blockers
    print("=" * 70)
    print("  POTENTIAL BLOCKERS")
    print("=" * 70)
    print()
    
    # Check trading hours
    time_rules = strategy_data.get('time_rules', [])
    if time_rules:
        print("Trading Hours:")
        current_time = datetime.now().time()
        print(f"  Current Time: {current_time.strftime('%H:%M:%S')}")
        for rule in time_rules:
            start = rule.get('start', '00:00')
            end = rule.get('end', '23:59')
            print(f"  Allowed: {start} - {end}")
        print("  [NOTE] Check if current time is within allowed trading hours")
    else:
        print("Trading Hours: No restrictions (trading allowed 24/7)")
    
    print()
    
    # Check if there are existing positions
    print("Position Limits:")
    print("  [NOTE] Check if max_positions limit is reached")
    print("  [NOTE] Check if there's already an open position for this symbol/strategy")
    
    print()
    
    # Check symbol tradeability
    print("Symbol Tradeability:")
    print(f"  Trade Mode: {symbol_info.trade_mode}")
    if symbol_info.trade_mode == 0:
        print("  [BLOCKER] Symbol trading is DISABLED")
    elif symbol_info.trade_mode == 4:
        print("  [OK] Full trading allowed")
    else:
        print(f"  [WARNING] Limited trading mode: {symbol_info.trade_mode}")
    
    print()
    
    # Summary
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print()
    
    if active_pivot_low is None:
        print("[PRIMARY REASON] No pivot low available")
        print("  - Need more bars to confirm a pivot low")
        print("  - Strategy requires at least {} bars".format(pivot_left + pivot_right + 3))
    elif trade_direction == 'short' and sell_filters:
        prev_close = closes[-2] if len(closes) >= 2 else current_price
        current_close = closes[-1] if closes else current_price
        
        if active_pivot_low:
            has_crossed = prev_close > active_pivot_low >= current_close
            
            if has_crossed:
                print("[CONDITION MET] Entry condition is satisfied")
                print("  - Price has crossed under pivot low")
                print("  - Check other factors:")
                print("    * Trading hours restrictions")
                print("    * Position limits")
                print("    * Strategy execution status")
                print("    * System logs for errors")
            elif current_price < active_pivot_low:
                print("[PARTIAL] Price is below pivot, but cross not confirmed")
                print(f"  - Need: prev_close ({prev_close:.5f}) > pivot ({active_pivot_low:.5f}) >= current_close ({current_close:.5f})")
            else:
                print("[PRIMARY REASON] Price hasn't reached pivot low yet")
                distance = (current_price - active_pivot_low) / symbol_info.point if symbol_info.point > 0 else 0
                print(f"  - Need price to drop {abs(distance):.1f} points to {active_pivot_low:.5f}")
                print(f"  - Then price must cross under (prev > pivot >= current)")
    
    print()
    
    mt5.shutdown()
    print("[OK] MT5 connection closed")


if __name__ == "__main__":
    try:
        analyze_eur_piv_no_entry()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Cancelled by user")
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        if mt5.initialize():
            mt5.shutdown()
