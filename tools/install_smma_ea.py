"""
Install SMMA Alert EA to MT5
Copies the EA file to MT5's Experts directory
"""

import os
import shutil
import sys
from pathlib import Path

def find_mt5_installation():
    """Find MT5 installation directory"""
    possible_paths = [
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "MetaQuotes", "Terminal"),
        os.path.join("C:", "Program Files", "MetaTrader 5"),
        os.path.join("C:", "Program Files (x86)", "MetaTrader 5"),
    ]
    
    for base_path in possible_paths:
        if os.path.exists(base_path):
            # Look for terminal directories
            if "Terminal" in base_path:
                # Find the terminal ID directory
                terminal_dir = Path(base_path)
                if terminal_dir.exists():
                    for terminal_id_dir in terminal_dir.iterdir():
                        if terminal_id_dir.is_dir():
                            experts_dir = terminal_id_dir / "MQL5" / "Experts"
                            if experts_dir.exists():
                                return str(experts_dir)
            else:
                # Direct MT5 installation
                experts_dir = Path(base_path) / "MQL5" / "Experts"
                if experts_dir.exists():
                    return str(experts_dir)
    
    return None

def main():
    """Install SMMA Alert EA"""
    print("=" * 80)
    print("SMMA Alert EA Installation")
    print("=" * 80)
    
    # Find source file
    project_root = Path(__file__).resolve().parent.parent
    source_file = project_root / "src" / "indicators" / "smma_alert_ea.mq5"
    
    if not source_file.exists():
        print(f"[ERROR] Source file not found: {source_file}")
        return 1
    
    # Find MT5 Experts directory
    experts_dir = find_mt5_installation()
    if not experts_dir:
        print("[ERROR] Could not find MT5 installation directory")
        print("\nPlease manually copy the EA file to:")
        print("  MT5 Installation Directory\\MQL5\\Experts\\")
        print(f"\nSource file: {source_file}")
        return 1
    
    # Copy file
    dest_file = Path(experts_dir) / "smma_alert_ea.mq5"
    try:
        shutil.copy2(source_file, dest_file)
        print(f"[OK] EA installed successfully!")
        print(f"  Source: {source_file}")
        print(f"  Destination: {dest_file}")
        print("\nNext steps:")
        print("  1. Open MetaEditor in MT5")
        print("  2. Compile smma_alert_ea.mq5")
        print("  3. Attach the EA to your chart (along with SMMA indicator)")
        print("  4. The EA will monitor alerts and write them to smma_alerts.txt")
    except Exception as e:
        print(f"[ERROR] Failed to install EA: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
