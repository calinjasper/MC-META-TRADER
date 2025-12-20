// MetaTrader 5 MQL5 Example - Sending Signals to Trading Platform
//
// This example shows how to send trading signals from MT5 Expert Advisor
// to the trading platform's signal server using HTTP requests.
//
// Requirements:
// - MT5 with WebRequest function enabled
// - Add "http://localhost:8080" to allowed URLs in MT5 settings
// - Trading platform signal server running on localhost:8080

#property copyright "Signal Integration Example"
#property version   "1.00"

// Signal Server Configuration
string SignalServerURL = "http://localhost:8080/signal";
string TradingSymbol = "EURUSD";  // Change to your symbol

// Function to send signal via HTTP GET (Format 1 or 2)
bool SendSignal(string symbol, string action, double quantity, double sl = 0, double tp = 0)
{
    string url = SignalServerURL + "?symbol=" + symbol + 
                 "&action=" + action + 
                 "&qty=" + DoubleToString(quantity, 2);
    
    if (sl > 0)
        url += "&sl=" + DoubleToString(sl, 5);
    if (tp > 0)
        url += "&tp=" + DoubleToString(tp, 5);
    
    char post[];
    char result[];
    string headers;
    
    int res = WebRequest("GET", url, "", NULL, 5000, post, 0, result, headers);
    
    if (res == -1)
    {
        int error = GetLastError();
        Print("WebRequest failed, error: ", error);
        if (error == 4060)  // URL not allowed
        {
            Print("Please add 'http://localhost:8080' to allowed URLs in MT5 settings");
        }
        return false;
    }
    
    Print("Signal sent: ", symbol, " ", action, " Response: ", CharArrayToString(result));
    return true;
}

// Function to send signal via HTTP POST (Format 3)
bool SendSignalPOST(string symbol, string action, double quantity, double sl = 0, double tp = 0, string comment = "")
{
    string json = "{\"symbol\":\"" + symbol + 
                  "\",\"action\":\"" + action + 
                  "\",\"quantity\":" + DoubleToString(quantity, 2) +
                  ",\"stop_loss\":" + DoubleToString(sl, 5) +
                  ",\"take_profit\":" + DoubleToString(tp, 5) +
                  ",\"comment\":\"" + comment + "\"}";
    
    char post[];
    char result[];
    string headers = "Content-Type: application/json\r\n";
    
    StringToCharArray(json, post, 0, StringLen(json));
    
    int res = WebRequest("POST", SignalServerURL, headers, 5000, post, result, headers);
    
    if (res == -1)
    {
        int error = GetLastError();
        Print("WebRequest failed, error: ", error);
        if (error == 4060)  // URL not allowed
        {
            Print("Please add 'http://localhost:8080' to allowed URLs in MT5 settings");
        }
        return false;
    }
    
    Print("Signal sent via POST: ", symbol, " ", action, " Response: ", CharArrayToString(result));
    return true;
}

// Expert Advisor OnTick function
void OnTick()
{
    // Example: RSI-based strategy
    
    int rsi_handle = iRSI(TradingSymbol, PERIOD_CURRENT, 14, PRICE_CLOSE);
    double rsi[];
    ArraySetAsSeries(rsi, true);
    
    if (CopyBuffer(rsi_handle, 0, 0, 2, rsi) <= 0)
    {
        Print("Failed to get RSI data");
        return;
    }
    
    double rsi_current = rsi[0];
    double rsi_prev = rsi[1];
    
    // Buy signal: RSI crosses above 30 (oversold)
    if (rsi_current > 30 && rsi_prev <= 30)
    {
        MqlTick tick;
        if (SymbolInfoTick(TradingSymbol, tick))
        {
            double current_price = tick.ask;
            double sl = current_price - (current_price * 0.02);  // 2% stop loss
            double tp = current_price + (current_price * 0.04);  // 4% take profit
            
            SendSignalPOST(TradingSymbol, "BUY", 0.01, sl, tp, "MT5 RSI Strategy");
            Print("BUY signal sent - RSI: ", rsi_current);
        }
    }
    
    // Sell signal: RSI crosses below 70 (overbought)
    if (rsi_current < 70 && rsi_prev >= 70)
    {
        MqlTick tick;
        if (SymbolInfoTick(TradingSymbol, tick))
        {
            double current_price = tick.bid;
            double sl = current_price + (current_price * 0.02);  // 2% stop loss (above for SELL)
            double tp = current_price - (current_price * 0.04);  // 4% take profit (below for SELL)
            
            SendSignalPOST(TradingSymbol, "SELL", 0.01, sl, tp, "MT5 RSI Strategy");
            Print("SELL signal sent - RSI: ", rsi_current);
        }
    }
    
    IndicatorRelease(rsi_handle);
}

// Example: Close all positions
void CloseAllPositions()
{
    SendSignal(TradingSymbol, "EXIT", 0);
}

