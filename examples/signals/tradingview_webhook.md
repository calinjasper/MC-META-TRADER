# TradingView Webhook Integration

This guide shows how to send trading signals from TradingView to the trading platform using webhooks.

## Setup

1. **Enable Webhooks in TradingView** (Paid accounts only)
   - Go to TradingView Settings
   - Enable Webhooks

2. **Configure Alert Webhook URL**
   - URL: `http://localhost:8080/signal`
   - Method: POST
   - Content-Type: application/json

## Alert Message Format

### Format 1: Simple Signal
```json
{
  "symbol": "{{ticker}}",
  "action": "BUY",
  "quantity": 0.01,
  "comment": "TradingView Alert"
}
```

### Format 2: With SL/TP
```json
{
  "symbol": "{{ticker}}",
  "action": "BUY",
  "quantity": 0.01,
  "stop_loss": {{close}} * 0.98,
  "take_profit": {{close}} * 1.04,
  "comment": "TradingView Strategy"
}
```

## TradingView Alert Setup

1. Create an alert on your chart
2. Set **Webhook URL** to: `http://localhost:8080/signal`
3. Set **Message** to one of the JSON formats above

### Example Alert Messages

#### BUY Signal
```json
{"symbol":"{{ticker}}","action":"BUY","quantity":0.01,"stop_loss":{{close}}*0.98,"take_profit":{{close}}*1.04,"comment":"TradingView BUY"}
```

#### SELL Signal
```json
{"symbol":"{{ticker}}","action":"SELL","quantity":0.01,"stop_loss":{{close}}*1.02,"take_profit":{{close}}*0.96,"comment":"TradingView SELL"}
```

#### Exit Signal
```json
{"symbol":"{{ticker}}","action":"EXIT","quantity":0,"comment":"TradingView Exit"}
```

## TradingView Variables

- `{{ticker}}` - Symbol name (e.g., "EURUSD")
- `{{close}}` - Close price
- `{{open}}` - Open price
- `{{high}}` - High price
- `{{low}}` - Low price
- `{{volume}}` - Volume

## Free Users Alternative

If you don't have TradingView paid account, you can use the TradingView Plugin method (see separate documentation) or use Python scripts to monitor TradingView alerts and forward them.

## Notes

- Make sure the signal server is running before sending alerts
- The server must be accessible from your network (use your computer's IP instead of localhost if TradingView is on a different machine)
- For production use, consider using a public URL with authentication

