import json

path = r"c:\Users\Calin Jasper\Music\mc_meta\strategies\VWAP_GOLD_1M.json"

try:
    with open(path, 'r') as f:
        data = json.load(f)
        
    print(f"Strategy: {data.get('name')}")
    
    print("\n--- BUY CONDITIONS ---")
    if 'buy_conditions' in data:
        for c in data['buy_conditions']:
            print(f"{c.get('left_field', 'Price')} {c.get('operator')} {c.get('right_field')} (EMA Field: {c.get('ema_field')})")
            
    print("\n--- SELL CONDITIONS ---")
    if 'sell_conditions' in data:
        for c in data['sell_conditions']:
            print(f"{c.get('left_field', 'Price')} {c.get('operator')} {c.get('right_field')} (EMA Field: {c.get('ema_field')})")

except Exception as e:
    print(f"Error: {e}")
