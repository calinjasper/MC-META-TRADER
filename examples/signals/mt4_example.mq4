// MetaTrader 4 MQL4 Example - Sending Signals to Trading Platform
//
// This example shows how to send trading signals from MT4 Expert Advisor
// to the trading platform's signal server using HTTP requests.
//
// Requirements:
// - MT4 with WebRequest function enabled
// - Add "http://localhost:8080" to allowed URLs in MT4 settings
// - Trading platform signal server running on localhost:8080

#property copyright "Signal Integration Example"
#property version   "1.00"
#property strict

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
            Print("Please add 'http://localhost:8080' to allowed URLs in MT4 settings");
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
            Print("Please add 'http://localhost:8080' to allowed URLs in MT4 settings");
        }
        return false;
    }
    
    Print("Signal sent via POST: ", symbol, " ", action, " Response: ", CharArrayToString(result));
    return true;
}

// Expert Advisor OnTick function
void OnTick()
{
    // Example: Simple moving average crossover strategy
    
    double ma_fast = iMA(TradingSymbol, PERIOD_CURRENT, 10, 0, MODE_SMA, PRICE_CLOSE, 0);
    double ma_slow = iMA(TradingSymbol, PERIOD_CURRENT, 20, 0, MODE_SMA, PRICE_CLOSE, 0);
    double ma_fast_prev = iMA(TradingSymbol, PERIOD_CURRENT, 10, 0, MODE_SMA, PRICE_CLOSE, 1);
    double ma_slow_prev = iMA(TradingSymbol, PERIOD_CURRENT, 20, 0, MODE_SMA, PRICE_CLOSE, 1);
    
    // Buy signal: Fast MA crosses above Slow MA
    if (ma_fast > ma_slow && ma_fast_prev <= ma_slow_prev)
    {
        double current_price = Ask;
        double sl = current_price - (current_price * 0.02);  // 2% stop loss
        double tp = current_price + (current_price * 0.04);  // 4% take profit
        
        SendSignalPOST(TradingSymbol, "BUY", 0.01, sl, tp, "MT4 MA Crossover");
        Print("BUY signal sent");
    }
    
    // Sell signal: Fast MA crosses below Slow MA
    if (ma_fast < ma_slow && ma_fast_prev >= ma_slow_prev)
    {
        double current_price = Bid;
        double sl = current_price + (current_price * 0.02);  // 2% stop loss (above for SELL)
        double tp = current_price - (current_price * 0.04);  // 4% take profit (below for SELL)
        
        SendSignalPOST(TradingSymbol, "SELL", 0.01, sl, tp, "MT4 MA Crossover");
        Print("SELL signal sent");
    }
}

// Example: Close all positions
void CloseAllPositions()
{
    SendSignal(TradingSymbol, "EXIT", 0);
}

