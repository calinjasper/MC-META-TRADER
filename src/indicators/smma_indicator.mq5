//+------------------------------------------------------------------+
//|                                        SMMA_Indicator.mq5        |
//|                        Smoothed Moving Average (SMMA) Indicator   |
//|                                                                  |
//| Converted from Pine Script version 6 indicator                   |
//| This indicator plots SMMA with Buy Entry and Sell Entry arrows only|
//+------------------------------------------------------------------+
#property copyright "SMMA Indicator for Visual Monitoring"
#property version   "1.05-DEBUG"
#property indicator_chart_window
#property indicator_buffers 7
#property indicator_plots   7

//--- Input Parameters
input int    Length = 7;              // Length (minval=1)
input ENUM_APPLIED_PRICE SourcePrice = PRICE_CLOSE;  // Source
input color  SMMAColor = 0x673AB7;    // SMMA Line Color (Purple)
input int    SMMALineWidth = 2;       // SMMA Line Width
input color  BuyEntryColor = clrBlue;         // Buy Entry Color
input color  SellEntryColor = clrRed;         // Sell Entry Color
input color  BuyEntryLineColor = clrGreen;    // Buy Entry Line Color
input color  SellEntryLineColor = clrRed;     // Sell Entry Line Color
input int    SignalSize = 2;          // Signal Arrow Size
input bool   ShowDebugInfo = false;   // Show Debug Info in Comments
input bool   EnableAlerts = true;    // Enable alerts for Buy/Sell Entry
input string AlertFileName = "smma_alerts.txt";  // Alert file name (in MQL5/Files/)

//--- Indicator Buffers
double SMMABuffer[];
double BuyEntryBuffer[];
double SellEntryBuffer[];
double BuyEntryLowBuffer[];
double BuyEntryHighBuffer[];
double SellEntryHighBuffer[];
double SellEntryLowBuffer[];

