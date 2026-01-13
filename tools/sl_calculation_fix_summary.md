# SL Calculation Bug Fix - Summary

## Problem Identified

The SL calculation was producing wrong values (0.20 points instead of 0.50 points) because:

1. **Stale Strategy Object in Memory**: Strategy objects are loaded once at startup into `strategy_manager`
2. **JSON Updated But Object Not Reloaded**: When JSON file is modified (manually or via edit dialog), the in-memory object retains old values
3. **Calculation Uses Stale Data**: `calculate_strategy_sl_tp()` reads `sl_value` from the in-memory object, not from JSON
4. **Result**: Wrong SL calculation (e.g., 20.0 points instead of 50.0 points)

### Example
- JSON file has: `sl_value: 50.0`
- In-memory object has: `sl_value: 20.0` (from initial load)
- Calculation uses: `20.0 * 0.01 = 0.20 points` ❌
- Should use: `50.0 * 0.01 = 0.50 points` ✅

## Solution Implemented

### 1. Added `reload_strategy()` Method to StrategyManager
**File**: `src/strategy/strategy_manager.py`

- Reloads a strategy from JSON file
- Preserves runtime state (enabled status, market data panel references)
- Sets MT5 connector if provided
- Logs the reloaded values for verification

**Usage**:
```python
strategy_manager.reload_strategy("BTC_BUY", mt5_connector=mt5)
```

### 2. Added `reload_all_strategies()` Method
**File**: `src/strategy/strategy_manager.py`

- Reloads all strategies from JSON files
- Useful for ensuring all strategies are in sync after external JSON edits

### 3. Auto-Reload After Save in Strategy Edit Dialog
**File**: `src/gui/strategy_edit_dialog.py`

- After saving strategy to JSON, automatically reloads it from disk
- Ensures in-memory object matches JSON file
- Updates the strategy reference to the reloaded object
- Logs the save and reload operations

**Changes**:
- Added logging when `sl_value` is updated
- Added reload call after `persistence.save_strategy()`
- Updates `self.strategy` reference to reloaded object

### 4. Safety Checks in SL Calculation
**File**: `src/gui/main_window.py`

- Added validation to detect potentially stale `sl_value`
- Warns if `sl_value` is 0.0 or invalid when SL is enabled
- Logs calculation details for debugging

**Changes**:
- Added safety check before calculation
- Added debug logging with calculation details
- Helps identify when stale data is being used

## How It Works

### Before Fix
1. Strategy loaded at startup: `sl_value=20.0` (from old JSON)
2. User edits JSON manually: `sl_value=50.0`
3. Calculation runs: Uses `sl_value=20.0` from memory ❌
4. Result: Wrong SL calculation

### After Fix
1. Strategy loaded at startup: `sl_value=20.0`
2. User edits JSON manually: `sl_value=50.0`
3. User saves via edit dialog: 
   - Updates in-memory object: `sl_value=50.0`
   - Saves to JSON: `sl_value=50.0`
   - **Reloads from JSON**: Ensures sync ✅
4. Calculation runs: Uses `sl_value=50.0` from reloaded object ✅
5. Result: Correct SL calculation

## Testing

To verify the fix works:

1. **Test 1: Edit Strategy via Dialog**
   - Open strategy edit dialog
   - Change `sl_value` from 20.0 to 50.0
   - Save
   - Check logs for: "Strategy X reloaded from JSON (sl_value=50.0)"
   - Verify calculation uses 50.0

2. **Test 2: Manual JSON Edit**
   - Edit JSON file directly: `sl_value: 50.0`
   - Call `strategy_manager.reload_strategy("BTC_BUY")`
   - Verify calculation uses 50.0

3. **Test 3: Safety Check**
   - Set `sl_value=0.0` in strategy object
   - Trigger calculation
   - Check logs for warning about invalid `sl_value`

## Files Modified

1. `src/strategy/strategy_manager.py`
   - Added `reload_strategy()` method
   - Added `reload_all_strategies()` method

2. `src/gui/strategy_edit_dialog.py`
   - Added reload after save
   - Added logging for `sl_value` updates

3. `src/gui/main_window.py`
   - Added safety checks in `calculate_strategy_sl_tp()`
   - Added debug logging for calculation details

## Benefits

1. **Automatic Sync**: Strategies are automatically reloaded after save
2. **Data Integrity**: In-memory objects always match JSON files
3. **Debugging**: Logging helps identify stale data issues
4. **Safety**: Validation catches invalid configurations early
5. **Flexibility**: Can manually reload strategies if needed

## Future Improvements

1. **Auto-reload on JSON file change**: Watch for JSON file modifications and auto-reload
2. **Version tracking**: Track strategy versions to detect stale data
3. **UI indicator**: Show when strategy needs reloading
4. **Bulk reload**: Add UI button to reload all strategies

## Notes

- The reload preserves runtime state (enabled status, references)
- MT5 connector is passed to reloaded strategies if available
- Logging helps track when strategies are reloaded and why
- The fix is backward compatible - existing code continues to work
