# CHoCH Price Implementation Confirmation

## ✅ Confirmed: CHoCH Price = Close Price of Candle That Broke the Pivot

### Implementation Status

Both the **Python Strategy** and **MT5 Indicator** correctly implement CHoCH price as the **close price of the candle that broke the pivot**, not the pivot price itself.

---

## Python Strategy Implementation

### Location: `src/strategy/smc_strategy.py`

**CHoCH Event Detection (Lines 250-262):**
```python
# Store event if detected
if event:
    # IMPORTANT: CHoCH/BOS price is the CLOSE price of the candle that broke the pivot
    # This is the confirmation level where the structure change was confirmed
    # NOT the pivot price itself, but the close price when the pivot was broken
    self.all_events.append(StructureEvent(
        event_type=event,
        direction=direction,
        price=current_close,  # Close price of candle that broke the pivot
        index=i
    ))
    
    # Update last event prices
    if event == "CHoCH":
        # CHoCH price = close price of the candle that broke the pivot
        self.last_choch_price = current_close
        self.last_choch_direction = direction
```

**Key Points:**
- ✅ `price=current_close` - Uses close price, not pivot price
- ✅ `self.last_choch_price = current_close` - Stores close price
- ✅ `self.active_choch_price = event.price` - Uses event price (which is close price)

**StructureEvent Definition (Line 32-38):**
```python
@dataclass
class StructureEvent:
    """Represents a BOS or CHoCH event"""
    event_type: str  # "BOS" | "CHoCH"
    direction: str  # "UP" | "DOWN"
    price: float  # Close price of the candle that broke the pivot (NOT the pivot price itself)
    index: int  # Index in the candles array
```

---

## MT5 Indicator Implementation

### Location: `src/indicators/smc_indicator.mq5`

**CHoCH Event Storage (Lines 887-899):**
```mql5
else if(event == "CHoCH")
{
   // IMPORTANT: CHoCH price is the CLOSE price of the candle that broke the pivot
   // This is the confirmation level where the structure change was confirmed
   // NOT the pivot price itself, but the close price when the pivot was broken
   int eventCount = ArraySize(chochEventPrices);
   ArrayResize(chochEventPrices, eventCount + 1);
   ArrayResize(chochEventIndices, eventCount + 1);
   chochEventPrices[eventCount] = currentClose;  // Close price of candle that broke pivot
   chochEventIndices[eventCount] = barIndex;
   
   // Also set buffer for visual markers (if EmitOn allows)
   if(EmitOn == "CHoCH" || EmitOn == "BOTH")
   {
      CHoCHBuffer[i] = currentClose;
   }
}
```

**Key Points:**
- ✅ `chochEventPrices[eventCount] = currentClose` - Stores close price
- ✅ `CHoCHBuffer[i] = currentClose` - Draws line at close price
- ✅ Uses `currentClose` (close price), not pivot price

---

## How It Works

### Example Scenario:

1. **Pivot High** is detected at price **4500.000**
2. **Price breaks above** the pivot high
3. **Candle closes** at **4493.669**
4. **CHoCH Event** is triggered (if bias was BEARISH)
5. **CHoCH Price = 4493.669** (the close price, NOT 4500.000)

### Why Close Price?

- **Confirmation Level**: The close price confirms the structure change
- **Trading Level**: This is the actual price where the market confirmed the change
- **Consistency**: Both strategy and indicator use the same logic
- **Visual Match**: The solid yellow line in MT5 shows this close price level

---

## Verification

### In Your Chart (AUUSDm/XAUSD):

- **Solid Yellow Line at 4493.669** = CHoCH Line
- **CHoCH Price = 4493.669** = Close price of candle that broke the pivot
- **Pivot High** (that was broken) = Likely around 4500 or higher
- **Strategy uses 4493.669** for all CHoCH price references

### Strategy Usage:

When the strategy references `smc_choch_price` in conditions:
- It uses the **close price** (4493.669)
- NOT the pivot price (4500.000)
- This matches the MT5 indicator display

---

## Summary

✅ **Both implementations are correct and consistent**

- Python Strategy: Uses `current_close` for CHoCH price
- MT5 Indicator: Uses `currentClose` for CHoCH price
- Both store and use the **close price of the candle that broke the pivot**
- This is the **confirmation level** where structure change was confirmed
- The solid yellow line in MT5 shows this close price level

**CHoCH Price = Close Price of Candle That Broke the Pivot** ✅
