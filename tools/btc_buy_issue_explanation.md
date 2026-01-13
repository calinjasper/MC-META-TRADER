# BTC_BUY Strategy Entry and Exit Analysis

## Summary
**BTC_BUY strategy NEVER successfully entered a trade.** All entry attempts failed with "Invalid stops" error.

## Entry Attempts (from logs around 12:31:19)

### Signal Generation
- **Time:** 12:31:19 - 12:31:21 (multiple attempts)
- **Strategy:** BTC_BUY
- **Symbol:** BTCUSDm
- **Signal:** BUY
- **Entry Condition:** ✅ **MET**
  - CHoCH event detected at price: 88594.74
  - Current price: 88908.99
  - Buy filter: `current_price crosses_above smc_choch_price`
  - Result: **Buy filter condition met!**

### Order Placement Attempts
**All attempts FAILED with the same error:**

```
Entry price: 88896.73 (ask)
Bid: 88878.73
Calculated SL: 88896.53
Calculated TP: 88896.73 (initial), then 88985.63 (adjusted)
Error: "Invalid stops - Invalid stop loss or take profit" (retcode=10016)
```

## Root Cause

### The Problem
The calculated **Stop Loss is too close to the entry price**:
- Entry price: **88896.73**
- Calculated SL: **88896.53**
- **Distance: Only 0.20 points** (88896.73 - 88896.53 = 0.20)

### Why This Fails
MT5 requires a **minimum distance** between entry price and stop loss, defined by the symbol's `trade_stops_level` property. For BTCUSDm, this minimum distance is likely much larger than 0.20 points.

**MT5 Error Code 10016** = "Invalid stops - Invalid stop loss or take profit"
- This occurs when SL/TP don't meet the broker's minimum distance requirements
- The SL of 0.20 points is too small for BTCUSDm

### Why SL is So Small
Looking at the calculation:
- The strategy likely has `sl_value: 0.0` or a very small value
- When `sl_value` is 0.0, the system may be using a default or fallback calculation
- The calculation results in only 0.20 points distance, which is insufficient

## Exit Analysis

**There is NO exit to analyze** because:
- The strategy **never successfully entered** a trade
- All order placement attempts were rejected by MT5
- No position was ever opened

## Evidence from Logs

### Entry Signal Generation (SUCCESS)
```
2026-01-02 12:31:19,096 - SMCStrategy BTC_BUY: Buy filter evaluation - result=True
2026-01-02 12:31:19,096 - SMCStrategy BTC_BUY: Buy filter condition met! 
  Price=88908.99000, CHoCH=88594.74
2026-01-02 12:31:19,097 - Strategy BTC_BUY: update() returned signal=BUY
2026-01-02 12:31:19,098 - Strategy BTC_BUY generated BUY signal for BTCUSDm
```

### Order Placement (FAILED)
```
2026-01-02 12:31:19,106 - Entry price for BUY = 88896.73000
2026-01-02 12:31:19,108 - Calculated SL=88896.53000, TP=88896.73000
2026-01-02 12:31:19,155 - place_order: Prepared order request: 
  symbol=BTCUSDm, type=0, volume=0.01, price=88896.73, 
  sl=88896.53, tp=88985.63
2026-01-02 12:31:19,157 - mt5.order_send() returned result with retcode=10016
2026-01-02 12:31:19,157 - Order failed: retcode=10016, comment=Invalid stops
2026-01-02 12:31:19,167 - Order placement failed for BTC_BUY. 
  Retcode: 10016, Error: Invalid stops - Invalid stop loss or take profit
```

## Solution

### Immediate Fix
1. **Check BTC_BUY strategy configuration** - verify `sl_value` setting
2. **Increase SL value** to ensure minimum distance is met
3. **Check symbol's `trade_stops_level`** to determine required minimum distance

### Recommended Actions
1. Open BTC_BUY strategy in Strategy Edit Dialog
2. Check the SL configuration:
   - If `sl_value: 0.0`, set it to a reasonable value (e.g., 50-100 points for BTC)
   - If `sl_type: "Price (Points)"`, ensure `sl_value` is large enough
3. Verify the calculated SL meets MT5's minimum distance requirement

### Code Issue
The SL/TP calculation in `calculate_strategy_sl_tp()` (lines 1987-2106 in `main_window.py`) does validate and adjust SL/TP for minimum distance (lines 2080-2105), but it seems the initial calculation is producing an invalid value that may not be caught properly.

## Conclusion

**BTC_BUY strategy:**
- ✅ **Entry condition:** Working correctly - generates BUY signals when CHoCH is crossed
- ❌ **Order placement:** Failing due to invalid SL (too close to entry price)
- ❌ **Trade entry:** Never successfully entered
- ❌ **Trade exit:** N/A (no position was ever opened)

The strategy is generating correct signals but cannot place orders due to invalid stop loss configuration.
