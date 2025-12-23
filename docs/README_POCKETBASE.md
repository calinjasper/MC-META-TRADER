# PocketBase Integration Guide

## What is PocketBase?

PocketBase is an open-source backend that provides:
- **SQLite Database** - Store all your trading data
- **REST API** - Access data from anywhere
- **Admin Dashboard** - Beautiful UI to view your data
- **Realtime Updates** - Auto-sync across devices
- **100% FREE** - MIT License, no limits

## Quick Start

### 1. Download PocketBase

1. Visit: https://github.com/pocketbase/pocketbase/releases
2. Download: `pocketbase_X.X.X_windows_amd64.zip` (Windows) or appropriate version
3. Extract `pocketbase.exe` to the `pocketbase/` directory

### 2. Start the System

**Windows:**
```bash
start_trading_system.bat
```

**Linux/Mac:**
```bash
chmod +x start_trading_system.sh
./start_trading_system.sh
```

This will:
1. Start PocketBase server
2. Start your trading system
3. Automatically connect them

### 3. Access Admin Dashboard

Open in browser: **http://127.0.0.1:8090/_/**

First time:
- Create an admin account
- Create the required collections (see below)

## Database Collections Setup

After first run, create these collections in the Admin UI:

### 1. `ticks` Collection
Store real-time tick data

Fields:
- `symbol` (text, required)
- `timestamp` (number, required, add index)
- `bid` (number, required)
- `ask` (number, required)
- `last` (number)
- `volume` (number)
- `spread` (number)

### 2. `ohlc` Collection
Store candlestick/OHLC data

Fields:
- `symbol` (text, required)
- `timeframe` (text, required)
- `timestamp` (number, required, add index)
- `open` (number, required)
- `high` (number, required)
- `low` (number, required)
- `close` (number, required)
- `tick_volume` (number)
- `real_volume` (number)

### 3. `trades` Collection
Store your trade history

Fields:
- `ticket` (number, required, unique)
- `symbol` (text, required)
- `direction` (text, required)
- `entry_time` (date, required)
- `entry_price` (number, required)
- `exit_time` (date)
- `exit_price` (number)
- `volume` (number, required)
- `sl` (number)
- `tp` (number)
- `profit` (number)
- `exit_reason` (text)
- `strategy_name` (text)
- `comment` (text)

### 4. `signals` Collection
Store strategy signals

Fields:
- `symbol` (text, required)
- `timestamp` (date, required)
- `signal_type` (text, required)
- `strategy_name` (text, required)
- `conditions` (json)
- `price` (number)

### 5. `indicators` Collection
Store indicator values

Fields:
- `symbol` (text, required)
- `timeframe` (text, required)
- `timestamp` (date, required)
- `indicator_name` (text, required)
- `value` (number)
- `metadata` (json)

## Features

### Automatic Storage

Once running, PocketBase automatically stores:
- ✅ Every tick as it arrives
- ✅ Every completed candle
- ✅ Every trade (entry and exit)
- ✅ Every signal generated
- ✅ All indicator values (optional)

### Historical Data Access

Query any historical data:

```python
from src.data.pocketbase_manager import PocketBaseManager
from datetime import datetime, timedelta

pb = PocketBaseManager()

# Get last 7 days of EURUSD H1 candles
start = datetime.now() - timedelta(days=7)
end = datetime.now()

candles = pb.get_ohlc(
    symbol='EURUSD',
    timeframe='H1',
    start_time=int(start.timestamp() * 1000),
    end_time=int(end.timestamp() * 1000)
)

# Get all trades from last month
trades = pb.get_trades(
    start_date=datetime(2024, 12, 1),
    end_date=datetime(2024, 12, 31)
)
```

### Admin Dashboard

Access: **http://127.0.0.1:8090/_/**

Features:
- View all data in tables
- Search and filter
- Export to CSV/JSON
- Real-time updates
- Manual edits (if needed)

### REST API

Base URL: `http://127.0.0.1:8090/api/`

Examples:
```bash
# Get all trades
GET http://127.0.0.1:8090/api/collections/trades/records

# Get EURUSD candles
GET http://127.0.0.1:8090/api/collections/ohlc/records?filter=symbol="EURUSD"

# Get recent signals
GET http://127.0.0.1:8090/api/collections/signals/records?sort=-timestamp
```

## Troubleshooting

### PocketBase Won't Start

- **Port 8090 in use**: Stop other PocketBase instances or change port
- **Permission denied**: Run as administrator (Windows) or use `sudo` (Linux)
- **File not found**: Ensure `pocketbase.exe` is in the `pocketbase/` directory

### Trading System Won't Connect

- **Check logs**: Look in `logs/trading_platform.log`
- **Verify PocketBase is running**: Open http://127.0.0.1:8090/_/
- **System works without PocketBase**: It will continue running, just without database storage

### Data Not Appearing

1. **Check PocketBase is running**: Should see it in task manager/terminal
2. **Verify collections exist**: Open Admin UI and check collections
3. **Check logs**: Look for PocketBase errors in logs
4. **Manual test**: Try creating a record manually in Admin UI

## Performance

### Storage Requirements

- **1 day of M1 candles (1 symbol)**: ~1 MB
- **1 month of trades**: < 1 MB
- **1 year of H1 candles (10 symbols)**: ~50 MB

### Batch Writing

PocketBase Manager uses batch writing:
- Queues up to 100 records
- Writes every 5 seconds
- Non-blocking (doesn't slow down trading)

## Benefits

✅ **Permanent Storage**: Never lose trade history  
✅ **Historical Analysis**: Query any past data  
✅ **Backtesting**: Test strategies on stored data  
✅ **Performance Reports**: Analyze your trading  
✅ **Multi-Device**: Access data from anywhere  
✅ **Beautiful UI**: Admin dashboard included  
✅ **Free Forever**: MIT License, no costs  

## Optional: Running Without PocketBase

The trading system works fine without PocketBase:
- Just start normally: `python src/main.py`
- Data won't be stored in database
- JSON file storage still works
- All features still available

## Support

For PocketBase issues:
- Documentation: https://pocketbase.io/docs/
- GitHub: https://github.com/pocketbase/pocketbase

For integration issues:
- Check `logs/trading_platform.log`
- Check `pocketbase/pb_data/logs.db`

