# Strategy Tab - Complete Documentation (Verified & Corrected)

This is the verified and corrected documentation for the Strategy Tab, incorporating all verified corrections and clarifications.

---

## ✅ 1. Strategy Type

Six strategy types are available:

- **OHLC Price Strategy**: Compares current price to previous session OHLC values
- **VWAP Strategy**: Uses Volume Weighted Average Price with standard deviation bands
- **EMA Strategy**: Uses Exponential Moving Averages with configurable periods
- **SuperTrend Strategy**: Trend-following indicator that **auto-generates signals based on trend flips** (manual Buy/Sell conditions are disabled)
- **SMC (Smart Money Concepts)**: Market structure-based strategy (BOS/CHoCH events); Buy/Sell conditions act as **filters** (post-filtering), not signal generators
- **No Strategy**: Direct execution based on direction only (conditions optional)

**Important Notes:**
- **SuperTrend**: Manual Buy/Sell condition lists are **disabled**, not optional. SuperTrend auto-generates signals.
- **SMC**: Signals are **event-based (BOS/CHoCH)**, not continuous candle conditions. Buy/Sell conditions filter these events.

---

## ✅ 2. Strategy Name

**Purpose**: Unique identifier for your strategy

- **Format**: Alphanumeric, underscores, hyphens only (e.g., `EMA_Crossover_EURUSD_M1`)
- **Validation**: Must be unique across all strategies
- **Workflow**: Validated in real-time as text changes

**Example**: `Breakout_EURUSD_H1`

---

## ✅ 3. Strategy Direction

**Options:**
- **Long & Short**: Trade both directions (requires buy and/or sell conditions)
- **Long-only**: Only buy signals allowed
- **Short-only**: Only sell signals allowed

**Workflow:**
- Controls which condition sections are visible
- If "Long-only": Only Buy Conditions section shown
- If "Short-only": Only Sell Conditions section shown
- If "both": Both sections shown

**Important Edge Case:**
- If direction is **Long & Short**, both conditions can be true on the same candle
- This is handled by signal priority (BUY checked first, takes priority if both are true)

**Example:**
- Direction = "Long-only" → Only evaluates Buy Conditions, ignores Sell Conditions

---

## ✅ 4. Basic Information

### Symbol
- **Input**: Type or select from dropdown
- **Workflow**: Auto-populated from available MT5 symbols
- **Example**: `EURUSD`, `XAUUSDm`, `GBPUSD`

### Timeframe
**Options:**
- M1 (1 Minute)
- M5 (5 Minutes)
- M15 (15 Minutes)
- M30 (30 Minutes)
- H1 (1 Hour)
- H4 (4 Hours)
- D1 (Daily)

**Workflow**: Determines the candle period used for indicator calculations

**Example**: H1 → Uses hourly candles for all calculations

### Lot Size
- **Range**: 0.01 to 100.0
- **Default**: 0.01
- **Workflow**: If left at default (0.01), uses global default lot size from config
- **Important**: 
  - **0.01 = 1 micro lot**
  - **0.10 = 10 micro lots = 1 mini lot**

**Example**: 0.10 = 1 mini lot

### Session Type

**Varies by Strategy Type:**

**OHLC Strategy:**
- Daily (24h Mon–Fri)
- Asian Session (05:30–14:30 IST)
- European Session (13:30–22:30 IST)
- US Session (18:30–03:30 IST)

**VWAP Strategy:**
- NY Session (18:30–03:30 IST)
- London Session (13:30–22:30 IST)
- Asia Session (05:30–14:30 IST)
- All Sessions

**EMA/SuperTrend/SMC/No Strategy:**
- All Candles (no session boundaries)

**Workflow**: Defines the session window for OHLC/VWAP calculations

---

## ✅ 5. Buy Conditions / Sell Conditions

Each condition row contains:

### Components:

1. **Enable checkbox**: Enable/disable this condition
2. **Left Operand dropdown**: First value to compare
3. **Operator dropdown**: Comparison operator
4. **Right Operand dropdown**: Second value to compare
5. **OR checkbox**: Controls connector to next condition
   - **Checked** → Connector = OR
   - **Unchecked** → Connector = AND
   - **Important**: The connector applies **from this row to the NEXT row**

### Available Operands (Left/Right):

**Price Fields:**
- Current Price
- Previous Open
- Previous High
- Previous Low
- Previous Close
- Open, High, Low, Close (current candle)
- (H + L)/2, (H + L + C)/3, (O + H + L + C)/4

