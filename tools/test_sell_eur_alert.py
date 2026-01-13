"""
Test SELL_EUR strategy with a simulated alert
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
from src.strategy.strategy_persistence import StrategyPersistence
from src.strategy.strategy_manager import StrategyManager

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Load SELL_EUR strategy
    persistence = StrategyPersistence()
    strategy = persistence.load_strategy(str(Path("strategies/SELL_EUR.json")))
    
    if not strategy:
        print("ERROR: Could not load SELL_EUR strategy")
        return
    
    print(f"Strategy: {strategy.name}")
    print(f"  Symbol: {strategy.symbol}")
    print(f"  Timeframe: {getattr(strategy, 'timeframe', 'N/A')}")
    print(f"  Trade Direction: {getattr(strategy, 'trade_direction', 'both')}")
    print(f"  Enabled: {strategy.enabled}")
    print(f"  Alert-driven: {getattr(strategy, 'alert_driven', False)}")
    print(f"  Has trigger_from_alert: {hasattr(strategy, 'trigger_from_alert')}")
    
    # Test alert matching
    strategy_manager = StrategyManager()
    strategy_manager.add_strategy(strategy)
    
    # Test with different alert formats
    test_alerts = [
        {"symbol": "EURUSDm", "action": "SELL", "price": 1.08500, "timeframe": 15},
        {"symbol": "EURUSD", "action": "SELL", "price": 1.08500, "timeframe": 15},
        {"symbol": "EURUSDm", "action": "BUY", "price": 1.08500, "timeframe": 15},
        {"symbol": "EURUSDm", "action": "SELL", "price": 1.08500, "timeframe": 5},
    ]
    
    print("\n" + "=" * 80)
    print("Testing Alert Matching")
    print("=" * 80)
    
    for alert in test_alerts:
        print(f"\nAlert: {alert['action']} {alert['symbol']} @ {alert['price']} (TF: {alert['timeframe']})")
        signals = strategy_manager.process_alert(alert)
        print(f"  Signals: {signals}")
        
        if not signals:
            # Check why it didn't match
            alert_symbol = alert.get('symbol', '').upper()
            strategy_symbol = strategy.symbol.upper()
            symbol_match = alert_symbol == strategy_symbol
            
            alert_timeframe = alert.get('timeframe')
            strategy_timeframe = getattr(strategy, 'timeframe', None)
            timeframe_match = True
            if alert_timeframe and strategy_timeframe:
                timeframe_match = alert_timeframe == strategy_timeframe
            
            alert_action = alert.get('action', '').upper()
            trade_direction = getattr(strategy, 'trade_direction', 'both')
            direction_match = True
            if trade_direction == 'long' and alert_action != 'BUY':
                direction_match = False
            if trade_direction == 'short' and alert_action != 'SELL':
                direction_match = False
            
            is_alert_driven = hasattr(strategy, 'alert_driven') and strategy.alert_driven
            
            print(f"  Symbol match: {symbol_match} ({alert_symbol} vs {strategy_symbol})")
            print(f"  Timeframe match: {timeframe_match} ({alert_timeframe} vs {strategy_timeframe})")
            print(f"  Direction match: {direction_match} ({alert_action} vs {trade_direction})")
            print(f"  Alert-driven: {is_alert_driven}")
            
            if symbol_match and timeframe_match and direction_match and is_alert_driven:
                # Try triggering directly
                if hasattr(strategy, 'trigger_from_alert'):
                    signal = strategy.trigger_from_alert(alert['action'], alert['price'])
                    print(f"  Direct trigger_from_alert returned: {signal}")

if __name__ == "__main__":
    main()
