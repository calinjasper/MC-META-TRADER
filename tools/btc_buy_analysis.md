# BTC_BUY Strategy Analysis

## Strategy Configuration

### Basic Settings
- **Name:** BTC_BUY
- **Symbol:** BTCUSDm
- **Type:** SMC (Smart Money Concepts)
- **Timeframe:** M15 (15 minutes)
- **Trade Direction:** Long only
- **Enabled:** Yes

### Entry Condition (Buy Filter)
```json
{
  "left_operand": "current_price",
  "operator": "crosses_above",
  "right_operand": "smc_choch_price"
}
```

**Condition:** `current_price crosses_above smc_choch_price`

**What this means:**
- The strategy enters a BUY trade when the current price crosses **above** the CHoCH (Change of Character) price
- CHoCH is detected when market structure changes (bullish to bearish or vice versa)

### SMC Settings
- **Pivot Left:** 2 bars
- **Pivot Right:** 2 bars
- **Emit On:** CHOCH (Change of Character events)

### Stop Loss & Take Profit Configuration
- **SL Type:** Price (Points)
- **SL Value:** 50.0 points
- **SL Enabled:** Yes
- **TP Value:** 100.0 points
- **TP Enabled:** Yes
- **Use Ratio:** No (using manual TP value)

**Expected SL/TP Calculation:**
- For BUY at entry price 88896.73:
  - SL should be: 88896.73 - (50.0 * point) = 88896.73 - 0.50 = **88896.23**
  - TP should be: 88896.73 + (100.0 * point) = 88896.73 + 1.00 = **88897.73**

### Advanced Risk Management
- **Trailing SL:** Enabled (gap: 40.0 points)
- **Profit Lock:** Enabled
  - Trigger: 50.0
  - Lock Value: 40.0
  - Trail Step: 50.0
  - Trail Amount: 40.0

## Current Market State (from logs)

### Latest Log Entry (12:38:43 - 12:39:02)
- **Current Price:** 88908.99
- **CHoCH Price:** 88594.74
- **Previous Price:** 88908.99

### Entry Condition Evaluation
**Condition:** `current_price crosses_above smc_choch_price`

**Logic Check:**
- For "crosses_above": `prev_price < right <= left`
- Values:
  - prev_price = 88908.99
  - right (CHoCH) = 88594.74
  - left (current) = 88908.99
- Check: `88908.99 < 88594.74 <= 88908.99`
- Result: **FALSE** (88908.99 is NOT less than 88594.74)

**Why it's not entering:**
- The current price (88908.99) is **already above** the CHoCH price (88594.74)
- For a "crosses_above" condition to trigger, the price must:
  1. Start **below** the CHoCH price (previous price < CHoCH)
  2. Then move **above** the CHoCH price (current price >= CHoCH)
- Since the price is already above, there's no "cross" happening

## When Will It Enter?

The strategy will enter a BUY trade when:

1. **A new CHoCH event occurs** at a price **above** the current price (88908.99)
2. **Price then drops below** that new CHoCH price
3. **Price then crosses back above** the CHoCH price

**Example Scenario:**
- New CHoCH detected at: 89000.00
- Price drops to: 88950.00 (below CHoCH)
- Price rises to: 89001.00 (crosses above CHoCH)
- **Result:** BUY signal generated ✅

## SL/TP Validity Issue

### Problem Identified
From earlier logs (12:31:19):
- Entry price: 88896.73
- **Calculated SL: 88896.53** (only 0.20 points below entry!)
- **Expected SL: 88896.23** (50 points below entry)

**The calculated SL is WRONG!**

### Root Cause
The SL calculation is producing 0.20 points instead of 50.0 points. This suggests:
1. The `sl_value` (50.0) might not be properly applied
2. There might be a calculation error in `calculate_strategy_sl_tp()`
3. The point size for BTCUSDm might be incorrectly interpreted

### MT5 Validation
- **Error:** "Invalid stops - Invalid stop loss or take profit" (retcode=10016)
- **Reason:** SL of 0.20 points is too close to entry price
- **MT5 Requirement:** SL must be at least `trade_stops_level * point` distance from entry

## Recommendations

### Fix Entry Condition
The "crosses_above" condition won't work when price is already above CHoCH. Consider:
- Change to `current_price > smc_choch_price` (simple comparison)
- OR wait for price to drop below CHoCH first, then cross back above

### Fix SL/TP Calculation
1. Verify `sl_value: 50.0` is being read correctly
2. Check point size calculation for BTCUSDm
3. Ensure SL calculation uses: `entry_price - (sl_value * point)`
4. Verify minimum distance validation is working

### Current Status
- ✅ Strategy configuration loaded
- ✅ Entry condition logic working (but not triggering due to market state)
- ❌ SL/TP calculation producing invalid values
- ❌ Orders failing due to invalid stops
