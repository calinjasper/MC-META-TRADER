"""
Interactive Setup Execution Helper
Guides you through each step and verifies completion
"""

import os
import sys
import shutil
from pathlib import Path

def print_step(step_num, title):
    """Print step header"""
    print("\n" + "=" * 60)
    print(f"STEP {step_num}: {title}")
    print("=" * 60)

def find_mt5_indicators_folder():
    """Find MT5 Indicators folder"""
    paths = [
        r"C:\Program Files\MetaTrader 5\MQL5\Indicators",
        r"C:\Program Files (x86)\MetaTrader 5\MQL5\Indicators",
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path
    
    # Try registry
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\MetaQuotes\MetaTrader 5"
        )
        try:
            install_path = winreg.QueryValueEx(key, "Path")[0]
            indicators_path = os.path.join(install_path, "MQL5", "Indicators")
            if os.path.exists(indicators_path):
                return indicators_path
        finally:
            winreg.CloseKey(key)
    except:
        pass
    
    return None

def find_mt5_files_folder():
    """Find MT5 Files folder"""
    paths = [
        r"C:\Program Files\MetaTrader 5\MQL5\Files",
        r"C:\Program Files (x86)\MetaTrader 5\MQL5\Files",
    ]
    
    for path in paths:
        if os.path.exists(path):
            return path
    
    # Try registry
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\MetaQuotes\MetaTrader 5"
        )
        try:
            install_path = winreg.QueryValueEx(key, "Path")[0]
            files_path = os.path.join(install_path, "MQL5", "Files")
            if os.path.exists(files_path):
                return files_path
        finally:
            winreg.CloseKey(key)
    except:
        pass
    
    return None

