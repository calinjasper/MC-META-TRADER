"""
Script to install SMMA Indicator to MT5
Copies the indicator file to MT5's Indicators folder
"""

import os
import shutil
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.mt5_utils import find_mt5_path


def find_mt5_indicators_directory():
    """Find MT5 Indicators directory"""
    # Get MT5 terminal path
    mt5_terminal = find_mt5_path()
    
    if not mt5_terminal:
        print("[ERROR] MT5 terminal not found. Please ensure MetaTrader 5 is installed.")
        return None
    
    # Extract MT5 installation directory
    mt5_install_dir = Path(mt5_terminal).parent
    
    # Try standard MQL5/Indicators path
    indicators_dir = mt5_install_dir / "MQL5" / "Indicators"
    
    if indicators_dir.exists():
        return indicators_dir
    
    # Try AppData path (common for MT5)
    import os
    appdata = os.getenv('APPDATA')
    if appdata:
        mt5_data = Path(appdata) / "MetaQuotes" / "Terminal"
        if mt5_data.exists():
            # Find the first terminal directory
            terminal_dirs = [d for d in mt5_data.iterdir() if d.is_dir()]
            if terminal_dirs:
                indicators_dir = terminal_dirs[0] / "MQL5" / "Indicators"
                if indicators_dir.exists():
                    return indicators_dir
                # Create if doesn't exist
                indicators_dir.mkdir(parents=True, exist_ok=True)
                return indicators_dir
    
    # Try to create in standard location
    indicators_dir = mt5_install_dir / "MQL5" / "Indicators"
    indicators_dir.mkdir(parents=True, exist_ok=True)
    return indicators_dir


def install_smma_indicator():
    """Install SMMA indicator to MT5"""
    print("=" * 60)
    print("Installing SMMA Indicator to MT5")
    print("=" * 60)
    
    # Find source file
    source_file = project_root / "src" / "indicators" / "smma_indicator.mq5"
    
    if not source_file.exists():
        print(f"[ERROR] Source file not found: {source_file}")
        return False
    
    # Find MT5 Indicators directory
    indicators_dir = find_mt5_indicators_directory()
    
    if not indicators_dir:
        print("[ERROR] Could not find MT5 Indicators directory")
        return False
    
    print(f"[OK] Found MT5 Indicators directory: {indicators_dir}")
    
    # Destination file
    dest_file = indicators_dir / "SMMA_Indicator.mq5"
    
    try:
        # Copy file
        shutil.copy2(source_file, dest_file)
        print(f"[OK] Copied indicator to: {dest_file}")
        print("\n" + "=" * 60)
        print("[SUCCESS] Installation Complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Open MetaTrader 5")
        print("2. Open MetaEditor (F4 or Tools > MetaQuotes Language Editor)")
        print("3. Navigate to: Indicators > SMMA_Indicator.mq5")
        print("4. Click 'Compile' button (F7) to compile the indicator")
        print("5. After compilation, the indicator will be available in MT5")
        print("6. To use: Right-click on chart > Insert Indicator > Custom > SMMA_Indicator")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"[ERROR] Error copying file: {e}")
        return False


if __name__ == "__main__":
    success = install_smma_indicator()
    sys.exit(0 if success else 1)
