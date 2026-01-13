"""Test SL/TP preview feature in Strategy Builder tab"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_preview_implementation():
    """Verify that preview feature is implemented in StrategyTab"""
    print("=" * 70)
    print("Testing SL/TP Preview Feature in Strategy Builder Tab")
    print("=" * 70)
    print()
    
    # Check if StrategyTab has the preview method
    try:
        from src.gui.strategy_tab import StrategyTab
        print("✅ StrategyTab imported successfully")
        
        # Check if _update_sl_tp_preview method exists
        if hasattr(StrategyTab, '_update_sl_tp_preview'):
            print("✅ _update_sl_tp_preview() method exists")
        else:
            print("❌ _update_sl_tp_preview() method NOT found")
            return False
        
        # Check if preview labels are created in _create_risk_management_section
        import inspect
        source = inspect.getsource(StrategyTab._create_risk_management_section)
        
        if 'sl_preview_label' in source:
            print("✅ sl_preview_label is created")
        else:
            print("❌ sl_preview_label NOT found in _create_risk_management_section")
            return False
        
        if 'tp_preview_label' in source:
            print("✅ tp_preview_label is created")
        else:
            print("❌ tp_preview_label NOT found in _create_risk_management_section")
            return False
        
        # Check if signals are connected
        if 'valueChanged.connect(self._update_sl_tp_preview)' in source:
            print("✅ Signal connections found")
        else:
            print("⚠️  Signal connections may be missing")
        
        # Check if symbol_combo signal is connected
        source_basic = inspect.getsource(StrategyTab._create_basic_info_section)
        if 'symbol_combo.currentTextChanged.connect(self._update_sl_tp_preview)' in source_basic:
            print("✅ Symbol combo signal connected")
        else:
            print("⚠️  Symbol combo signal may not be connected")
        
        # Check if preview is called in load_strategy
        source_load = inspect.getsource(StrategyTab.load_strategy)
        if '_update_sl_tp_preview()' in source_load:
            print("✅ Preview update called in load_strategy()")
        else:
            print("⚠️  Preview update may not be called in load_strategy()")
        
        print()
        print("=" * 70)
        print("Implementation Check Complete")
        print("=" * 70)
        print()
        print("To fully test:")
        print("1. Open the application")
        print("2. Go to 'Strategy Builder' tab")
        print("3. Select a symbol (e.g., BTCUSDm)")
        print("4. Enter SL value: 50")
        print("5. Verify preview shows: '50.00 points = 0.50 price points | BUY SL: X.XX | SELL SL: X.XX'")
        print("6. Change TP value and verify TP preview updates")
        print("7. Change symbol and verify preview updates")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import StrategyTab: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_preview_implementation()
    sys.exit(0 if success else 1)
