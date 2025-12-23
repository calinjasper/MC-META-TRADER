# Filtering Ticks in PocketBase - Complete Guide

## Overview

With the single `ticks` collection, you can easily filter and view data for specific symbols using PocketBase's built-in filtering features.

---

## Quick Start

### 1. Open PocketBase Admin UI
```
http://127.0.0.1:8090/_/
```

### 2. Navigate to Ticks Collection
- Click on **"ticks"** in the left sidebar (under "Others" section)

### 3. Use the Filter Box
- At the top of the records view, you'll see a search/filter box
- Enter your filter expression there

---

## Basic Filtering

### Filter by Symbol

**Show only XAUUSD ticks:**
```
symbol = "XAUUSDm"
```

**Show only EURUSD ticks:**
```
symbol = "EURUSDm"
```

**Show only GBPUSD ticks:**
```
symbol = "GBPUSDm"
```

### Filter by Time

**Show recent ticks (last hour):**
```
timestamp >= 1734900000000
```

*Note: Replace with actual timestamp. Use https://www.epochconverter.com/ to convert dates.*

**Show ticks from today:**
```
timestamp >= 1734825600000
```

---

## Advanced Filtering

### Contains/Partial Match

**Show all symbols containing "USD":**
```
symbol ~ "USD"
```

**Show all EUR pairs:**
```
symbol ~ "EUR"
```

**Show all XAU (Gold) pairs:**
```
symbol ~ "XAU"
```

### Combine Multiple Filters

**Show XAUUSD ticks from specific time range:**
```
symbol = "XAUUSDm" && timestamp >= 1734825600000 && timestamp <= 1734912000000
```

**Show all USD pairs with high bid price:**
```
symbol ~ "USD" && bid > 100
```

**Show ticks with large spread:**
```
spread > 0.001
```

### Price Range Filters

**Show EURUSD ticks above certain price:**
```
symbol = "EURUSDm" && bid > 1.10
```

**Show XAUUSD ticks in price range:**
```
symbol = "XAUUSDm" && bid >= 4400 && bid <= 4450
```

### Volume Filters

**Show ticks with volume:**
```
volume > 0
```

**Show high-volume ticks:**
```
volume >= 1000
```

---

## Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equals | `symbol = "XAUUSDm"` |
| `!=` | Not equals | `symbol != "EURUSDm"` |
| `>` | Greater than | `bid > 4400` |
| `>=` | Greater or equal | `timestamp >= 1734825600000` |
| `<` | Less than | `spread < 0.0005` |
| `<=` | Less or equal | `volume <= 100` |
| `~` | Contains | `symbol ~ "USD"` |
| `!~` | Does not contain | `symbol !~ "EUR"` |
| `&&` | AND | `symbol = "XAUUSDm" && bid > 4400` |
| `\|\|` | OR | `symbol = "XAUUSDm" \|\| symbol = "EURUSDm"` |

---

## Saving Filter Presets

### Create a Saved Filter

1. Enter your filter in the search box
2. Click the **"⭐ Save filter"** button (if available)
3. Give it a name (e.g., "XAUUSD Only")
4. Click Save

### Use a Saved Filter

1. Click the filter dropdown
2. Select your saved filter
3. Results will be filtered instantly

---

## Sorting Results

### Sort by Time (Newest First)
Click the **"timestamp"** column header twice

### Sort by Symbol
Click the **"symbol"** column header

### Sort by Price
Click the **"bid"** or **"ask"** column header

---

## Exporting Filtered Data

### Method 1: Direct Export from PocketBase

1. Apply your filter
2. Click the **"⋮"** (three dots) menu
3. Select **"Export"**
4. Choose format (CSV, JSON)
5. Download

### Method 2: Using Export Script

The `export_ticks_to_csv.py` script supports filtering:

```bash
# Export specific symbol
python export_ticks_to_csv.py --symbol XAUUSD

# Export date range
python export_ticks_to_csv.py --from 2025-12-22 --to 2025-12-23

# Export specific symbol with date range
python export_ticks_to_csv.py --symbol EURUSD --from 2025-12-20 --to 2025-12-22
```

