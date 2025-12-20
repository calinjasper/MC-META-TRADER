"""
MetaTrader 5 Utility Functions
"""

import os
import winreg
from pathlib import Path
from typing import Optional


def find_mt5_path() -> Optional[str]:
    """
    Auto-detect MetaTrader 5 installation path on Windows
    
    Returns:
        Path to MT5 terminal executable or None if not found
    """
    # Common installation paths
    common_paths = [
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
        r"C:\Program Files\MetaTrader 5\terminal.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal.exe",
    ]
    
    # Check common paths first
    for path in common_paths:
        if os.path.exists(path):
            return path
    
    # Try to find from registry
    try:
        # Check 64-bit registry
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\MetaQuotes\MetaTrader 5"
        )
        try:
            install_path = winreg.QueryValueEx(key, "Path")[0]
            terminal_path = os.path.join(install_path, "terminal64.exe")
            if os.path.exists(terminal_path):
                return terminal_path
            
            terminal_path = os.path.join(install_path, "terminal.exe")
            if os.path.exists(terminal_path):
                return terminal_path
        finally:
            winreg.CloseKey(key)
    except (FileNotFoundError, OSError):
        pass
    
    try:
        # Check 32-bit registry (WOW64)
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\MetaQuotes\MetaTrader 5"
        )
        try:
            install_path = winreg.QueryValueEx(key, "Path")[0]
            terminal_path = os.path.join(install_path, "terminal64.exe")
            if os.path.exists(terminal_path):
                return terminal_path
            
            terminal_path = os.path.join(install_path, "terminal.exe")
            if os.path.exists(terminal_path):
                return terminal_path
        finally:
            winreg.CloseKey(key)
    except (FileNotFoundError, OSError):
        pass
    
    # Search in Program Files
    program_files_paths = [
        Path(r"C:\Program Files"),
        Path(r"C:\Program Files (x86)"),
    ]
    
    for pf_path in program_files_paths:
        if pf_path.exists():
            mt5_dirs = list(pf_path.glob("MetaTrader 5*"))
            for mt5_dir in mt5_dirs:
                terminal_path = mt5_dir / "terminal64.exe"
                if terminal_path.exists():
                    return str(terminal_path)
                
                terminal_path = mt5_dir / "terminal.exe"
                if terminal_path.exists():
                    return str(terminal_path)
    
    return None

