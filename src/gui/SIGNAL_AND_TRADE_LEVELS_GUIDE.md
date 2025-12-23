# Signal & Trade Level Display Features

## Overview

The chart widget now includes two powerful visualization features to help traders track strategy signals and active trade positions directly on the chart:

1. **Show Signals** - Displays buy/sell arrows when strategies generate trading signals
2. **Trade Levels** - Shows horizontal lines at entry, stop loss, and take profit prices for active trades

## Features

### Show Signals Toggle

When enabled, this feature displays visual markers (arrows) on the chart at the exact moment a strategy generates a buy or sell signal.

**Visual Elements:**
- **BUY Signal**: Green upward arrow (▲) below the candlestick
- **SELL Signal**: Red downward arrow (▼) above the candlestick
- **Hover Text**: Shows strategy name and signal type (e.g., "MyStrategy: BUY")

**Signal Storage:**
- Automatically stores the last 100 signals per symbol to avoid memory bloat
- Signals are associated with timestamps and prices
- Only signals for the currently viewed symbol are displayed

### Trade Levels Toggle

When enabled, this feature displays horizontal price lines showing entry points and exit targets for all active positions on the current symbol.

**Visual Elements:**
- **Entry Line (BUY)**: Blue solid line (#2196F3) with label "Entry: [ticket] BUY [volume]"
- **Entry Line (SELL)**: Orange solid line (#FF9800) with label "Entry: [ticket] SELL [volume]"
- **Stop Loss Line**: Red dashed line (#F44336) with label "SL: [ticket]"
- **Take Profit Line**: Green dashed line (#4CAF50) with label "TP: [ticket]"

**Line Properties:**
- Entry lines: Solid, 2px width
- SL/TP lines: Dashed, 1px width
- All lines show labels on the price axis
- Lines update automatically when positions are opened or closed

## Usage

### Enabling Show Signals

1. Navigate to the Charts tab
2. Locate the "Show Signals" checkbox in the top control panel
3. Check the box to enable signal display
4. All strategy signals for the current symbol will appear as arrows on the chart
5. Hover over any arrow to see the strategy name and signal type

### Enabling Trade Levels

1. Navigate to the Charts tab
2. Locate the "Trade Levels" checkbox in the top control panel (next to Show Signals)
3. Check the box to enable trade level display
4. All active positions for the current symbol will show entry, SL, and TP lines
5. Lines will update automatically as positions change

### Viewing Signal History

- Signals remain visible on the chart even after the position is closed
- The chart stores up to 100 signals per symbol
- Change symbols to see signals for different instruments
- Uncheck "Show Signals" to hide all arrows temporarily

### Monitoring Active Trades

- Trade level lines only show for currently open positions
- When a position is closed, the lines disappear automatically
- If no positions are open, no lines will be displayed
- Lines follow the current symbol - switch symbols to see trades on different instruments

## Technical Details

### Data Flow - Show Signals

```
Strategy generates signal
    ↓
MainWindow.update_strategies() captures signal
    ↓
ChartWidget.add_strategy_signal() stores signal data
    ↓
ChartWidget.get_signal_markers() formats for TradingView
    ↓
Bridge emits markersUpdated signal
    ↓
JavaScript updateMarkers() renders arrows on chart
```

### Data Flow - Trade Levels

```
User enables Trade Levels checkbox
    ↓
ChartWidget.on_trade_levels_toggled() sets flag
    ↓
ChartWidget.refresh_chart() is called
    ↓
ChartWidget.get_trade_level_lines() queries OrderManager
    ↓
OrderManager.get_positions() returns active trades
    ↓
Format as price line data (entry, SL, TP)
    ↓
Bridge emits priceLinesUpdated signal
    ↓
JavaScript updatePriceLines() creates/removes lines
```

### Signal Marker Format

Each signal marker contains:
```python
{
    'time': 1234567890,              # Unix timestamp
    'position': 'belowBar',          # 'belowBar' for BUY, 'aboveBar' for SELL
    'color': '#00E676',              # Green for BUY, Red (#FF1744) for SELL
    'shape': 'arrowUp',              # 'arrowUp' for BUY, 'arrowDown' for SELL
    'text': 'Strategy Name: BUY'    # Hover tooltip text
}
```

### Price Line Format

Each price line contains:
```python
{
    'price': 1850.50,                           # Price level
    'color': '#2196F3',                         # Blue/Orange for entry, Red for SL, Green for TP
    'lineWidth': 2,                             # 2 for entry, 1 for SL/TP
    'lineStyle': 0,                             # 0=Solid, 2=Dashed
    'axisLabelVisible': True,                   # Show label on price axis
    'title': 'Entry: 12345 BUY 0.10'          # Label text
}
```

## Integration with Strategies

### Automatic Signal Tracking

Signals are automatically captured when:
- Any enabled strategy generates a BUY or SELL signal
- The signal is processed in `MainWindow.update_strategies()`
- Before the trade is executed via `execute_strategy_signal()`

### Signal Information Captured

For each signal, the system stores:
- **Symbol**: Which instrument the signal is for
- **Signal Type**: BUY or SELL
- **Price**: Current market price when signal was generated
- **Timestamp**: Exact moment the signal occurred
- **Strategy Name**: Which strategy generated the signal

### Trade Level Information

For each active position, the system displays:
- **Entry Price**: The price at which the position was opened
- **Trade Direction**: BUY (blue) or SELL (orange) 
- **Volume**: Lot size of the position
- **Ticket Number**: MT5 ticket ID for reference
- **Stop Loss**: If set, shown as red dashed line
- **Take Profit**: If set, shown as green dashed line

## Performance Considerations

### Memory Management

- **Signal History**: Limited to 100 signals per symbol
- Older signals are automatically removed when the limit is reached
- Signals are stored in memory only (not persisted to disk)

### Chart Performance

- Signal markers use TradingView's built-in `setMarkers()` API for optimal rendering
- Price lines use the native `createPriceLine()` API
- Lines are removed and recreated on updates for consistency
- No performance impact on chart scrolling or zooming

### Update Frequency

- Signals are added immediately when generated
- Trade levels refresh on every chart refresh (every 5 seconds by default)
- Manual refresh updates both signals and trade levels
- Switching symbols clears and reloads appropriate data

## Troubleshooting

### Signals Not Appearing

**Issue**: Checked "Show Signals" but no arrows appear

**Solutions**:
1. Ensure at least one strategy is enabled and running
2. Verify the strategy is generating signals (check logs)
3. Confirm you're viewing the correct symbol for the strategy
4. Try manually refreshing the chart
5. Check that the strategy's symbol matches the chart symbol exactly

### Trade Levels Not Showing

**Issue**: Checked "Trade Levels" but no lines appear

**Solutions**:
1. Verify you have open positions for the current symbol
2. Check that MT5 is connected
3. Ensure the symbol name matches between chart and MT5 (use resolved symbol)
4. Try manually refreshing the chart
5. Look in logs for "Generated X trade level lines" messages

### Arrows at Wrong Positions

**Issue**: Signal arrows appear at incorrect price levels

**Solutions**:
1. This is expected - arrows are placed at the signal generation price
2. Arrows appear on the bar where the signal was generated
3. The actual trade execution price may differ slightly due to slippage
4. Check logs to compare signal price vs. execution price

### Lines Not Updating

**Issue**: Trade level lines don't update when positions change

**Solutions**:
1. Manually refresh the chart
2. Check that auto-refresh is enabled (chart refreshes every 5 seconds)
3. Verify OrderManager is connected correctly
4. Look for errors in the log file
5. Try toggling "Trade Levels" off and on again

### Too Many Signals

**Issue**: Chart is cluttered with signal arrows

**Solutions**:
1. Uncheck "Show Signals" to hide all arrows temporarily
2. Signals auto-cleanup after 100 per symbol
3. Switch to a different symbol and back to reset view
4. Consider reducing the number of active strategies

## Best Practices

### Using Show Signals

- Enable signals during backtesting to visualize strategy behavior
- Use signals to identify entry/exit timing patterns
- Compare signals across multiple strategies on the same chart
- Review signal history to analyze strategy performance
- Disable when not needed to reduce visual clutter

### Using Trade Levels

- Enable trade levels when actively managing positions
- Use entry lines to see your average position price
- Monitor distance to SL/TP lines for risk assessment
- Compare multiple positions on the same symbol
- Disable when paper trading or analyzing historical data

### Combined Usage

- Use both features together for comprehensive trade analysis
- Signals show where strategies wanted to enter
- Trade levels show where you actually entered and your exits
- Compare signal arrows to entry lines to identify execution lag
- Great for debugging strategy timing issues

## Examples

### Example 1: Monitoring Active Strategy

```
Scenario: You have a SuperTrend strategy running on XAUUSD

Steps:
1. Select XAUUSD on the chart
2. Enable "Show Signals" checkbox
3. Enable "Trade Levels" checkbox
4. Wait for strategy to generate signals
5. When BUY signal appears (green arrow), check for entry line
6. Monitor SL (red dashed) and TP (green dashed) lines
7. Exit is automatic when price hits SL or TP
```

### Example 2: Analyzing Signal History

```
Scenario: Review why a strategy triggered multiple signals

Steps:
1. Enable "Show Signals"
2. Scroll back through chart history
3. Observe the spacing between signal arrows
4. Hover over arrows to see strategy name and signal type
5. Correlate arrows with price action to understand triggers
6. Use this to optimize strategy parameters
```

### Example 3: Managing Multiple Positions

```
Scenario: You have 3 open positions on EURUSD with different strategies

Steps:
1. Select EURUSD on chart
2. Enable "Trade Levels"
3. See 3 entry lines (blue/orange depending on direction)
4. Each line labeled with ticket number and volume
5. See all 6 SL/TP lines (3 positions × 2 lines each)
6. Quickly assess risk/reward for all positions at once
```

## API Reference

### Python Methods

#### ChartWidget.add_strategy_signal()
```python
def add_strategy_signal(self, symbol: str, signal_type: str, price: float, 
                       timestamp: datetime, strategy_name: str):
    """
    Store a strategy signal for display on chart
    
    Args:
        symbol: Trading symbol
        signal_type: 'BUY' or 'SELL'
        price: Price when signal was generated
        timestamp: When the signal occurred
        strategy_name: Name of strategy that generated signal
    """
```

#### ChartWidget.get_signal_markers()
```python
def get_signal_markers(self) -> List[Dict]:
    """
    Get signal markers for the current symbol
    
    Returns:
        List of marker dictionaries for TradingView chart
    """
```

#### ChartWidget.get_trade_level_lines()
```python
def get_trade_level_lines(self) -> List[Dict]:
    """
    Get price lines for active trades on current symbol
    
    Returns:
        List of price line dictionaries for TradingView chart
    """
```

### JavaScript Functions

#### updateMarkers()
```javascript
function updateMarkers(markersData)
```
Receives array of marker objects and displays them on the candlestick series.

#### updatePriceLines()
```javascript
function updatePriceLines(linesData)
```
Removes existing price lines and creates new ones based on the provided data.

## Future Enhancements

### Potential Features

1. **Signal Filtering**: Filter signals by strategy name or signal type
2. **Signal Statistics**: Count and display success rate of signals
3. **Historical Trades**: Show closed positions as markers with entry/exit
4. **Trade Annotations**: Add notes or comments to specific signals
5. **Signal Colors**: Customize arrow colors per strategy
6. **Export Signals**: Save signal history to CSV for analysis
7. **Signal Alerts**: Play sound or notification when signal appears
8. **Win/Loss Markers**: Color code signals based on trade outcome

### Customization Options

Future versions may include:
- Adjustable signal history limit (currently 100)
- Custom arrow shapes and sizes
- Different line styles for different position types
- Configurable colors per strategy
- Toggle individual strategy signals on/off
- Symbol-specific signal persistence

## Support

For issues or questions:
- Check application logs in `logs/trading_platform.log`
- Enable debug logging to see detailed signal and trade level information
- Verify MT5 connection and symbol availability
- Ensure strategies are enabled and generating signals
- Confirm chart is on the correct symbol and timeframe

