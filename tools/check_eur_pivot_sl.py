"""
Check EUR_PIVOT Stop Loss Configuration
Analyze the stop loss settings and calculate actual SL value
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
from src.config import Config


def check_eur_pivot_sl():
    """Check EUR_PIVOT stop loss configuration"""
    print("=" * 70)
    print("  EUR_PIVOT Stop Loss Analysis")
    print("=" * 70)
    print()
    
    # Load strategy
    strategy_file = project_root / "strategies" / "EUR_PIVOT.json"
    if not strategy_file.exists():
        print(f"[ERROR] Strategy file not found: {strategy_file}")
        return
    
    with open(strategy_file, 'r') as f:
        strategy_data = json.load(f)
    
    print(f"Strategy: {strategy_data['name']}")
    print(f"Symbol: {strategy_data['symbol']}")
    print(f"Trade Direction: {strategy_data.get('trade_direction', 'both')}")
    print()
    
    # Stop Loss Configuration
    print("=" * 70)
    print("  STOP LOSS CONFIGURATION")
    print("=" * 70)
    print()
    
    sl_enabled = strategy_data.get('sl_enabled', False)
    sl_type = strategy_data.get('sl_type', 'None')
    sl_value = strategy_data.get('sl_value', 0.0)
    use_ratio = strategy_data.get('use_ratio', False)
    
    print(f"Stop Loss Enabled: {sl_enabled}")
    print(f"Stop Loss Type: {sl_type}")
    print(f"Stop Loss Value: {sl_value}")
    print(f"Use Ratio: {use_ratio}")
    print()
    
    if not sl_enabled:
        print("[WARNING] Stop Loss is DISABLED")
        print("No stop loss will be set for trades from this strategy")
        return
    
    # Initialize MT5 to get symbol info
    config = Config()
    mt5_config = config.get('mt5', {})
    
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
    point = symbol_info.point
    digits = symbol_info.digits
    
    print(f"Symbol Information:")
    print(f"  Current Price: {current_price:.{digits}f}")
    print(f"  Point: {point}")
    print(f"  Digits: {digits}")
    print()
    
    # Calculate stop loss based on configuration
    print("=" * 70)
    print("  STOP LOSS CALCULATION")
    print("=" * 70)
    print()
    
    trade_direction = strategy_data.get('trade_direction', 'both')
    
    if sl_value == 0.0:
        print("[WARNING] Stop Loss Value is 0.0")
        print()
        print("This means:")
        if sl_type == "Price (Points)":
            print("  - No fixed stop loss in points will be set")
            print("  - The system may use default risk manager calculation")
            print("  - Or no stop loss will be applied")
        else:
            print("  - No stop loss will be calculated based on this value")
        print()
        print("Recommendation: Set a proper sl_value for risk management")
    else:
        # Calculate actual SL price
        if sl_type == "Price (Points)":
            # sl_value is in points
            sl_points = sl_value
            sl_price_diff = sl_points * point
            
            if trade_direction in ('long', 'both'):
                # BUY: SL below entry
                sl_price_buy = current_price - sl_price_diff
                print(f"BUY Trade Stop Loss:")
                print(f"  Entry Price (example): {current_price:.{digits}f}")
                print(f"  SL Value: {sl_value} points")
                print(f"  SL Distance: {sl_price_diff:.{digits}f}")
                print(f"  SL Price: {sl_price_buy:.{digits}f}")
                print(f"  Risk: {sl_price_diff:.{digits}f} ({sl_points} points)")
                print()
            
            if trade_direction in ('short', 'both'):
                # SELL: SL above entry
                sl_price_sell = current_price + sl_price_diff
                print(f"SELL Trade Stop Loss:")
                print(f"  Entry Price (example): {current_price:.{digits}f}")
                print(f"  SL Value: {sl_value} points")
                print(f"  SL Distance: {sl_price_diff:.{digits}f}")
                print(f"  SL Price: {sl_price_sell:.{digits}f}")
                print(f"  Risk: {sl_price_diff:.{digits}f} ({sl_points} points)")
                print()
        
        elif sl_type == "Price (Percentage)":
            # sl_value is percentage
            sl_percentage = sl_value / 100.0
            
            if trade_direction in ('long', 'both'):
                sl_price_buy = current_price * (1 - sl_percentage)
                print(f"BUY Trade Stop Loss:")
                print(f"  Entry Price (example): {current_price:.{digits}f}")
                print(f"  SL Value: {sl_value}%")
                print(f"  SL Price: {sl_price_buy:.{digits}f}")
                print()
            
            if trade_direction in ('short', 'both'):
                sl_price_sell = current_price * (1 + sl_percentage)
                print(f"SELL Trade Stop Loss:")
                print(f"  Entry Price (example): {current_price:.{digits}f}")
                print(f"  SL Value: {sl_value}%")
                print(f"  SL Price: {sl_price_sell:.{digits}f}")
                print()
        
        elif sl_type == "Price (Absolute)":
            # sl_value is absolute price
            sl_price = sl_value
            
            print(f"Stop Loss Price (Absolute):")
            print(f"  SL Price: {sl_price:.{digits}f}")
            if trade_direction in ('long', 'both'):
                sl_distance = current_price - sl_price
                print(f"  For BUY: Distance = {sl_distance:.{digits}f} ({sl_distance/point:.1f} points)")
            if trade_direction in ('short', 'both'):
                sl_distance = sl_price - current_price
                print(f"  For SELL: Distance = {sl_distance:.{digits}f} ({sl_distance/point:.1f} points)")
            print()
    
    # Additional settings
    print("=" * 70)
    print("  ADDITIONAL RISK MANAGEMENT")
    print("=" * 70)
    print()
    
    enable_trailing_sl = strategy_data.get('enable_trailing_sl', False)
    trailing_sl_gap = strategy_data.get('trailing_sl_gap', 0.0)
    
    print(f"Trailing Stop Loss: {'ENABLED' if enable_trailing_sl else 'DISABLED'}")
    if enable_trailing_sl:
        print(f"  Trailing SL Gap: {trailing_sl_gap} points")
        print(f"  This will move SL by {trailing_sl_gap} points as price moves favorably")
    
    enable_profit_lock = strategy_data.get('enable_profit_lock', False)
    profit_lock_trigger = strategy_data.get('profit_lock_trigger', 0.0)
    profit_lock_value = strategy_data.get('profit_lock_value', 0.0)
    
    print()
    print(f"Profit Lock: {'ENABLED' if enable_profit_lock else 'DISABLED'}")
    if enable_profit_lock:
        print(f"  Trigger: {profit_lock_trigger} points profit")
        print(f"  Lock Value: {profit_lock_value} points")
    
    print()
    print("=" * 70)
    print()
    
    # Summary
    print("SUMMARY:")
    print("-" * 70)
    if sl_enabled:
        if sl_value == 0.0:
            print("[WARNING] Stop Loss is enabled but value is 0.0")
            print("  - No stop loss will be set based on configuration")
            print("  - System may use default risk manager or no SL")
        else:
            print(f"[OK] Stop Loss is configured: {sl_value} ({sl_type})")
    else:
        print("[WARNING] Stop Loss is DISABLED")
        print("  - No stop loss will be set for trades")
    
    print()
    
    mt5.shutdown()
    print("[OK] MT5 connection closed")


if __name__ == "__main__":
    try:
        check_eur_pivot_sl()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Cancelled by user")
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        if mt5.initialize():
            mt5.shutdown()