//--- Global Variables (persistent state - equivalent to Pine Script 'var')
double entry_high = 0.0;
double entry_low = 0.0;
double entry_high_s = 0.0;
double entry_low_s = 0.0;
double High = 0.0;
double Low = 0.0;
double High_s = 0.0;
double Low_s = 0.0;
bool valid_buy = false;
bool valid_sell = false;
bool f1 = false;  // Flag to track buy signal state
bool f2 = false;  // Flag to track sell signal state
datetime last_buy_entry_time = 0;  // Track bar time when buy entry was last alerted
datetime last_sell_entry_time = 0;  // Track bar time when sell entry was last alerted
int alert_file_handle = INVALID_HANDLE;  // Handle for alert file

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // CRITICAL DEBUG: This MUST appear if new code is loaded
   Print("========================================");
   Print("SMMA Indicator: NEW DEBUG VERSION LOADED");
   Print("SMMA Indicator: [DEBUG] OnInit() called - Starting initialization");
   Print("SMMA Indicator: [DEBUG] EnableAlerts=", EnableAlerts ? "true" : "false", " | AlertFileName=", AlertFileName);
   Print("========================================");
   
   // Validate length
   if(Length < 1)
   {
      Print("SMMA Indicator: Invalid length. Length must be >= 1.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   
   // Set indicator buffers
   SetIndexBuffer(0, SMMABuffer, INDICATOR_DATA);
   SetIndexBuffer(1, BuyEntryBuffer, INDICATOR_DATA);
   SetIndexBuffer(2, SellEntryBuffer, INDICATOR_DATA);
   SetIndexBuffer(3, BuyEntryLowBuffer, INDICATOR_DATA);
   SetIndexBuffer(4, BuyEntryHighBuffer, INDICATOR_DATA);
   SetIndexBuffer(5, SellEntryHighBuffer, INDICATOR_DATA);
   SetIndexBuffer(6, SellEntryLowBuffer, INDICATOR_DATA);
   
   // Set plot properties - SMMA Line
   PlotIndexSetInteger(0, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, SMMAColor);
   PlotIndexSetInteger(0, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(0, PLOT_LINE_WIDTH, SMMALineWidth);
   PlotIndexSetString(0, PLOT_LABEL, "SMMA(" + IntegerToString(Length) + ")");
   
   // Set plot properties - Buy Entry (arrow up)
   PlotIndexSetInteger(1, PLOT_DRAW_TYPE, DRAW_ARROW);
   PlotIndexSetInteger(1, PLOT_ARROW, 233);  // Arrow up
   PlotIndexSetInteger(1, PLOT_LINE_COLOR, BuyEntryColor);
   PlotIndexSetInteger(1, PLOT_LINE_WIDTH, SignalSize);
   PlotIndexSetString(1, PLOT_LABEL, "Buy Entry");
   
   // Set plot properties - Sell Entry (arrow down)
   PlotIndexSetInteger(2, PLOT_DRAW_TYPE, DRAW_ARROW);
   PlotIndexSetInteger(2, PLOT_ARROW, 234);  // Arrow down
   PlotIndexSetInteger(2, PLOT_LINE_COLOR, SellEntryColor);
   PlotIndexSetInteger(2, PLOT_LINE_WIDTH, SignalSize);
   PlotIndexSetString(2, PLOT_LABEL, "Sell Entry");
   
   // Set plot properties - Buy Entry Low Line
   PlotIndexSetInteger(3, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(3, PLOT_LINE_COLOR, BuyEntryLineColor);
   PlotIndexSetInteger(3, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(3, PLOT_LINE_WIDTH, 2);
   PlotIndexSetString(3, PLOT_LABEL, "Buy Entry Low");
   
   // Set plot properties - Buy Entry High Line
   PlotIndexSetInteger(4, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(4, PLOT_LINE_COLOR, BuyEntryLineColor);
   PlotIndexSetInteger(4, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(4, PLOT_LINE_WIDTH, 2);
   PlotIndexSetString(4, PLOT_LABEL, "Buy Entry High");
   
   // Set plot properties - Sell Entry High Line
   PlotIndexSetInteger(5, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(5, PLOT_LINE_COLOR, SellEntryLineColor);
   PlotIndexSetInteger(5, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(5, PLOT_LINE_WIDTH, 2);
   PlotIndexSetString(5, PLOT_LABEL, "Sell Entry High");
   
   // Set plot properties - Sell Entry Low Line
   PlotIndexSetInteger(6, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(6, PLOT_LINE_COLOR, SellEntryLineColor);
   PlotIndexSetInteger(6, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(6, PLOT_LINE_WIDTH, 2);
   PlotIndexSetString(6, PLOT_LABEL, "Sell Entry Low");
   
   // Set empty values
   ArraySetAsSeries(SMMABuffer, true);
   ArraySetAsSeries(BuyEntryBuffer, true);
   ArraySetAsSeries(SellEntryBuffer, true);
   ArraySetAsSeries(BuyEntryLowBuffer, true);
   ArraySetAsSeries(BuyEntryHighBuffer, true);
   ArraySetAsSeries(SellEntryHighBuffer, true);
   ArraySetAsSeries(SellEntryLowBuffer, true);
   
   // Initialize buffers
   ArrayInitialize(SMMABuffer, EMPTY_VALUE);
   ArrayInitialize(BuyEntryBuffer, EMPTY_VALUE);
   ArrayInitialize(SellEntryBuffer, EMPTY_VALUE);
   ArrayInitialize(BuyEntryLowBuffer, EMPTY_VALUE);
   ArrayInitialize(BuyEntryHighBuffer, EMPTY_VALUE);
   ArrayInitialize(SellEntryHighBuffer, EMPTY_VALUE);
   ArrayInitialize(SellEntryLowBuffer, EMPTY_VALUE);
   
   // Initialize alert tracking
   last_buy_entry_time = 0;
   last_sell_entry_time = 0;
   
   // #region agent log - DEBUG: File opening attempt
   Print("SMMA Indicator: [DEBUG] Attempting to open alert file...");
   Print("SMMA Indicator: [DEBUG] AlertFileName=", AlertFileName);
   Print("SMMA Indicator: [DEBUG] File flags: FILE_WRITE|FILE_READ|FILE_TXT|FILE_COMMON|FILE_ANSI");
   // #endregion
   
   // Open alert file for writing
   // FILE_COMMON flag writes to: %AppData%\Roaming\MetaQuotes\Terminal\Common\Files\
   // FILE_ANSI flag ensures compatibility with Python file reading
   alert_file_handle = FileOpen(AlertFileName, FILE_WRITE|FILE_READ|FILE_TXT|FILE_COMMON|FILE_ANSI);
   
   // #region agent log - DEBUG: File open result
   Print("SMMA Indicator: [DEBUG] FileOpen() returned handle: ", IntegerToString(alert_file_handle));
   Print("SMMA Indicator: [DEBUG] INVALID_HANDLE constant: ", IntegerToString(INVALID_HANDLE));
   // #endregion
   
   if(alert_file_handle == INVALID_HANDLE)
   {
      int error_code = GetLastError();
      Print("SMMA Indicator: ERROR - Could not open alert file: ", AlertFileName);
      Print("SMMA Indicator: Error code: ", error_code, " | File path: Common\\Files\\", AlertFileName);
      Print("SMMA Indicator: Alerts will not be written to file until this is resolved");
      
      // #region agent log - DEBUG: File open failure
      Print("SMMA Indicator: [DEBUG] HYPOTHESIS-1: File handle is INVALID_HANDLE - CONFIRMED");
      Print("SMMA Indicator: [DEBUG] GetLastError()=", error_code);
      // #endregion
   }
   else
   {
      // Get full file path for logging
      string file_path = "Common\\Files\\" + AlertFileName;
      Print("SMMA Indicator: Alert file opened successfully: ", file_path);
      Print("SMMA Indicator: File handle: ", IntegerToString(alert_file_handle));
      
      // #region agent log - DEBUG: File open success
      Print("SMMA Indicator: [DEBUG] HYPOTHESIS-1: File handle opened successfully - REJECTED");
      ulong file_size = FileSize(alert_file_handle);
      Print("SMMA Indicator: [DEBUG] File size after open: ", IntegerToString(file_size), " bytes");
      // #endregion
      
      // Move to end of file to append new alerts
      ulong seek_result = FileSeek(alert_file_handle, 0, SEEK_END);
      Print("SMMA Indicator: [DEBUG] FileSeek(END) result: ", IntegerToString(seek_result));
   }
   
   // #region agent log - DEBUG: OnInit completion
   Print("SMMA Indicator: [DEBUG] OnInit() completing, alert_file_handle=", IntegerToString(alert_file_handle));
   // #endregion
   
   IndicatorSetString(INDICATOR_SHORTNAME, "SMMA(" + IntegerToString(Length) + ")");
   IndicatorSetInteger(INDICATOR_DIGITS, _Digits);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Close alert file
   if(alert_file_handle != INVALID_HANDLE)
   {
      FileClose(alert_file_handle);
      alert_file_handle = INVALID_HANDLE;
   }
   // Cleanup if needed
}

//+------------------------------------------------------------------+
//| Calculate SMA for initialization                                 |
//+------------------------------------------------------------------+
double CalculateSMA(const double &price[], int period, int startIndex)
{
   if(startIndex + period > ArraySize(price))
      return(0.0);
   
   double sum = 0.0;
   for(int i = 0; i < period; i++)
   {
      sum += price[startIndex + i];
   }
   return(sum / period);
}

//+------------------------------------------------------------------+
//| Calculate SMMA                                                   |
//+------------------------------------------------------------------+
void CalculateSMMA(double &smmaBuffer[], const double &source[], int rates_total, int prev_calculated)
{
   if(rates_total < Length)
      return;
   
   int limit = rates_total - prev_calculated;
   
   if(prev_calculated == 0)
   {
      // Initialize SMMA with SMA for the first value
      limit = rates_total - Length;
      
      // Find the first index where we can calculate SMA
      int firstIndex = rates_total - Length;
      if(firstIndex >= 0 && firstIndex < rates_total)
      {
         double smaValue = CalculateSMA(source, Length, firstIndex);
         smmaBuffer[firstIndex] = smaValue;
         
         // Calculate SMMA for remaining bars going backwards (forward in time)
         for(int i = firstIndex - 1; i >= 0; i--)
         {
            double prevSMMA = smmaBuffer[i + 1];
            smmaBuffer[i] = (prevSMMA * (Length - 1) + source[i]) / Length;
         }
      }
   }
   else
   {
      limit++;
      
      // Calculate SMMA for new bars only
      for(int i = limit - 1; i >= 0; i--)
      {
         if(i + 1 >= rates_total)
         {
            // This is the oldest bar - need to check if we can calculate
            if(rates_total >= Length)
            {
               double smaValue = CalculateSMA(source, Length, i);
               smmaBuffer[i] = smaValue;
            }
         }
         else
         {
            // Use previous SMMA value
            double prevSMMA = smmaBuffer[i + 1];
            if(prevSMMA != EMPTY_VALUE)
            {
               smmaBuffer[i] = (prevSMMA * (Length - 1) + source[i]) / Length;
            }
            else
            {
               // Fallback: use SMA if previous SMMA not available
               if(i + Length <= rates_total)
               {
                  double smaValue = CalculateSMA(source, Length, i);
                  smmaBuffer[i] = smaValue;
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Check if crossover occurred (price crosses above level)          |
//+------------------------------------------------------------------+
bool IsCrossover(double current, double previous, double levelCurrent, double levelPrevious)
{
   return(current > levelCurrent && previous <= levelPrevious);
}

//+------------------------------------------------------------------+
//| Check if crossunder occurred (price crosses below level)         |
//+------------------------------------------------------------------+
bool IsCrossunder(double current, double previous, double levelCurrent, double levelPrevious)
{
   return(current < levelCurrent && previous >= levelPrevious);
}

//+------------------------------------------------------------------+
//| Get price value based on SourcePrice input                       |
//+------------------------------------------------------------------+
double GetPriceValue(int index, const double &open[], const double &high[], 
                     const double &low[], const double &close[])
{
   switch(SourcePrice)
   {
      case PRICE_OPEN:  return(open[index]);
      case PRICE_HIGH:  return(high[index]);
      case PRICE_LOW:   return(low[index]);
      case PRICE_CLOSE: return(close[index]);
      case PRICE_MEDIAN: return((high[index] + low[index]) / 2.0);
      case PRICE_TYPICAL: return((high[index] + low[index] + close[index]) / 3.0);
      case PRICE_WEIGHTED: return((high[index] + low[index] + close[index] + close[index]) / 4.0);
      default: return(close[index]);
   }
}

//+------------------------------------------------------------------+
//| Custom indicator iteration function                               |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   if(rates_total < Length + 2)
      return(0);
   
   // Set arrays as series
   ArraySetAsSeries(close, true);
   ArraySetAsSeries(open, true);
   ArraySetAsSeries(high, true);
   ArraySetAsSeries(low, true);
   ArraySetAsSeries(SMMABuffer, true);
   
   // Create source price array
   double source[];
   ArrayResize(source, rates_total);
   ArraySetAsSeries(source, true);
   
   for(int i = 0; i < rates_total && i < rates_total; i++)
   {
      source[i] = GetPriceValue(i, open, high, low, close);
   }
   
   // Calculate SMMA
   CalculateSMMA(SMMABuffer, source, rates_total, prev_calculated);
  
   // IMPORTANT:
   // Do NOT clear full buffers on every tick. That prevents level lines (High/Low) from persisting,
   // unlike Pine Script's `var` series. We only clear/update the bars we recalculate below.
   if(prev_calculated == 0)
   {
      ArrayInitialize(BuyEntryBuffer, EMPTY_VALUE);
      ArrayInitialize(SellEntryBuffer, EMPTY_VALUE);
      ArrayInitialize(BuyEntryLowBuffer, EMPTY_VALUE);
      ArrayInitialize(BuyEntryHighBuffer, EMPTY_VALUE);
      ArrayInitialize(SellEntryHighBuffer, EMPTY_VALUE);
      ArrayInitialize(SellEntryLowBuffer, EMPTY_VALUE);
      // Reset alert tracking on full recalculation
      last_buy_entry_time = 0;
      last_sell_entry_time = 0;
   }
   
   int limit = rates_total - prev_calculated;
   if(prev_calculated == 0)
      limit = rates_total - 2;
   else
      limit = MathMin(limit + 1, rates_total - 1);
   
   // Process bars from oldest to newest (going backwards in array since it's series)
   for(int i = limit - 1; i >= 0; i--)
   {
      if(i + 1 >= rates_total || SMMABuffer[i] == EMPTY_VALUE || SMMABuffer[i + 1] == EMPTY_VALUE)
         continue;
     
      // Clear outputs for this bar only (keeps history intact)
      BuyEntryBuffer[i] = EMPTY_VALUE;
      SellEntryBuffer[i] = EMPTY_VALUE;
      BuyEntryLowBuffer[i] = EMPTY_VALUE;
      BuyEntryHighBuffer[i] = EMPTY_VALUE;
      SellEntryHighBuffer[i] = EMPTY_VALUE;
      SellEntryLowBuffer[i] = EMPTY_VALUE;
      
      double currentClose = close[i];
      double prevClose = close[i + 1];
      double currentSMMA = SMMABuffer[i];
      double prevSMMA = SMMABuffer[i + 1];
      double currentHigh = high[i];
      double currentLow = low[i];
      double eps = _Point * 0.5;
      
      // Detect crossover/crossunder (signal candles) - used internally but not plotted
      bool signal_candle = IsCrossover(currentClose, prevClose, currentSMMA, prevSMMA);
      bool sig_candle = IsCrossunder(currentClose, prevClose, currentSMMA, prevSMMA);
      
      // Handle signal candle (crossover) - Buy signal (internal state only, no arrow)
      if(signal_candle && !f1)
      {
         Low = currentLow;
         High = currentHigh;
         valid_buy = true;
         valid_sell = false;
      }
      
      // Handle signal candle (crossunder) - Sell signal (internal state only, no arrow)
      if(sig_candle && !f2)
      {
         High_s = currentHigh;
         Low_s = currentLow;
         valid_buy = false;
         valid_sell = true;
      }
      
      // Buy condition: Price crosses above the High of the crossover candle
      bool buy = false;
      if(High > 0.0 && i + 1 < rates_total)
      {
         // Check if current close crosses above High (from below or equal)
         buy = (currentClose > High) && (prevClose <= High);
      }
      
      // Sell condition: Price crosses below the Low of the crossunder candle
      bool sell = false;
      if(Low_s > 0.0 && i + 1 < rates_total)
      {
         // Check if current close crosses below Low_s (from above or equal)
         sell = (currentClose < Low_s) && (prevClose >= Low_s);
      }
      
      // Handle buy entry
      if(buy)
      {
         f1 = true;
         f2 = false;
         entry_high = High;
         entry_low = Low;
         BuyEntryBuffer[i] = low[i];
         
         // Alert on Buy Entry (only once per bar when entry is first detected)
         // #region agent log - DEBUG: Buy alert condition check
         if(i == 0)
         {
            Print("SMMA Indicator: [DEBUG] Bar 0 detected - checking buy alert conditions");
            Print("SMMA Indicator: [DEBUG] EnableAlerts=", EnableAlerts ? "true" : "false");
            Print("SMMA Indicator: [DEBUG] time[0]=", TimeToString(time[0]), " | last_buy_entry_time=", TimeToString(last_buy_entry_time));
            Print("SMMA Indicator: [DEBUG] buy condition=", buy ? "true" : "false");
         }
         // #endregion
         
         if(EnableAlerts && i == 0 && time[0] != last_buy_entry_time)
         {
            // #region agent log - DEBUG: Buy alert triggered
            Print("SMMA Indicator: [DEBUG] HYPOTHESIS-2: WriteAlertToFile() will be called for BUY");
            Print("SMMA Indicator: [DEBUG] Buy alert parameters: Symbol=", _Symbol, " Price=", currentClose, " High=", High, " Period=", Period());
            // #endregion
            
            string alertMsg = StringFormat("SMMA Buy Entry: %s | Price: %.5f | Entry High: %.5f", 
                                          _Symbol, currentClose, High);
            Alert(alertMsg);
            Print(alertMsg);
            WriteAlertToFile(_Symbol, "BUY", currentClose, High, Period());
            
            // Create alert in Alerts tab (price alert that will trigger on next tick)
            // Using price slightly above current so alert shows in tab and triggers soon
            datetime expiration = TimeCurrent() + PeriodSeconds(PERIOD_D1); // Expires in 1 day
            double alertPrice = currentClose + _Point; // Price 1 point above current
            string alertTabMsg = StringFormat("SMMA BUY: %s @ %.5f", _Symbol, currentClose);
            if(!AlertCreate(_Symbol, ALERT_TYPE_PRICE_UP, alertPrice, expiration, alertTabMsg))
            {
               Print("SMMA Indicator: Failed to create alert in Alerts tab. Error: ", GetLastError());
            }
            
            last_buy_entry_time = time[0];  // Remember this bar's time
         }
      }
      
      // Reset buy levels when price crosses below entry_low
      if(entry_low > 0.0 && i + 1 < rates_total)
      {
         if(IsCrossunder(currentClose, prevClose, entry_low, entry_low))
         {
            High = 0.0;
            Low = 0.0;
            f1 = false;
            valid_buy = false;
         }
      }
      
      // Handle sell entry
      if(sell)
      {
         entry_high_s = currentHigh;
         entry_low_s = currentLow;
         f1 = false;
         f2 = true;
         SellEntryBuffer[i] = high[i];
         
         // Alert on Sell Entry (only once per bar when entry is first detected)
         // #region agent log - DEBUG: Sell alert condition check
         if(i == 0 && sell)
         {
            Print("SMMA Indicator: [DEBUG] Bar 0 detected - checking sell alert conditions");
            Print("SMMA Indicator: [DEBUG] EnableAlerts=", EnableAlerts ? "true" : "false");
            Print("SMMA Indicator: [DEBUG] time[0]=", TimeToString(time[0]), " | last_sell_entry_time=", TimeToString(last_sell_entry_time));
            Print("SMMA Indicator: [DEBUG] sell condition=", sell ? "true" : "false");
         }
         // #endregion
         
         if(EnableAlerts && i == 0 && time[0] != last_sell_entry_time)
         {
            // #region agent log - DEBUG: Sell alert triggered
            Print("SMMA Indicator: [DEBUG] HYPOTHESIS-2: WriteAlertToFile() will be called for SELL");
            Print("SMMA Indicator: [DEBUG] Sell alert parameters: Symbol=", _Symbol, " Price=", currentClose, " Low_s=", Low_s, " Period=", Period());
            // #endregion
            
            string alertMsg = StringFormat("SMMA Sell Entry: %s | Price: %.5f | Entry Low: %.5f", 
                                          _Symbol, currentClose, Low_s);
            Alert(alertMsg);
            Print(alertMsg);
            WriteAlertToFile(_Symbol, "SELL", currentClose, Low_s, Period());
            
            // Create alert in Alerts tab (price alert that will trigger on next tick)
            // Using price slightly below current so alert shows in tab and triggers soon
            datetime expiration = TimeCurrent() + PeriodSeconds(PERIOD_D1); // Expires in 1 day
            double alertPrice = currentClose - _Point; // Price 1 point below current
            string alertTabMsg = StringFormat("SMMA SELL: %s @ %.5f", _Symbol, currentClose);
            if(!AlertCreate(_Symbol, ALERT_TYPE_PRICE_DOWN, alertPrice, expiration, alertTabMsg))
            {
               Print("SMMA Indicator: Failed to create alert in Alerts tab. Error: ", GetLastError());
            }
            
            last_sell_entry_time = time[0];  // Remember this bar's time
         }
      }
      
      // Reset sell levels when price crosses above entry_high_s
      if(entry_high_s > 0.0 && i + 1 < rates_total)
      {
         if(IsCrossover(currentClose, prevClose, entry_high_s, entry_high_s))
         {
            High_s = 0.0;
            Low_s = 0.0;
            f2 = false;
            valid_sell = false;
         }
      }
      
      // Plot entry level lines (conditional - only when valid)
      // In Pine Script: plot(valid_buy ? Low : Low[1], ...) - plots current or previous value
      // We need to persist the line across bars when valid
      if(valid_buy && Low > 0.0)
      {
         // Get previous Low value for comparison (conditional color logic)
         double prevLow = (i + 1 < rates_total && BuyEntryLowBuffer[i + 1] != EMPTY_VALUE) ? BuyEntryLowBuffer[i + 1] : 0.0;
         
         // Only plot if Low is the same as previous (matching Pine Script conditional color)
         if(prevLow == 0.0 || MathAbs(Low - prevLow) <= eps)
         {
            BuyEntryLowBuffer[i] = Low;
         }
      }
      else if(i + 1 < rates_total && BuyEntryLowBuffer[i + 1] != EMPTY_VALUE)
      {
         // Continue plotting previous value if it existed
         BuyEntryLowBuffer[i] = BuyEntryLowBuffer[i + 1];
      }
      
      if(valid_buy && High > 0.0)
      {
         double prevHigh = (i + 1 < rates_total && BuyEntryHighBuffer[i + 1] != EMPTY_VALUE) ? BuyEntryHighBuffer[i + 1] : 0.0;
         if(prevHigh == 0.0 || MathAbs(High - prevHigh) <= eps)
         {
            BuyEntryHighBuffer[i] = High;
         }
      }
      else if(i + 1 < rates_total && BuyEntryHighBuffer[i + 1] != EMPTY_VALUE)
      {
         BuyEntryHighBuffer[i] = BuyEntryHighBuffer[i + 1];
      }
      
      if(valid_sell && High_s > 0.0)
      {
         double prevHigh_s = (i + 1 < rates_total && SellEntryHighBuffer[i + 1] != EMPTY_VALUE) ? SellEntryHighBuffer[i + 1] : 0.0;
         if(prevHigh_s == 0.0 || MathAbs(High_s - prevHigh_s) <= eps)
         {
            SellEntryHighBuffer[i] = High_s;
         }
      }
      else if(i + 1 < rates_total && SellEntryHighBuffer[i + 1] != EMPTY_VALUE)
      {
         SellEntryHighBuffer[i] = SellEntryHighBuffer[i + 1];
      }
      
      if(valid_sell && Low_s > 0.0)
      {
         double prevLow_s = (i + 1 < rates_total && SellEntryLowBuffer[i + 1] != EMPTY_VALUE) ? SellEntryLowBuffer[i + 1] : 0.0;
         if(prevLow_s == 0.0 || MathAbs(Low_s - prevLow_s) <= eps)
         {
            SellEntryLowBuffer[i] = Low_s;
         }
      }
      else if(i + 1 < rates_total && SellEntryLowBuffer[i + 1] != EMPTY_VALUE)
      {
         SellEntryLowBuffer[i] = SellEntryLowBuffer[i + 1];
      }
   }
   
   // Flush alert file periodically
   if(alert_file_handle != INVALID_HANDLE && prev_calculated > 0)
   {
      FileFlush(alert_file_handle);
   }
   
   return(rates_total);
}

//+------------------------------------------------------------------+
//| Write alert to file for Python platform                          |
//+------------------------------------------------------------------+
void WriteAlertToFile(string symbol, string action, double price, double entry_level, int timeframe)
{
   // #region agent log - DEBUG: WriteAlertToFile entry
   Print("SMMA Indicator: [DEBUG] WriteAlertToFile() called");
   Print("SMMA Indicator: [DEBUG] Parameters: symbol=", symbol, " action=", action, " price=", price, " entry_level=", entry_level, " timeframe=", timeframe);
   Print("SMMA Indicator: [DEBUG] Current alert_file_handle=", IntegerToString(alert_file_handle));
   Print("SMMA Indicator: [DEBUG] INVALID_HANDLE=", IntegerToString(INVALID_HANDLE));
   // #endregion
   
   // Check if file handle is valid, try to reopen if not
   if(alert_file_handle == INVALID_HANDLE)
   {
      // #region agent log - DEBUG: File handle invalid
      Print("SMMA Indicator: [DEBUG] HYPOTHESIS-3: File handle is INVALID_HANDLE - CONFIRMED");
      Print("SMMA Indicator: [DEBUG] Attempting to reopen file...");
      // #endregion
      
      Print("SMMA Indicator: File handle invalid, attempting to reopen file...");
      alert_file_handle = FileOpen(AlertFileName, FILE_WRITE|FILE_READ|FILE_TXT|FILE_COMMON|FILE_ANSI);
      
      // #region agent log - DEBUG: Reopen attempt result
      Print("SMMA Indicator: [DEBUG] Reopen attempt handle: ", IntegerToString(alert_file_handle));
      // #endregion
      
      if(alert_file_handle == INVALID_HANDLE)
      {
         int error_code = GetLastError();
         Print("SMMA Indicator: ERROR - Cannot write alert - file not open");
         Print("SMMA Indicator: Error code: ", error_code, " | File: ", AlertFileName);
         Print("SMMA Indicator: Alert NOT written to file: ", action, " ", symbol, " @ ", price);
         
         // #region agent log - DEBUG: Reopen failed
         Print("SMMA Indicator: [DEBUG] HYPOTHESIS-3: File reopen failed - CONFIRMED");
         Print("SMMA Indicator: [DEBUG] GetLastError()=", error_code);
         // #endregion
         
         return;
      }
      else
      {
         Print("SMMA Indicator: File reopened successfully");
         FileSeek(alert_file_handle, 0, SEEK_END);
         
         // #region agent log - DEBUG: Reopen succeeded
         Print("SMMA Indicator: [DEBUG] HYPOTHESIS-3: File reopened successfully - REJECTED");
         // #endregion
      }
   }
   else
   {
      // #region agent log - DEBUG: File handle valid
      Print("SMMA Indicator: [DEBUG] HYPOTHESIS-3: File handle is valid - REJECTED");
      // #endregion
   }
   
   // Convert timeframe to string
   string timeframe_str = "";
   switch(timeframe)
   {
      case PERIOD_M1:  timeframe_str = "1"; break;
      case PERIOD_M5:  timeframe_str = "5"; break;
      case PERIOD_M15: timeframe_str = "15"; break;
      case PERIOD_M30: timeframe_str = "30"; break;
      case PERIOD_H1:  timeframe_str = "60"; break;
      case PERIOD_H4:  timeframe_str = "240"; break;
      case PERIOD_D1:  timeframe_str = "1440"; break;
      default: timeframe_str = IntegerToString(timeframe); break;
   }
   
   // Format: timestamp|symbol|action|price|entry_level|indicator|timeframe
   datetime current_time = TimeCurrent();
   string alert_line = StringFormat("%s|%s|%s|%.5f|%.5f|SMMA|%s",
                                    TimeToString(current_time, TIME_DATE|TIME_SECONDS),
                                    symbol,
                                    action,
                                    price,
                                    entry_level,
                                    timeframe_str);
   
   // #region agent log - DEBUG: Before file write operations
   Print("SMMA Indicator: [DEBUG] About to write alert line: ", alert_line);
   ulong file_size_before = FileSize(alert_file_handle);
   Print("SMMA Indicator: [DEBUG] File size before write: ", IntegerToString(file_size_before), " bytes");
   // #endregion
   
   // Write to file (append mode)
   // Move to end of file
   ulong file_position = FileSeek(alert_file_handle, 0, SEEK_END);
   
   // #region agent log - DEBUG: FileSeek result
   Print("SMMA Indicator: [DEBUG] FileSeek(END) returned: ", IntegerToString(file_position));
   // #endregion
   
   if(file_position == INVALID_FILE_POSITION)
   {
      int error_code = GetLastError();
      Print("SMMA Indicator: ERROR - FileSeek failed. Error code: ", error_code);
      Print("SMMA Indicator: Alert NOT written: ", action, " ", symbol);
      
      // #region agent log - DEBUG: FileSeek failed
      Print("SMMA Indicator: [DEBUG] HYPOTHESIS-4: FileSeek failed - CONFIRMED");
      Print("SMMA Indicator: [DEBUG] GetLastError()=", error_code);
      // #endregion
      
      return;
   }
   
   // Write the alert line
   uint bytes_written = FileWriteString(alert_file_handle, alert_line + "\n");
   
   // #region agent log - DEBUG: FileWriteString result
   Print("SMMA Indicator: [DEBUG] FileWriteString() returned: ", IntegerToString(bytes_written), " bytes");
   // #endregion
   
   if(bytes_written == 0)
   {
      int error_code = GetLastError();
      Print("SMMA Indicator: ERROR - FileWriteString failed. Error code: ", error_code);
      Print("SMMA Indicator: Alert NOT written: ", action, " ", symbol);
      
      // #region agent log - DEBUG: FileWriteString failed
      Print("SMMA Indicator: [DEBUG] HYPOTHESIS-4: FileWriteString failed - CONFIRMED");
      Print("SMMA Indicator: [DEBUG] GetLastError()=", error_code);
      // #endregion
      
      return;
   }
   
   // Flush to ensure data is written immediately
   bool flush_result = FileFlush(alert_file_handle);
   
   // #region agent log - DEBUG: FileFlush result
   Print("SMMA Indicator: [DEBUG] FileFlush() returned: ", flush_result ? "true" : "false");
   // #endregion
   
   if(!flush_result)
   {
      int error_code = GetLastError();
      Print("SMMA Indicator: WARNING - FileFlush failed. Error code: ", error_code);
      Print("SMMA Indicator: Alert may not be immediately available");
   }
   
   // #region agent log - DEBUG: After file write operations
   ulong file_size_after = FileSize(alert_file_handle);
   Print("SMMA Indicator: [DEBUG] File size after write: ", IntegerToString(file_size_after), " bytes");
   Print("SMMA Indicator: [DEBUG] HYPOTHESIS-4: File write operations completed - REJECTED");
   // #endregion
   
   // Success message with full details
   Print("SMMA Indicator: Alert written to file successfully");
   Print("SMMA Indicator: Alert line: ", alert_line);
   Print("SMMA Indicator: Bytes written: ", IntegerToString(bytes_written));
}

   // Debug info
   if(ShowDebugInfo)
   {
      string symbolName = _Symbol;
      int digits = (int)SymbolInfoInteger(symbolName, SYMBOL_DIGITS);
      string debugInfo = StringFormat("SMMA(%d): %.*f | valid_buy: %s | valid_sell: %s | High: %.*f | Low: %.*f | High_s: %.*f | Low_s: %.*f", 
                                      Length, digits, SMMABuffer[0],
                                      valid_buy ? "true" : "false",
                                      valid_sell ? "true" : "false",
                                      digits, High, digits, Low,
                                      digits, High_s, digits, Low_s);
      Comment(debugInfo);
   }
   
   return(rates_total);
}

//+------------------------------------------------------------------+
