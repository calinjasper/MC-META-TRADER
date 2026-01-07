from datetime import datetime, timedelta
import re

log_path = r"c:\Users\Calin Jasper\Music\mc_meta\logs\trading_platform.log"
output_path = r"c:\Users\Calin Jasper\Music\mc_meta\recent_logs.txt"

now = datetime.now()
five_mins_ago = now - timedelta(minutes=5)

try:
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    recent = []
    for line in lines[-2000:]:
        # Extract time
        match = re.search(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if match:
            log_time = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
            if log_time > five_mins_ago:
                if "VWAP" in line: # Filter for VWAP strategy relevant logs
                    recent.append(line.strip())
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(recent))
        
    print(f"Filtered {len(recent)} lines to {output_path}")

except Exception as e:
    print(f"Error: {e}")
