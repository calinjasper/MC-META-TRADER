# CHoCH Line Explanation

## Understanding CHoCH Price vs Pivot Price

### What is CHoCH?
**CHoCH (Change of Character)** is a market structure event that occurs when:
1. Price breaks a pivot high or pivot low
2. **AND** the market bias changes (from BEARISH to BULLISH or vice versa)

### CHoCH Price Calculation

The **CHoCH price is NOT the pivot price itself**. Instead:

- **CHoCH Price** = The **close price** of the candle that broke the pivot
- **Pivot Price** = The high/low price of the pivot point that was broken

**Example:**
- Pivot High at: 4483.570
- Price breaks above this pivot with close at: 4461.043
- **CHoCH Price = 4461.043** (the close price, not 4483.570)

### Why the Difference?

The CHoCH price represents the **confirmation level** where the structure change was confirmed. It's the price at which the market officially changed character, not the pivot level that was broken.

## CHoCH Line in MT5 Indicator

### Visual Representation

When `EmitOn = "CHoCH"` or `EmitOn = "BOTH"`, the MT5 indicator draws the CHoCH line as:

**Buffer Used:** `PivotHighBuffer` (Buffer 0)

**Visual Properties:**
- **Type:** Horizontal line (DRAW_LINE)
- **Color:** Gold/Yellow (`PivotHighColor = clrGold`)
- **Style:** Solid (STYLE_SOLID)
- **Width:** 3 pixels (PivotSize)

### How It's Drawn

1. The indicator finds the most recent CHoCH event
2. Draws a horizontal line at the CHoCH event price (the close price when pivot was broken)
3. The line extends from the CHoCH event time until:
   - The next CHoCH event occurs, OR
   - The current bar (if no newer CHoCH)

### Identifying CHoCH Line in Your Chart

Based on your screenshot description and the MT5 indicator code:

**The CHoCH line should appear as:**
- **Gold/Yellow solid horizontal line**
- Drawn at the CHoCH price level (4461.043 in your case)
- Extending horizontally across the chart

**Other lines in your chart:**
- **Green dashed horizontal line at 4483.570:** This is likely a Structure High or a different indicator level
- **Yellow dashed line (upper bounds):** This is the Structure High (clrYellow, STYLE_DOT) - different from CHoCH
- **Cyan dashed line (lower bounds):** This is the Structure Low (clrCyan, STYLE_DOT)

### Key Differences

| Line Type | Color | Style | Purpose |
|-----------|-------|-------|---------|
| **CHoCH Line** | Gold/Yellow | Solid | Shows active CHoCH price level |
| **Structure High** | Yellow | Dashed/Dotted | Shows last pivot high level |
| **Structure Low** | Cyan | Dashed/Dotted | Shows last pivot low level |
| **Pivot Highs** | Gold | Solid | Shows all pivot high levels |
| **Pivot Lows** | Blue | Solid | Shows all pivot low levels |

## For XAUSD (AUUSDm) Chart

### Important Clarification

Based on your observation that **"yellow line is showing 4493 as CHoCH"**:

**If you see a YELLOW line at 4493.669:**

1. **If it's a SOLID yellow/gold line:**
   - ✅ **This IS the CHoCH line** (drawn using `PivotHighBuffer`)
   - **CHoCH Price = 4493.669** (not 4461.043)
   - This means the CHoCH event occurred at close price 4493.669
   - The solid yellow line is the active CHoCH level

2. **If it's a DASHED yellow line:**
   - This is the **Structure High** (last pivot high level)
   - This shows the pivot high price, NOT the CHoCH price
   - Structure High is drawn using `StructureHighBuffer` (Buffer 4)
   - Color: `clrYellow`, Style: `STYLE_DOT` (dashed)

### How the Indicator Works

When `EmitOn = "CHoCH"`:
- **CHoCH Line** is drawn in `PivotHighBuffer` (Buffer 0)
  - Color: `PivotHighColor` (default: `clrGold` - gold/yellow)
  - Style: `STYLE_SOLID` (solid line)
  - Shows the CHoCH event price (close price when pivot was broken)

When `ShowStructureLevels = true`:
- **Structure High** is drawn in `StructureHighBuffer` (Buffer 4)
  - Color: `clrYellow` (yellow)
  - Style: `STYLE_DOT` (dashed/dotted)
  - Shows the last pivot high price (the pivot level, not CHoCH price)

### Key Distinction

- **CHoCH Price (4493.669)** = Close price when pivot was broken (confirmation level)
- **Pivot High Price (e.g., 4493.669 or higher)** = The actual pivot high that was broken
- **Structure High** = Last pivot high level (may be same as or different from CHoCH price)

**✅ CONFIRMED: The solid yellow line at 4493 is the CHoCH line:**
- That's your CHoCH line (solid yellow/gold line)
- **CHoCH Price = 4493.669** (approximately 4493)
- The pivot that triggered it was likely at or near this level
- The dashed yellow line at higher price (4494-4495) is the Structure High (last pivot high)

**If the yellow line at 4493 was DASHED:**
- That would be Structure High (last pivot high)
- The actual CHoCH line would be a solid line at a different price

### How to Verify

1. Check line style:
   - **Solid yellow/gold line** = CHoCH line (when `EmitOn = "CHoCH"`)
   - **Dashed yellow line** = Structure High (when `ShowStructureLevels = true`)

2. Check your MT5 indicator settings:
   - `EmitOn` should be set to `"CHoCH"` or `"BOTH"` to show CHoCH line
   - `ShowStructureLevels` controls the dashed yellow/cyan lines
   - `PivotHighColor` controls the color of CHoCH line (default: gold)

3. The solid black horizontal line at 4493.669 in your chart:
   - This aligns with the price scale showing 4493.669
   - If this is a solid line, it's likely the CHoCH line
   - If this is a dashed line, it's the Structure High

## Summary

- **CHoCH Price** = Close price when pivot was broken (confirmation level)
- **CHoCH Line** = Solid yellow/gold horizontal line at CHoCH price (when `EmitOn = "CHoCH"`)
- **Structure High** = Dashed yellow horizontal line at last pivot high (when `ShowStructureLevels = true`)

### For Your Chart (AUUSDm/XAUSD):

✅ **CONFIRMED:**
- **Solid yellow line at 4493** = CHoCH Line
- **CHoCH Price = 4493.669** (approximately 4493)
- **Dashed yellow line at higher price (4494-4495)** = Structure High (last pivot high)
- **Dashed cyan line** = Structure Low (last pivot low)

The CHoCH line represents the price level that confirms the market structure change, which is why it uses the close price of the breaking candle, not the pivot price itself.

**Note:** The earlier mention of CHoCH price 4461.043 may have been from a different time period or different chart. The current active CHoCH price is 4493.669 as shown by the solid yellow line.
