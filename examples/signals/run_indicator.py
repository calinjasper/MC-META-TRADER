"""
Simple Script to Run Python MT5 Indicator
Copy this file and modify for your needs
"""

import sys
import os

# Add parent directory to path to import examples
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from examples.signals.python_mt5_indicator import PythonMT5Indicator
import MetaTrader5 as mt5

def main():
    print("=" * 60)
    print("Python MT5 Indicator - Starting...")
    print("=" * 60)
    
    # ============================================
    # CONFIGURATION - Modify these settings
    # ============================================
    
    SYMBOL = "EURUSD"                    # Trading symbol
    TIMEFRAME = mt5.TIMEFRAME_M15        # Timeframe (M15, H1, etc.)
    QUANTITY = 0.01                      # Lot size
    CHECK_INTERVAL = 60                  # Check every N seconds
    SIGNAL_SERVER = "http://localhost:8080"  # Signal server URL
    
    # Optional: MT5 Login credentials (leave None to use default terminal)
    MT5_LOGIN = None      # e.g., 123456
    MT5_PASSWORD = None   # e.g., "password"
    MT5_SERVER = None    # e.g., "Broker-Server"
    
    # ============================================
    # Create and run indicator
    # ============================================
    
    # Create indicator instance
    indicator = PythonMT5Indicator(
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        signal_server_url=SIGNAL_SERVER
    )
    
    # Connect to MT5
    print(f"\nConnecting to MT5...")
    if MT5_LOGIN:
        connected = indicator.connect(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
    else:
        connected = indicator.connect()  # Use default terminal
    
    if not connected:
        print("Failed to connect to MT5. Please check:")
        print("1. MetaTrader 5 terminal is running")
        print("2. Login credentials are correct (if provided)")
        return
    
    print(f"✓ Connected to MT5")
    print(f"✓ Monitoring: {SYMBOL} on {TIMEFRAME}")
    print(f"✓ Signal Server: {SIGNAL_SERVER}")
    print(f"✓ Lot Size: {QUANTITY}")
    print(f"✓ Check Interval: {CHECK_INTERVAL} seconds")
    print("\n" + "=" * 60)
    print("Indicator is running. Press Ctrl+C to stop.")
    print("=" * 60 + "\n")
    
    # Run the indicator
    try:
        indicator.run(quantity=QUANTITY, check_interval=CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        indicator.disconnect()
        print("Disconnected from MT5.")

if __name__ == "__main__":
    main()

