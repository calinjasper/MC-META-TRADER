# BTC_SMC Strategy Entry and Exit Issue - Explanation

## Problem Summary
BTC_SMC strategy entered a trade but the trailing stop loss is failing to update, causing repeated errors. The position may have exited quickly due to this issue.

## Root Cause Analysis

### From Log Analysis (2026-01-02 12:07:27 onwards)

**Entry Details:**
- **Position Ticket:** 1058929896
- **Symbol:** BTCUSDm
- **Type:** BUY
- **Entry Price:** 88875.13
- **Initial SL:** 88786.25 (but requested was 88875.13 - mismatch warning)
- **TP:** 88964.01
- **Trailing SL Gap:** 5.0 points
- **Trailing SL Enabled:** Yes

### The Critical Issue

**Repeated Error in Logs:**
```
Failed to modify position 1058929896: SL must be at least 0.00 below bid 88853.92/88856.89/88858.59
```

**What's Happening:**
1. Trailing SL calculates: `new_sl = highest_price - sl_gap`
2. When price moves up (e.g., to 88876.59), trailing SL tries to move SL to 88871.59
3. **BUT** current bid is around 88856-88858
4. For BUY positions, MT5 requires: **SL must be BELOW the bid price**
5. The trailing SL (88871.59) is **ABOVE** the bid (88856-88858)
6. MT5 rejects the modification with error: "SL must be at least 0.00 below bid"

### Why This Happens

**Trailing SL Logic:**
- Tracks highest price: 88876.59
- Calculates new SL: 88876.59 - 5.0 = 88871.59
- Tries to set SL to 88871.59

**MT5 Requirement:**
- For BUY positions: SL must be **below** current bid
- Current bid: ~88856-88858
- Required SL: Must be < 88856-88858
- Calculated SL: 88871.59 (INVALID - above bid)

**The Problem:**
The trailing SL calculation doesn't account for MT5's requirement that SL must be below bid for BUY positions. It calculates based on highest price seen, but doesn't validate against current bid.

### Why Position May Have Exited

If the position exited quickly, it could be because:

1. **Price Dropped Below Original SL:**
   - Original SL was 88786.25
   - If price dropped below this, MT5 would close the position

2. **Trailing SL Trigger Logic:**
   - The trailing SL checks: `current_price <= stop_loss`
   - If price dropped to trigger the trailing SL (even though it couldn't be set), the position might close

3. **SL/TP Mismatch at Entry:**
   - Logs show: "SL mismatch: requested 88875.13000, actual 88786.25000"
   - This suggests the SL calculation had issues from the start

## The Bug

**Location:** `src/trading/trade_monitor.py` - `update_advanced_risk_management()`

**Issue:** When updating trailing SL, the code doesn't validate that the new SL is:
1. Below current bid (for BUY positions)
2. Above current ask (for SELL positions)
3. Respects MT5's `trade_stops_level` minimum distance

**Current Code Flow:**
```python
new_sl = trailing_sl.update_price(current_price)  # Calculates: highest_price - gap
if new_sl != current_sl:
    updates['new_sl'] = new_sl  # Tries to set without validation
```

**What Should Happen:**
```python
new_sl = trailing_sl.update_price(current_price)
# Validate new_sl is valid for MT5
if pos_type == 0:  # BUY
    if new_sl >= current_bid:  # Invalid!
        # Adjust: new_sl = current_bid - min_distance
        new_sl = current_bid - (trade_stops_level * point)
```

## Solution

The trailing SL update logic needs to:
1. Get current bid/ask price
2. Validate new SL is on correct side (below bid for BUY, above ask for SELL)
3. Respect `trade_stops_level` minimum distance
4. Only update if new SL is valid and different from current

## Impact

- **Immediate:** Trailing SL cannot update, position loses protection
- **Long-term:** If price reverses, position may hit original SL instead of trailing SL
- **Performance:** Repeated failed modification attempts waste resources

## Recommendation

Fix the trailing SL update logic in `src/trading/trade_monitor.py` to validate SL against current bid/ask and MT5's minimum distance requirements before attempting to modify the position.
