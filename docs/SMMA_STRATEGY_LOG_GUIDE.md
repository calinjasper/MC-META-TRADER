# SMMA Strategy - Log Guide

This document explains what log messages you'll see when the SMMA strategy is running and when it will enter trades.

## Log Message Sequence

### 1. Strategy Initialization
When the strategy is enabled:
```
INFO - Strategy <strategy_name> enabled
```

### 2. Buy Signal Detection (Step 1 - Crossover)
When price crosses **above** the SMMA line (this is the signal candle, NOT the entry):
```
DEBUG - SMMAStrategy <strategy_name>: Buy Signal detected (crossover) - High=<high_value>, Low=<low_value>
```

**Note:** This is a DEBUG level log. You may need to enable DEBUG logging to see it. This indicates the strategy is **waiting** for entry.

### 3. Buy Entry (Step 2 - Actual Trade Trigger)
When price crosses **above the High** of the crossover candle (this is when the trade is triggered):
```
INFO - SMMAStrategy <strategy_name>: ✅ Buy Entry detected - Price crossed above High=<high_value>
INFO - Strategy <strategy_name> generated NEW BUY signal for <symbol> (was None)
```

**This is when the strategy will enter a BUY trade.**

### 4. Sell Signal Detection (Step 1 - Crossunder)
When price crosses **below** the SMMA line (this is the signal candle, NOT the entry):
```
DEBUG - SMMAStrategy <strategy_name>: Sell Signal detected (crossunder) - High_s=<high_value>, Low_s=<low_value>
```

**Note:** This is a DEBUG level log. This indicates the strategy is **waiting** for entry.

### 5. Sell Entry (Step 2 - Actual Trade Trigger)
When price crosses **below the Low** of the crossunder candle (this is when the trade is triggered):
```
INFO - SMMAStrategy <strategy_name>: ✅ Sell Entry detected - Price crossed below Low_s=<low_value>
INFO - Strategy <strategy_name> generated NEW SELL signal for <symbol> (was None)
```

**This is when the strategy will enter a SELL trade.**

## Direction Filtering Logs

### Long-Only Mode
If direction is set to "Long-only" and a Sell Entry is detected:
```
DEBUG - SMMAStrategy <strategy_name>: Sell Entry ignored (Long-only mode)
```

### Short-Only Mode
If direction is set to "Short-only" and a Buy Entry is detected:
```
DEBUG - SMMAStrategy <strategy_name>: Buy Entry ignored (Short-only mode)
```

## Reset Logs

### Buy Levels Reset
If price crosses below entry_low after a buy entry:
```
DEBUG - SMMAStrategy <strategy_name>: Buy levels reset - price crossed below entry_low
```

### Sell Levels Reset
If price crosses above entry_high_s after a sell entry:
```
DEBUG - SMMAStrategy <strategy_name>: Sell levels reset - price crossed above entry_high_s
```

## Important Notes

1. **DEBUG vs INFO Logs:**
   - `DEBUG` logs show signal detection (waiting for entry)
   - `INFO` logs show actual entry triggers (when trade will execute)

2. **Two-Step Process:**
   - **Step 1 (Signal):** Price crosses SMMA → Strategy detects signal, stores High/Low
   - **Step 2 (Entry):** Price crosses stored High/Low → Strategy triggers trade

3. **To See All Logs:**
   - Enable DEBUG logging level in your logging configuration
   - Check `logs/trading_platform.log` file

4. **Trade Execution:**
   - The strategy returns "BUY" or "SELL" from `generate_signal()`
   - The base strategy logs: `Strategy <name> generated NEW <signal> signal for <symbol>`
   - The signal router/execution layer will then process the trade

## Example Log Sequence for Buy Entry

```
DEBUG - SMMAStrategy MySMMA: Buy Signal detected (crossover) - High=1.0850, Low=1.0840
INFO  - SMMAStrategy MySMMA: ✅ Buy Entry detected - Price crossed above High=1.0850
INFO  - Strategy MySMMA generated NEW BUY signal for EURUSD (was None)
```

## Example Log Sequence for Sell Entry

```
DEBUG - SMMAStrategy MySMMA: Sell Signal detected (crossunder) - High_s=1.0850, Low_s=1.0840
INFO  - SMMAStrategy MySMMA: ✅ Sell Entry detected - Price crossed below Low_s=1.0840
INFO  - Strategy MySMMA generated NEW SELL signal for EURUSD (was None)
```
