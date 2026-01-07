# Strategy Tab - Professional Documentation
## Complete Reference Guide with Implementation Details

**Document Version:** 2.0  
**Last Updated:** December 2025  
**Status:** Production-Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Strategy Types](#strategy-types)
3. [Strategy Configuration](#strategy-configuration)
4. [Condition Logic System](#condition-logic-system)
5. [Strategy-Specific Parameters](#strategy-specific-parameters)
6. [Risk Management](#risk-management)
7. [Advanced Features](#advanced-features)
8. [Workflow Examples](#workflow-examples)
9. [Troubleshooting Guide](#troubleshooting-guide)

---

## Overview

### Purpose
The Strategy Tab provides a comprehensive interface for creating, configuring, and managing automated trading strategies. It supports multiple strategy types with customizable entry/exit conditions, risk management parameters, and position management rules.

### Core Principles
- **Signal Generation**: Strategies generate BUY/SELL signals based on market conditions
- **Rule-Based Execution**: All trades follow predefined logical conditions
- **Risk Control**: Multiple layers of risk management and position protection
- **Flexibility**: Supports various trading styles from scalping to swing trading

### System Architecture
```
Market Data → Strategy Evaluation → Signal Generation → Risk Checks → Order Execution
     ↓              ↓                      ↓               ↓              ↓
  Price/Vol    Conditions Met?        BUY/SELL       SL/TP Set      Position Open
  Indicators   AND/OR Logic           Priority       Trailing       Monitoring
```

---

## Strategy Types

### 1. OHLC Price Strategy

**Description**: Compares current price action against previous session's Open, High, Low, Close values to identify breakouts, reversals, or continuation patterns.

**Use Cases:**
- Breakout trading above/below previous high/low
- Gap trading strategies
- Session open price reversals
- Support/resistance based on OHLC levels

**Available Fields:**
- Previous Open, Previous High, Previous Low, Previous Close
- Current Open, High, Low, Close
- Derived values: (H+L)/2, (H+L+C)/3, (O+H+L+C)/4

**Example Strategy:**
- **Breakout Long**: Current Price > Previous High AND Close > Open
- **Reversal Short**: Current Price < Previous Low AND Close < (H+L)/2

**Session Dependency**: Requires defined session (Daily, Asian, European, US) to calculate OHLC reference values

---

### 2. VWAP Strategy

**Description**: Volume Weighted Average Price strategy using standard deviation bands to identify value areas and potential reversals or trend continuations.

**Mathematical Foundation:**
```
VWAP = Σ(Price × Volume) / Σ(Volume)
Standard Deviation = √[Σ(Price - VWAP)² × Volume / Σ(Volume)]
Upper Band = VWAP + (σ × Multiplier)
Lower Band = VWAP - (σ × Multiplier)
```

**Use Cases:**
- Mean reversion at extreme bands (±2σ)
- Trend following when price stays above/below VWAP
- Institution price level identification
- Intraday value area trading

**Available Fields:**
- VWAP (base line)
- Upper Bands: +1.0σ, +1.5σ, +2.0σ
- Lower Bands: -1.0σ, -1.5σ, -2.0σ

**Special Operators:**
- **Within_Band**: Price is between specified band limits
- **Outside_Band**: Price has exceeded band limits

**Example Strategy:**
- **Mean Reversion Long**: Price crosses below VWAP -2.0σ AND Volume > Average Volume
- **Trend Following Short**: Price < VWAP AND Price crosses under VWAP -1.0σ

**Configuration Parameters:**
- **Standard Deviation Bands**: Comma-separated multipliers (default: "1, 1.5, 2")
- **Swing Period**: 5-50 candles (default: 10) - used for advanced filtering only
- **Session Type**: NY Session, London Session, Asia Session, or All Sessions

**Important Notes:**
- VWAP resets at the beginning of each session
- Higher timeframes (H4, D1) may show less VWAP sensitivity
- Volume data quality affects VWAP accuracy

---

### 3. EMA Strategy

**Description**: Exponential Moving Average strategy using multiple EMAs to identify trend direction, momentum, and potential entry points through crossovers and price relationships.

**Mathematical Foundation:**
```
EMA = (Price × Multiplier) + (Previous EMA × (1 - Multiplier))
Where Multiplier = 2 / (Period + 1)
```

**Use Cases:**
- Moving average crossover systems
- Trend direction confirmation
- Dynamic support/resistance levels
- Multi-timeframe trend alignment

**Available Fields:**
- EMA_1 (default: 20-period)
- EMA_2 (default: 50-period)
- EMA_3 (default: 100-period)
- EMA_4 (default: 200-period)

**Common Configurations:**

| Setup Type | EMA Periods | Strategy Logic |
|------------|-------------|----------------|
| Fast Scalping | 8, 13, 21, 55 | Quick crossovers, short-term trends |
| Standard Swing | 20, 50, 100, 200 | Medium-term trend following |
| Long-term Position | 50, 100, 200, 500 | Major trend identification |
| Custom Ribbon | 10, 20, 30, 40 | Multiple confirmation layers |

**Example Strategies:**

**Golden Cross (Long):**
```
Condition 1: EMA_50 Crosses Above EMA_200 [AND]
Condition 2: Current Price > EMA_50 [AND]
Condition 3: Close > Open (bullish candle)
```

**Death Cross (Short):**
```
Condition 1: EMA_50 Crosses Under EMA_200 [AND]
Condition 2: Current Price < EMA_50 [AND]
Condition 3: Close < Open (bearish candle)
```

**Triple EMA Alignment (Long):**
```
Condition 1: Current Price > EMA_20 [AND]
Condition 2: EMA_20 > EMA_50 [AND]
Condition 3: EMA_50 > EMA_100
```

**Configuration Parameters:**
- **EMA 1 Period**: 1-500 (default: 20)
- **EMA 2 Period**: 1-500 (default: 50)
- **EMA 3 Period**: 1-500 (default: 100)
- **EMA 4 Period**: 1-500 (default: 200)

**Best Practices:**
- Faster EMAs (8-21) for scalping on M1-M15
- Standard EMAs (20-50-100-200) for swing trading on H1-H4
- Avoid too many EMAs in conditions (increases complexity)
- Test crossover strategies in trending vs ranging markets

---

### 4. SuperTrend Strategy

**Description**: Trend-following indicator that automatically generates signals based on trend direction changes. Uses Average True Range (ATR) to create dynamic support/resistance levels.

**Mathematical Foundation:**
```
Basic Upper Band = (High + Low) / 2 + (ATR × Multiplier)
Basic Lower Band = (High + Low) / 2 - (ATR × Multiplier)

Final Upper Band = Basic Upper Band < Final Upper Band[1] OR Close[1] > Final Upper Band[1] 
                   ? Basic Upper Band : Final Upper Band[1]
                   
Final Lower Band = Basic Lower Band > Final Lower Band[1] OR Close[1] < Final Lower Band[1]
                   ? Basic Lower Band : Final Lower Band[1]

SuperTrend = Trend == UP ? Final Lower Band : Final Upper Band
```

**Signal Generation Logic:**
- **BUY Signal**: SuperTrend flips from DOWN to UP (Close crosses above SuperTrend)
- **SELL Signal**: SuperTrend flips from UP to DOWN (Close crosses below SuperTrend)
- **Trend UP**: Price > SuperTrend (shows lower band, typically green)
- **Trend DOWN**: Price < SuperTrend (shows upper band, typically red)

**Key Characteristics:**
- **Automated Signals**: Manual Buy/Sell conditions are DISABLED - SuperTrend auto-generates all signals
- **Trend Following**: Keeps you in trades during strong trends
- **Adaptive**: ATR-based bands adjust to market volatility
- **Lag**: Like all trend indicators, signals appear after trend starts

**Available Fields:**
- **SuperTrend Value**: Current SuperTrend line level
- **SuperTrend Upper**: Upper band value (resistance in downtrend)
- **SuperTrend Lower**: Lower band value (support in uptrend)

**Configuration Parameters:**

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| ATR Period | 1-500 | 10 | Lookback period for ATR calculation |
| ATR Multiplier | 0.1-50.0 | 3.0 | Distance of bands from centerline |
| ATR Method | ATR/SMA | ATR | True Range averaging method |

**Parameter Effects:**
- **Lower ATR Period (5-7)**: More sensitive, more signals, more whipsaws
- **Higher ATR Period (14-20)**: Less sensitive, fewer signals, stronger trends
- **Lower Multiplier (1-2)**: Tighter bands, earlier signals, more false signals
- **Higher Multiplier (4-5)**: Wider bands, later signals, more reliable trends

**Recommended Configurations:**

| Market Condition | ATR Period | Multiplier | Timeframe |
|------------------|------------|------------|-----------|
| High Volatility | 10-14 | 3.5-4.5 | M15-H1 |
| Low Volatility | 7-10 | 2.5-3.0 | M5-M30 |
| Strong Trends | 14-20 | 3.0-4.0 | H1-H4 |
| Ranging Market | 7-10 | 2.0-2.5 | M15-H1 |

**Use Cases:**
- Trend identification and following
- Automatic signal generation without complex conditions
- Volatile markets requiring adaptive stops
- Combining with other filters (EMA, volume) for confirmation

**Limitations:**
- Generates signals AFTER trend has started (lagging indicator)
- Can produce whipsaws in ranging/choppy markets
- Not suitable for mean reversion strategies
- Requires trending markets for best performance

**Important Notes:**
- You CANNOT add manual Buy/Sell conditions - the system ignores them
- SuperTrend generates its own signals based on trend flips
- Best used in clearly trending markets
- Consider combining with trend filters to reduce whipsaws

---

### 5. SMC (Smart Money Concepts) Strategy

**Description**: Market structure-based strategy that identifies Break of Structure (BOS) and Change of Character (CHoCH) events to detect institutional order flow and trend changes.

**Core Concepts:**

**1. Market Structure:**
- **Higher Highs (HH)**: Each swing high exceeds the previous swing high (uptrend)
- **Higher Lows (HL)**: Each swing low exceeds the previous swing low (uptrend)
- **Lower Highs (LH)**: Each swing high is below the previous swing high (downtrend)
- **Lower Lows (LL)**: Each swing low is below the previous swing low (downtrend)

**2. Break of Structure (BOS):**
- **Bullish BOS**: Price breaks above previous swing high in uptrend (continuation)
- **Bearish BOS**: Price breaks below previous swing low in downtrend (continuation)
- **Meaning**: Trend continuation, institutional momentum

**3. Change of Character (CHoCH):**
- **Bullish CHoCH**: Price breaks above previous swing high during downtrend (reversal to up)
- **Bearish CHoCH**: Price breaks below previous swing low during uptrend (reversal to down)
- **Meaning**: Potential trend reversal, shift in institutional bias

**Signal Generation Logic:**
```
IF market is in DOWNTREND:
    - If price breaks above last swing high → Bullish CHoCH (potential BUY)
    
IF market is in UPTREND:
    - If price breaks below last swing low → Bearish CHoCH (potential SELL)
    
IF BOS event occurs:
    - Bullish BOS → Potential BUY (if filters pass)
    - Bearish BOS → Potential SELL (if filters pass)
```

**Available Fields:**
- **SMC Pivot High**: Latest identified swing high pivot
- **SMC Pivot Low**: Latest identified swing low pivot

**Configuration Parameters:**

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| Pivot Left Bars | 1-10 | 2 | Bars to the left of pivot point |
| Pivot Right Bars | 1-10 | 2 | Bars to the right of pivot point |
| Emit Signals On | CHoCH/BOS/Both | Both | Which events generate signals |

**Emit Signals Options:**
- **CHoCH only**: Only reversal signals (trend changes)
- **BOS only**: Only continuation signals (trend follows through)
- **Both**: All BOS and CHoCH events generate signals

**Pivot Identification:**
```
For Pivot High (with Left=2, Right=2):
    Bar must be highest of 5 bars (2 left + center + 2 right)
    
For Pivot Low (with Left=2, Right=2):
    Bar must be lowest of 5 bars (2 left + center + 2 right)
```

**Buy/Sell Condition Behavior:**
- **CRITICAL**: Buy/Sell conditions are POST-FILTERS, not signal generators
- Signals are generated by BOS/CHoCH events
- Conditions then FILTER which signals to act on
- Empty conditions = all BOS/CHoCH signals are accepted

**Example Filtering Logic:**

**Scenario 1: No Conditions Set**
```
Emit Signals On: Both
Buy Conditions: (empty)
Sell Conditions: (empty)

→ Result: ALL BOS and CHoCH events generate trades
```

**Scenario 2: Buy Filter with EMA**
```
Emit Signals On: Both
Buy Conditions: Current Price > EMA_50
Sell Conditions: Current Price < EMA_50

→ Result: 
  - Bullish BOS/CHoCH only executed if Price > EMA_50
  - Bearish BOS/CHoCH only executed if Price < EMA_50
```

**Scenario 3: Volume Confirmation**
```
Emit Signals On: CHoCH only
Buy Conditions: Volume > Volume_MA [AND] Price > EMA_20
Sell Conditions: Volume > Volume_MA [AND] Price < EMA_20

→ Result: 
  - Only CHoCH events (reversals) generate signals
  - Must have high volume AND price/EMA alignment to execute
```

**Recommended Configurations:**

| Trading Style | Pivot Bars | Emit On | Timeframe | Filter Conditions |
|---------------|------------|---------|-----------|-------------------|
| Scalping | 1-2 | Both | M1-M5 | Volume, fast EMA |
| Intraday | 2-3 | CHoCH | M15-H1 | EMA trend alignment |
| Swing Trading | 3-5 | CHoCH only | H1-H4 | Major trend confirmation |
| Trend Following | 2-3 | BOS only | M30-H4 | Moving average ribbon |

**Use Cases:**
- Identifying institutional order flow
- Trading market structure breaks
- Reversal trading at CHoCH points
- Continuation trading at BOS points
- Combining with order blocks and fair value gaps

**Best Practices:**
- Use longer pivot periods (3-5) for cleaner signals on higher timeframes
- Combine with volume analysis to confirm institutional activity
- Add EMA filters to align with larger trend
- Avoid over-filtering (too many conditions = missed opportunities)
- Test "CHoCH only" for reversals vs "BOS only" for continuations

**Common Mistakes:**
- ❌ Expecting conditions to generate signals (they only filter)
- ❌ Using too many pivot bars on lower timeframes (delays signals)
- ❌ Not understanding BOS vs CHoCH difference
- ❌ Trading against higher timeframe structure

**Important Notes:**
- SMC signals are EVENT-BASED (discrete points), not continuous
- Pivot detection requires completed bars (right bars must finish)
- More pivot bars = more reliable but delayed signals
- Works best in markets with clear structure (not choppy ranges)

---

### 6. No Strategy

**Description**: Direct execution mode that generates signals based solely on Strategy Direction and optional custom conditions, without any predefined indicator logic.

**Use Cases:**
- Manual signal generation with basic filters
- Testing custom condition combinations
- Simple price action strategies
- Placeholder for external signal integration

**Behavior:**
- **No Direction Set**: No signals generated
- **Long-only + No Conditions**: Generates BUY signal on every tick (not recommended)
- **Short-only + No Conditions**: Generates SELL signal on every tick (not recommended)
- **Long & Short + Conditions**: Evaluates conditions to generate signals

**Recommended Usage:**
```
Direction: Long & Short
Buy Conditions: [Your entry logic]
Sell Conditions: [Your exit logic]
```

**Warning**: Using "No Strategy" with no conditions and a direction set will generate continuous signals, potentially opening many positions. Always use conditions or external signal logic.

---

## Strategy Configuration

### Strategy Name

**Purpose**: Unique identifier for the strategy across the entire system.

**Validation Rules:**
- **Characters Allowed**: Alphanumeric (A-Z, a-z, 0-9), underscores (_), hyphens (-)
- **Characters Not Allowed**: Spaces, special characters (@, #, $, %, etc.)
- **Length**: 3-100 characters recommended
- **Uniqueness**: Must be unique across all strategies (checked in real-time)

**Naming Conventions (Best Practices):**

```
Format: [StrategyType]_[Symbol]_[Timeframe]_[Variant]

Examples:
- EMA_Crossover_EURUSD_H1
- VWAP_Reversion_XAUUSD_M15
- SuperTrend_GBPJPY_M5_Aggressive
- SMC_Breakout_BTCUSD_H4_Conservative
```

**Workflow:**
1. User types strategy name in text field
2. System validates in real-time (visual feedback: green check or red X)
3. Uniqueness checked against database
4. Invalid names cannot be saved

**Error Messages:**
- "Strategy name already exists"
- "Invalid characters in strategy name"
- "Strategy name too short (minimum 3 characters)"

---

### Strategy Direction

**Purpose**: Controls which trading directions are allowed for signal generation.

**Options:**

| Option | Description | Behavior |
|--------|-------------|----------|
| **Long & Short** | Trade both directions | Both Buy and Sell conditions evaluated |
| **Long-only** | Only buy positions | Only Buy Conditions section visible |
| **Short-only** | Only sell positions | Only Sell Conditions section visible |

**UI Behavior:**
- **Long & Short selected**: Both "Buy Conditions" and "Sell Conditions" sections appear
- **Long-only selected**: Only "Buy Conditions" section appears, Sell section hidden
- **Short-only selected**: Only "Sell Conditions" section appears, Buy section hidden

**Signal Priority (Long & Short mode):**
```
Evaluation Order:
1. Check Buy Conditions
2. If Buy Conditions = TRUE → Return BUY signal (stop evaluation)
3. If Buy Conditions = FALSE → Check Sell Conditions
4. If Sell Conditions = TRUE → Return SELL signal
5. If both FALSE → Return None (no signal)
```

**Edge Case - Simultaneous Signals:**
```
Scenario: Both Buy and Sell conditions evaluate to TRUE on same candle

Example Conditions:
Buy:  Current Price > Previous High
Sell: Current Price < Previous Close

If Price = 1.1050, PrevHigh = 1.1040, PrevClose = 1.1060:
- Buy Condition: 1.1050 > 1.1040 = TRUE ✓
- Sell Condition: 1.1050 < 1.1060 = TRUE ✓

Resolution: BUY signal takes priority (executed first)
```

**Use Case Examples:**

**Long-only (Buy the Dip):**
```
Direction: Long-only
Buy Conditions: Price crosses above EMA_50 AND RSI < 40
Strategy: Only buys when oversold, never sells
```

**Short-only (Fade the Rally):**
```
Direction: Short-only
Sell Conditions: Price crosses below EMA_20 AND RSI > 60
Strategy: Only sells when overbought, never buys
```

**Long & Short (Full Trading):**
```
Direction: Long & Short
Buy Conditions: EMA_20 > EMA_50 AND Close > EMA_20
Sell Conditions: EMA_20 < EMA_50 AND Close < EMA_20
Strategy: Trades both directions based on trend
```

**Best Practices:**
- Use **Long-only** for long-term bullish assets (stocks, crypto in bull markets)
- Use **Short-only** for bearish or hedging strategies
- Use **Long & Short** for neutral, trend-following, or mean-reversion strategies
- Consider market conditions: strongly trending vs ranging

---

### Basic Information

#### Symbol

**Purpose**: Select the financial instrument to trade.

**Input Method:**
- Type symbol name directly (autocomplete appears)
- Select from dropdown menu of available MT5 symbols

**Symbol Format Examples:**
- **Forex**: `EURUSD`, `GBPJPY`, `AUDUSD`
- **Gold**: `XAUUSD`, `GOLD`, `XAUUSDm` (micro)
- **Indices**: `US30`, `NAS100`, `SPX500`
- **Crypto**: `BTCUSD`, `ETHUSD`

**Validation:**
- Symbol must exist in connected MT5 broker
- Symbol must be available for trading (not disabled/archived)
- Symbol data must be accessible (market watch)

**Important Notes:**
- Different brokers may use different symbol suffixes (`.m`, `.a`, `.e`)
- Check exact symbol name in your MT5 Market Watch
- Symbol precision affects calculation accuracy

**Workflow:**
1. User types symbol name or clicks dropdown
2. System queries available MT5 symbols
3. Autocomplete suggests matching symbols
4. User selects symbol
5. System validates symbol availability

---

#### Timeframe

**Purpose**: Define the candle period used for all indicator calculations and signal generation.

**Available Timeframes:**

| Timeframe | Period | Typical Use Case |
|-----------|--------|------------------|
| **M1** | 1 Minute | Scalping, high-frequency trading |
| **M5** | 5 Minutes | Intraday scalping, quick moves |
| **M15** | 15 Minutes | Short-term intraday trading |
| **M30** | 30 Minutes | Intraday swing trades |
| **H1** | 1 Hour | Standard swing trading |
| **H4** | 4 Hours | Longer swing trading, position setups |
| **D1** | Daily | Position trading, long-term trends |

**Timeframe Selection Guide:**

**Scalping (M1-M5):**
- Requires fast execution
- Many trades per day
- Tight stop losses (5-20 points)
- Best for high liquidity pairs

**Intraday (M15-M30):**
- Multiple trades per day
- Medium stop losses (20-50 points)
- Session-based strategies
- Balance of speed and stability

**Swing Trading (H1-H4):**
- Few trades per week
- Wider stop losses (50-200 points)
- Trend-following strategies
- Lower time commitment

**Position Trading (D1):**
- Long-term holds (days to weeks)
- Very wide stop losses (200+ points)
- Major trend identification
- Fundamental alignment

**Impact on Indicators:**
```
Example: EMA_20 on different timeframes

M1:  20 minutes of data (20 × 1-minute candles)
M5:  100 minutes of data (20 × 5-minute candles)
H1:  20 hours of data (20 × 1-hour candles)
D1:  20 days of data (20 × daily candles)
```

**Best Practices:**
- Match timeframe to your trading style and availability
- Lower timeframes = more signals, more noise, more commissions
- Higher timeframes = fewer signals, more reliable, less stress
- Consider using multiple timeframe analysis (trade H1, confirm on H4)

**Common Mistakes:**
- ❌ Using M1 for strategies designed for H1
- ❌ Not accounting for spread impact on lower timeframes
- ❌ Mixing indicator periods without adjusting for timeframe
- ❌ Scalping on illiquid timeframes/symbols

---

#### Lot Size

**Purpose**: Define position size for trade execution.

**Format**: Decimal value representing trading volume

**Range**: 0.01 to 100.0

**Default Behavior**: If set to 0.01, system uses global default lot size from configuration

**Lot Size Terminology:**

| Value | Description | Contract Size (Forex) |
|-------|-------------|------------------------|
| 0.01 | 1 micro lot | 1,000 units |
| 0.10 | 10 micro lots = 1 mini lot | 10,000 units |
| 1.00 | 100 micro lots = 10 mini lots = 1 standard lot | 100,000 units |
| 10.00 | 10 standard lots | 1,000,000 units |

**Calculation Examples:**

**Forex (EURUSD):**
```
Lot Size: 0.01 (1 micro lot)
Position Size: 1,000 units
Pip Value: $0.10 per pip

Price Move: 1.1000 → 1.1010 (10 pips)
Profit/Loss: 10 pips × $0.10 = $1.00
```

**Forex (EURUSD) - Mini Lot:**
```
Lot Size: 0.10 (1 mini lot)
Position Size: 10,000 units
Pip Value: $1.00 per pip

Price Move: 1.1000 → 1.1010 (10 pips)
Profit/Loss: 10 pips × $1.00 = $10.00
```

**Forex (EURUSD) - Standard Lot:**
```
Lot Size: 1.00 (1 standard lot)
Position Size: 100,000 units
Pip Value: $10.00 per pip

Price Move: 1.1000 → 1.1010 (10 pips)
Profit/Loss: 10 pips × $10.00 = $100.00
```

**Gold (XAUUSD):**
```
Lot Size: 0.01
Position Size: 1 ounce
Pip Value: $0.01 per pip (point)

Price Move: $2000.00 → $2010.00 (1000 pips)
Profit/Loss: 1000 pips × $0.01 = $10.00
```

**Risk Management Formula:**
```
Lot Size = (Account Risk Amount) / (Stop Loss in Pips × Pip Value)

Example:
Account Balance: $10,000
Risk Per Trade: 1% = $100
Stop Loss: 50 pips
Pip Value (mini lot): $1.00

Lot Size = $100 / (50 × $1.00) = $100 / $50 = 2 mini lots = 0.20
```

**Best Practices:**
- **Fixed Fractional Risk**: Risk 1-2% of account per trade
- **Position Sizing**: Adjust lot size based on account balance
- **Stop Loss Integration**: Larger SL = smaller lot size for same risk
- **Broker Limits**: Check minimum/maximum lot size with your broker

**Broker-Specific Limits:**
- Some brokers allow 0.001 (micro lots)
- Some brokers minimum is 0.01
- Maximum lot size varies (typically 100-500 lots)
- Margin requirements increase with lot size

**Common Mistakes:**
- ❌ Using same lot size regardless of stop loss width
- ❌ Not accounting for pip value differences (JPY vs EUR pairs)
- ❌ Over-leveraging with large lot sizes
- ❌ Ignoring broker's lot size step (e.g., 0.01 minimum increment)

---

#### Session Type

**Purpose**: Define the trading session window for OHLC reference values (OHLC/VWAP strategies) or candle evaluation scope.

**Strategy-Specific Options:**

**OHLC Price Strategy:**

| Session | Time Range (IST) | Purpose |
|---------|------------------|---------|
| **Daily** | 24h Mon-Fri | Full day OHLC values |
| **Asian Session** | 05:30-14:30 | Tokyo market hours |
| **European Session** | 13:30-22:30 | London market hours |
| **US Session** | 18:30-03:30 | New York market hours |

**VWAP Strategy:**

| Session | Time Range (IST) | Purpose |
|---------|------------------|---------|
| **NY Session** | 18:30-03:30 | New York volume anchor |
| **London Session** | 13:30-22:30 | London volume anchor |
| **Asia Session** | 05:30-14:30 | Asian volume anchor |
| **All Sessions** | 24h | Continuous VWAP |

**EMA / SuperTrend / SMC / No Strategy:**

| Session | Purpose |
|---------|---------|
| **All Candles** | No session restrictions, continuous evaluation |

**Session Impact on OHLC:**
```
Example: European Session (13:30-22:30 IST)

At 13:30: Session opens
- Previous Open = Open price at 13:30 yesterday
- Previous High = Highest price during 13:30-22:30 yesterday
- Previous Low = Lowest price during 13:30-22:30 yesterday
- Previous Close = Close price at 22:30 yesterday

During 13:30-22:30 today:
- Current candles compared against yesterday's OHLC values
- Strategies evaluate breakouts/reversals based on these levels

At 22:30: Session closes, values stored for next day
```

**Session Impact on VWAP:**
```
Example: London Session VWAP

At 13:30: VWAP resets
- Cumulative Price×Volume = 0
- Cumulative Volume = 0
- VWAP starts calculating fresh

During 13:30-22:30:
- VWAP accumulates volume-weighted prices
- Bands calculate based on session data only

At 22:30: VWAP calculation stops (carries forward until next reset)
Next day 13:30: VWAP resets and restarts
```

**Timezone Considerations:**
- All times listed in IST (Indian Standard Time)
- System automatically handles timezone conversions
- Server time (MT5 broker time) may differ
- Verify session times align with your broker's quote timezone

**Best Practices:**
- **Forex**: Match session to major market hours (London for EUR, NY for USD)
- **Gold**: Use NY or All Sessions (gold active during US hours)
- **Indices**: Use corresponding market hours (US30 = NY session)
- **Crypto**: Use All Sessions (24/7 trading)

**Use Case Examples:**

**London Breakout (OHLC):**
```
Session: European Session
Strategy: Break above/below previous session high/low
Rationale: London session highest volume, clear breakouts
```

**NY VWAP Mean Reversion:**
```
Session: NY Session
Strategy: Trade away from ±2σ VWAP bands back to mean
Rationale: US session volume defines institutional value area
```

**24H Trend Following (EMA):**
```
Session: All Candles
Strategy: Continuous EMA crossover monitoring
Rationale: No session boundaries, pure trend following
```

---

## Condition Logic System

### Understanding Buy/Sell Conditions

**Purpose**: Define precise entry rules using logical operators and market data comparisons.

**Condition Structure:**
```
[Enable ☑] [Left Operand ▼] [Operator ▼] [Right Operand ▼] [OR ☐]
```

**Components Breakdown:**

1. **Enable Checkbox**: Turn condition on/off without deleting it
2. **Left Operand**: First value in comparison (price, indicator, etc.)
3. **Operator**: Comparison method (>, <, crosses, etc.)
4. **Right Operand**: Second value in comparison
5. **OR Checkbox**: Logical connector to next condition

---

### Available Operands

#### Price-Based Operands

| Operand | Description | Example Value |
|---------|-------------|---------------|
| **Current Price** | Latest bid/ask price | 1.10500 |
| **Open** | Current candle open | 1.10480 |
| **High** | Current candle high | 1.10520 |
| **Low** | Current candle low | 1.10450 |
| **Close** | Current candle close | 1.10510 |
| **Previous Open** | Previous candle/session open | 1.10400 |
| **Previous High** | Previous candle/session high | 1.10600 |
| **Previous Low** | Previous candle/session low | 1.10300 |
| **Previous Close** | Previous candle/session close | 1.10450 |
| **(H + L)/2** | Midpoint of high and low | 1.10485 |
| **(H + L + C)/3** | Typical price | 1.10493 |
| **(O + H + L + C)/4** | Average price | 1.10490 |

**Use Cases:**
- **Current Price vs Previous High**: Breakout detection
- **Close vs Open**: Candle direction (bullish if Close > Open)
- **(H+L)/2**: Mean reversion from midpoint
- **(H+L+C)/3**: Weighted average for smoother comparisons

---

#### EMA Operands

| Operand | Description | Configurable Period |
|---------|-------------|---------------------|
| **EMA_1** | Fast EMA | Default: 20, Range: 1-500 |
| **EMA_2** | Medium EMA | Default: 50, Range: 1-500 |
| **EMA_3** | Slow EMA | Default: 100, Range: 1-500 |
| **EMA_4** | Very Slow EMA | Default: 200, Range: 1-500 |

**Note**: The subscript number (EMA_20, EMA_50) dynamically updates based on configured periods.

**Use Cases:**
- **Price vs EMA**: Trend direction confirmation
- **EMA vs EMA**: Crossover systems, trend strength
- **Multiple EMA alignment**: Strong trend confirmation

---

#### VWAP Operands (VWAP Strategy Only)

| Operand | Description | Calculation |
|---------|-------------|-------------|
| **VWAP** | Volume-weighted average price | Σ(P×V)/ΣV |
| **VWAP Upper 1.0σ** | +1 standard deviation | VWAP + (1.0 × σ) |
| **VWAP Upper 1.5σ** | +1.5 standard deviations | VWAP + (1.5 × σ) |
| **VWAP Upper 2.0σ** | +2 standard deviations | VWAP + (2.0 × σ) |
| **VWAP Lower 1.0σ** | -1 standard deviation | VWAP - (1.0 × σ) |
| **VWAP Lower 1.5σ** | -1.5 standard deviations | VWAP - (1.5 × σ) |
| **VWAP Lower 2.0σ** | -2 standard deviations | VWAP - (2.0 × σ) |

**Statistical Interpretation:**
- **±1σ**: ~68% of price action (normal range)
- **±1.5σ**: ~87% of price action (extended range)
- **±2σ**: ~95% of price action (extreme range)

**Use Cases:**
- **Mean Reversion**: Trade from ±2σ toward VWAP
- **Trend Following**: Enter when price breaks above/below VWAP
- **Volatility**: Distance from VWAP indicates market extremes

---

#### SuperTrend Operands (SuperTrend Strategy Only)

| Operand | Description | Usage |
|---------|-------------|-------|
| **SuperTrend Value** | Current SuperTrend line level | Trailing stop reference |
| **SuperTrend Upper** | Upper band (resistance) | Downtrend resistance level |
| **SuperTrend Lower** | Lower band (support) | Uptrend support level |

**Note**: SuperTrend auto-generates signals; these operands are for reference/display only.

---

#### SMC Operands (SMC Strategy Only)

| Operand | Description | Usage |
|---------|-------------|-------|
| **SMC Pivot High** | Latest swing high | Resistance level, BOS/CHoCH reference |
| **SMC Pivot Low** | Latest swing low | Support level, BOS/CHoCH reference |

**Use Cases:**
- **Filter by pivot proximity**: Only trade near key structure
- **Confirmation**: Ensure price has cleared pivot levels
- **Risk management**: Set stops beyond pivots

---

### Comparison Operators

#### Basic Comparison Operators

**Greater_Than (>)**
```
Definition: Left > Right
Example: Current Price > EMA_50
Use Case: Confirm price above moving average (bullish)

Evaluation: TRUE if left value strictly greater than right value
```

**Lower_Than (<)**
```
Definition: Left < Right
Example: Current Price < Previous Low
Use Case: Breakout below support

Evaluation: TRUE if left value strictly less than right value
```

**Equals (==)**
```
Definition: Left == Right (within epsilon)
Example: Close == Open (doji candle)
Use Case: Indecision candles, price equilibrium

Evaluation: TRUE if |Left - Right| < epsilon (default: 0.00001)
Note: Exact equality rare in floating-point; uses tolerance
```

---

#### Cross Operators (Advanced)

**Crosses Above**
```
Definition: Left crosses from below to above Right
Mathematical: (Left_prev <= Right_prev) AND (Left_current > Right_current)

Timing:
- Previous tick/candle: Left was at or below Right
- Current tick/candle: Left is now above Right

Example:
Condition: EMA_20 Crosses Above EMA_50 (Golden Cross)

Tick/Candle n-1:
- EMA_20 = 1.1040
- EMA_50 = 1.1050
- EMA_20 <= EMA_50 ✓ (below condition met)

Tick/Candle n:
- EMA_20 = 1.1060
- EMA_50 = 1.1050
- EMA_20 > EMA_50 ✓ (above condition met)

Result: Crosses Above = TRUE → Generate signal
```

**Crosses Under**
```
Definition: Left crosses from above to below Right
Mathematical: (Left_prev >= Right_prev) AND (Left_current < Right_current)

Timing:
- Previous tick/candle: Left was at or above Right
- Current tick/candle: Left is now below Right

Example:
Condition: Current Price Crosses Under VWAP (Bearish entry)

Tick/Candle n-1:
- Current Price = 1.1080
- VWAP = 1.1070
- Price >= VWAP ✓ (above condition met)

Tick/Candle n:
- Current Price = 1.1060
- VWAP = 1.1070
- Price < VWAP ✓ (below condition met)

Result: Crosses Under = TRUE → Generate signal
```

**Any_Cross**
```
Definition: Left crosses Right in either direction
Mathematical: Crosses Above OR Crosses Under

Use Case: Detect any interaction between two indicators
Example: Price Any_Cross EMA_20 (any touch or cross)
```

---

#### VWAP-Specific Operators

**Within_Band**
```
Definition: Price is between specified VWAP band limits
Example: Current Price Within_Band VWAP ±1.0σ

Evaluation:
- TRUE if: VWAP - 1.0σ <= Price <= VWAP + 1.0σ
- FALSE if: Price outside this range

Use Case: Identify when price returns to value area
```

**Outside_Band**
```
Definition: Price has exceeded VWAP band limits
Example: Current Price Outside_Band VWAP ±2.0σ

Evaluation:
- TRUE if: Price < VWAP - 2.0σ OR Price > VWAP + 2.0σ
- FALSE if: Price within band range

Use Case: Extreme value detection for mean reversion
```

---

### AND/OR Connector Logic

**Connector Mechanism:**
- Each condition row has an "OR" checkbox
- The checkbox sets the connector **from this row to the NEXT row**
- First condition always starts evaluation (no previous connector)

**Checkbox States:**
- **OR unchecked** = AND connector (default)
- **OR checked** = OR connector

---

#### Evaluation Order

**Processing Flow:**
```
1. Start with first condition (always evaluated)
2. For each subsequent condition:
   a. Get connector from PREVIOUS row
   b. If previous connector = "AND":
      result = result AND current_condition
   c. If previous connector = "OR":
      result = result OR current_condition
3. Final result determines signal generation
```

**Operator Precedence:**
- AND has higher precedence than OR in standard logic
- Evaluation is LEFT-TO-RIGHT with accumulation
- Use parenthetical thinking: (A AND B) OR C

---

#### Logic Examples

**Example 1: Simple AND Chain**
```
Row 1: Current Price > EMA_20 [OR unchecked = AND]
Row 2: EMA_20 > EMA_50 [OR unchecked = AND]
Row 3: Volume > Volume_MA [OR unchecked = AND]

Connector Chain:
Row 1 → AND → Row 2 → AND → Row 3

Evaluation:
(Current Price > EMA_20) AND (EMA_20 > EMA_50) AND (Volume > Volume_MA)

Result: ALL three conditions must be TRUE
```

**Example 2: Simple OR Chain**
```
Row 1: Current Price > Previous High [OR checked = OR]
Row 2: Current Price < Previous Low [OR checked = OR]
Row 3: Volume > 2 × Volume_MA [OR checked = OR]

Connector Chain:
Row 1 → OR → Row 2 → OR → Row 3

Evaluation:
(Price > PrevHigh) OR (Price < PrevLow) OR (Volume > 2×VolMA)

Result: ANY one condition TRUE generates signal
```

**Example 3: Mixed AND/OR (Common Pattern)**
```
Row 1: Current Price > EMA_20 [OR unchecked = AND]
Row 2: EMA_20 > EMA_50 [OR checked = OR]
Row 3: Volume > Volume_MA [OR checked = OR]

Connector Chain:
Row 1 → AND → Row 2 → OR → Row 3

Evaluation:
((Current Price > EMA_20) AND (EMA_20 > EMA_50)) OR (Volume > Volume_MA)

Logical Flow:
1. Evaluate Row 1: Price > EMA_20
2. Apply AND with Row 2: result = result AND (EMA_20 > EMA_50)
3. Apply OR with Row 3: result = result OR (Volume > VolMA)

Result: 
- Signal if both trend conditions TRUE, OR
- Signal if volume condition TRUE (regardless of trend)
```

**Example 4: Complex Multi-Filter**
```
Row 1: Current Price > EMA_50 [OR unchecked = AND]
Row 2: Close > Open [OR unchecked = AND]
Row 3: Volume > Volume_MA [OR checked = OR]
Row 4: RSI < 30 [OR unchecked = AND]
Row 5: Price < VWAP Lower 2.0σ [OR checked = OR]

Connector Chain:
Row 1 → AND → Row 2 → AND → Row 3 → OR → Row 4 → AND → Row 5

Evaluation:
(
  ((Price > EMA_50) AND (Close > Open) AND (Volume > VolMA))
  OR
  ((RSI < 30) AND (Price < VWAP -2σ))
)

Logical Groupings:
Group A: Price > EMA_50 AND Close > Open AND Volume > VolMA
Group B: RSI < 30 AND Price < VWAP -2σ

Result: Signal if EITHER group is TRUE
```

---

#### Truth Table Reference

**Two Conditions:**
```
A = Condition 1
B = Condition 2

A AND B:
| A | B | Result |
|---|---|--------|
| T | T |   T    |
| T | F |   F    |
| F | T |   F    |
| F | F |   F    |

A OR B:
| A | B | Result |
|---|---|--------|
| T | T |   T    |
| T | F |   T    |
| F | T |   T    |
| F | F |   F    |
```

**Three Conditions:**
```
(A AND B) OR C:
| A | B | C | A AND B | Result |
|---|---|---|---------|--------|
| T | T | T |    T    |   T    |
| T | T | F |    T    |   T    |
| T | F | T |    F    |   T    |
| T | F | F |    F    |   F    |
| F | T | T |    F    |   T    |
| F | T | F |    F    |   F    |
| F | F | T |    F    |   T    |
| F | F | F |    F    |   F    |
```

---

#### Best Practices

**DO:**
- ✓ Group related conditions with AND (trend confirmation)
- ✓ Use OR for alternative entry scenarios
- ✓ Test conditions individually before combining
- ✓ Start simple (2-3 conditions) then add complexity
- ✓ Document your logic in strategy name/notes

**DON'T:**
- ✗ Create overly complex chains (>5 conditions)
- ✗ Mix too many OR connectors (loses specificity)
- ✗ Use contradictory conditions in AND chain
- ✗ Forget that last row's OR checkbox has no effect

---

#### Common Condition Patterns

**1. Trend Confirmation (AND Chain):**
```
Current Price > EMA_20 [AND]
EMA_20 > EMA_50 [AND]
EMA_50 > EMA_200
→ Strong bullish alignment
```

**2. Breakout with Volume (AND Chain):**
```
Current Price > Previous High [AND]
Volume > 1.5 × Volume_MA [AND]
Close > Open
→ Confirmed breakout
```

**3. Oversold Bounce (OR for alternatives):**
```
RSI < 30 [OR]
Price < VWAP Lower 2.0σ [OR]
Stochastic < 20
→ Any oversold indicator triggers
```

**4. Mean Reversion Setup (Mixed):**
```
Price < VWAP Lower 2.0σ [AND]
Volume > Volume_MA [OR]
RSI < 30
→ Extreme value + (volume OR RSI confirmation)
```

**5. Crossover with Filter (Mixed):**
```
EMA_20 Crosses Above EMA_50 [AND]
Current Price > EMA_100 [OR]
Volume > 2 × Volume_MA
→ Crossover in trend OR high volume confirmation
```

---

## Strategy-Specific Parameters

### VWAP Configuration

**Standard Deviation Bands**

**Purpose**: Define VWAP band multipliers for value area identification.

**Format**: Comma-separated decimal values

**Default**: `1, 1.5, 2`

**Range**: 0.1 to 5.0 per value

**Examples:**
```
"1, 1.5, 2"        → Standard configuration (68%, 87%, 95%)
"1, 2, 3"          → Wide bands for volatile markets
"0.5, 1, 1.5"      → Tight bands for ranging markets
"1.5, 2.5"         → Custom two-band system
"1"                → Single band only
```

**Band Interpretation:**

| Multiplier | Coverage | Use Case |
|------------|----------|----------|
| 0.5σ | ~38% | Very tight, high-frequency mean reversion |
| 1.0σ | ~68% | Standard deviation, normal value area |
| 1.5σ | ~87% | Extended range, moderate extremes |
| 2.0σ | ~95% | Extreme range, strong mean reversion |
| 3.0σ | ~99% | Very extreme, rare events |

**Visual Representation:**
```
+3σ  ─────────────────── (Very Extreme)
+2σ  ═══════════════════ (Extreme - 2.5% above)
+1.5σ ─────────────────── (Extended)
+1σ  ------------------- (Normal range - 34% above)
VWAP =================== (Institutional value)
-1σ  ------------------- (Normal range - 34% below)
-1.5σ ─────────────────── (Extended)
-2σ  ═══════════════════ (Extreme - 2.5% below)
-3σ  ─────────────────── (Very Extreme)
```

**Strategy Applications:**

**Mean Reversion from ±2σ:**
```
Buy Condition: Price < VWAP Lower 2.0σ [AND] Volume > Volume_MA
Sell Condition: Price > VWAP Upper 2.0σ [AND] Volume > Volume_MA
Target: VWAP (mean)
```

**Trend Following with VWAP:**
```
Buy Condition: Price Crosses Above VWAP [AND] Price > VWAP Upper 1.0σ
Sell Condition: Price Crosses Under VWAP [AND] Price < VWAP Lower 1.0σ
Target: ±2σ bands
```

**Breakout Trading:**
```
Buy Condition: Price > VWAP Upper 1.5σ [AND] Close > Open
Sell Condition: Price < VWAP Lower 1.5σ [AND] Close < Open
Target: Extended move beyond 2σ
```

---

**Swing Period**

**Purpose**: Define lookback period for swing high/low detection (used in advanced SMC-style filtering).

**Range**: 5-50 candles

**Default**: 10

**Important Note**: This parameter is NOT used in core VWAP calculation. It's only utilized if swing-based logic or SMC-style structure detection is enabled as an additional filter.

**Swing Detection Logic:**
```
Swing High (period = 10):
- High of current bar must be highest of 21 bars (10 left + center + 10 right)

Swing Low (period = 10):
- Low of current bar must be lowest of 21 bars (10 left + center + 10 right)
```

**Use Cases:**
- Filtering VWAP signals near swing points
- Identifying structure breaks combined with VWAP extremes
- Avoiding entries too far from swing pivots

---

### EMA Configuration

**EMA Period Settings**

Each of the four EMAs can be independently configured with custom periods.

**Parameters:**

| EMA | Default Period | Typical Range | Common Use |
|-----|----------------|---------------|------------|
| **EMA 1** | 20 | 8-50 | Fast trend, short-term direction |
| **EMA 2** | 50 | 20-100 | Medium trend, crossover systems |
| **EMA 3** | 100 | 50-200 | Slow trend, major support/resistance |
| **EMA 4** | 200 | 100-500 | Very slow trend, long-term bias |

**Period Selection Guide:**

**Scalping (M1-M5):**
```
EMA 1: 8-13
EMA 2: 21-34
EMA 3: 55-89
EMA 4: 144-233
→ Fibonacci-based, fast response
```

**Intraday (M15-H1):**
```
EMA 1: 20
EMA 2: 50
EMA 3: 100
EMA 4: 200
→ Standard configuration, balanced
```

**Swing Trading (H4-D1):**
```
EMA 1: 50
EMA 2: 100
EMA 3: 200
EMA 4: 500
→ Longer periods, major trends only
```

**Custom Ribbon:**
```
EMA 1: 10
EMA 2: 20
EMA 3: 30
EMA 4: 40
→ Evenly spaced, ribbon visualization
```

**EMA Mathematical Properties:**

**Response Speed:**
```
Weighting Factor = 2 / (Period + 1)

EMA 20: Factor = 2/21 = 0.095 (9.5% weight on new data)
EMA 50: Factor = 2/51 = 0.039 (3.9% weight on new data)
EMA 200: Factor = 2/201 = 0.010 (1.0% weight on new data)

→ Smaller period = faster response, more noise
→ Larger period = slower response, smoother line
```

**Lag Estimation:**
```
Approximate Lag (bars) ≈ (Period - 1) / 2

EMA 20: Lag ≈ 9.5 bars
EMA 50: Lag ≈ 24.5 bars
EMA 200: Lag ≈ 99.5 bars

→ Longer periods have significant lag
```

---

**Dynamic Operand Naming:**

The system automatically updates operand labels based on configured periods:

```
If EMA 1 Period = 20 → Operand shows as "EMA_20"
If EMA 1 Period = 13 → Operand shows as "EMA_13"
If EMA 2 Period = 89 → Operand shows as "EMA_89"
```

This ensures conditions remain readable and self-documenting.

---

**Classic EMA Strategies:**

**Golden Cross / Death Cross:**
```
EMA 1: 50
EMA 2: 200

Buy: EMA_50 Crosses Above EMA_200
Sell: EMA_50 Crosses Under EMA_200
```

**Triple EMA System:**
```
EMA 1: 12
EMA 2: 26
EMA 3: 50

Buy: EMA_12 > EMA_26 AND EMA_26 > EMA_50 AND Price > EMA_12
Sell: EMA_12 < EMA_26 AND EMA_26 < EMA_50 AND Price < EMA_12
```

**EMA Ribbon:**
```
EMA 1: 10
EMA 2: 20
EMA 3: 30
EMA 4: 40

Buy: All EMAs aligned up (EMA_10 > EMA_20 > EMA_30 > EMA_40) AND Price > EMA_10
Sell: All EMAs aligned down (EMA_10 < EMA_20 < EMA_30 < EMA_40) AND Price < EMA_10
```

---

### SuperTrend Configuration

**ATR Period**

**Purpose**: Defines the lookback period for Average True Range calculation.

**Range**: 1-500

**Default**: 10

**Impact:**
- **Lower Period (5-7)**: More responsive, adapts quickly to volatility changes, more signals
- **Higher Period (14-20)**: Smoother, less reactive, fewer but more reliable signals

**Recommended Settings:**

| Market Condition | ATR Period | Rationale |
|------------------|------------|-----------|
| High Volatility | 10-14 | Captures current volatility accurately |
| Low Volatility | 7-10 | Maintains sensitivity |
| Trending | 14-20 | Reduces noise, clearer trend |
| Ranging | 7-10 | More signals for range breaks |

---

**ATR Multiplier**

**Purpose**: Determines the distance of SuperTrend bands from the centerline.

**Range**: 0.1-50.0

**Default**: 3.0

**Impact:**
- **Lower Multiplier (1-2)**: Tighter bands, earlier signals, more whipsaws
- **Higher Multiplier (4-5)**: Wider bands, later signals, fewer false signals

**Risk/Reward Trade-off:**

| Multiplier | Signal Timing | Reliability | Best For |
|------------|---------------|-------------|----------|
| 1.5-2.0 | Very Early | Lower | Scalping, quick profits |
| 2.5-3.0 | Early | Moderate | Intraday swing |
| 3.0-4.0 | Standard | Good | Standard trend following |
| 4.5-5.0+ | Late | High | Strong trend confirmation |

**Optimal Combinations:**

```
Aggressive Scalping:
ATR Period: 7
Multiplier: 2.0
→ Fast, frequent signals

Balanced Intraday:
ATR Period: 10
Multiplier: 3.0
→ Default, proven balance

Conservative Swing:
ATR Period: 14
Multiplier: 4.0
→ Strong trends, fewer trades
```

---

**ATR Method**

**Purpose**: Defines how True Range is averaged.

**Options:**

**ATR (Wilder)**
- Uses Wilder's smoothing method (EMA-like)
- Formula: `ATR = ((Prior ATR × (n-1)) + TR) / n`
- Smoother, less responsive to sudden spikes
- Industry standard for SuperTrend

**SMA(TR)**
- Simple Moving Average of True Range
- Formula: `ATR = SUM(TR, n) / n`
- More responsive to recent volatility
- Treats all periods equally

**Comparison:**

| Method | Response | Smoothness | Use Case |
|--------|----------|------------|----------|
| ATR (Wilder) | Slower | Smoother | Standard, recommended |
| SMA(TR) | Faster | Less smooth | High volatility, quick adaptation |

**Recommendation**: Use **ATR (Wilder)** for standard SuperTrend behavior (default and most tested).

---

**Complete SuperTrend Calculation:**

```
Step 1: Calculate True Range (TR)
TR = MAX(
  High - Low,
  |High - Previous Close|,
  |Low - Previous Close|
)

Step 2: Calculate ATR
ATR_Wilder = ((Prior ATR × (n-1)) + TR) / n

Step 3: Calculate Basic Bands
HL_Avg = (High + Low) / 2
Basic_Upper = HL_Avg + (ATR × Multiplier)
Basic_Lower = HL_Avg - (ATR × Multiplier)

Step 4: Calculate Final Bands (with trend logic)
Final_Upper = 
  IF Basic_Upper < Final_Upper[1] OR Close[1] > Final_Upper[1]:
    Basic_Upper
  ELSE:
    Final_Upper[1]

Final_Lower = 
  IF Basic_Lower > Final_Lower[1] OR Close[1] < Final_Lower[1]:
    Basic_Lower
  ELSE:
    Final_Lower[1]

Step 5: Determine Trend
IF Close > Final_Upper[1]:
  Trend = UP
  SuperTrend = Final_Lower
ELSE IF Close < Final_Lower[1]:
  Trend = DOWN
  SuperTrend = Final_Upper
ELSE:
  Trend = Previous Trend
  SuperTrend = Previous SuperTrend

Step 6: Generate Signals
BUY Signal: Trend changes from DOWN to UP
SELL Signal: Trend changes from UP to DOWN
```

---

### SMC Configuration

**Pivot Left Bars**

**Purpose**: Number of bars to the left of pivot point required for validation.

**Range**: 1-10

**Default**: 2

**Meaning**: A swing high must be higher than X bars to its left to qualify as a pivot.

---

**Pivot Right Bars**

**Purpose**: Number of bars to the right of pivot point required for validation.

**Range**: 1-10

**Default**: 2

**Meaning**: A swing high must be higher than X bars to its right to qualify as a pivot.

**Important**: Right bars create LAG - pivot is only confirmed after right bars complete.

---

**Pivot Detection Visual:**

```
Left=2, Right=2 (Total = 5 bars)

     X ← Pivot High (must be highest of 5 bars)
   /   \
  /     \
 /       \
L1  L2  P  R1  R2

L1, L2 = Left bars (must be lower than P)
P = Pivot candidate
R1, R2 = Right bars (must be lower than P)

→ Pivot confirmed only AFTER R2 completes
```

**Configuration Trade-offs:**

| Setting | Lag | Reliability | Signal Frequency | Use Case |
|---------|-----|-------------|------------------|----------|
| Left=1, Right=1 | Low | Lower | High | M1-M5 scalping |
| Left=2, Right=2 | Medium | Moderate | Medium | M15-H1 intraday |
| Left=3, Right=3 | High | High | Low | H1-H4 swing |
| Left=5, Right=5 | Very High | Very High | Very Low | H4-D1 position |

**Asymmetric Configurations:**

```
Left=3, Right=1:
→ More confirmation from past, quicker detection
→ Good for breakout strategies

Left=1, Right=3:
→ Quick initial detection, strong confirmation
→ Good for reversal strategies
```

---

**Emit Signals On**

**Purpose**: Control which market structure events generate trading signals.

**Options:**

**CHoCH only (Change of Character)**
- Signals on trend reversals only
- Bullish CHoCH: Downtrend → Uptrend (price breaks above swing high)
- Bearish CHoCH: Uptrend → Downtrend (price breaks below swing low)
- **Use Case**: Reversal trading, catching trend changes early

**BOS only (Break of Structure)**
- Signals on trend continuation only
- Bullish BOS: Uptrend continues (price breaks above swing high)
- Bearish BOS: Downtrend continues (price breaks below swing low)
- **Use Case**: Trend following, riding strong momentum

**Both (BOS + CHoCH)**
- Signals on all structure events
- Captures reversals AND continuations
- **Use Case**: Maximum signal generation, comprehensive SMC approach

---

**Signal Event Examples:**

**CHoCH (Reversal) Example:**
```
Market State: Downtrend (making Lower Lows)
Structure: LL at 1.0950, LL at 1.0920, LL at 1.0900
Last Swing High: 1.0970

Event: Price breaks above 1.0970 (previous swing high in downtrend)
Signal: Bullish CHoCH → BUY signal generated
Interpretation: Trend reversal, downtrend potentially ending
```

**BOS (Continuation) Example:**
```
Market State: Uptrend (making Higher Highs)
Structure: HH at 1.1020, HH at 1.1050, HH at 1.1080
Last Swing High: 1.1080

Event: Price breaks above 1.1080 (previous swing high in uptrend)
Signal: Bullish BOS → BUY signal generated
Interpretation: Trend continuation, uptrend strengthening
```

---

**Filtering Logic (CRITICAL Understanding):**

SMC Buy/Sell conditions do NOT generate signals. They FILTER signals generated by BOS/CHoCH events.

**Workflow:**
```
1. SMC detects BOS or CHoCH event → Raw signal generated
2. System checks if corresponding Buy/Sell conditions are met
3. If conditions TRUE → Signal executed
4. If conditions FALSE → Signal filtered out (ignored)
```

**Example Scenarios:**

**Scenario 1: No Filters (Accept All)**
```
Emit Signals On: Both
Buy Conditions: (empty)
Sell Conditions: (empty)

Result:
- Every Bullish BOS/CHoCH → BUY executed
- Every Bearish BOS/CHoCH → SELL executed
- No filtering applied
```

**Scenario 2: EMA Trend Filter**
```
Emit Signals On: Both
Buy Conditions: Price > EMA_50 [AND] EMA_20 > EMA_50
Sell Conditions: Price < EMA_50 [AND] EMA_20 < EMA_50

Result:
- Bullish BOS/CHoCH only executed if price and EMAs aligned bullish
- Bearish BOS/CHoCH only executed if price and EMAs aligned bearish
- Filters out counter-trend structure breaks
```

**Scenario 3: Volume + Timeframe Filter**
```
Emit Signals On: CHoCH only
Buy Conditions: Volume > 1.5 × Volume_MA [AND] Hour >= 14 [AND] Hour <= 22
Sell Conditions: Volume > 1.5 × Volume_MA [AND] Hour >= 14 [AND] Hour <= 22

Result:
- Only CHoCH reversals generate signals (not BOS)
- Must have high volume confirmation
- Only trades during specified hours (London/NY session)
- Filters out low-volume and off-hours reversals
```

**Scenario 4: Multi-Indicator Confluence**
```
Emit Signals On: Both
Buy Conditions: Price > EMA_20 [AND] RSI > 50 [OR] Volume > 2 × Volume_MA
Sell Conditions: Price < EMA_20 [AND] RSI < 50 [OR] Volume > 2 × Volume_MA

Result:
- All BOS/CHoCH events considered
- Must have: (price/EMA + RSI alignment) OR (extreme volume)
- Flexible filtering with multiple confirmation options
```

---

## Risk Management

### Stop Loss and Take Profit

**SL Type: Price (Points)**

The system uses point-based stop loss calculation, where 1 point = smallest price increment × 10.

**Stop Loss Configuration**

**Range**: 0.0-100000.0

**Default**: 20.0 points

**Unit**: Points (not pips or price difference)

---

**Point Calculation by Broker Type:**

**5-Digit Broker (Most Common - EURUSD, GBPUSD, etc.):**
```
Price Format: 1.10500
Smallest Increment: 0.00001 (1 pipette)
1 Point: 0.00001

Stop Loss: 20 points
SL Distance: 20 × 0.00001 = 0.00020 (2 pips)

Example (BUY):
Entry: 1.10500
SL: 1.10500 - 0.00020 = 1.10480 (20 points below)

Example (SELL):
Entry: 1.10500
SL: 1.10500 + 0.00020 = 1.10520 (20 points above)
```

**3-Digit Broker (JPY Pairs - USDJPY, EURJPY, etc.):**
```
Price Format: 149.500
Smallest Increment: 0.001
1 Point: 0.001

Stop Loss: 20 points
SL Distance: 20 × 0.001 = 0.020 (2 pips)

Example (BUY):
Entry: 149.500
SL: 149.500 - 0.020 = 149.480

Example (SELL):
Entry: 149.500
SL: 149.500 + 0.020 = 149.520
```

**Gold (XAUUSD):**
```
Price Format: 2050.00
Smallest Increment: 0.01
1 Point: 0.01

Stop Loss: 20 points
SL Distance: 20 × 0.01 = 0.20 ($0.20)

Example (BUY):
Entry: 2050.00
SL: 2050.00 - 0.20 = 2049.80

Example (SELL):
Entry: 2050.00
SL: 2050.00 + 0.20 = 2050.20
```

---

**Take Profit Configuration**

**Range**: 0.0-100000.0

**Default**: 40.0 points

**Calculation**: Same point system as Stop Loss

**Example (EURUSD, 5-digit broker):**
```
Entry: 1.10500
SL: 20 points (1.10480)
TP: 40 points (1.10540)

Risk: 20 points = 0.00020
Reward: 40 points = 0.00040
Risk:Reward = 1:2
```

---

**Risk:Reward Ratio Configuration:**

Common ratios and their configurations:

| Ratio | SL (points) | TP (points) | Example (EURUSD) |
|-------|-------------|-------------|------------------|
| 1:1 | 20 | 20 | SL: 20pts, TP: 20pts |
| 1:1.5 | 20 | 30 | SL: 20pts, TP: 30pts |
| 1:2 | 20 | 40 | SL: 20pts, TP: 40pts (default) |
| 1:3 | 20 | 60 | SL: 20pts, TP: 60pts |
| 1:5 | 10 | 50 | SL: 10pts, TP: 50pts |

---

**Determining Appropriate SL/TP Sizes:**

**Based on Timeframe:**
```
M1-M5 (Scalping):
SL: 5-15 points
TP: 10-30 points
→ Tight, quick profits

M15-M30 (Intraday):
SL: 15-30 points
TP: 30-60 points
→ Medium range

H1-H4 (Swing):
SL: 30-100 points
TP: 60-200 points
→ Wider, multi-hour holds

D1 (Position):
SL: 100-500 points
TP: 200-1000 points
→ Very wide, multi-day holds
```

**Based on Volatility (ATR):**
```
Stop Loss = ATR × Multiplier

Conservative: SL = 2 × ATR(14)
Moderate: SL = 1.5 × ATR(14)
Aggressive: SL = 1 × ATR(14)

If ATR(14) = 15 points:
Conservative SL: 30 points
Moderate SL: 23 points
Aggressive SL: 15 points
```

**Based on Structure:**
```
Place SL beyond key structure:

Support/Resistance Level: SL 5-10 points beyond
Swing High/Low: SL 5-10 points beyond
Previous Session High/Low: SL 10-20 points beyond
Round Number (1.1000): SL 10-15 points beyond
```

---

### Trailing Stop-Loss

**Purpose**: Dynamic stop loss that follows price in favorable direction, locking in profits while allowing trade to run.

**Enable Trailing SL**

**Options**: Disabled / Enabled

**Default**: Disabled

---

**SL Gap (Price Points)**

**Purpose**: Distance between current price and trailing stop.

**Range**: 0.1-10000.0

**Default**: 1.0 point

**Unit**: Points (same as SL/TP)

---

**Trailing Mechanism:**

**For BUY Positions:**
```
1. Track highest price since entry (high_water_mark)
2. Calculate: Trailing_SL = high_water_mark - gap
3. Update SL if Trailing_SL > Current_SL (never moves backward)

Example (Entry: 1.10500, Gap: 20 points):
Entry: 1.10500, Initial SL: 1.10480
Price → 1.10600, High: 1.10600, Trailing SL: 1.10580 (1.10600 - 0.00020)
Price → 1.10700, High: 1.10700, Trailing SL: 1.10680 (1.10700 - 0.00020)
Price → 1.10650, High: 1.10700, Trailing SL: 1.10680 (unchanged, high still 1.10700)
Price hits 1.10680 → Position closed at break-even+ profit
```

**For SELL Positions:**
```
1. Track lowest price since entry (low_water_mark)
2. Calculate: Trailing_SL = low_water_mark + gap
3. Update SL if Trailing_SL < Current_SL (never moves backward)

Example (Entry: 1.10500, Gap: 20 points):
Entry: 1.10500, Initial SL: 1.10520
Price → 1.10400, Low: 1.10400, Trailing SL: 1.10420 (1.10400 + 0.00020)
Price → 1.10300, Low: 1.10300, Trailing SL: 1.10320 (1.10300 + 0.00020)
Price → 1.10350, Low: 1.10300, Trailing SL: 1.10320 (unchanged, low still 1.10300)
Price hits 1.10320 → Position closed with profit locked
```

---

**Gap Configuration Strategy:**

| Gap Size | Behavior | Best For | Risk |
|----------|----------|----------|------|
| Tight (5-10 points) | Follows closely, locks profit quickly | Scalping, M1-M5 | Early exit risk |
| Medium (15-30 points) | Balanced protection | Intraday, M15-H1 | Moderate breathing room |
| Wide (50+ points) | Allows large swings | Swing, H1-H4 | Larger drawdown tolerance |

**Examples by Strategy Type:**

**Scalping (Tight Trailing):**
```
Entry: 1.10500
Initial SL: 20 points (1.10480)
Trailing Gap: 10 points
TP: 30 points (1.10530)

Behavior:
- Price moves +15 points → Trailing activates at 1.10505 (break-even)
- Price moves +25 points → Trailing at 1.10515 (+15 points locked)
- Price retraces -10 points → Stopped at 1.10515 (locked profit)
```

**Swing Trading (Wide Trailing):**
```
Entry: 1.10500
Initial SL: 50 points (1.10450)
Trailing Gap: 50 points
TP: 150 points (1.10650)

Behavior:
- Allows price to breathe and retrace
- Only trails after significant favorable movement
- Locks profit on major trend moves
```

---

**Important Notes:**
- Trailing NEVER widens stop loss (only moves in favorable direction)
- Initial SL remains until price moves favorably by at least gap distance
- If price immediately moves against you, initial SL triggers (trailing hasn't started)
- Consider spread and slippage in gap calculation
- Gap should account for normal market noise/volatility

---

### Profit Lock + Trailing

**Purpose**: Advanced profit protection that locks minimum profit once threshold is reached, then trails to capture additional gains.

**Enable Profit Lock**

**Options**: Disabled / Enabled

**Default**: Disabled

---

**Profit Lock Trigger (Amount)**

**Purpose**: Profit threshold that must be reached before profit locking activates.

**Range**: 0.01-1000000.0

**Default**: $100.0

**Unit**: Currency (USD, EUR, etc. - depends on account base currency)

**Meaning**: Once position P&L reaches this amount, the profit locking system activates.

---

**Minimum Profit to Lock**

**Purpose**: Guaranteed profit amount after trigger is reached.

**Range**: 0.01-1000000.0

**Default**: $50.0

**Unit**: Currency

**Meaning**: Once triggered, at least this much profit is protected (position cannot close for less).

---

**Trail Step (Profit Increase Threshold)**

**Purpose**: Additional profit required to advance the lock to the next level.

**Range**: 0.0-1000000.0

**Default**: $100.0

**Unit**: Currency

**Meaning**: Each time profit increases by this amount, the lock level increases.

---

**Trail Amount (Profit Increment)**

**Purpose**: How much additional profit is locked at each trail step.

**Range**: 0.0-1000000.0

**Default**: $50.0

**Unit**: Currency

**Meaning**: Amount added to the locked profit at each step.

---

**Profit Lock Workflow:**

```
Configuration:
- Trigger: $100
- Lock: $50
- Step: $100
- Amount: $50

Position Flow:

Open: P&L = $0
  → No protection yet

P&L = $50:
  → Below trigger, no lock

P&L = $100:
  → TRIGGER REACHED
  → Lock activated: Minimum $50 profit guaranteed
  → TP adjusted to secure at least $50

P&L = $150:
  → Below next step ($100 + $100 = $200), lock remains $50

P&L = $200:
  → STEP REACHED (+$100 from trigger)
  → Lock increases: $50 + $50 = $100
  → TP adjusted to secure at least $100

P&L = $300:
  → STEP REACHED AGAIN (+$200 from trigger)
  → Lock increases: $100 + $50 = $150
  → TP adjusted to secure at least $150

P&L = $280:
  → Retraced but lock protects $150
  → Position cannot close below $150 profit

P&L = $400:
  → STEP REACHED (+$300 from trigger)
  → Lock increases: $150 + $50 = $200
  → Continues trailing...
```

---

**Visual Progression:**

```
Profit Levels:              Lock Status:
$0 ────────────────────     No Lock
$50 ───────────────────     No Lock
$100 ══════════════════     🔒 LOCK: $50 (Triggered)
$150 ──────────────────     🔒 LOCK: $50
$200 ══════════════════     🔒 LOCK: $100 (Step 1)
$250 ──────────────────     🔒 LOCK: $100
$300 ══════════════════     🔒 LOCK: $150 (Step 2)
$350 ──────────────────     🔒 LOCK: $150
$400 ══════════════════     🔒 LOCK: $200 (Step 3)
```

---

**Configuration Strategies:**

**Conservative (Protect Early):**
```
Trigger: $50
Lock: $30
Step: $50
Amount: $25

→ Low trigger, quick protection
→ Small steps, frequent lock increases
→ Good for volatile markets
```

**Aggressive (Let It Run):**
```
Trigger: $200
Lock: $100
Step: $200
Amount: $100

→ High trigger, allows initial movement
→ Large steps, substantial lock increases
→ Good for strong trending markets
```

**Balanced (Default):**
```
Trigger: $100
Lock: $50
Step: $100
Amount: $50

→ Moderate trigger, reasonable protection
→ 1:2 risk protection ratio
→ Suitable for most strategies
```

---

**Use Cases:**

**Scalping with Protection:**
```
TP Target: $100
Trigger: $80
Lock: $50
Step: $50
Amount: $25

→ If profit reaches $80, guarantee $50
→ Protects against sudden reversals
→ Still aims for full $100 TP
```

**Swing Trading Trail:**
```
TP Target: $500
Trigger: $300
Lock: $200
Step: $100
Amount: $75

→ Let position develop to $300
→ Then protect $200 minimum
→ Trail to capture extended moves
```

---

**Important Considerations:**

- Profit lock modifies TP dynamically (not SL)
- Works in conjunction with regular TP (whichever hits first)
- Lock amount should be < Trigger amount (typical: 50-70% of trigger)
- Step size affects how aggressively you trail
- Consider broker spread and slippage in lock levels
- Currency amount varies with lot size and pip value

---

### Trail Wait & Trade (W&T)

**Purpose**: Dynamic trailing mechanism that closes positions when price retraces to a trailing line calculated from highest/lowest point reached.

**Enable W&T**

**Options**: Disabled / Enabled

**Default**: Disabled

---

**W&T Value**

**Purpose**: Defines the trailing line offset from extreme price.

**Range**: -1000000.0 to +1000000.0

**Default**: -15.0 points

**Unit**: Points OR Percentage (configurable)

**Sign Convention:**
- **BUY positions**: Typically negative (trails below high)
- **SELL positions**: Typically positive (trails above low)

---

**Use Percentage Toggle**

**Options**: Checkbox (unchecked = points, checked = percentage)

**Point Mode Example:**
```
W&T Value: -15 points

BUY Position:
- Entry: 1.10500
- Price reaches: 1.10700 (highest point)
- W&T Line: 1.10700 - 15 points = 1.10685
- Position closes if price falls to 1.10685
```

**Percentage Mode Example:**
```
W&T Value: -0.5%

BUY Position:
- Entry: 1.10500
- Price reaches: 1.10700 (highest point)
- W&T Line: 1.10700 × (1 - 0.005) = 1.10700 × 0.995 = 1.10146
- Position closes if price falls to 1.10146
```

---

**Mechanism Detail:**

**For BUY Positions:**
```
1. Track highest price reached since entry (peak)
2. Calculate: W&T_Line = peak + wt_value
3. Close position if current_price <= W&T_Line

Example (Point Mode, W&T: -15):
Entry: 1.10500
Price → 1.10600, Peak: 1.10600, W&T: 1.10585 (1.10600 - 15pts)
Price → 1.10700, Peak: 1.10700, W&T: 1.10685 (1.10700 - 15pts)
Price → 1.10750, Peak: 1.10750, W&T: 1.10735 (1.10750 - 15pts)
Price → 1.10680, Still: W&T: 1.10735 (peak still 1.10750)
Price → 1.10735 → CLOSE (W&T line hit)

Result: Closed at 1.10735, Profit: +235 points
```

**For SELL Positions:**
```
1. Track lowest price reached since entry (trough)
2. Calculate: W&T_Line = trough + wt_value
3. Close position if current_price >= W&T_Line

Example (Point Mode, W&T: +15):
Entry: 1.10500
Price → 1.10400, Trough: 1.10400, W&T: 1.10415 (1.10400 + 15pts)
Price → 1.10300, Trough: 1.10300, W&T: 1.10315 (1.10300 + 15pts)
Price → 1.10250, Trough: 1.10250, W&T: 1.10265 (1.10250 + 15pts)
Price → 1.10320, Still: W&T: 1.10265 (trough still 1.10250)
Price → 1.10265 → CLOSE (W&T line hit)

Result: Closed at 1.10265, Profit: +235 points
```

---

**W&T Value Configuration Guide:**

**Tight W&T (Quick Exits):**
```
Point Mode: -5 to -10 points (BUY) / +5 to +10 points (SELL)
Percentage Mode: -0.1% to -0.3%

Behavior:
- Follows very closely
- Exits quickly on retracement
- Locks profit fast
- May exit prematurely in volatile markets

Best For: Scalping, M1-M5, high volatility
```

**Medium W&T (Balanced):**
```
Point Mode: -15 to -30 points (BUY) / +15 to +30 points (SELL)
Percentage Mode: -0.5% to -1.0%

Behavior:
- Allows moderate retracement
- Balances profit protection and continuation
- Standard breathing room

Best For: Intraday, M15-H1, normal volatility
```

**Wide W&T (Let It Run):**
```
Point Mode: -50 to -100 points (BUY) / +50 to +100 points (SELL)
Percentage Mode: -1.5% to -3.0%

Behavior:
- Allows large retracements
- Stays in strong trends longer
- Higher risk of profit giveback
- Captures major moves

Best For: Swing, H1-H4, trending markets
```

---

**W&T vs Trailing SL Comparison:**

| Feature | Trailing SL | W&T |
|---------|-------------|-----|
| **Reference Point** | Current price | Extreme price (high/low) |
| **Calculation** | Price - Gap | Peak/Trough + Value |
| **Movement** | Follows every tick | Only updates on new extremes |
| **Exit Trigger** | SL hit | Price retraces to line |
| **Flexibility** | Less flexible | More dynamic |
| **Use Case** | Standard profit protection | Advanced trailing |

---

**Practical Examples:**

**Example 1: Scalping with Tight W&T**
```
Strategy: M5 EMA Crossover
Entry: 1.10500 BUY
W&T: -10 points
TP: 30 points (1.10530)

Flow:
Entry: 1.10500
Peak: 1.10525 → W&T: 1.10515 (already +15pts profit locked)
Price retraces to 1.10515 → CLOSE
Result: +15 points (50% of TP target, but safe exit)

Alternative (if continued):
Peak: 1.10530 → TP Hit
Result: +30 points (full target)
```

**Example 2: Swing Trading with Wide W&T**
```
Strategy: H1 SuperTrend
Entry: 1.10500 BUY
W&T: -50 points
TP: 200 points (1.10700)

Flow:
Entry: 1.10500
Peak: 1.10650 → W&T: 1.10600 (+100pts locked minimum)
Price retraces: 1.10620 → Holds (above W&T)
Peak: 1.10720 → W&T: 1.10670 (+170pts locked minimum)
Price retraces to 1.10670 → CLOSE
Result: +170 points (85% of target captured)
```

**Example 3: News Trading with Percentage W&T**
```
Strategy: News Breakout
Entry: 1.10500 BUY (on news spike)
W&T: -1.0% (percentage mode)
No TP (let W&T manage exit)

Flow:
Entry: 1.10500
Peak: 1.11000 (+500pts) → W&T: 1.10890 (1.11000 × 0.99)
Peak: 1.11500 (+1000pts) → W&T: 1.13485 (1.11500 × 0.99)
Price retraces to 1.13485 → CLOSE
Result: +985 points captured from news spike
```

---

**Important Notes:**

- W&T is **not a stop loss** - it's a profit-taking mechanism
- Initial SL still protects against losses
- W&T only activates after price moves favorably
- Consider volatility when setting W&T value
- Percentage mode better for different instruments (scales automatically)
- Can combine with Profit Lock for layered protection
- Test in demo to understand behavior before live trading

---

### Position Management

**Preserve Position**

**Purpose**: Prevents duplicate positions for the same strategy on the same symbol.

**Options**: Checkbox (unchecked / checked)

**Default**: Unchecked

**Behavior:**

**Unchecked (Preserve OFF):**
```
- Multiple positions allowed
- Each new signal opens a new trade
- Can have multiple BUY and SELL positions simultaneously

Example:
Signal 1: BUY EURUSD 0.01 lot at 1.10500
Signal 2: BUY EURUSD 0.01 lot at 1.10550 (second position opened)
Signal 3: BUY EURUSD 0.01 lot at 1.10600 (third position opened)

Result: 3 concurrent BUY positions
```

**Checked (Preserve ON):**
```
- Maximum 1 BUY position + 1 SELL position per strategy
- New BUY signal ignored if BUY position already open
- New SELL signal ignored if SELL position already open
- Allows hedging (1 BUY + 1 SELL simultaneously)

Example:
Signal 1: BUY EURUSD 0.01 lot at 1.10500 (opened)
Signal 2: BUY EURUSD 0.01 lot at 1.10550 (ignored - position exists)
Signal 3: SELL EURUSD 0.01 lot at 1.10600 (opened - different direction allowed)
Signal 4: SELL EURUSD 0.01 lot at 1.10650 (ignored - SELL position exists)

Result: 1 BUY + 1 SELL position (hedged)
```

**Use Cases:**

**Preserve OFF:**
- Grid trading strategies
- Pyramiding into trends
- Averaging strategies
- High-frequency scalping with multiple entries

**Preserve ON:**
- Single-position strategies
- Clear entry/exit rules
- Risk control (limit exposure)
- Avoid over-leveraging

**Recommendation**: Enable Preserve Position for most strategies to maintain clear position management and risk control.

---

### Re-Entry on Stop Loss

**Purpose**: Automatically re-enter trades after stop loss is hit, with configurable re-entry logic.

**Enable Re-Entry on SL**

**Options**: Checkbox (unchecked / checked)

**Default**: Unchecked

---

**SL Re-Entry Mode**

**Options:**

**RE-ASAP (Re-Enter As Soon As Possible)**
```
Behavior:
- Immediately re-enter in SAME direction after SL hit
- Uses current market conditions for new entry
- No waiting period

Example:
Position: BUY EURUSD at 1.10500, SL at 1.10480
SL Hit: Closed at 1.10480 (loss: -20pts)
Re-Entry: Immediately BUY EURUSD at 1.10475 (current price)
New SL: 1.10455 (20pts below new entry)

Use Case: Expect price to reverse quickly, trend continues
```

**RE-ASAP Reverse**
```
Behavior:
- Immediately re-enter in OPPOSITE direction after SL hit
- Assumes original direction was wrong

Example:
Position: BUY EURUSD at 1.10500, SL at 1.10480
SL Hit: Closed at 1.10480 (loss: -20pts)
Re-Entry: Immediately SELL EURUSD at 1.10475 (opposite direction)
New SL: 1.10495 (20pts above new entry)

Use Case: Failed breakout, expect reversal
```

**RE-COST (Re-Enter at Original Entry Price)**
```
Behavior:
- Wait for price to return to original entry level
- Re-enter in SAME direction at cost basis
- May wait indefinitely for price to return

Example:
Position: BUY EURUSD at 1.10500, SL at 1.10480
SL Hit: Closed at 1.10480 (loss: -20pts)
Waiting: Price at 1.10450, 1.10470, 1.10490...
Price Returns: 1.10500 reached
Re-Entry: BUY EURUSD at 1.10500 (original entry price)
New SL: 1.10480 (same SL distance)

Use Case: Believe in original analysis, want second chance at same price
```

**RE-COST Reverse**
```
Behavior:
- Wait for price to return to original entry level
- Re-enter in OPPOSITE direction at cost basis

Example:
Position: BUY EURUSD at 1.10500, SL at 1.10480
SL Hit: Closed at 1.10480 (loss: -20pts)
Waiting: Price climbs back...
Price Returns: 1.10500 reached
Re-Entry: SELL EURUSD at 1.10500 (opposite direction at original entry)
New SL: 1.10520 (20pts above)

Use Case: Original entry was resistance, now selling from that level
```

---

**SL Re-Entry Max Count**

**Purpose**: Limit the number of times re-entry can occur to control risk.

**Range**: 0-20

**Default**: 0 (no re-entries)

**Behavior:**
```
Max Count: 3

Sequence:
1. Initial Position: BUY at 1.10500
   SL Hit: -20pts
   Re-Entry 1: BUY at 1.10475 (count: 1)

2. SL Hit Again: -20pts
   Re-Entry 2: BUY at 1.10450 (count: 2)

3. SL Hit Again: -20pts
   Re-Entry 3: BUY at 1.10425 (count: 3)

4. SL Hit Again: -20pts
   Max Count Reached: NO MORE RE-ENTRIES

Total Loss: 4 × -20pts = -80pts
```

**Risk Management:**
```
Single Trade Risk: $100 (20pts × 0.1 lots)
Max Re-Entry: 3
Maximum Potential Loss: $400 (4 trades × $100)

→ Plan for total maximum risk when enabling re-entry
```

---

### Re-Entry on Take Profit

**Purpose**: Automatically re-enter trades after take profit is hit, capturing extended moves.

**Enable Re-Entry on TP**

**Options**: Checkbox (unchecked / checked)

**Default**: Unchecked

---

**TP Re-Entry Mode**

**Options**: Same as SL Re-Entry Mode

**RE-ASAP**
```
Example:
Position: BUY EURUSD at 1.10500, TP at 1.10540
TP Hit: Closed at 1.10540 (profit: +40pts)
Re-Entry: Immediately BUY EURUSD at 1.10545 (current price)
New TP: 1.10585 (40pts above new entry)

Use Case: Strong trend, expect continuation
```

**RE-ASAP Reverse**
```
Example:
Position: BUY EURUSD at 1.10500, TP at 1.10540
TP Hit: Closed at 1.10540 (profit: +40pts)
Re-Entry: Immediately SELL EURUSD at 1.10545 (opposite)
New TP: 1.10505 (40pts below)

Use Case: Expect resistance at TP level, reversal likely
```

**RE-COST**
```
Example:
Position: BUY EURUSD at 1.10500, TP at 1.10540
TP Hit: Closed at 1.10540 (profit: +40pts)
Waiting: Price retraces...
Price Returns: 1.10500 reached
Re-Entry: BUY EURUSD at 1.10500 (original entry)

Use Case: Take profit, wait for pullback, re-enter trend
```

**RE-COST Reverse**
```
Example:
Position: BUY EURUSD at 1.10500, TP at 1.10540
TP Hit: Closed at 1.10540 (profit: +40pts)
Waiting: Price retraces...
Price Returns: 1.10500 reached
Re-Entry: SELL EURUSD at 1.10500 (opposite at original entry)

Use Case: Ride up, then ride back down (range trading)
```

---

**TP Re-Entry Max Count**

**Purpose**: Limit pyramiding or re-entries after TP to avoid overexposure.

**Range**: 0-20

**Default**: 0

**Example (Trend Following with RE-ASAP):**
```
Configuration:
TP: 40 points
Re-Entry Mode: RE-ASAP
Max Count: 5

Strong Uptrend Scenario:
1. BUY at 1.10500, TP at 1.10540 (+40pts profit)
2. RE-ASAP: BUY at 1.10545, TP at 1.10585 (+40pts profit)
3. RE-ASAP: BUY at 1.10590, TP at 1.10630 (+40pts profit)
4. RE-ASAP: BUY at 1.10635, TP at 1.10675 (+40pts profit)
5. RE-ASAP: BUY at 1.10680, TP at 1.10720 (+40pts profit)
6. Max Count Reached: No more re-entries

Total Profit: 5 × 40pts = 200pts captured from extended trend
```

---

**Re-Entry Strategy Recommendations:**

**Conservative:**
```
SL Re-Entry: Disabled
TP Re-Entry: RE-COST with Max Count 1
→ Only re-enter after pullback to original level
→ Limits exposure, waits for confirmation
```

**Moderate:**
```
SL Re-Entry: RE-ASAP with Max Count 2
TP Re-Entry: RE-ASAP with Max Count 2
→ Allows quick re-entries in strong trends
→ Limited exposure (max 2 additional trades)
```

**Aggressive:**
```
SL Re-Entry: RE-ASAP Reverse with Max Count 3
TP Re-Entry: RE-ASAP with Max Count 5
→ Reverses on SL (assumes wrong direction)
→ Pyramids on TP (captures extended moves)
→ High risk, high reward potential
```

---

### Trading Hours

**Purpose**: Restrict signal generation to specific time windows, avoiding unfavorable market conditions.

**Enable Time Restrictions**

**Options**: Checkbox (unchecked / checked)

**Default**: Unchecked

---

**Start Time / End Time**

**Format**: HH:mm (24-hour format)

**Default**: 09:00 to 17:00

**Timezone**: Uses MT5 broker server time

---

**Normal Session (Start < End):**
```
Start: 09:00
End: 17:00

Behavior:
- Signals ONLY generated between 09:00 and 17:00
- Existing positions remain open outside hours
- No new entries before 09:00 or after 17:00

Use Case: Trade London/NY session only, avoid Asian session
```

**Overnight Session (Start > End):**
```
Start: 22:00
End: 05:00

Behavior:
- Signals generated from 22:00 to 23:59 AND from 00:00 to 05:00
- Spans midnight
- Existing positions remain open outside hours

Use Case: Trade Asian session overnight, avoid European session
```

---

**Practical Examples:**

**London Session Only:**
```
Start: 08:00
End: 16:00
Timezone: GMT+0 broker

→ Captures high liquidity London hours
→ Avoids low liquidity Asian session
```

**New York Session Only:**
```
Start: 13:00
End: 22:00
Timezone: GMT+0 broker

→ Trades during US market hours
→ Captures high volatility news releases
```

**Avoid News Hours:**
```
Start: 10:00
End: 14:00
Skip: 14:30-15:30 (major news time)

→ Trade stable hours only
→ Close positions before high-impact news
```

**Scalping Active Hours:**
```
Start: 08:00
End: 11:00, AND Start: 14:00, End: 17:00

→ Trade high-volume hours only
→ Avoid lunch hour low liquidity
```

---

**Important Considerations:**

- **Existing Positions**: Trading hours only affect NEW entries, not open positions
- **Position Management**: Consider closing all positions at end time
- **Timezone**: Verify broker server timezone (GMT, GMT+2, GMT+3, etc.)
- **DST Changes**: Daylight saving time may shift effective hours
- **Backtesting**: Historical results depend on accurate time filtering
- **Weekends**: System automatically handles weekend (no trading Sat/Sun)

---

## Advanced Features

### Signal Priority Resolution

When both Buy and Sell conditions evaluate to TRUE simultaneously:

**Default Behavior: BUY Priority**
```
Evaluation Order:
1. Evaluate Buy Conditions
2. If Buy = TRUE → Return BUY signal (stop here)
3. If Buy = FALSE → Evaluate Sell Conditions
4. If Sell = TRUE → Return SELL signal
5. If both FALSE → Return None

Result: BUY signal always takes precedence
```

**Why This Matters:**
```
Scenario: Volatile candle with wide range

Conditions:
Buy: Current Price > Previous High (TRUE at 1.10600)
Sell: Current Price < Previous Close (TRUE at 1.10550)

Both conditions TRUE on same tick!

Resolution: BUY signal executed (priority rule)
SELL signal ignored
```

**Recommended Enhancement:**

Consider implementing **Conflict Resolution Mode** setting:

```
Options:
1. BUY Priority (current default)
2. SELL Priority
3. Ignore Both (no signal when conflict)
4. Last Signal Direction (maintain momentum)
5. Stronger Signal (compare condition margins)

This would provide more flexibility for different strategy types.
```

---

### Multi-Timeframe Considerations

While the system operates on a single configured timeframe, advanced traders often consider multiple timeframes:

**Top-Down Analysis Approach:**
```
Higher Timeframe (H4): Identify overall trend direction
Medium Timeframe (H1): Identify entry zones
Lower Timeframe (M15): Execute precise entries

Implementation:
1. Check H4 EMA alignment manually or via external indicator
2. Add condition: Trade only with H4 trend direction
3. Use configured timeframe (M15) for signal generation
```

**Example Multi-Timeframe Strategy:**
```
Strategy Timeframe: M15
Additional Manual Check: H4 trend

Buy Conditions (M15):
- EMA_20 Crosses Above EMA_50 [AND]
- Current Price > EMA_100 [AND]
- Volume > Volume_MA

Manual Filter (H4):
- Only take Buy signals if H4