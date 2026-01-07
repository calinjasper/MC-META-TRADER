# MetaTrader 5 GUI Trading Platform

A professional PyQt6-based desktop trading platform that integrates with MetaTrader 5, providing live market data visualization, technical indicators, strategy creation and management, automated trade execution, and comprehensive risk management.

## Table of Contents

1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Quick Start Guide](#quick-start-guide)
6. [User Guide](#user-guide)
7. [Strategy Types](#strategy-types)
8. [Risk Management](#risk-management)
9. [Technical Indicators](#technical-indicators)
10. [Data Storage](#data-storage)
11. [Troubleshooting](#troubleshooting)
12. [Project Structure](#project-structure)

---

## Features

### Core Trading Features

- **MetaTrader 5 Integration**: Seamless connection to MT5 terminal with automatic reconnection
- **Live Market Data**: Real-time price streaming and visualization with customizable update intervals
- **Multiple Symbols**: Monitor and trade multiple instruments simultaneously
- **Automated Trading**: Execute trades based on strategy signals automatically
- **Manual Trading**: Quick trade widget for manual order placement

### Strategy System

- **Multiple Strategy Types**: OHLC Price, VWAP, EMA, SuperTrend, SMC (Smart Money Concepts), Structure-based
- **Strategy Builder**: Visual interface for creating custom trading strategies
- **Condition Logic**: Complex AND/OR condition chains for entry/exit signals
- **Multiple Strategies**: Run multiple strategies simultaneously on different symbols/timeframes
- **Strategy Persistence**: Automatic saving and loading of strategies
- **Signal Routing**: HTTP server for external signal integration

### Risk Management

- **Stop Loss & Take Profit**: Configurable SL/TP in pips, points, or percentage
- **Position Sizing**: Automatic lot size calculation based on risk percentage
- **Max Positions**: Limit total number of open positions
- **Trailing Stop Loss**: Dynamic stop loss that follows price movement
- **Profit Lock**: Lock in profits at specified levels
- **Re-Entry Management**: Configurable re-entry logic after SL/TP hits
- **Trade Monitoring**: Real-time position monitoring with LTP or candle-close modes

### Technical Analysis

- **Technical Indicators**: 
  - Moving Averages (SMA, EMA)
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - Bollinger Bands
  - Stochastic Oscillator
  - VWAP (Volume Weighted Average Price)
  - Volume Analysis
- **Real-Time Indicators**: Live indicator calculations with automatic updates
- **Custom Indicator Configuration**: Adjustable periods and parameters
- **MT5 Indicator Export**: Export Python indicators to MT5 MQ5 format

### Data & Visualization

- **TradingView Charts**: Professional charting with TradingView integration
- **Real-Time Charts**: Live price action visualization
- **Historical Data**: Access to historical tick and OHLC data
- **PocketBase Integration**: Optional database storage for ticks, OHLC, trades, and signals
- **Data Export**: Export trading data to CSV format
- **Trade History**: Complete trade tracking with entry/exit details

### User Interface

- **Modern GUI**: PyQt6-based professional interface
- **Dark/Light Theme**: Toggle between themes
- **Multiple Panels**: 
  - Market Data Panel
  - Strategy Panel
  - Trade Book Panel
  - Order Book Panel
  - System Logs Panel
  - Operation Monitoring Panel
- **Quick Settings**: Fast access to common settings
- **Log Viewer**: Real-time log monitoring

### Notifications

- **Telegram Integration**: Send trade alerts and notifications to Telegram channels
- **Signal Server**: HTTP endpoint for external signal integration
- **System Logs**: Comprehensive logging system

---

## Requirements

### System Requirements

- **Operating System**: Windows 10/11 (Linux/Mac support via WINE for MT5)
- **Python**: 3.8 or higher
- **RAM**: Minimum 4GB (8GB recommended)
- **Disk Space**: 500MB for application + data storage

### Software Requirements

1. **MetaTrader 5 Terminal**
   - Download from: https://www.metatrader5.com/
   - Install and configure with your broker account
   - Ensure MT5 is running before starting the application

2. **Python Dependencies** (installed automatically)
   - PyQt6 >= 6.6.0
   - MetaTrader5 >= 5.0.45
   - pandas >= 2.0.0
   - numpy >= 1.24.0
   - pyqtgraph >= 0.13.0
   - And more (see `requirements.txt`)

3. **Optional: PocketBase** (for database storage)
   - Download from: https://github.com/pocketbase/pocketbase/releases
   - Place `pocketbase.exe` in `pocketbase/` directory

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/calinjasper/MC-META-TRADER.git
cd MC-META-TRADER
```

Or using SSH:
```bash
git clone git@github.com:calinjasper/MC-META-TRADER.git
cd MC-META-TRADER
```

### Step 2: Install Python Dependencies

   ```bash
   pip install -r requirements.txt
   ```

**Note**: If you encounter issues, try using a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure MetaTrader 5

1. Install MetaTrader 5 terminal
2. Log in to your MT5 account
3. Note your account credentials (login, password, server)

### Step 4: Configure Application

1. Copy `config/config.json.example` to `config/config.json` (if exists)
2. Edit `config/config.json` with your MT5 credentials:

```json
{
  "mt5": {
    "path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
    "login": YOUR_LOGIN,
    "password": "YOUR_PASSWORD",
    "server": "YOUR_SERVER",
    "timeout": 10000
  },
  "trading": {
    "default_symbol": "EURUSD",
    "default_lot_size": 0.01,
    "max_positions": 10
  }
}
```

**⚠️ Security Note**: Never commit `config/config.json` with real credentials. Use environment variables or secure credential management for production.

### Step 5: (Optional) Setup PocketBase Database

1. Download PocketBase from: https://github.com/pocketbase/pocketbase/releases
2. Extract `pocketbase.exe` to the `pocketbase/` directory
3. The application will automatically set up collections on first run

### Step 6: Run the Application

**Option 1: Using Startup Script (Recommended)**

Windows:
```bash
start_trading_system.bat
```

Linux/Mac:
```bash
chmod +x start_trading_system.sh
./start_trading_system.sh
```

**Option 2: Direct Python Execution**

   ```bash
   python src/main.py
   ```

---

## Configuration

### Main Configuration File: `config/config.json`

```json
{
  "mt5": {
    "path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
    "login": 12345678,
    "password": "your_password",
    "server": "YourBroker-Server",
    "timeout": 10000
  },
  "trading": {
    "default_symbol": "EURUSD",
    "default_lot_size": 0.01,
    "default_slippage": 3,
    "max_positions": 10
  },
  "data_feed": {
    "update_interval_seconds": 0.05,
    "real_time_updates": true,
    "symbols": ["XAUUSDm", "EURUSDm", "USDCADm"]
  },
  "signal_server": {
    "enabled": true,
    "port": 8080,
    "host": "0.0.0.0"
  },
  "telegram": {
    "enabled": true,
    "bot_token": "YOUR_BOT_TOKEN",
    "channel_id": "YOUR_CHANNEL_ID"
  }
}
```

### Configuration Sections

- **mt5**: MetaTrader 5 connection settings
- **trading**: Default trading parameters
- **data_feed**: Market data update settings
- **signal_server**: HTTP signal server configuration
- **telegram**: Telegram bot notifications
- **strategy_types**: Enable/disable specific strategy types

---

## Quick Start Guide

### 1. Launch the Application

Run the startup script or execute `python src/main.py`

### 2. Connect to MetaTrader 5

- The application will attempt to connect automatically
- Check the status bar for connection status
- If connection fails, verify MT5 is running and credentials are correct

### 3. Select Trading Symbol

- Use the Market Data Panel to select symbols
- Add symbols to your watchlist
- Monitor real-time prices

### 4. Create a Strategy

1. Go to the **Strategy Tab**
2. Click **"Create New Strategy"**
3. Select strategy type (e.g., EMA Strategy)
4. Configure entry/exit conditions
5. Set risk management parameters (SL/TP)
6. Save the strategy

### 5. Enable and Monitor

1. Enable your strategy from the Strategy Panel
2. Monitor signals in the Signal Panel
3. Watch trades execute automatically
4. View open positions in the Trade Book Panel

### 6. Monitor Performance

- Check Trade History for completed trades
- View System Logs for detailed information
- Monitor real-time P&L in the Trade Book

---

## User Guide

### Main Window Overview

The main window consists of several panels:

1. **Market Data Panel**: Real-time price quotes and symbol selection
2. **Strategy Panel**: Create, edit, and manage trading strategies
3. **Trade Book Panel**: View open positions and trade history
4. **Chart Widget**: TradingView charts with indicators
5. **Signal Panel**: View strategy signals in real-time
6. **System Logs Panel**: Application logs and debugging information

### Creating a Strategy

#### Step-by-Step Strategy Creation

1. **Navigate to Strategy Tab**
   - Click on the "Strategy" tab in the main window

2. **Click "Create New Strategy"**
   - Choose a strategy type from the dropdown

3. **Configure Basic Settings**
   - **Name**: Unique strategy name
   - **Symbol**: Trading instrument (e.g., XAUUSDm)
   - **Timeframe**: M1, M5, M15, H1, H4, D1, etc.

4. **Set Entry Conditions**
   - Add conditions using the condition builder
   - Combine conditions with AND/OR logic
   - Configure indicator parameters

5. **Set Exit Conditions** (Optional)
   - Define when to exit positions
   - Can use same condition logic as entries

6. **Configure Risk Management**
   - **Stop Loss**: Type (Pips/Points/Percentage) and value
   - **Take Profit**: Type and value, or use risk:reward ratio
   - **Position Size**: Fixed lot size or risk-based calculation

7. **Advanced Settings** (Optional)
   - **Trade Cooldown**: Minimum time between trades
   - **Time Rules**: Trading hours restrictions
   - **Re-Entry Logic**: Configure re-entry after SL/TP

8. **Save Strategy**
   - Click "Save" to persist the strategy
   - Strategy is automatically loaded on next startup

### Managing Strategies

- **Enable/Disable**: Toggle strategy on/off without deleting
- **Edit**: Modify strategy parameters
- **Duplicate**: Create a copy for testing variations
- **Delete**: Remove strategy (with confirmation)

### Manual Trading

Use the **Quick Trade Widget** for manual order placement:

1. Select symbol
2. Choose order type (Market Buy/Sell, Pending orders)
3. Set lot size
4. Set SL/TP (optional)
5. Click "Place Order"

### Monitoring Trades

**Trade Book Panel** shows:
- Open positions with real-time P&L
- Entry price, current price, SL/TP levels
- Trade duration
- Strategy name that opened the trade

**Trade History** shows:
- Completed trades
- Entry/exit prices and times
- Profit/loss
- Exit reason (SL, TP, Manual, etc.)

### Chart Features

- **TradingView Integration**: Professional charting
- **Indicators**: Add/remove technical indicators
- **Timeframes**: Switch between different timeframes
- **Symbol Selection**: View charts for different instruments
- **Signal Markers**: Visual indicators for strategy signals

---

## Strategy Types

### 1. OHLC Price Strategy

Compares current price action against previous session's OHLC values.

**Use Cases:**
- Breakout trading above/below previous high/low
- Gap trading strategies
- Session-based reversals

**Available Fields:**
- Previous Open, High, Low, Close
- Current Open, High, Low, Close
- Derived values: (H+L)/2, (H+L+C)/3, (O+H+L+C)/4

**Example Strategy:**
- **Breakout Long**: Current Price > Previous High AND Close > Open
- **Reversal Short**: Current Price < Previous Low AND Close < (H+L)/2

### 2. VWAP Strategy

Volume Weighted Average Price strategy using standard deviation bands.

**Use Cases:**
- Mean reversion at extreme bands (±2σ)
- Trend following when price stays above/below VWAP
- Institution price level identification

**Available Fields:**
- VWAP (base line)
- Upper Bands: +1.0σ, +1.5σ, +2.0σ
- Lower Bands: -1.0σ, -1.5σ, -2.0σ

**Configuration:**
- Standard Deviation Bands: Comma-separated multipliers (default: "1, 1.5, 2")
- Session Type: NY Session, London Session, Asia Session, or All Sessions

### 3. EMA Strategy

Exponential Moving Average strategy using multiple EMAs.

**Use Cases:**
- Moving average crossover systems
- Trend direction confirmation
- Dynamic support/resistance levels

**Available Fields:**
- EMA_1 (default: 20-period)
- EMA_2 (default: 50-period)
- EMA_3 (default: 100-period)
- EMA_4 (default: 200-period)

**Common Configurations:**
- **Fast Scalping**: 8, 13, 21, 55 periods
- **Standard Swing**: 20, 50, 100, 200 periods
- **Long-term Position**: 50, 100, 200, 500 periods

**Example: Golden Cross (Long)**
- EMA_50 Crosses Above EMA_200
- Current Price > EMA_50
- Close > Open (bullish candle)

### 4. SuperTrend Strategy

Trend-following indicator using ATR-based dynamic support/resistance.

**Signal Generation:**
- **BUY**: SuperTrend flips from DOWN to UP
- **SELL**: SuperTrend flips from UP to DOWN

**Configuration:**
- Period: ATR calculation period (default: 10)
- Multiplier: ATR multiplier (default: 3.0)

### 5. SMC (Smart Money Concepts) Strategy

Structure-based trading following institutional order flow concepts.

**Features:**
- Swing pivot detection
- Break of Structure (BOS) / Change of Character (CHoCH)
- Order blocks and liquidity zones
- Market structure analysis

### 6. Structure Strategy

Fractal-based structure detection for trend identification.

**Features:**
- Pivot high/low detection
- Structure break identification
- Bias tracking (BULLISH/BEARISH)
- BOS and CHoCH signal generation

---

## Risk Management

### Stop Loss & Take Profit

**Stop Loss Types:**
- **Price (Pips)**: Fixed distance in pips
- **Price (Points)**: Fixed distance in points
- **Percentage**: Percentage of entry price

**Take Profit Types:**
- Same as Stop Loss types
- **Risk:Reward Ratio**: Automatic TP calculation (e.g., 1:2 ratio)

### Position Sizing

**Options:**
- **Fixed Lot Size**: Use specified lot size
- **Risk-Based**: Calculate lot size based on risk percentage
  - Risk per trade: Configurable percentage of account balance
  - Automatic calculation based on SL distance

### Advanced Risk Management

**Trailing Stop Loss:**
- Automatically moves SL in favorable direction
- Configurable gap distance
- Only moves in profit direction (never widens loss)

**Profit Lock:**
- Lock in profits at specified trigger level
- Configurable lock value
- Optional trailing profit lock

**Re-Entry Management:**
- Re-enter after stop loss hit
- Re-enter after take profit hit
- Configurable re-entry modes:
  - RE_ASAP: Re-enter immediately
  - RE_ASAP_REVERSE: Re-enter in opposite direction
  - RE_COST: Re-enter at entry cost
  - RE_COST_REVERSE: Re-enter at entry cost in opposite direction

**Trade Monitoring Modes:**
- **LTP Mode**: Continuous monitoring, executes immediately when conditions met
- **Candle Close Mode**: Executes on candle close (59th second)

### Position Limits

- **Max Positions**: Limit total number of open positions
- **Per-Symbol Limits**: Limit positions per symbol
- **Risk Per Trade**: Maximum risk percentage per trade

---

## Technical Indicators

### Available Indicators

1. **SMA (Simple Moving Average)**
   - Period: Configurable
   - Use: Trend identification

2. **EMA (Exponential Moving Average)**
   - Period: Configurable
   - Use: Trend following with faster response

3. **RSI (Relative Strength Index)**
   - Period: Default 14
   - Use: Overbought/oversold conditions

4. **MACD (Moving Average Convergence Divergence)**
   - Fast/Slow/Signal periods: Configurable
   - Use: Momentum and trend changes

5. **Bollinger Bands**
   - Period: Default 20
   - Standard Deviations: Default 2
   - Use: Volatility and mean reversion

6. **Stochastic Oscillator**
   - %K and %D periods: Configurable
   - Use: Momentum and overbought/oversold

7. **VWAP (Volume Weighted Average Price)**
   - Session-based calculation
   - Use: Intraday value area identification

8. **Volume**
   - Tick volume and real volume
   - Use: Confirmation and trend strength

### Using Indicators in Strategies

1. Select indicator from dropdown
2. Configure parameters (period, etc.)
3. Use in condition builder:
   - Price crosses above/below indicator
   - Indicator value comparisons
   - Indicator crossovers

---

## Data Storage

### Strategy Persistence

- Strategies are automatically saved to `strategies/` directory
- JSON format for easy editing
- Auto-loaded on application startup

### Trade History

- Stored in `data/trade_history.json`
- Includes all trade details
- Automatic backups

### PocketBase Integration (Optional)

**Collections:**
1. **ticks**: Real-time tick data
2. **ohlc**: Candlestick/OHLC data
3. **trades**: Trade history
4. **signals**: Strategy signals

**Setup:**
1. Download PocketBase (see Installation)
2. Start with application (automatic via startup script)
3. Access admin UI at: http://127.0.0.1:8090/_/
4. Create collections (see `docs/README_POCKETBASE.md`)

**Benefits:**
- Persistent data storage
- Query historical data
- Export to CSV
- Multi-device access via API

---

## Troubleshooting

### Connection Issues

**Problem**: Cannot connect to MT5
- **Solution**: 
  - Verify MT5 terminal is running
  - Check credentials in `config/config.json`
  - Ensure MT5 path is correct
  - Try restarting MT5 terminal

### Strategy Not Executing Trades

**Problem**: Strategy generates signals but no trades
- **Solution**:
  - Check if strategy is enabled
  - Verify risk management settings (SL/TP valid)
  - Check max positions limit
  - Review system logs for errors
  - Ensure AutoTrading is enabled in MT5

### Performance Issues

**Problem**: Application is slow or lagging
- **Solution**:
  - Reduce `update_interval_seconds` in config
  - Limit number of monitored symbols
  - Disable unnecessary indicators
  - Close unused strategy tabs

### Data Not Saving

**Problem**: PocketBase data not storing
- **Solution**:
  - Verify PocketBase server is running
  - Check connection in system logs
  - Ensure collections are created
  - Check network connectivity (if remote PocketBase)

### Import Errors

**Problem**: Module not found errors
- **Solution**:
  - Reinstall dependencies: `pip install -r requirements.txt`
  - Verify Python version (3.8+)
  - Check virtual environment is activated
  - Ensure you're in project root directory

### Chart Not Loading

**Problem**: TradingView chart blank
- **Solution**:
  - Check internet connection
  - Verify PyQt6-WebEngine is installed
  - Try refreshing the chart
  - Check browser console for errors

---

## Project Structure

```
MC-META-TRADER/
│
├── src/                          # Main application source code
│   ├── main.py                  # Application entry point
│   ├── config.py                # Configuration management
│   ├── mt5_connector.py         # MetaTrader 5 connector
│   ├── data_feed.py             # Data feed manager
│   │
│   ├── gui/                     # GUI components
│   │   ├── main_window.py       # Main application window
│   │   ├── chart_widget.py      # TradingView chart widget
│   │   ├── strategy_tab.py      # Strategy management UI
│   │   └── ...                  # Other GUI panels
│   │
│   ├── trading/                 # Trading logic
│   │   ├── order_manager.py     # Order management
│   │   ├── trade_history.py     # Trade history tracking
│   │   ├── risk_manager.py      # Risk management
│   │   └── ...                  # Position tracking, monitoring
│   │
│   ├── strategy/                # Trading strategies
│   │   ├── base_strategy.py     # Base strategy class
│   │   ├── strategy_manager.py  # Strategy manager
│   │   ├── ema_strategy.py      # EMA strategy
│   │   ├── vwap_strategy.py     # VWAP strategy
│   │   └── ...                  # Other strategies
│   │
│   ├── indicators/              # Technical indicators
│   │   ├── base_indicator.py    # Base indicator class
│   │   ├── rsi.py               # RSI indicator
│   │   ├── ema.py               # EMA indicator
│   │   └── ...                  # Other indicators
│   │
│   ├── data/                     # Data management
│   │   └── pocketbase_manager.py # PocketBase integration
│   │
│   └── signal_routing/           # Signal routing system
│
├── scripts/                      # Utility scripts
│   ├── setup/                    # Setup scripts
│   ├── database/                 # Database operations
│   └── export/                   # Data export
│
├── config/                       # Configuration files
│   └── config.json               # Main configuration
│
├── strategies/                   # Saved strategies (JSON)
├── data/                         # Application data
├── logs/                         # Log files
├── pocketbase/                   # PocketBase database
├── docs/                         # Documentation
├── examples/                     # Example code
├── tests/                        # Test scripts
│
├── requirements.txt              # Python dependencies
├── start_trading_system.bat      # Windows startup script
├── start_trading_system.sh       # Linux/Mac startup script
└── README.md                     # This file
```

---

## Additional Resources

### Documentation

- **Strategy Documentation**: See `STRATEGY_TAB_DOCUMENTATION_CORRECTED.md`
- **PocketBase Guide**: See `docs/README_POCKETBASE.md`
- **Project Structure**: See `PROJECT_STRUCTURE.md`
- **Indicator Guide**: See `src/gui/INDICATOR_MANAGEMENT_GUIDE.md`

### Examples

- **Signal Examples**: See `examples/signals/` directory
- **Sample Strategies**: See `src/strategy/examples/`

### Support

- Check system logs in the Log Viewer Panel
- Review `logs/trading_platform.log` for detailed information
- See troubleshooting section above

---

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit credentials**: `config/config.json` is in `.gitignore` for a reason
2. **Use environment variables**: For production, use environment variables for sensitive data
3. **Secure your MT5 account**: Use strong passwords and enable 2FA if available
4. **Network security**: If using remote PocketBase, secure the connection
5. **API keys**: Keep Telegram bot tokens and API keys secure

---

## License

This project is provided as-is for educational and personal use. Use at your own risk when trading with real money.

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## Disclaimer

This software is for educational purposes only. Trading involves substantial risk of loss. Past performance is not indicative of future results. Always test strategies on a demo account before using real money. The authors and contributors are not responsible for any financial losses incurred from using this software.

---

## Version History

- **v1.0**: Initial release with core trading features
- Multiple strategy types support
- Risk management system
- PocketBase integration
- Real-time data feed
- Professional GUI

---

**Last Updated**: January 2025

For the latest updates and issues, visit: https://github.com/calinjasper/MC-META-TRADER
