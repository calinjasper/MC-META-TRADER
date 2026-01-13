"""
Debug script to diagnose why alerts are not executing trades
Run this when alerts are generated but trades are not executed
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from datetime import datetime
from src.alerts.mt5_alert_listener import MT5AlertListener
from src.strategy.strategy_manager import StrategyManager
from src.strategy.smma_strategy import SMMAStrategy
import MetaTrader5 as mt5

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_alert_file():
    """Check if alert file exists and has recent alerts"""
    print("\n" + "="*80)
    print("1. CHECKING ALERT FILE")
    print("="*80)
    
    listener = MT5AlertListener()
    alert_file = listener.alert_file_path
    
    if not alert_file:
        print("[ERROR] Alert file path not found!")
        return False
    
    print(f"Alert file path: {alert_file}")
    
    if not os.path.exists(alert_file):
        print(f"[ERROR] Alert file does not exist: {alert_file}")
        return False
    
    print(f"[OK] Alert file exists: {alert_file}")
    
    # Read recent alerts
    try:
        with open(alert_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            print(f"Total alert lines in file: {len(lines)}")
            
            if lines:
                print("\nLast 5 alerts:")
                for i, line in enumerate(lines[-5:], 1):
                    print(f"  {i}. {line.strip()}")
                
                # Parse last alert
                last_alert = listener.parse_alert(lines[-1].strip())
                if last_alert:
                    print(f"\n[OK] Last alert parsed successfully:")
                    print(f"   Symbol: {last_alert.get('symbol')}")
                    print(f"   Action: {last_alert.get('action')}")
                    print(f"   Price: {last_alert.get('price')}")
                    print(f"   Timeframe: {last_alert.get('timeframe')}")
                    print(f"   Timestamp: {last_alert.get('timestamp')}")
                    return last_alert
                else:
                    print("[ERROR] Failed to parse last alert")
                    return False
            else:
                print("[WARNING] Alert file is empty")
                return False
    except Exception as e:
        print(f"[ERROR] Error reading alert file: {e}")
        return False

def check_mt5_connection():
    """Check MT5 connection"""
    print("\n" + "="*80)
    print("2. CHECKING MT5 CONNECTION")
    print("="*80)
    
    if not mt5.initialize():
        print("[ERROR] MT5 initialization failed")
        print(f"   Error: {mt5.last_error()}")
        return False
    
    print("[OK] MT5 initialized")
    
    account_info = mt5.account_info()
    if account_info:
        print(f"[OK] MT5 connected - Account: {account_info.login}, Server: {account_info.server}")
        print(f"   Trade allowed: {account_info.trade_allowed}")
        print(f"   Trade mode: {account_info.trade_mode}")
        print(f"   Margin free: {account_info.margin_free}")
    else:
        print("[ERROR] Failed to get account info")
        return False
    
    return True

def check_symbol(symbol: str):
    """Check if symbol exists and is tradeable"""
    print("\n" + "="*80)
    print(f"3. CHECKING SYMBOL: {symbol}")
    print("="*80)
    
    # Try exact symbol
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info:
        print(f"[OK] Symbol found: {symbol}")
        print(f"   Trade mode: {symbol_info.trade_mode} (0=disabled, 4=enabled)")
        print(f"   Digits: {symbol_info.digits}")
        print(f"   Point: {symbol_info.point}")
        return symbol
    
    # Try with 'm' suffix (common for MT5)
    symbol_m = symbol + "m"
    symbol_info = mt5.symbol_info(symbol_m)
    if symbol_info:
        print(f"[OK] Symbol found with 'm' suffix: {symbol_m}")
        print(f"   Trade mode: {symbol_info.trade_mode}")
        return symbol_m
    
    # Try uppercase
    symbol_upper = symbol.upper()
    symbol_info = mt5.symbol_info(symbol_upper)
    if symbol_info:
        print(f"[OK] Symbol found (uppercase): {symbol_upper}")
        return symbol_upper
    
    print(f"[ERROR] Symbol not found: {symbol}")
    print("   Available symbols (first 10):")
    symbols = mt5.symbols_get()
    for i, s in enumerate(symbols[:10]):
        print(f"   {i+1}. {s.name}")
    
    return None

def check_strategies(symbol: str, timeframe: int = None):
    """Check if strategies exist for the symbol"""
    print("\n" + "="*80)
    print("4. CHECKING STRATEGIES")
    print("="*80)
    
    from src.strategy.strategy_persistence import StrategyPersistence
    
    persistence = StrategyPersistence()
    strategies_dir = persistence.strategies_dir
    
    if not strategies_dir.exists():
        print(f"[ERROR] Strategies directory not found: {strategies_dir}")
        return []
    
    print(f"Strategies directory: {strategies_dir}")
    
    # Load all strategies
    strategy_files = list(strategies_dir.glob("*.json"))
    print(f"Found {len(strategy_files)} strategy files")
    
    matching_strategies = []
    
    for strategy_file in strategy_files:
        try:
            strategy = persistence.load_strategy(str(strategy_file))
            if not strategy:
                continue
            
            strategy_symbol = getattr(strategy, 'symbol', '').upper()
            strategy_timeframe = getattr(strategy, 'timeframe', None)
            strategy_enabled = getattr(strategy, 'enabled', False)
            alert_driven = getattr(strategy, 'alert_driven', False)
            trade_direction = getattr(strategy, 'trade_direction', 'both')
            
            print(f"\n📋 Strategy: {strategy.name}")
            print(f"   Symbol: {strategy_symbol} (alert: {symbol.upper()})")
            print(f"   Timeframe: {strategy_timeframe} (alert: {timeframe})")
            print(f"   Enabled: {strategy_enabled}")
            print(f"   Alert-driven: {alert_driven}")
            print(f"   Trade direction: {trade_direction}")
            
            # Check if matches
            symbol_match = strategy_symbol == symbol.upper()
            timeframe_match = (timeframe is None or strategy_timeframe is None or 
                             strategy_timeframe == timeframe)
            
            if symbol_match and timeframe_match:
                matching_strategies.append({
                    'strategy': strategy,
                    'symbol_match': symbol_match,
                    'timeframe_match': timeframe_match,
                    'enabled': strategy_enabled,
                    'alert_driven': alert_driven,
                    'trade_direction': trade_direction
                })
                print(f"   [OK] MATCHES ALERT")
            else:
                print(f"   [NO MATCH] Does not match alert")
                if not symbol_match:
                    print(f"      - Symbol mismatch: {strategy_symbol} != {symbol.upper()}")
                if not timeframe_match:
                    print(f"      - Timeframe mismatch: {strategy_timeframe} != {timeframe}")
        except Exception as e:
            print(f"   [ERROR] Error loading strategy: {e}")
    
    return matching_strategies

def simulate_alert_processing(symbol: str, action: str, price: float, timeframe: int = None):
    """Simulate alert processing to see what happens"""
    print("\n" + "="*80)
    print("5. SIMULATING ALERT PROCESSING")
    print("="*80)
    
    from src.strategy.strategy_persistence import StrategyPersistence
    
    # Create alert dict
    alert = {
        'symbol': symbol,
        'action': action.upper(),
        'price': price,
        'timeframe': timeframe,
        'timestamp': datetime.now(),
        'indicator': 'SMMA'
    }
    
    print(f"Alert: {alert}")
    
    # Load strategy manager
    persistence = StrategyPersistence()
    strategy_manager = StrategyManager()
    
    # Load all strategies
    strategies_dir = persistence.strategies_dir
    if strategies_dir.exists():
        for strategy_file in strategies_dir.glob("*.json"):
            try:
                strategy = persistence.load_strategy(str(strategy_file))
                if strategy:
                    strategy_manager.add_strategy(strategy)
            except Exception as e:
                print(f"Error loading {strategy_file}: {e}")
    
    print(f"\nLoaded {strategy_manager.get_strategy_count()} strategies")
    
    # Process alert
    print(f"\nProcessing alert...")
    signals = strategy_manager.process_alert(alert)
    
    print(f"\nSignals generated: {signals}")
    
    if not signals:
        print("[ERROR] No signals generated from alert")
        print("\nPossible reasons:")
        print("  1. No matching strategy found (symbol/timeframe mismatch)")
        print("  2. Strategy not enabled")
        print("  3. Strategy not alert-driven")
        print("  4. Trade direction mismatch")
        print("  5. Duplicate alert (within 60 seconds)")
    else:
        print(f"[OK] {len(signals)} signal(s) generated:")
        for strategy_name, signal in signals.items():
            print(f"   - {strategy_name}: {signal}")

def main():
    """Main diagnostic function"""
    print("\n" + "="*80)
    print("ALERT-TO-TRADE DIAGNOSTIC TOOL")
    print("="*80)
    print("This tool helps diagnose why alerts are not executing trades")
    
    # Check alert file
    last_alert = check_alert_file()
    
    if not last_alert:
        print("\n[ERROR] No valid alerts found. Make sure the indicator is generating alerts.")
        return
    
    symbol = last_alert.get('symbol', 'USDJPY')
    action = last_alert.get('action', 'BUY')
    price = last_alert.get('price', 0.0)
    timeframe = last_alert.get('timeframe')
    
    # Check MT5
    if not check_mt5_connection():
        print("\n[ERROR] MT5 connection failed. Cannot proceed.")
        return
    
    # Check symbol
    actual_symbol = check_symbol(symbol)
    if not actual_symbol:
        print(f"\n[ERROR] Symbol {symbol} not found in MT5")
        return
    
    # Check strategies
    matching_strategies = check_strategies(actual_symbol, timeframe)
    
    if not matching_strategies:
        print(f"\n[ERROR] No matching strategies found for {actual_symbol}")
        print("\nTo fix this:")
        print(f"  1. Create a strategy for {actual_symbol}")
        print(f"  2. Set timeframe to {timeframe} (or leave blank for any timeframe)")
        print(f"  3. Enable 'Alert-driven' mode")
        print(f"  4. Enable the strategy")
        return
    
    # Check if any are enabled
    enabled_strategies = [s for s in matching_strategies if s['enabled']]
    if not enabled_strategies:
        print(f"\n[WARNING] Found {len(matching_strategies)} matching strategy(ies) but none are ENABLED")
        print("   Enable at least one strategy to execute trades")
    
    # Check if any are alert-driven
    alert_driven = [s for s in matching_strategies if s['alert_driven']]
    if not alert_driven:
        print(f"\n[WARNING] Found {len(matching_strategies)} matching strategy(ies) but none are ALERT-DRIVEN")
        print("   Set 'Alert-driven' mode to true for strategies to process alerts")
    
    # Simulate alert processing
    simulate_alert_processing(actual_symbol, action, price, timeframe)
    
    print("\n" + "="*80)
    print("DIAGNOSTIC COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("  1. Check the logs above for any [ERROR] messages")
    print("  2. Ensure at least one strategy matches the alert symbol/timeframe")
    print("  3. Ensure the strategy is enabled and alert-driven")
    print("  4. Check that trade_direction allows the alert action (BUY/SELL)")
    print("  5. Verify MT5 is connected and trading is enabled")

if __name__ == "__main__":
    main()
