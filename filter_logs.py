import re

log_path = r"c:\Users\Calin Jasper\Music\mc_meta\logs\trading_platform.log"
output_path = r"c:\Users\Calin Jasper\Music\mc_meta\filtered_logs.txt"

try:
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    relevant = []
    for line in lines[-2000:]: # Check last 2000 lines
        if "EMA" in line and ("signal" in line or "Executing" in line or "Order" in line):
            relevant.append(line.strip())
            
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(relevant))
        
    print(f"Filtered {len(relevant)} lines to {output_path}")

except Exception as e:
    print(f"Error: {e}")