---

## Common Filter Examples

### By Symbol Type

**Forex pairs only:**
```
symbol ~ "USD" || symbol ~ "EUR" || symbol ~ "GBP"
```

**Stock symbols:**
```
symbol ~ "m" && symbol !~ "USD" && symbol !~ "EUR"
```

**Commodities (Gold/Silver):**
```
symbol ~ "XAU" || symbol ~ "XAG"
```

### By Trading Session

**Asian session (approximate, using timestamp):**
```
timestamp >= 1734912000000 && timestamp <= 1734930000000
```

**US session:**
```
timestamp >= 1734951600000 && timestamp <= 1734987600000
```

### By Price Movement

**Large spread (potential volatility):**
```
spread > 0.002
```

**Tight spread (low volatility):**
```
spread < 0.0001
```

**Price above moving average (example):**
```
bid > 4430
```

### By Data Quality

**Ticks with complete data:**
```
volume > 0 && last > 0
```

**Recent ticks only (last 24 hours):**
```
timestamp >= 1734825600000
```

---

## Tips & Tricks

### 1. Use Wildcards for Symbol Matching
Instead of exact match, use `~` for partial matching:
```
symbol ~ "m"  # Shows all symbols ending with 'm'
```

### 2. Combine Time and Symbol Filters
For focused analysis:
```
symbol = "XAUUSDm" && timestamp >= 1734912000000
```

### 3. Find Anomalies
Look for unusual spreads or prices:
```
spread > 0.01 || bid < 0.01
```

### 4. Quick Date Conversion
Use online tools to convert dates to Unix timestamps:
- https://www.epochconverter.com/
- https://www.unixtimestamp.com/

Multiply by 1000 for milliseconds (PocketBase format)

### 5. Create Filters for Each Symbol
Save a filter preset for each symbol you trade:
- "XAUUSD Ticks" → `symbol = "XAUUSDm"`
- "EURUSD Ticks" → `symbol = "EURUSDm"`
- "GBPUSD Ticks" → `symbol = "GBPUSDm"`

---

## Performance Tips

### 1. Add Indexes
For faster filtering, add indexes on commonly filtered fields:
- `symbol` (already indexed)
- `timestamp`

### 2. Limit Results
When browsing large datasets, use time filters to reduce results:
```
timestamp >= 1734912000000  # Last 24 hours only
```

### 3. Export Instead of Browsing
For large datasets, export to CSV and analyze in Excel/Python

---

## Troubleshooting

### No Results Found

**Check:**
1. Symbol name is exact (case-sensitive)
2. Timestamps are in milliseconds
3. Filter syntax is correct
4. Data actually exists for that period

### Slow Performance

**Solutions:**
1. Add time range filter
2. Create indexes
3. Use export script for large datasets

### Filter Not Working

**Common Issues:**
1. Missing quotes around strings: `symbol = XAUUSDm` ❌ → `symbol = "XAUUSDm"` ✅
2. Wrong operator: `symbol == "XAUUSDm"` ❌ → `symbol = "XAUUSDm"` ✅
3. Wrong timestamp format: seconds instead of milliseconds

---

## Real-World Examples

### Day Trading View
```
symbol = "EURUSDm" && timestamp >= 1734912000000
```

### Swing Trading Analysis
```
symbol = "XAUUSDm" && timestamp >= 1734739200000
```

### Multi-Symbol Dashboard
```
symbol ~ "USD" && timestamp >= 1734912000000
```

### High-Volatility Periods
```
spread > 0.002 && timestamp >= 1734912000000
```

### Low-Liquidity Detection
```
volume < 10 && timestamp >= 1734912000000
```

---

## Summary

✅ **Single Collection** = Simple management  
✅ **Powerful Filters** = Easy symbol viewing  
✅ **Fast Queries** = With proper indexes  
✅ **Flexible Export** = CSV, JSON, or script  

**Your ticks are now organized and easy to filter!** 🎯