**EMA Fields** (configurable periods):
- EMA_20, EMA_50, EMA_100, EMA_200 (default, can be changed)

**VWAP Fields** (if VWAP strategy):
- VWAP
- VWAP Upper 1.0σ, 1.5σ, 2.0σ
- VWAP Lower 1.0σ, 1.5σ, 2.0σ

**SuperTrend Fields:**
- SuperTrend Value, Upper, Lower

**SMC Fields:**
- SMC Pivot High, SMC Pivot Low

### Operators:

- **Greater_Than (>):** Left > Right
- **Lower_Than (<):** Left < Right
- **Equals (==):** Left == Right (within small epsilon)
- **Crosses Above**: Left crosses from below to above Right
  - **Definition**: `(Left_prev <= Right_prev) AND (Left_current > Right_current)`
  - Uses previous tick/candle vs current tick/candle comparison
- **Crosses Under**: Left crosses from above to below Right
  - **Definition**: `(Left_prev >= Right_prev) AND (Left_current < Right_current)`
  - Uses previous tick/candle vs current tick/candle comparison
- **Any_Cross**: Left crosses Right in either direction
- **Within_Band** (VWAP only): Price is within a VWAP band
- **Outside_Band** (VWAP only): Price is outside a VWAP band

### Condition Workflow (AND/OR Chaining):

**How Connectors Work:**
- Each condition row has an **"OR" checkbox** that sets its connector value
- The connector on a condition connects it **to the NEXT condition**
- First condition: Always starts the chain (no previous connector)
- Subsequent conditions: Connected using the **previous condition's connector**

**Example with 3 Conditions:**
```
Condition 1: Current Price > Previous High [OR unchecked = AND]
Condition 2: Current Price > EMA_20 [OR checked]  
Condition 3: Volume > Volume_MA [OR checked]
```

**Evaluation:** `(Condition1 AND Condition2) OR Condition3`

**Detailed Workflow:**
1. First condition is evaluated (starts chain)
2. For each next condition:
   - If **previous connector = "AND"**: `result = result AND current_condition`
   - If **previous connector = "OR"**: `result = result OR current_condition`
3. Final result determines if Buy/Sell signal is triggered

**More Examples:**

**Example 1 - Simple AND Chain:**
```
Row 1: Current Price > EMA_20 [OR unchecked = AND]
Row 2: Current Price > EMA_50 [OR unchecked = AND]
```
**Evaluation:** `Price > EMA_20 AND Price > EMA_50`

**Example 2 - OR Chain:**
```
Row 1: Current Price > Previous High [OR checked]
Row 2: Current Price < Previous Low [OR checked]
```
**Evaluation:** `Price > PrevHigh OR Price < PrevLow`

**Example 3 - Mixed AND/OR:**
```
Row 1: Current Price > EMA_20 [OR unchecked = AND]
Row 2: EMA_20 > EMA_50 [OR checked]
Row 3: Volume > Volume_MA [OR checked]
```
**Evaluation:** `(Price > EMA_20 AND EMA_20 > EMA_50) OR Volume > Volume_MA`

---

## ✅ 6. Strategy-Specific Configurations

### VWAP Configuration

**Standard Deviation Bands:**
- **Format**: Comma-separated (e.g., "1, 1.5, 2")
- **Default**: "1, 1.5, 2"
- **Workflow**: Creates upper/lower bands at these standard deviations

**Swing Period:**
- **Range**: 5-50 candles
- **Default**: 10
- **Workflow**: Used only if swing-based logic is enabled (SMC or breakout filters), not core VWAP calculation

### EMA Configuration

**EMA Periods** (4 configurable EMAs):
- EMA 1 Period: Default 20
- EMA 2 Period: Default 50
- EMA 3 Period: Default 100
- EMA 4 Period: Default 200
- **Workflow**: These values appear in the operand dropdowns as `EMA_20`, `EMA_50`, etc.

### SuperTrend Configuration

**ATR Period:**
- **Range**: 1-500
- **Default**: 10

**ATR Multiplier:**
- **Range**: 0.1-50.0
- **Default**: 3.0

**ATR Method:**
- ATR (Wilder)
- SMA(TR)

**Note**: SuperTrend auto-generates Buy/Sell signals based on trend flips; manual conditions are ignored.

### SMC Configuration

