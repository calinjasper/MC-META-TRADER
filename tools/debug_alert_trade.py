"""
Debug script to check why alerts are not triggering trades
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from src.alerts.mt5_alert_listener import MT5AlertListener
from src.strategy.strategy_manager import StrategyManager
from src.strategy.strategy_persistence import StrategyPersistence

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Debug alert processing"""
    print("=" * 80)
    print("Alert Trade Debug Tool")
    print("=" * 80)
    
    # Load strategies
    persistence = StrategyPersistence()
    strategies_dir = persistence.strategies_dir
    
    print(f"\nLooking for strategies in: {strategies_dir}")
    
    strategy_files = list(strategies_dir.glob("*.json"))
    if not strategy_files:
        print("No strategies found!")
        return
    
    print(f"\nFound {len(strategy_files)} strategies:")
    strategy_manager = StrategyManager()
    
    for strategy_file in strategy_files:
        try:
            strategy = persistence.load_strategy(strategy_file.stem)
            if strategy:
                strategy_manager.add_strategy(strategy)
                print(f"  - {strategy.name}: {strategy.symbol} (TF: {strategy.timeframe if hasattr(strategy, 'timeframe') else 'N/A'}, "
                      f"Direction: {getattr(strategy, 'trade_direction', 'both')}, "
                      f"Enabled: {strategy.enabled}, "
                      f"Alert-driven: {getattr(strategy, 'alert_driven', False)})")
        except Exception as e:
            print(f"  - Error loading {strategy_file.stem}: {e}")
    
    # Check alert file
    alert_listener = MT5AlertListener()
    print(f"\nAlert file path: {alert_listener.alert_file_path}")
    
    if alert_listener.alert_file_path and os.path.exists(alert_listener.alert_file_path):
        print(f"Alert file exists: Yes")
        # Read recent alerts
        recent_alerts = alert_listener.get_recent_alerts(count=10)
        print(f"\nRecent alerts ({len(recent_alerts)}):")
        for alert in recent_alerts:
            print(f"  - {alert['timestamp']}: {alert['action']} {alert['symbol']} @ {alert['price']:.5f} (TF: {alert['timeframe']})")
        
        # Test alert processing
        if recent_alerts:
            print("\n" + "=" * 80)
            print("Testing Alert Processing")
            print("=" * 80)
            
            for alert in recent_alerts[-3:]:  # Test last 3 alerts
                print(f"\nProcessing alert: {alert['action']} {alert['symbol']} @ {alert['price']:.5f}")
                print(f"  Alert details: {alert}")
                
                # Check matching strategies
                matching_strategies = []
                for name, strategy in strategy_manager.get_all_strategies():
                    if not strategy.enabled:
                        print(f"  Strategy {name}: SKIPPED (disabled)")
                        continue
                    
                    # Check symbol match
                    alert_symbol = alert.get('symbol', '').upper()
                    strategy_symbol = strategy.symbol.upper()
                    symbol_match = alert_symbol == strategy_symbol
                    
                    # Check timeframe match
                    alert_timeframe = alert.get('timeframe')
                    strategy_timeframe = getattr(strategy, 'timeframe', None)
                    timeframe_match = True
                    if alert_timeframe and strategy_timeframe:
                        timeframe_match = alert_timeframe == strategy_timeframe
                    
                    # Check direction match
                    alert_action = alert.get('action', '').upper()
                    trade_direction = getattr(strategy, 'trade_direction', 'both')
                    direction_match = True
                    if trade_direction == 'long' and alert_action != 'BUY':
                        direction_match = False
                    if trade_direction == 'short' and alert_action != 'SELL':
                        direction_match = False
                    
                    # Check if alert-driven
                    is_alert_driven = hasattr(strategy, 'alert_driven') and strategy.alert_driven
                    
                    print(f"  Strategy {name}:")
                    print(f"    Symbol: {strategy_symbol} (alert: {alert_symbol}) - {'MATCH' if symbol_match else 'NO MATCH'}")
                    print(f"    Timeframe: {strategy_timeframe} (alert: {alert_timeframe}) - {'MATCH' if timeframe_match else 'NO MATCH'}")
                    print(f"    Direction: {trade_direction} (alert: {alert_action}) - {'MATCH' if direction_match else 'NO MATCH'}")
                    print(f"    Alert-driven: {is_alert_driven}")
                    
                    if symbol_match and timeframe_match and direction_match and is_alert_driven:
                        matching_strategies.append((name, strategy))
                        print(f"    -> MATCHES!")
                    else:
                        print(f"    -> DOES NOT MATCH")
                
                # Process alert
                signals = strategy_manager.process_alert(alert)
                print(f"\n  Signals generated: {signals}")
                
                if not signals:
                    print("  -> NO SIGNALS GENERATED")
                    if not matching_strategies:
                        print("  -> REASON: No matching strategies found")
                    else:
                        print(f"  -> REASON: {len(matching_strategies)} matching strategies but no signals")
                        for name, strategy in matching_strategies:
                            if hasattr(strategy, 'trigger_from_alert'):
                                signal = strategy.trigger_from_alert(alert['action'], alert['price'])
                                print(f"    Strategy {name} trigger_from_alert returned: {signal}")
    else:
        print(f"Alert file does not exist or path not set")
        print("Make sure the SMMA indicator is writing alerts to the file")
    
    print("\n" + "=" * 80)
    print("Debug Complete")
    print("=" * 80)

if __name__ == "__main__":
    main()
