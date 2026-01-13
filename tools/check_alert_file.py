"""Check alert file locations and contents"""

import os
from pathlib import Path

# Check project data directory
project_alert_file = Path("data/smma_alerts.txt")
print(f"Project alert file: {project_alert_file.absolute()}")
print(f"  Exists: {project_alert_file.exists()}")
if project_alert_file.exists():
    with open(project_alert_file, 'r', encoding='utf-8') as f:
        content = f.read()
        print(f"  Size: {len(content)} bytes")
        if content.strip():
            print(f"  Last 500 chars:\n{content[-500:]}")

# Check MT5 Common Files directory
mt5_file = Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "Common" / "Files" / "smma_alerts.txt"
print(f"\nMT5 Common Files alert file: {mt5_file}")
print(f"  Exists: {mt5_file.exists()}")
print(f"  Parent exists: {mt5_file.parent.exists()}")
if mt5_file.exists():
    with open(mt5_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"  Total lines: {len(lines)}")
        if lines:
            print(f"  Last 10 lines:")
            for i, line in enumerate(lines[-10:], max(1, len(lines)-9)):
                print(f"    {i}: {line.strip()}")
