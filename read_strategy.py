import json
import os

path = r"c:\Users\Calin Jasper\Music\mc_meta\strategies\VWAP_GOLD_1M.json"

try:
    with open(path, 'r') as f:
        content = f.read()
        print(content)
        # Try to parse it to ensure valid JSON
        data = json.loads(content)
        print("\n--- Parsed JSON ---")
        print(json.dumps(data, indent=2))
        
        print("\n--- Conditions ---")
        if 'buy_conditions' in data:
            for i, c in enumerate(data['buy_conditions']):
                print(f"Buy Condition {i+1}: Left={c.get('left_field')}, Op={c.get('operator')}, Right={c.get('right_field')}, EMA_Field={c.get('ema_field')}")
        
        if 'sell_conditions' in data:
            for i, c in enumerate(data['sell_conditions']):
                print(f"Sell Condition {i+1}: Left={c.get('left_field')}, Op={c.get('operator')}, Right={c.get('right_field')}, EMA_Field={c.get('ema_field')}")

except Exception as e:
    print(f"Error: {e}")
