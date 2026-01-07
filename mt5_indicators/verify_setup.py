"""
Verification Script for MT5 Indicator Export System
Checks if everything is set up correctly
"""

import os
import json
from pathlib import Path

def find_mt5_data_folder():
    """Find MT5 data folder"""
    import winreg
    common_paths = [
        r"C:\Program Files\MetaTrader 5\MQL5\Files",
        r"C:\Program Files (x86)\MetaTrader 5\MQL5\Files",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    # Try registry
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\MetaQuotes\MetaTrader 5"
        )
        try:
            install_path = winreg.QueryValueEx(key, "Path")[0]
            data_folder = os.path.join(install_path, "MQL5", "Files")
            if os.path.exists(data_folder):
                return data_folder
        finally:
            winreg.CloseKey(key)
    except:
        pass
    
    return None

def verify_setup():
    """Verify the setup"""
    print("=" * 60)
    print("MT5 Indicator Export System - Verification")
    print("=" * 60)
    print()
    
    # 1. Check MT5 data folder
    print("1. Checking MT5 Data Folder...")
    mt5_data_folder = find_mt5_data_folder()
    if mt5_data_folder:
        print(f"   [OK] Found: {mt5_data_folder}")
    else:
        print("   [ERROR] MT5 data folder not found!")
        print("   Please ensure MT5 is installed.")
        return False
    
    # 2. Check export folder
    print("\n2. Checking Export Folder...")
    export_folder = os.path.join(mt5_data_folder, "PythonIndicators")
    if os.path.exists(export_folder):
        print(f"   [OK] Export folder exists: {export_folder}")
    else:
        print(f"   [ERROR] Export folder not found: {export_folder}")
        print("   Creating folder...")
        try:
            os.makedirs(export_folder, exist_ok=True)
            print("   [OK] Folder created successfully")
        except Exception as e:
            print(f"   [ERROR] Failed to create folder: {e}")
            return False
    
    # 3. Check for JSON files
    print("\n3. Checking for JSON Files...")
    json_files = [f for f in os.listdir(export_folder) if f.endswith('.json')]
    if json_files:
        print(f"   [OK] Found {len(json_files)} JSON file(s):")
        for f in json_files[:5]:  # Show first 5
            filepath = os.path.join(export_folder, f)
            mtime = os.path.getmtime(filepath)
            from datetime import datetime
            mod_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"      - {f} (modified: {mod_time})")
        
        # Check if files are recent (within last 5 minutes)
        from datetime import datetime, timedelta
        now = datetime.now()
        recent_files = []
        for f in json_files:
            filepath = os.path.join(export_folder, f)
            mtime = os.path.getmtime(filepath)
            mod_time = datetime.fromtimestamp(mtime)
            if (now - mod_time) < timedelta(minutes=5):
                recent_files.append(f)
        
        if recent_files:
            print(f"   [OK] {len(recent_files)} file(s) updated in last 5 minutes")
        else:
            print("   [WARNING] No files updated recently - Python app may not be running")
    else:
        print("   [WARNING] No JSON files found")
        print("   This is OK if Python app hasn't started yet")
    
    # 4. Check indicator file location
    print("\n4. Checking Indicator File Location...")
    indicator_paths = [
        r"C:\Program Files\MetaTrader 5\MQL5\Indicators\PythonIndicators.mq5",
        r"C:\Program Files (x86)\MetaTrader 5\MQL5\Indicators\PythonIndicators.mq5",
    ]
    
    found_indicator = False
    for path in indicator_paths:
        if os.path.exists(path):
            print(f"   [OK] Indicator file found: {path}")
            found_indicator = True
            
            # Check if compiled version exists
            ex5_path = path.replace('.mq5', '.ex5')
            if os.path.exists(ex5_path):
                print(f"   [OK] Compiled version exists: {ex5_path}")
            else:
                print(f"   [WARNING] Compiled version not found: {ex5_path}")
                print("   Please compile the indicator in MetaEditor (F7)")
            break
    
    if not found_indicator:
        print("   [ERROR] Indicator file not found in standard locations")
        print("   Please copy PythonIndicators.mq5 to:")
        print("   C:\\Program Files\\MetaTrader 5\\MQL5\\Indicators\\")
    
    # 5. Validate JSON file format (if files exist)
    print("\n5. Validating JSON File Format...")
    if json_files:
        sample_file = os.path.join(export_folder, json_files[0])
        try:
            with open(sample_file, 'r') as f:
                data = json.load(f)
            
            print(f"   [OK] JSON is valid")
            print(f"   Symbol: {data.get('symbol', 'N/A')}")
            print(f"   Timeframe: {data.get('timeframe', 'N/A')}")
            
            indicators = data.get('indicators', {})
            print(f"   Indicators found: {len(indicators)}")
            for key in list(indicators.keys())[:5]:  # Show first 5
                value = indicators[key]
                if isinstance(value, dict):
                    print(f"      - {key}: {list(value.keys())}")
                else:
                    print(f"      - {key}: {value}")
            
            # Check for required indicators
            required = ['EMA_50', 'EMA_200', 'VWAP']
            missing = [r for r in required if r not in indicators]
            if missing:
                print(f"   [WARNING] Missing indicators: {missing}")
            else:
                print("   [OK] All required indicators present")
                
        except json.JSONDecodeError as e:
            print(f"   [ERROR] Invalid JSON: {e}")
        except Exception as e:
            print(f"   [ERROR] Error reading file: {e}")
    else:
        print("   [WARNING] No JSON files to validate")
    
    print("\n" + "=" * 60)
    print("Verification Complete!")
    print("=" * 60)
    print("\nNext Steps:")
    print("1. If indicator file not found, copy PythonIndicators.mq5 to MT5 Indicators folder")
    print("2. Compile the indicator in MetaEditor (F7)")
    print("3. Ensure Python app is running and connected to MT5")
    print("4. Attach indicator to chart in MT5")
    print()
    
    return True

if __name__ == "__main__":
    verify_setup()

