# BTC_SELL Strategy Analysis

## Strategy Configuration

### Basic Settings
- **Name:** BTC_SELL
- **Symbol:** BTCUSDm
- **Type:** SMC (Smart Money Concepts)
- **Timeframe:** M15 (15 minutes)
- **Trade Direction:** Short only
- **Enabled:** Yes

### Entry Condition (Sell Filter)
```json
{
  "left_operand": "current_price",
  "operator": "crosses_under",
  "right_operand": "smc_choch_price"
}
```

**Condition:** `current_price crosses_under smc_choch_price`

**What this means:**
- The strategy enters a SELL trade when the current price crosses **below** the CHoCH (Change of Character) price
- CHoCH is detected when market structure changes (bullish to bearish or vice versa)

### SMC Settings
- **Pivot Left:** 2 bars
- **Pivot Right:** 2 bars
- **Emit On:** CHOCH (Change of Character events)

### Stop Loss & Take Profit Configuration
- **SL Type:** Price (Points)
- **SL Value:** 30.0 points
- **SL Enabled:** Yes
- **TP Value:** 60.0 points
- **TP Enabled:** Yes
- **Use Ratio:** No (using manual TP value)

**Expected SL/TP Calculation:**
- For SELL at entry price 88849.87:
  - SL should be: 88849.87 + (30.0 * point) = 88849.87 + 0.30 = **88850.17**
  - TP should be: 88849.87 - (60.0 * point) = 88849.87 - 0.60 = **88849.27**

### Advanced Risk Management
- **Trailing SL:** Enabled (gap: 10.0 points)
- **Profit Lock:** Enabled
  - Trigger: 20.0
  - Lock Value: 10.0
  - Trail Step: 20.0
  - Trail Amount: 10.0

## Current Market State (from logs)

### Latest Log Entry (13:00:00 - 13:00:06)
- **Current Price:** 88790.53
- **CHoCH Price:** 88849.87
- **Previous Price:** 88790.53

### Entry Condition Evaluation
**Condition:** `current_price crosses_under smc_choch_price`

**Logic Check:**
- For "crosses_under": `prev_price > right >= left`
- Values:
  - prev_price = 88790.53
  - right (CHoCH) = 88849.87
  - left (current) = 88790.53
- Check: `88790.53 > 88849.87 >= 88790.53`
- Result: **FALSE** ❌ (88790.53 is NOT greater than 88849.87)

**Why it's not entering:**
- The current price (88790.53) is **already below** the CHoCH price (88849.87)
- For a "crosses_under" condition to trigger, the price must:
  1. Start **above** the CHoCH price (previous price > CHoCH)
  2. Then move **below** the CHoCH price (current price <= CHoCH)
- Since the price is already below, there's no "cross" happening

## When Will It Enter?

The strategy will enter a SELL trade when:

1. **A new CHoCH event occurs** at a price **below** the current price (88790.53)
2. **Price then rises above** that new CHoCH price
3. **Price then crosses back below** the CHoCH price

**Example Scenario:**
- New CHoCH detected at: 88800.00
- Price rises to: 88850.00 (above CHoCH)
- Price drops to: 88799.00 (crosses below CHoCH)
- **Result:** SELL signal generated ✅

## Alternative Scenario

If price moves up first:
- Current price: 88790.53
- Price rises to: 88850.00 (above CHoCH at 88849.87)
- Price then drops to: 88849.00 (crosses below CHoCH)
- **Result:** SELL signal generated ✅

## Summary

### Entry Condition
- ✅ **Configuration:** Correct
- ✅ **Logic:** Working correctly
- ❌ **Current State:** Not triggering (price already below CHoCH)
- ✅ **Will Enter:** When price crosses below a CHoCH event

### Current Status
- **Current Price:** 88790.53
- **CHoCH Price:** 88849.87
- **Price is 59.34 points BELOW CHoCH**
- **No cross possible** - price must be above CHoCH first, then cross below

### Recommendations

1. **Wait for Price to Rise Above CHoCH:**
   - Price needs to move above 88849.87 first
   - Then wait for it to cross back below

2. **Or Wait for New CHoCH Event:**
   - A new CHoCH event below current price
   - Price rises above it
   - Price crosses back below

3. **Consider Alternative Condition:**
   - If you want immediate entry when price is below CHoCH, change to:
     - `current_price < smc_choch_price` (simple comparison)
   - This would enter immediately since price (88790.53) < CHoCH (88849.87)
