# BUY Strategy - When Will It Enter Trade?

## Strategy Configuration

### Entry Condition (Buy Filter)
```json
{
  "left_operand": "current_price",
  "operator": "crosses_above",
  "right_operand": "smc_pivot_high"
}
```

**Condition:** `current_price crosses_above smc_pivot_high`

**What this means:**
- The strategy enters a BUY trade when the current price crosses **above** the active SMC pivot high
- Pivot high is the highest unbroken pivot point in the current market structure

### SMC Settings
- **Symbol:** USDJPYm
- **Timeframe:** M5 (5 minutes)
- **Pivot Left:** 2 bars
- **Pivot Right:** 2 bars
- **Emit On:** NONE (tracks pivots, not CHoCH events)

### Risk Management
- **Stop Loss:** 25.0 points
- **Take Profit:** 50.0 points
- **Trailing SL:** Disabled
- **Trade Direction:** Long only

## Current Market State (from logs - 14:04:05 - 14:04:07)

### Latest Log Entry
- **Current Price:** 156.979
- **Active Pivot High:** 156.962
- **Active Pivot Low:** 156.913
- **Previous Price:** 156.979

### Entry Condition Evaluation
**Condition:** `current_price crosses_above smc_pivot_high`

**Logic Check:**
- For "crosses_above": `prev_price < right <= left`
- Values:
  - prev_price = 156.979
  - right (pivot high) = 156.962
  - left (current) = 156.979
- Check: `156.979 < 156.962 <= 156.979`
- Result: **FALSE** ❌ (156.979 is NOT less than 156.962)

**Why it's not entering:**
- The current price (156.979) is **already above** the pivot high (156.962)
- For a "crosses_above" condition to trigger, the price must:
  1. Start **below** the pivot high (previous price < pivot high)
  2. Then move **above** the pivot high (current price >= pivot high)
- Since the price is already above, there's no "cross" happening

## When Will It Enter?

The strategy will enter a BUY trade when:

### Scenario 1: Price Drops Below Pivot High, Then Crosses Back Above
1. **Price drops below pivot high** (below 156.962)
   - Example: Price drops to 156.950
2. **Price then crosses back above pivot high** (above 156.962)
   - Example: Price rises to 156.965
   - **Result:** BUY signal generated ✅

**Example:**
- Current: 156.979 (above pivot high 156.962)
- Price drops to: 156.950 (below pivot high)
- Price rises to: 156.965 (crosses above pivot high)
- **Result:** BUY signal generated ✅

### Scenario 2: New Higher Pivot High Forms, Price Drops Below It, Then Crosses Above
1. **A new higher pivot high forms** (e.g., 157.000)
2. **Price drops below** that new pivot high (e.g., 156.980)
3. **Price crosses back above** the pivot high (e.g., 157.005)
   - **Result:** BUY signal generated ✅

## Current Status

- **Current Price:** 156.979
- **Active Pivot High:** 156.962
- **Price is 0.017 points ABOVE pivot high** (156.979 - 156.962 = 0.017)
- **No cross possible** - price must be below pivot high first, then cross above

## Price Difference Analysis

- **Current Price:** 156.979
- **Pivot High:** 156.962
- **Difference:** +0.017 points (price is above)

For entry to occur:
- Price needs to drop below 156.962
- Then price needs to cross back above 156.962
- This will trigger the "crosses_above" condition

## Summary

### Entry Condition
- ✅ **Configuration:** Correct
- ✅ **Logic:** Working correctly
- ❌ **Current State:** Not triggering (price already above pivot high)
- ✅ **Will Enter:** When price crosses above pivot high from below

### What Needs to Happen

**For immediate entry possibility:**
1. Price needs to drop below 156.962 (pivot high)
2. Then price needs to cross back above 156.962
3. This will trigger the "crosses_above" condition

**Current situation:**
- Price is slightly above pivot high (0.017 points)
- Strategy is waiting for price to drop first, then cross back up
- This is the correct behavior for a "crosses_above" condition

### Recommendation

If you want immediate entry when price is above pivot high, change the condition to:
- `current_price > smc_pivot_high` (simple comparison)
- This would enter immediately since 156.979 > 156.962

But the current "crosses_above" condition is correct and will trigger when price crosses above the pivot high from below.

### Visual Representation

```
Price Chart:
157.000 |                    ════════════════════ Current: 156.979
        |                   ╱
156.980 |                  ╱
        |                 ╱
156.970 |                ╱
        |               ╱
156.962 |═══════════════ Pivot High (Entry Trigger Level)
        |              ╱
156.950 |             ╱
        |            ╱
156.913 |═══════════ Pivot Low
        |
```

**Entry will occur when:**
- Price drops below 156.962
- Then crosses back above 156.962 ✅
