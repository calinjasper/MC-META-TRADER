"""Test SL calculation with actual strategy object"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.strategy.strategy_persistence import StrategyPersistence
from src.mt5_connector import MT5Connector
from src.gui.main_window import MainWindow

def test_calculation():
    # Load strategy
    persistence = StrategyPersistence()
    strategy = persistence.load_strategy("strategies/BTC_BUY.json")
    
    if not strategy:
        print("Failed to load strategy")
        return
    
    print("Strategy loaded:")
    print(f"  sl_type: {getattr(strategy, 'sl_type', None)}")
    print(f"  sl_value: {getattr(strategy, 'sl_value', None)}")
    print(f"  sl_enabled: {getattr(strategy, 'sl_enabled', None)}")
    print()
    
    # Initialize MT5
    mt5 = MT5Connector()
    if not mt5.initialize():
        print("Failed to initialize MT5")
        return
    
    # Create a minimal main_window-like object to test calculation
    class TestCalc:
        def __init__(self):
            self.mt5 = mt5
            from src.trading.risk_manager import RiskManager
            self.risk_manager = RiskManager(mt5)
        
        def calculate_strategy_sl_tp(self, strategy, symbol, entry_price, signal):
            """Copy of calculate_strategy_sl_tp from main_window.py"""
            symbol_info = self.mt5.get_symbol_info(symbol)
            if not symbol_info:
                sl = self.risk_manager.calculate_stop_loss(symbol, entry_price, signal)
                tp = self.risk_manager.calculate_take_profit(symbol, entry_price, signal, stop_loss=sl)
                return sl, tp
            
            point = symbol_info.get('point', 0.0001)
            digits = symbol_info.get('digits', 5)
            
            sl_enabled = getattr(strategy, 'sl_enabled', True)
            tp_enabled = getattr(strategy, 'tp_enabled', True)
            
            if not sl_enabled and not tp_enabled:
                return 0.0, 0.0
            
            if not hasattr(strategy, 'sl_type') or strategy.sl_type is None:
                if sl_enabled and tp_enabled:
                    sl = self.risk_manager.calculate_stop_loss(symbol, entry_price, signal)
                    tp = self.risk_manager.calculate_take_profit(symbol, entry_price, signal, stop_loss=sl)
                    return sl, tp
                elif sl_enabled:
                    sl = self.risk_manager.calculate_stop_loss(symbol, entry_price, signal)
                    return sl, 0.0
                else:
                    return 0.0, 0.0
            
            sl_value = getattr(strategy, 'sl_value', 20.0)
            sl_type = strategy.sl_type
            
            print(f"  In calculation:")
            print(f"    sl_type: {sl_type}")
            print(f"    sl_value: {sl_value}")
            print(f"    point: {point}")
            print(f"    digits: {digits}")
            
            if "Pips" in sl_type:
                pip_size = point * (10 if digits == 5 else 1)
                sl_distance = sl_value * pip_size
            elif "Points" in sl_type:
                sl_distance = sl_value * point
            else:
                sl_distance = entry_price * (sl_value / 100.0)
            
            print(f"    sl_distance: {sl_distance}")
            
            if sl_enabled:
                if signal == 'BUY':
                    sl = entry_price - sl_distance
                else:
                    sl = entry_price + sl_distance
            else:
                sl = 0.0
            
            print(f"    Calculated SL: {sl}")
            
            # Round
            sl = round(sl, digits)
            print(f"    Rounded SL: {sl}")
            
            return sl, 0.0
    
    calc = TestCalc()
    entry_price = 88896.73
    sl, tp = calc.calculate_strategy_sl_tp(strategy, 'BTCUSDm', entry_price, 'BUY')
    
    print()
    print(f"Final Result:")
    print(f"  Entry: {entry_price}")
    print(f"  SL: {sl}")
    print(f"  Expected: 88896.23 (50 points)")
    print(f"  From logs: 88896.53 (20 points)")
    
    mt5.shutdown()

if __name__ == "__main__":
    test_calculation()