def main():
    print("\n" + "=" * 60)
    print("MT5 Indicator Export System - Interactive Setup")
    print("=" * 60)
    print("\nThis script will guide you through the setup process.")
    print("Press Enter after completing each step.\n")
    
    # Get current script directory
    script_dir = Path(__file__).parent
    source_file = script_dir / "PythonIndicators.mq5"
    
    if not source_file.exists():
        print(f"[ERROR] PythonIndicators.mq5 not found in {script_dir}")
        print("Please ensure you're running this from the mt5_indicators folder.")
        input("\nPress Enter to exit...")
        return
    
    # STEP 1: Copy Indicator File
    print_step(1, "Copy Indicator File to MT5")
    mt5_indicators_folder = find_mt5_indicators_folder()
    
    if mt5_indicators_folder:
        target_file = os.path.join(mt5_indicators_folder, "PythonIndicators.mq5")
        print(f"Source: {source_file}")
        print(f"Target: {target_file}")
        
        if os.path.exists(target_file):
            response = input("\nFile already exists. Overwrite? (y/n): ").lower()
            if response != 'y':
                print("Skipping copy...")
            else:
                try:
                    shutil.copy2(str(source_file), target_file)
                    print("[OK] File copied successfully!")
                except Exception as e:
                    print(f"[ERROR] Failed to copy: {e}")
                    print("Please copy manually or run as Administrator.")
        else:
            try:
                shutil.copy2(str(source_file), target_file)
                print("[OK] File copied successfully!")
            except Exception as e:
                print(f"[ERROR] Failed to copy: {e}")
                print("Please copy manually or run as Administrator.")
                print(f"\nManual copy:")
                print(f"  FROM: {source_file}")
                print(f"  TO:   {target_file}")
    else:
        print("[WARNING] MT5 Indicators folder not found automatically.")
        print("Please copy manually:")
        print(f"  FROM: {source_file}")
        print(f"  TO:   {Your MT5 Path}\\MQL5\\Indicators\\PythonIndicators.mq5")
    
    input("\nPress Enter to continue to Step 2...")
    
    # STEP 2: Compile Indicator
    print_step(2, "Compile Indicator in MetaEditor")
    print("Instructions:")
    print("1. Open MetaTrader 5")
    print("2. Press F4 (opens MetaEditor)")
    print("3. File → Open → Navigate to MQL5\\Indicators\\PythonIndicators.mq5")
    print("4. Press F7 (compile)")
    print("5. Verify: 0 error(s), 0 warning(s)")
    print("\n[IMPORTANT] You must do this step manually in MT5.")
    
    response = input("\nHave you compiled the indicator? (y/n): ").lower()
    if response == 'y':
        # Check if .ex5 file exists
        if mt5_indicators_folder:
            ex5_file = os.path.join(mt5_indicators_folder, "PythonIndicators.ex5")
            if os.path.exists(ex5_file):
                print("[OK] Compiled file found!")
            else:
                print("[WARNING] Compiled file not found. Please verify compilation.")
        print("[OK] Proceeding...")
    else:
        print("[WARNING] Please compile before continuing.")
        print("The indicator will not work without compilation.")
    
    input("\nPress Enter to continue to Step 3...")
    
    # STEP 3: Verify Export Folder
    print_step(3, "Verify Export Folder")
    mt5_files_folder = find_mt5_files_folder()
    
    if mt5_files_folder:
        export_folder = os.path.join(mt5_files_folder, "PythonIndicators")
        print(f"Export folder: {export_folder}")
        
        if not os.path.exists(export_folder):
            print("Folder doesn't exist. Creating...")
            try:
                os.makedirs(export_folder, exist_ok=True)
                print("[OK] Folder created!")
            except Exception as e:
                print(f"[ERROR] Failed to create folder: {e}")
                print("Please create manually or run as Administrator.")
        else:
            print("[OK] Export folder exists!")
        
        # Check for JSON files
        json_files = [f for f in os.listdir(export_folder) if f.endswith('.json')] if os.path.exists(export_folder) else []
        if json_files:
            print(f"[OK] Found {len(json_files)} JSON file(s)")
            print("Files will be created/updated when Python app runs.")
        else:
            print("[INFO] No JSON files yet. They will be created when Python app runs.")
    else:
        print("[WARNING] MT5 Files folder not found.")
        print("Please create manually: {Your MT5 Path}\\MQL5\\Files\\PythonIndicators\\")
    
    input("\nPress Enter to continue to Step 4...")
    
    # STEP 4: Run Python App
    print_step(4, "Run Python Application")
    print("Instructions:")
    print("1. Open terminal in project root")
    print("2. Run: python src/main.py")
    print("3. Click 'Connect to MT5' in the app")
    print("4. Wait for connection confirmation")
    print("\n[IMPORTANT] You must do this step manually.")
    
    response = input("\nIs the Python app running and connected to MT5? (y/n): ").lower()
    if response == 'y':
        # Check for JSON files
        if mt5_files_folder:
            export_folder = os.path.join(mt5_files_folder, "PythonIndicators")
            if os.path.exists(export_folder):
                json_files = [f for f in os.listdir(export_folder) if f.endswith('.json')]
                if json_files:
                    print(f"[OK] Found {len(json_files)} JSON file(s)!")
                    for f in json_files[:3]:
                        print(f"  - {f}")
                else:
                    print("[WARNING] No JSON files found yet.")
                    print("Make sure:")
                    print("  - Python app is running")
                    print("  - Connected to MT5")
                    print("  - Symbols are being monitored")
        print("[OK] Proceeding...")
    else:
        print("[WARNING] Please start Python app before continuing.")
    
    input("\nPress Enter to continue to Step 5...")
    
    # STEP 5: Attach to Chart
    print_step(5, "Attach Indicator to MT5 Chart")
    print("Instructions:")
    print("1. Open MT5 chart (e.g., XAUUSDm M1)")
    print("2. Press Ctrl+N (opens Navigator)")
    print("3. Expand Indicators → Custom")
    print("4. Drag PythonIndicators onto chart")
    print("5. In properties, enable indicators you want:")
    print("   - Show EMA 50")
    print("   - Show EMA 200")
    print("   - Show VWAP")
    print("   - Show SuperTrend")
    print("6. Click OK")
    print("\n[IMPORTANT] You must do this step manually in MT5.")
    
    response = input("\nHave you attached the indicator to a chart? (y/n): ").lower()
    if response == 'y':
        print("[OK] Great!")
        print("\nVerify indicators are showing:")
        print("  - EMA 50 (orange line)")
        print("  - EMA 200 (blue line)")
        print("  - VWAP (cyan line)")
        print("  - SuperTrend (green line)")
    else:
        print("[INFO] Please attach the indicator to see the indicators on chart.")
    
    input("\nPress Enter to continue...")
    
    # Final Summary
    print("\n" + "=" * 60)
    print("SETUP SUMMARY")
    print("=" * 60)
    
    checklist = []
    
    # Check indicator file
    if mt5_indicators_folder:
        if os.path.exists(os.path.join(mt5_indicators_folder, "PythonIndicators.mq5")):
            checklist.append("[OK] Indicator file copied")
        else:
            checklist.append("[ ] Indicator file copied")
        
        if os.path.exists(os.path.join(mt5_indicators_folder, "PythonIndicators.ex5")):
            checklist.append("[OK] Indicator compiled")
        else:
            checklist.append("[ ] Indicator compiled")
    else:
        checklist.append("[?] Indicator file (MT5 folder not found)")
    
    # Check export folder
    if mt5_files_folder:
        export_folder = os.path.join(mt5_files_folder, "PythonIndicators")
        if os.path.exists(export_folder):
            checklist.append("[OK] Export folder exists")
            json_files = [f for f in os.listdir(export_folder) if f.endswith('.json')] if os.path.exists(export_folder) else []
            if json_files:
                checklist.append(f"[OK] JSON files created ({len(json_files)} files)")
            else:
                checklist.append("[ ] JSON files created (run Python app)")
        else:
            checklist.append("[ ] Export folder exists")
    else:
        checklist.append("[?] Export folder (MT5 folder not found)")
    
    print("\nChecklist:")
    for item in checklist:
        print(f"  {item}")
    
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nIf indicators are not showing:")
    print("1. Check TROUBLESHOOTING.md")
    print("2. Verify symbol/timeframe match")
    print("3. Check MT5 Expert/Journal tabs for errors")
    print("4. Ensure JSON files are updating")
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")

