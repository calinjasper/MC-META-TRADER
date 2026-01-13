"""
Force reload of strategies to apply latest code changes
This will reload strategies and reinitialize their state
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("=" * 80)
print("Strategy Reload Instructions")
print("=" * 80)
print("\nTo apply the latest SMMA strategy fixes, you need to:")
print("\n1. Close the trading platform application completely")
print("2. Restart the trading platform")
print("3. The strategies will automatically reload with the new code")
print("\nOR")
print("\nIf the platform is running:")
print("1. Go to Strategy Panel")
print("2. Remove the strategies (XA_BUY, BTC_SELL)")
print("3. Re-add them from the Strategy Builder or load from saved files")
print("\nThe new code includes:")
print("- Historical state initialization (processes past candles)")
print("- Missed cross detection (triggers entry if price already past entry level)")
print("=" * 80)