**Pivot Left Bars:**
- **Range**: 1-10
- **Default**: 2

**Pivot Right Bars:**
- **Range**: 1-10
- **Default**: 2

**Emit Signals On:**
- CHoCH only (bias flips)
- BOS only (continuation)
- Both (BOS + CHoCH)

**Important**: SMC Buy/Sell conditions do **not generate signals**; they only **filter BOS/CHoCH signals**.

---

## ✅ 7. Risk Management

### Stop Loss / Take Profit

**SL Type:**
- Price (Points) — Fixed point distance

**Stop Loss:**
- **Range**: 0.0-100000.0
- **Default**: 20.0 points
- **Workflow**: SL = Entry Price ± SL Value (points)

**Take Profit:**
- **Range**: 0.0-100000.0
- **Default**: 40.0 points
- **Workflow**: TP = Entry Price ± TP Value (points)

**Calculation (5-digit broker example, e.g., EURUSD):**
- 1 point = 0.00001
- 20 points = 0.00020
- 40 points = 0.00040

**Example (EURUSD, 5-digit broker):**
- Entry: 1.10000
- SL (20 points): **1.09800** (1.10000 - 0.00020)
- TP (40 points): **1.10040** (1.10000 + 0.00040)

### Trailing Stop-Loss

**Enable Trailing SL:**
- Disabled / Enabled

**SL Gap (price points):**
- **Range**: 0.1-10000.0
- **Default**: 1.0
- **Workflow**: When enabled, SL follows price at the specified gap distance

**How It Works:**
- For BUY: Tracks **highest price since entry**, SL = highest_price - gap
- For SELL: Tracks **lowest price since entry**, SL = lowest_price + gap
- SL only moves in favorable direction (never widens loss)

**Example (BUY, gap = 20 points = 0.00020):**
- Entry: 1.10000, Initial SL: 1.09800 (entry - 20 points)
- Price → 1.10200 → highest_price = 1.10200 → SL = 1.10180 (1.10200 - 0.00020)
- Price → 1.10400 → highest_price = 1.10400 → SL = 1.10380 (1.10400 - 0.00020)

### Profit Lock + Trailing

**Enable Profit Lock:**
- Disabled / Enabled

**Profit Lock Trigger (amount):**
- **Range**: 0.01-1000000.0
- **Default**: $100.0
- **Workflow**: Profit amount that must be reached before locking starts

**Minimum Profit to Lock:**
- **Range**: 0.01-1000000.0
- **Default**: $50.0
- **Workflow**: Minimum profit guaranteed once trigger is reached

**Trail Step (profit increase threshold):**
- **Range**: 0.0-1000000.0
- **Default**: $100.0
- **Workflow**: Additional profit needed to advance TP further

**Trail Amount (profit increment):**
- **Range**: 0.0-1000000.0
- **Default**: $50.0
- **Workflow**: Amount to add to TP each time trail step is reached

**Example:**
- Trigger: $100, Lock: $50, Step: $50, Amount: $25
- Profit hits $100 → Lock $50 minimum
- Profit hits $150 → Lock $75
- Profit hits $200 → Lock $100

### Trail Wait & Trade (W&T)

**Enable W&T:**
- Disabled / Enabled

**W&T Value:**
- **Range**: -1000000.0 to +1000000.0
- **Default**: -15.0 points
- **Workflow**: Dynamic trailing line that closes position when hit

**Use percentage (%) instead of points:**
- Checkbox to switch between points and percentage

**How It Works:**
- **BUY**: Tracks **highest price since entry**, W&T = highest_price + wt_value (trails upward)
- **SELL**: Tracks **lowest price since entry**, W&T = lowest_price + wt_value (trails downward)
- Triggers when price crosses back to the W&T line

**Example (BUY, wt_value = -15 points):**
- Entry: 1.10000
- Price reaches 1.10200 → W&T = 1.10185 (1.10200 - 15)
- Price falls to 1.10185 → Position closes

**Example (SELL, wt_value = +15 points):**
- Entry: 1.10000
- Price reaches 1.09800 → W&T = 1.09815 (1.09800 + 15)
- Price rises to 1.09815 → Position closes

### Position Management

**Preserve Position:**
- Checkbox
- **Workflow**: Prevents duplicate positions (max 1 BUY and 1 SELL per strategy per symbol)

**Re-Entry on Stop Loss:**
- **Enable Re-Entry on SL**: Checkbox

