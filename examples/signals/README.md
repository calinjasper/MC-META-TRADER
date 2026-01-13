# Signal Integration Examples

This directory contains examples for sending trading signals to the platform from various external applications.

## Quick Start

**For Python MT5 Indicators (Recommended):**
1. See `QUICK_START.md` for step-by-step instructions
2. Run `run_indicator.py` for a ready-to-use indicator
3. Or create your own using `python_mt5_custom_strategy.py`

**For Other Platforms:**
- See individual example files for each platform

## Signal Server Endpoint

The signal server runs on `http://localhost:8080` by default.

**Main Endpoint:** `POST /signal` or `GET /signal`

**Health Check:** `GET /health`

**Statistics:** `GET /stats`

## Signal Formats

### Format 1: Simple GET Request
```
GET http://localhost:8080/signal?symbol=EURUSD&action=BUY&qty=1
```

### Format 2: GET with SL/TP
```
GET http://localhost:8080/signal?symbol=EURUSD&action=BUY&qty=1&sl=1.0800&tp=1.0900
```

### Format 3: POST JSON (Standard)
```json
POST http://localhost:8080/signal
Content-Type: application/json

{
  "symbol": "EURUSD",
  "action": "BUY",
  "quantity": 1.0,
  "stop_loss": 1.0800,
  "take_profit": 1.0900,
  "comment": "My Strategy"
}
```

### Format 4: POST JSON (Extended)
```json
POST http://localhost:8080/signal
Content-Type: application/json

{
  "symbol": "EURUSD",
  "action": "BUY",
  "quantity": 1.0,
  "stop_loss": 1.0800,
  "take_profit": 1.0900,
  "price": 0.0,
  "order_type": "MARKET",
  "deviation": 20,
  "magic": 234000,
  "comment": "Advanced Strategy"
}
```

## Actions

- `BUY` - Open buy position
- `SELL` - Open sell position
- `EXIT` or `CLOSE` - Close all positions for symbol
- `MODIFY` - Modify existing positions (requires SL/TP)

## Examples by Platform

See individual example files for each platform:
- `python_example.py` - Python requests
- `amibroker_example.afl` - AmiBroker AFL code
- `mt4_example.mq4` - MetaTrader 4 MQL4 code
- `mt5_example.mq5` - MetaTrader 5 MQL5 code
- `excel_example.vba` - Excel VBA code
- `tradingview_webhook.md` - TradingView webhook setup

## MT5 SMC Indicator

**Visual Monitoring Tool**: `smc_indicator.mq5`

Plot SMC (Smart Money Concepts) indicators directly on your MT5 charts for visual monitoring and verification:
- Pivot Highs and Lows
- BOS (Break of Structure) events
- CHoCH (Change of Character) events
- Market Bias display
- Structure Levels

**See**: `SMC_INDICATOR_GUIDE.md` for complete installation and usage instructions.

