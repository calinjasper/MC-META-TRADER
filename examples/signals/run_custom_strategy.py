"""
Simple Script to Run Custom Strategy
Copy this file and modify for your needs
"""

import sys
import os

# Add parent directory to path to import examples
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from examples.signals.python_mt5_custom_strategy import MovingAverageCrossoverStrategy, RSIStrategy, StrategyRunner
import MetaTrader5 as mt5
import time

def main():
    print("=" * 60)
    print("Python MT5 Custom Strategy - Starting...")
    print("=" * 60)
    
    # ============================================
    # CONFIGURATION - Modify these settings
    # ============================================
    
    SYMBOL = "EURUSD"                    # Trading symbol
    TIMEFRAME = mt5.TIMEFRAME_M15        # Timeframe
    CHECK_INTERVAL = 60                  # Check every N seconds
    SIGNAL_SERVER = "http://localhost:8080"
    
    # Choose strategy type:
    # "MA_CROSSOVER" - Moving Average Crossover
    # "RSI" - RSI Mean Reversion
    STRATEGY_TYPE = "MA_CROSSOVER"
    
    # Strategy parameters
    MA_FAST_PERIOD = 10
    MA_SLOW_PERIOD = 20
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    
    # Optional: MT5 Login credentials
    MT5_LOGIN = None
    MT5_PASSWORD = None
    MT5_SERVER = None
    
    # ============================================
    # Create strategy
    # ============================================
    
    if STRATEGY_TYPE == "MA_CROSSOVER":
        strategy = MovingAverageCrossoverStrategy(
            symbol=SYMBOL,
            fast_period=MA_FAST_PERIOD,
            slow_period=MA_SLOW_PERIOD,
            timeframe=TIMEFRAME
        )
        print(f"Strategy: Moving Average Crossover ({MA_FAST_PERIOD}/{MA_SLOW_PERIOD})")
    elif STRATEGY_TYPE == "RSI":
        strategy = RSIStrategy(
            symbol=SYMBOL,
            rsi_period=RSI_PERIOD,
            oversold=RSI_OVERSOLD,
            overbought=RSI_OVERBOUGHT,
            timeframe=TIMEFRAME
        )
        print(f"Strategy: RSI Mean Reversion ({RSI_OVERSOLD}/{RSI_OVERBOUGHT})")
    else:
        print(f"Unknown strategy type: {STRATEGY_TYPE}")
        return
    
    # Create runner
    runner = StrategyRunner(strategy, signal_server_url=SIGNAL_SERVER)
    
    # Connect to MT5
    print(f"\nConnecting to MT5...")
    if MT5_LOGIN:
        connected = runner.connect(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
    else:
        connected = runner.connect()
    
    if not connected:
        print("Failed to connect to MT5.")
        return
    
    print(f"✓ Connected to MT5")
    print(f"✓ Monitoring: {SYMBOL} on {TIMEFRAME}")
    print(f"✓ Signal Server: {SIGNAL_SERVER}")
    print(f"✓ Check Interval: {CHECK_INTERVAL} seconds")
    print("\n" + "=" * 60)
    print("Strategy is running. Press Ctrl+C to stop.")
    print("=" * 60 + "\n")
    
    # Run strategy in loop
    try:
        while True:
            result = runner.run_once()
            if result:
                print(f"\n[{time.strftime('%H:%M:%S')}] Signal: {result['signal']}")
                print(f"  Quantity: {result['quantity']}")
                print(f"  SL: {result['sl']:.5f}, TP: {result['tp']:.5f}")
                if result['result'].get('success'):
                    print(f"  ✓ {result['result'].get('message')}")
                else:
                    print(f"  ✗ {result['result'].get('error')}")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] No signal")
            
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

