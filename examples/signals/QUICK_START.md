# Quick Start: Running Python MT5 Indicators with Your Platform

## Step-by-Step Guide

### Step 1: Start Your Trading Platform

1. Open your trading platform application
2. Connect to MT5 (if not already connected)
3. The **Signal Server** will start automatically on port 8080
4. Go to the **"Signals"** tab to verify the server is running
   - Status should show "Running"
   - Port should show 8080

### Step 2: Install Python Dependencies

Open a terminal/command prompt and run:

```bash
pip install MetaTrader5 pandas numpy requests
```

### Step 3: Choose Your Approach

You have two options:

#### Option A: Use the Complete Indicator (Recommended for Beginners)

This runs automatically and checks for signals periodically.

#### Option B: Create Your Own Custom Strategy

This gives you full control over the strategy logic.

---

## Option A: Using the Complete Indicator

### Step 1: Navigate to Examples Folder

```bash
cd examples/signals
```

### Step 2: Run the Indicator

```bash
python python_mt5_indicator.py
```

**What it does:**
- Connects to MT5
- Monitors EURUSD on M15 timeframe
- Calculates RSI, MACD, and EMA indicators
- Generates BUY/SELL signals when conditions are met
- Automatically sends signals to your platform
- Checks every 60 seconds

### Step 3: Customize (Optional)

Edit `python_mt5_indicator.py` to change:

```python
# Change symbol
indicator = PythonMT5Indicator("GBPUSD")  # Instead of EURUSD

# Change timeframe
indicator = PythonMT5Indicator("EURUSD", timeframe=mt5.TIMEFRAME_H1)  # H1 instead of M15

# Change check interval (in seconds)
indicator.run(quantity=0.01, check_interval=30)  # Check every 30 seconds
```

### Step 4: Monitor in Platform

1. Go to the **"Signals"** tab in your platform
2. Watch the **Signal History** table for incoming signals
3. Check the **Execution History** to see if orders were placed
4. Go to **"Strategies"** tab to see open positions

---

## Option B: Creating Your Own Strategy

### Step 1: Create Your Strategy File

Create a new file `my_strategy.py`:

```python
from python_mt5_custom_strategy import BaseStrategy, StrategyRunner
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

class MyStrategy(BaseStrategy):
    def __init__(self, symbol: str):
        super().__init__(symbol, timeframe=mt5.TIMEFRAME_M15)
    
    def calculate_indicators(self, df):
        # Calculate your indicators here
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['rsi'] = self.calculate_rsi(df, 14)
        
        return {
            'sma_20': df['sma_20'],
            'sma_50': df['sma_50'],
            'rsi': df['rsi']
        }
    
    def calculate_rsi(self, df, period=14):
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def generate_signal(self, df, indicators):
        # Your signal logic here
        sma_20 = indicators['sma_20']
        sma_50 = indicators['sma_50']
        rsi = indicators['rsi']
        
        # BUY: SMA crossover + RSI > 50
        if (sma_20.iloc[-1] > sma_50.iloc[-1] and 
            sma_20.iloc[-2] <= sma_50.iloc[-2] and
            rsi.iloc[-1] > 50):
            return "BUY"
        
        # SELL: SMA crossunder + RSI < 50
        if (sma_20.iloc[-1] < sma_50.iloc[-1] and 
            sma_20.iloc[-2] >= sma_50.iloc[-2] and
            rsi.iloc[-1] < 50):
            return "SELL"
        
        return None
    
    def calculate_position_size(self, df):
        # Fixed lot size
        return 0.01
    
    def calculate_sl_tp(self, df, signal):
        # Calculate ATR for SL/TP
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14).mean().iloc[-1]
        
        current_price = df['close'].iloc[-1]
        
        if signal == "BUY":
            sl = current_price - (atr * 2)
            tp = current_price + (atr * 4)  # 1:2 risk-reward
        else:
            sl = current_price + (atr * 2)
            tp = current_price - (atr * 4)
        
        return sl, tp

# Run the strategy
if __name__ == "__main__":
    strategy = MyStrategy("EURUSD")
    runner = StrategyRunner(strategy, signal_server_url="http://localhost:8080")
    
    # Connect to MT5
    runner.connect()  # Uses default MT5 terminal
    
    # Run continuously
    import time
    while True:
        result = runner.run_once()
        if result:
            print(f"Signal sent: {result['signal']}")
        time.sleep(60)  # Check every minute
```

