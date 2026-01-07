import json
import os
from pathlib import Path

path = Path("c:/Users/Calin Jasper/Music/mc_meta/data/trade_history.json")

print(f"Reading {path}")
if not path.exists():
    print("File not found")
else:
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        
        print(f"Total trades in history: {len(data)}")
        
        open_positions = [p for p in data if p.get('status') == 'Open']
        print(f"Open positions: {len(open_positions)}")
        
        for p in open_positions:
            print(f"- Strategy: {p.get('strategy_name')}, Symbol: {p.get('symbol')}, Direction: {p.get('direction')}")

    except Exception as e:
        print(f"Error reading path: {e}")
