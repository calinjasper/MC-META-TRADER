"""
Check symbol trade_stops_level and provide SL/TP recommendations
"""
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import MetaTrader5 as mt5
except ImportError:
    print("Error: MetaTrader5 module not found. Install with: pip install MetaTrader5")
    sys.exit(1)

def load_config():
    """Load MT5 configuration"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config.get('mt5', {})
    except Exception as e:
        print(f"Warning: Could not load config: {e}")
        return {}

def check_symbol_stops_level(symbol: str):
    """Check trade_stops_level for a symbol and provide recommendations"""
    # Initialize MT5
    config = load_config()
    
    if not mt5.initialize(path=config.get('path', ''), 
                         login=config.get('login', 0),
                         password=config.get('password', ''),
                         server=config.get('server', '')):
        error = mt5.last_error()
        print(f"MT5 initialization failed: {error}")
        return
    
    print(f"\n{'='*60}")
    print(f"Checking Symbol: {symbol}")
    print(f"{'='*60}\n")
    
    # Try to find the symbol (case-insensitive)
    symbol_info = mt5.symbol_info(symbol)
    
    if symbol_info is None:
        # Try case variations
        all_symbols = mt5.symbols_get()
        found_symbol = None
        symbol_upper = symbol.upper()
        
        if all_symbols:
            for s in all_symbols:
                if s.name.upper() == symbol_upper:
                    found_symbol = s.name
                    symbol_info = mt5.symbol_info(found_symbol)
                    print(f"Found symbol variant: {found_symbol}")
                    break
        
        if symbol_info is None:
            print(f"❌ Symbol '{symbol}' not found in MT5")
            print("\nAvailable symbols (first 20):")
            if all_symbols:
                for s in all_symbols[:20]:
                    print(f"  - {s.name}")
            mt5.shutdown()
            return
    
    # Display symbol information
    print(f"Symbol Name: {symbol_info.name}")
    print(f"Digits: {symbol_info.digits}")
    print(f"Point: {symbol_info.point}")
    print(f"Trade Mode: {symbol_info.trade_mode} ({'Tradeable' if symbol_info.trade_mode > 0 else 'Not Tradeable'})")
    print(f"\n{'─'*60}")
    print(f"STOP LOSS / TAKE PROFIT REQUIREMENTS")
    print(f"{'─'*60}")
    print(f"Trade Stops Level: {symbol_info.trade_stops_level} points")
    
    if symbol_info.trade_stops_level > 0:
        min_distance = symbol_info.trade_stops_level * symbol_info.point
        print(f"Minimum Distance: {min_distance:.5f} ({symbol_info.trade_stops_level} points)")
        
        # Calculate recommended values
        recommended_sl = max(50, symbol_info.trade_stops_level + 10)
        recommended_tp = recommended_sl * 2  # 1:2 ratio
        
        print(f"\n{'─'*60}")
        print(f"RECOMMENDATIONS")
        print(f"{'─'*60}")
        print(f"✅ Recommended SL Value: {recommended_sl} points")
        print(f"✅ Recommended TP Value: {recommended_tp} points (1:2 ratio)")
        print(f"   OR use manual TP: {recommended_tp} points")
        
        # Check current strategy settings
        strategy_path = os.path.join(os.path.dirname(__file__), '..', 'strategies', 'emi.json')
        if os.path.exists(strategy_path):
            try:
                with open(strategy_path, 'r') as f:
                    strategy = json.load(f)
                
                if strategy.get('symbol') == symbol or strategy.get('symbol', '').upper() == symbol.upper():
                    current_sl = strategy.get('sl_value', 0)
                    current_tp = strategy.get('tp_value', 0)
                    
                    print(f"\n{'─'*60}")
                    print(f"CURRENT STRATEGY SETTINGS ('emi')")
                    print(f"{'─'*60}")
                    print(f"Current SL Value: {current_sl} points")
                    print(f"Current TP Value: {current_tp} points")
                    
                    if current_sl < symbol_info.trade_stops_level:
                        print(f"\n⚠️  WARNING: Current SL ({current_sl}) is less than required ({symbol_info.trade_stops_level})")
                        print(f"   This will cause 'Invalid stops' errors!")
                    elif current_sl < recommended_sl:
                        print(f"\n⚠️  WARNING: Current SL ({current_sl}) is below recommended ({recommended_sl})")
                        print(f"   Consider increasing to avoid issues with price movements")
                    else:
                        print(f"\n✅ Current SL value is acceptable")
                    
                    if current_tp < recommended_tp:
                        print(f"⚠️  Current TP ({current_tp}) is below recommended ({recommended_tp})")
                    else:
                        print(f"✅ Current TP value is acceptable")
            except Exception as e:
                print(f"\nNote: Could not read strategy file: {e}")
    else:
        print("⚠️  No minimum stops level requirement (unusual)")
        print("   Default recommendation: 20-50 points for SL")
    
    print(f"\n{'='*60}\n")
    
    mt5.shutdown()

if __name__ == "__main__":
    # Check XAUUSDM by default, or use command line argument
    symbol = sys.argv[1] if len(sys.argv) > 1 else "XAUUSDM"
    check_symbol_stops_level(symbol)