### Step 2: Run Your Strategy

```bash
python my_strategy.py
```

---

## Running Multiple Strategies

You can run multiple strategies simultaneously:

### Terminal 1:
```bash
python python_mt5_indicator.py
```

### Terminal 2:
```bash
python my_strategy.py
```

Both will send signals to the same platform, and you can monitor all of them in the **"Signals"** tab.

---

## Testing Your Strategy

### Step 1: Test on Demo Account First

1. Make sure your platform is connected to a demo MT5 account
2. Run your Python indicator
3. Monitor signals in the platform
4. Check if orders are being placed correctly

### Step 2: Verify Signal Reception

1. Go to **"Signals"** tab
2. Check **Signal History** table
3. Verify signals are appearing with correct symbol, action, and parameters

### Step 3: Verify Order Execution

1. Go to **"Strategies"** tab
2. Check **Positions** table
3. Verify orders are being placed with correct SL/TP

---

## Common Customizations

### Change Symbol
```python
indicator = PythonMT5Indicator("GBPUSD")  # or "USDJPY", "AUDUSD", etc.
```

### Change Timeframe
```python
# Available timeframes:
# mt5.TIMEFRAME_M1, M5, M15, M30, H1, H4, D1, W1, MN1
indicator = PythonMT5Indicator("EURUSD", timeframe=mt5.TIMEFRAME_H1)
```

### Change Check Frequency
```python
indicator.run(quantity=0.01, check_interval=30)  # Check every 30 seconds
```

### Change Lot Size
```python
indicator.run(quantity=0.1, check_interval=60)  # 0.1 lots instead of 0.01
```

### Use MT5 Credentials
```python
indicator.connect(login=123456, password="your_password", server="Broker-Server")
```

---

## Troubleshooting

### Problem: "MT5 initialization failed"
**Solution:** Make sure MetaTrader 5 terminal is running

### Problem: "Signal server not responding"
**Solution:** 
1. Check that your platform is running
2. Go to "Signals" tab and verify server status is "Running"
3. Check the port (default: 8080)

### Problem: "No signals being generated"
**Solution:**
1. Check that you have enough historical data (need at least 50-100 bars)
2. Verify your signal conditions are being met
3. Add print statements to debug:
   ```python
   signal = indicator.generate_signal(df)
   print(f"Signal: {signal}, RSI: {rsi.iloc[-1]}")
   ```

### Problem: "Orders not being placed"
**Solution:**
1. Check MT5 connection in your platform
2. Verify account has sufficient margin
3. Check symbol is tradeable
4. Look at Execution History in Signals tab for error messages

---

## Best Practices

1. **Start Small**: Test with 0.01 lots first
2. **Use Demo Account**: Always test on demo before live
3. **Monitor Closely**: Watch the Signals tab when first running
4. **Set Appropriate SL/TP**: Don't trade without stop loss
5. **Log Everything**: Keep track of what signals were generated
6. **Backtest First**: Test your strategy logic on historical data

---

## Next Steps

1. Start with the simple example (`python_mt5_indicator.py`)
2. Monitor signals in your platform
3. Once comfortable, create your own strategy
4. Test thoroughly on demo account
5. Gradually increase position size
6. Monitor performance and optimize

---

## Need Help?

- Check the **Signals** tab in your platform for signal history
- Check the logs in `logs/trading_platform.log`
- Review the examples in `examples/signals/` folder
- Read `README_PYTHON_MT5.md` for detailed documentation

