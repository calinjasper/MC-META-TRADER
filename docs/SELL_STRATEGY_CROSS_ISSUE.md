# SELL Strategy Cross Detection Issue

## Problem

The SELL strategy with condition `current_price crosses_under smc_pivot_low` is not entering trades even when:
- A pivot low exists (e.g., 156.677)
- Price has crossed below the pivot low

## Root Causes

### 1. Pivot Confirmation Timing

**Issue:** A pivot needs `pivot_right` bars (2 bars) AFTER it to be confirmed.

**Example:**
- Pivot low forms at bar N (price 156.677)
- Pivot is confirmed at bar N+2
- If price crosses below at bar N+1, the pivot isn't confirmed yet
- Strategy can't use an unconfirmed pivot

**Solution:** The strategy needs to wait for pivot confirmation before using it in conditions.

### 2. Previous Price Tracking

**Issue:** The `crosses_under` condition requires:
```
prev_price > pivot_low >= current_price
```

**Problem:** If `_prev_filter_price` is not set correctly, the cross won't be detected.

**Check:** Ensure `_prev_filter_price` is being updated on each `generate_signal()` call.

### 3. Strategy Update Cycle

**Issue:** The strategy might not be receiving updates frequently enough to catch the cross.

**Solution:** Ensure the strategy is being called on every new candle/price update.

## Current Strategy Configuration

```json
{
  "name": "SELL",
  "symbol": "USDJPYm",
  "timeframe": 5,
  "pivot_left": 2,
  "pivot_right": 2,
  "emit_on": "NONE",
  "sell_filters": [{
    "enabled": true,
    "left_operand": "current_price",
    "operator": "crosses_under",
    "right_operand": "smc_pivot_low"
  }]
}
```

## Debugging Steps

1. **Check if pivots are being detected:**
   - Verify `strategy.all_pivot_lows` has entries
   - Check `strategy.active_pivot_low_price` is set

2. **Check previous price tracking:**
   - Verify `strategy._prev_filter_price` is being updated
   - Check if it's None (would cause cross detection to fail)

3. **Check timing:**
   - Verify the pivot was confirmed BEFORE the cross happened
   - If cross happened before confirmation, that's the issue

4. **Check signal generation:**
   - Add logging to see when `generate_signal()` is called
   - Check if candles are being fetched correctly

## Potential Solutions

### Solution 1: Use Unconfirmed Pivots (Not Recommended)

Allow the strategy to use pivots that aren't fully confirmed yet. This could lead to false signals.

### Solution 2: Change Entry Condition

Instead of `crosses_under`, use a simple comparison:
```json
{
  "operator": "<",
  "right_operand": "smc_pivot_low"
}
```

This will enter when price is below pivot, regardless of cross timing.

### Solution 3: Ensure Proper Update Cycle

Make sure the strategy is updated on every new candle, not just periodically.

### Solution 4: Add Previous Price Fallback

If `_prev_filter_price` is None, use the previous candle's close price:
```python
prev_price = self._prev_filter_price if self._prev_filter_price is not None else closes[-2]
```

## Recommended Fix

The most likely issue is that the pivot wasn't confirmed when the cross happened. The strategy should:

1. Wait for pivot confirmation (2 bars after pivot formation)
2. Track previous price correctly
3. Detect cross on the next candle after pivot is confirmed

**Action Items:**
1. Add logging to track when pivots are confirmed vs when crosses happen
2. Ensure `_prev_filter_price` is always set
3. Consider using a simpler condition (`<` instead of `crosses_under`) if timing is critical