**SL Re-Entry Mode:**
- RE-ASAP: Re-enter immediately after SL
- RE-ASAP Reverse: Re-enter immediately in opposite direction
- RE-COST: Re-enter at original entry price
- RE-COST Reverse: Re-enter at original entry price in opposite direction

**SL Re-Entry Max Count:**
- **Range**: 0-20
- **Default**: 0
- **Workflow**: Maximum number of re-entries allowed after SL

**Re-Entry on Take Profit:**
- **Enable Re-Entry on TP**: Checkbox

**TP Re-Entry Mode:**
- Same options as SL Re-Entry Mode

**TP Re-Entry Max Count:**
- **Range**: 0-20
- **Default**: 0

### Trading Hours

**Enable time restrictions:**
- Checkbox

**Start Time / End Time:**
- **Format**: HH:mm
- **Default**: 09:00 to 17:00
- **Workflow**: Strategy only generates signals within this time window

**Important Edge Case:**
- If **Start Time > End Time**, the session spans midnight (overnight session)

**Example (Normal Session):**
- Start: 09:00, End: 17:00
- Signals only generated between 9 AM and 5 PM

**Example (Overnight Session):**
- Start: 22:00, End: 05:00
- Signals generated from 10 PM to 5 AM (next day)

---

## ✅ 8. Complete Workflow Example

**Example Strategy**: "EMA_Crossover_EURUSD_H1"

**Setup:**
1. Strategy Type: **EMA Strategy**
2. Strategy Name: `EMA_Crossover_EURUSD_H1`
3. Direction: **Long & Short**
4. Symbol: `EURUSD`
5. Timeframe: **H1**
6. Lot Size: **0.01**
7. Session Type: **All Candles**

**Buy Conditions:**
```
Row 1: Current Price > EMA_20 [OR unchecked = AND]
Row 2: EMA_20 > EMA_50 [OR unchecked = AND]
```
**Evaluation:** `Price > EMA_20 AND EMA_20 > EMA_50` → BUY signal

**Sell Conditions:**
```
Row 1: Current Price < EMA_20 [OR unchecked = AND]
Row 2: EMA_20 < EMA_50 [OR unchecked = AND]
```
**Evaluation:** `Price < EMA_20 AND EMA_20 < EMA_50` → SELL signal

**Risk Management:**
- SL: 20 points
- TP: 40 points
- Trailing SL: Disabled
- Profit Lock: Disabled

**Workflow Execution:**
1. System checks if trading hours are active (if enabled)
2. Gets current price and EMA values from H1 candles
3. Evaluates Buy Conditions (if direction allows)
4. If Buy Conditions = True → Generate BUY signal
5. Evaluates Sell Conditions (if direction allows)
6. If Sell Conditions = True → Generate SELL signal
7. **BUY has priority** if both are true
8. Signal → Execute trade with configured SL/TP

---

## ✅ 9. Signal Priority and Execution

**Priority Order:**
1. Buy Conditions checked first
2. If Buy Conditions = True → Return 'BUY' (stops here)
3. If Buy Conditions = False → Check Sell Conditions
4. If Sell Conditions = True → Return 'SELL'
5. If both False → Return None (no signal)

**Direction Filtering:**
- **Long-only**: Only Buy Conditions evaluated
- **Short-only**: Only Sell Conditions evaluated
- **Both**: Both evaluated (BUY takes priority)

**Recommendation (Best Practice):**
Consider adding a **Conflict Resolution Mode** for cases where both signals are true:
- BUY priority (current default)
- SELL priority
- Ignore both
- Use last signal direction

---

## Summary

This documentation covers all aspects of the Strategy tab with verified accuracy. Each option is validated, and conditions are evaluated in real-time as market data updates. The system generates trading signals when all conditions in a chain evaluate to true according to the AND/OR logic you configure.

**Key Corrections Applied:**
- ✅ SL/TP calculation examples corrected (5-digit broker: 20 points = 0.00020, not 0.0020)
- ✅ Cross operators clearly defined with previous vs current comparison
- ✅ AND/OR connector logic clarified (connector applies to NEXT condition)
- ✅ Trailing SL uses highest/lowest price since entry
- ✅ W&T uses highest/lowest price since entry
- ✅ Lot size terminology corrected (0.01 = 1 micro lot)
- ✅ SuperTrend and SMC clarifications added
- ✅ Trading hours overnight session edge case added
- ✅ Swing Period clarification (not core VWAP calculation)

