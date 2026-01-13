"""
Check BUY_SMC Strategy Status
Diagnoses why the strategy is not taking trades
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from src.mt5_connector import MT5Connector
from src.strategy.strategy_persistence import StrategyPersistence
from src.config import Config
import MetaTrader5 as mt5

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_buy_smc():
    """Check BUY_SMC strategy status"""
    print(f"\n{'='*80}")
    print("BUY_SMC Strategy Diagnostic")
    print(f"{'='*80}\n")
    
    # Initialize MT5
    mt5_conn = MT5Connector()
    config = Config()
    mt5_path = config.get('mt5.path', '')
    mt5_login = config.get('mt5.login', 0)
    mt5_password = config.get('mt5.password', '')
    mt5_server = config.get('mt5.server', '')
    
    if not mt5_conn.initialize(mt5_path, mt5_login, mt5_password, mt5_server):
        print("[ERROR] MT5 not connected")
        return
    
    if not mt5_conn.is_connected():
        print("[ERROR] MT5 initialization failed")
        return
    
    print("[OK] MT5 connected\n")
    
    # Load strategy
    persistence = StrategyPersistence()
    strategy = persistence.load_strategy("strategies/BUY_SMC.json")
    
    if not strategy:
        print("[ERROR] Could not load BUY_SMC strategy")
        mt5_conn.shutdown()
        return
    
    strategy.set_mt5_connector(mt5_conn)
    
    print(f"Strategy: {strategy.name}")
    print(f"Symbol: {strategy.symbol}")
    print(f"Timeframe: M{strategy.timeframe}")
    print(f"Enabled: {strategy.enabled}")
    print(f"Emit On: {strategy.emit_on}")
    print(f"Pivot Left/Right: {strategy.pivot_left}/{strategy.pivot_right}")
    print(f"Trade Direction: {strategy.trade_direction}")
    print()
    
    # Get current market data
    tick = mt5_conn.get_tick(strategy.symbol)
    if not tick:
        print(f"[ERROR] Could not get tick data for {strategy.symbol}")
        mt5_conn.shutdown()
        return
    
    current_price = (tick.get('bid', 0) + tick.get('ask', 0)) / 2.0
    if current_price == 0:
        current_price = tick.get('bid', tick.get('ask', 0))
    
    print(f"Current Price (LTP): {current_price:.2f}")
    print(f"Bid: {tick.get('bid', 0):.2f}, Ask: {tick.get('ask', 0):.2f}")
    print()
    
    # Get candles
    rates = mt5_conn.get_rates(strategy.symbol, strategy.timeframe if hasattr(strategy, 'timeframe') else mt5.TIMEFRAME_M15, 300)
    if not rates:
        print(f"[ERROR] Could not get rates for {strategy.symbol}")
        mt5_conn.shutdown()
        return
    
    print(f"Loaded {len(rates)} candles")
    print(f"Last candle: O={rates[-1]['open']:.2f}, H={rates[-1]['high']:.2f}, L={rates[-1]['low']:.2f}, C={rates[-1]['close']:.2f}")
    print()
    
    # Create market data
    market_data = {
        'tick': tick,
        'current_price': current_price,
        'rates': rates
    }
    
    # Generate signal to update state
    signal = strategy.generate_signal(market_data)
    
    print(f"{'='*80}")
    print("SMC State:")
    print(f"{'='*80}")
    print(f"Active Pivot High: {strategy.active_pivot_high_price}")
    print(f"Active Pivot Low: {strategy.active_pivot_low_price}")
    print(f"Active CHoCH Price: {strategy.active_choch_price}")
    print(f"Active BOS Price: {strategy.active_bos_price}")
    print(f"Bias: {strategy.bias}")
    print(f"Total Pivot Highs: {len(strategy.all_pivot_highs)}")
    print(f"Total Pivot Lows: {len(strategy.all_pivot_lows)}")
    print(f"Total Events: {len(strategy.all_events)}")
    print()
    
    # Check buy filters
    print(f"{'='*80}")
    print("Buy Filters:")
    print(f"{'='*80}")
    if strategy.buy_filters:
        for i, filt in enumerate(strategy.buy_filters, 1):
            enabled = filt.get('enabled', True)
            left = filt.get('left_operand', filt.get('left_field', 'N/A'))
            op = filt.get('operator', 'N/A')
            right = filt.get('right_operand', filt.get('right_field', 'N/A'))
            print(f"{i}. [{'ENABLED' if enabled else 'DISABLED'}] {left} {op} {right}")
            
            if enabled:
                # Resolve operands
                from src.strategy.smc_utils import extract_ohlc_arrays
                opens, highs, lows, closes = extract_ohlc_arrays(rates)
                ohlc = {
                    'open': opens[-1] if opens else 0,
                    'high': highs[-1] if highs else 0,
                    'low': lows[-1] if lows else 0,
                    'close': closes[-1] if closes else 0
                }
                
                left_val = strategy._resolve_operand(left, current_price, ohlc, market_data)
                right_val = strategy._resolve_operand(right, current_price, ohlc, market_data)
                
                print(f"   Left ({left}): {left_val}")
                print(f"   Right ({right}): {right_val}")
                
                if left_val is None or right_val is None:
                    print(f"   [ISSUE] Cannot resolve operands - left={left_val}, right={right_val}")
                else:
                    # Check condition
                    prev_price = getattr(strategy, '_prev_filter_price', current_price)
                    if op == 'crosses_above':
                        result = prev_price < right_val <= left_val
                        print(f"   Previous price: {prev_price:.2f}")
                        print(f"   Cross check: prev < right <= left")
                        print(f"   Check 1: {prev_price:.2f} < {right_val:.2f} = {prev_price < right_val}")
                        print(f"   Check 2: {right_val:.2f} <= {left_val:.2f} = {right_val <= left_val}")
                        print(f"   Result: {result}")
                        
                        if not result:
                            if prev_price >= right_val:
                                print(f"   [REASON] Previous price ({prev_price:.2f}) is not below pivot ({right_val:.2f})")
                            elif right_val > left_val:
                                print(f"   [REASON] Current price ({left_val:.2f}) is below pivot ({right_val:.2f}) - waiting for price to rise")
                                distance = right_val - left_val
                                print(f"   [INFO] Price needs to rise {distance:.2f} points to cross above pivot")
    else:
        print("No buy filters configured")
    print()
    
    # Check sell filters
    print(f"{'='*80}")
    print("Sell Filters:")
    print(f"{'='*80}")
    if strategy.sell_filters:
        for i, filt in enumerate(strategy.sell_filters, 1):
            enabled = filt.get('enabled', True)
            left = filt.get('left_operand', filt.get('left_field', 'N/A'))
            op = filt.get('operator', 'N/A')
            right = filt.get('right_operand', filt.get('right_field', 'N/A'))
            print(f"{i}. [{'ENABLED' if enabled else 'DISABLED'}] {left} {op} {right}")
            
            # Check if condition is invalid
            if left == right and op in ('>', '<', '>=', '<='):
                print(f"   [WARNING] Invalid condition: {left} {op} {right} (always False)")
    else:
        print("No sell filters configured")
    print()
    
    print(f"{'='*80}")
    print("Signal Status:")
    print(f"{'='*80}")
    print(f"Generated Signal: {signal}")
    print()
    
    if signal is None:
        print("Reason: Buy filter conditions not met")
        if strategy.buy_filters:
            print("The strategy is waiting for:")
            print(f"  - Price to cross above pivot high ({strategy.active_pivot_high_price})")
            print(f"  - Current price: {current_price:.2f}")
            if strategy.active_pivot_high_price:
                distance = strategy.active_pivot_high_price - current_price
                print(f"  - Distance to pivot: {distance:.2f} points")
    
    print(f"{'='*80}\n")
    
    mt5_conn.shutdown()


if __name__ == "__main__":
    check_buy_smc()
