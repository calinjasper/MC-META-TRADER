# Python MT5 Indicator Development Guide

This guide shows you how to develop MT5 indicators in Python and send trading signals to the platform.

## Overview

You can develop custom trading indicators and strategies in Python using the MetaTrader5 Python package, then send signals to the trading platform via the signal routing system.

## Advantages of Python Indicators

1. **Flexibility**: Use any Python library (pandas, numpy, scipy, etc.)
2. **Easy Development**: Python's syntax is simpler than MQL5
3. **Rich Ecosystem**: Access to machine learning, data analysis, and more
4. **Integration**: Easy integration with external data sources and APIs
5. **Testing**: Easy to backtest and optimize strategies

## Setup

### 1. Install Required Packages

```bash
pip install MetaTrader5 pandas numpy requests
```

### 2. Connect to MT5

You can either:
- Use the default MT5 terminal (auto-detected)
- Specify login credentials

```python
import MetaTrader5 as mt5

# Auto-detect and connect
mt5.initialize()

# Or with credentials
mt5.initialize()
mt5.login(login=123456, password="password", server="Broker-Server")
```

## Basic Example

### Simple Indicator

```python
import MetaTrader5 as mt5
import pandas as pd
import requests

# Connect to MT5
mt5.initialize()

# Get rates
rates = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_M15, 0, 100)
df = pd.DataFrame(rates)

# Calculate simple moving average
df['sma_20'] = df['close'].rolling(window=20).mean()
df['sma_50'] = df['close'].rolling(window=50).mean()

# Generate signal
if df['sma_20'].iloc[-1] > df['sma_50'].iloc[-1]:
    signal = "BUY"
else:
    signal = "SELL"

# Send signal
requests.post("http://localhost:8080/signal", json={
    "symbol": "EURUSD",
    "action": signal,
    "quantity": 0.01
})
```

## Available Examples

### 1. `python_mt5_indicator.py`
Complete indicator with:
- RSI calculation
- MACD calculation
- EMA calculation
- Bollinger Bands
- Combined signal generation
- Automatic signal sending

**Usage:**
```python
from python_mt5_indicator import PythonMT5Indicator

indicator = PythonMT5Indicator("EURUSD")
indicator.connect()
indicator.run(quantity=0.01, check_interval=60)
```

### 2. `python_mt5_custom_strategy.py`
Object-oriented approach with:
- Base strategy class
- Moving Average Crossover strategy
- RSI strategy
- Easy to extend with your own strategies

**Usage:**
```python
from python_mt5_custom_strategy import MovingAverageCrossoverStrategy, StrategyRunner

strategy = MovingAverageCrossoverStrategy("EURUSD", fast_period=10, slow_period=20)
runner = StrategyRunner(strategy)
runner.connect()
runner.run_once()
```

## Creating Your Own Strategy

### Step 1: Create Strategy Class

```python
from python_mt5_custom_strategy import BaseStrategy
import pandas as pd

class MyCustomStrategy(BaseStrategy):
    def calculate_indicators(self, df):
        # Calculate your indicators
        return {
            'my_indicator': df['close'].rolling(20).mean()
        }
    
    def generate_signal(self, df, indicators):
        # Your signal logic
        if indicators['my_indicator'].iloc[-1] > df['close'].iloc[-1]:
            return "BUY"
        return None
    
    def calculate_position_size(self, df):
        return 0.01
    
    def calculate_sl_tp(self, df, signal):
        current_price = df['close'].iloc[-1]
        if signal == "BUY":
            return current_price * 0.99, current_price * 1.02
        else:
            return current_price * 1.01, current_price * 0.98
```

### Step 2: Use Your Strategy

```python
strategy = MyCustomStrategy("EURUSD")
runner = StrategyRunner(strategy)
runner.connect()
runner.run_once()
```

## Common Indicators

### RSI (Relative Strength Index)
```python
def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
```

### MACD
```python
def calculate_macd(df, fast=12, slow=26, signal=9):
    ema_fast = df['close'].ewm(span=fast).mean()
    ema_slow = df['close'].ewm(span=slow).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal).mean()
    return macd, signal_line
```

### Bollinger Bands
```python
def calculate_bollinger_bands(df, period=20, std_dev=2):
    sma = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    return {
        'upper': sma + (std * std_dev),
        'middle': sma,
        'lower': sma - (std * std_dev)
    }
```

## Running Strategies

### Option 1: One-Time Check
```python
runner = StrategyRunner(strategy)
runner.connect()
result = runner.run_once()
```

### Option 2: Continuous Monitoring
```python
import time

runner = StrategyRunner(strategy)
runner.connect()

while True:
    runner.run_once()
    time.sleep(60)  # Check every minute
```

### Option 3: Scheduled Execution
```python
import schedule

def check_signals():
    runner.run_once()

schedule.every(5).minutes.do(check_signals)

while True:
    schedule.run_pending()
    time.sleep(1)
```

## Tips

1. **Backtesting**: Test your strategies on historical data before live trading
2. **Risk Management**: Always calculate appropriate SL/TP
3. **Error Handling**: Handle connection errors and data issues
4. **Logging**: Log all signals and results for analysis
5. **Optimization**: Use optimization libraries to find best parameters

## Integration with Platform

The signal routing system automatically:
- Validates signals
- Applies risk management
- Executes orders through MT5
- Tracks signal history
- Provides monitoring UI

## Troubleshooting

### MT5 Connection Issues
- Ensure MT5 terminal is running
- Check login credentials
- Verify symbol names match MT5 format

### Signal Server Issues
- Ensure signal server is running (check platform UI)
- Verify server URL (default: http://localhost:8080)
- Check firewall settings

### Data Issues
- Ensure sufficient historical data is available
- Check timeframe compatibility
- Verify symbol is tradeable

## Next Steps

1. Start with simple strategies
2. Add more indicators gradually
3. Test thoroughly on demo accounts
4. Monitor performance
5. Optimize parameters
6. Scale up gradually

