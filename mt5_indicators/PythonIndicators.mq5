//+------------------------------------------------------------------+
//| PythonIndicators.mq5                                             |
//| Displays Python-calculated indicators on MT5 charts              |
//| Reads indicator values from JSON files in MQL5/Files/           |
//+------------------------------------------------------------------+
#property copyright "Python Strategy Indicators"
#property link      ""
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 20
#property indicator_plots   20

// Input parameters
input string InpSymbol = "";           // Symbol (empty = chart symbol)
input int    InpTimeframe = 0;         // Timeframe (0 = chart timeframe)
input bool   ShowEMA_50 = true;        // Show EMA 50
input bool   ShowEMA_200 = true;       // Show EMA 200
input bool   ShowVWAP = true;          // Show VWAP
input bool   ShowSuperTrend = true;    // Show SuperTrend
input bool   ShowRSI = false;          // Show RSI (separate window)
input bool   ShowMACD = false;          // Show MACD (separate window)
input bool   ShowBB = false;           // Show Bollinger Bands
input bool   ShowStochastic = false;   // Show Stochastic (separate window)

// Indicator buffers
double EMA50Buffer[];
double EMA200Buffer[];
double VWAPBuffer[];
double SuperTrendBuffer[];
double SuperTrendUpperBuffer[];
double SuperTrendLowerBuffer[];
double RSIBuffer[];
double MACDBuffer[];
double MACDSignalBuffer[];
double MACDHistogramBuffer[];
double BBUpperBuffer[];
double BBMiddleBuffer[];
double BBLowerBuffer[];
double StochasticKBuffer[];
double StochasticDBuffer[];

// Global variables
string g_symbol;
int g_timeframe;
string g_filepath;
datetime g_last_file_check = 0;
int g_file_check_interval_seconds = 1; // Check file every 1 second

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Set symbol and timeframe
   g_symbol = (InpSymbol == "") ? _Symbol : InpSymbol;
   g_timeframe = (InpTimeframe == 0) ? _Period : InpTimeframe;
   
   // Build file path (use forward slash for MQL5 compatibility)
   string timeframe_str = TimeframeToString(g_timeframe);
   string filename = g_symbol + "_" + timeframe_str + "_indicators.json";
   g_filepath = "PythonIndicators/" + filename;
   
   // Set up buffers
   SetIndexBuffer(0, EMA50Buffer, INDICATOR_DATA);
   SetIndexBuffer(1, EMA200Buffer, INDICATOR_DATA);
   SetIndexBuffer(2, VWAPBuffer, INDICATOR_DATA);
   SetIndexBuffer(3, SuperTrendBuffer, INDICATOR_DATA);
   SetIndexBuffer(4, SuperTrendUpperBuffer, INDICATOR_DATA);
   SetIndexBuffer(5, SuperTrendLowerBuffer, INDICATOR_DATA);
   SetIndexBuffer(6, RSIBuffer, INDICATOR_DATA);
   SetIndexBuffer(7, MACDBuffer, INDICATOR_DATA);
   SetIndexBuffer(8, MACDSignalBuffer, INDICATOR_DATA);
   SetIndexBuffer(9, MACDHistogramBuffer, INDICATOR_DATA);
   SetIndexBuffer(10, BBUpperBuffer, INDICATOR_DATA);
   SetIndexBuffer(11, BBMiddleBuffer, INDICATOR_DATA);
   SetIndexBuffer(12, BBLowerBuffer, INDICATOR_DATA);
   SetIndexBuffer(13, StochasticKBuffer, INDICATOR_DATA);
   SetIndexBuffer(14, StochasticDBuffer, INDICATOR_DATA);
   
   // Initialize all buffers with EMPTY_VALUE
   ArrayInitialize(EMA50Buffer, EMPTY_VALUE);
   ArrayInitialize(EMA200Buffer, EMPTY_VALUE);
   ArrayInitialize(VWAPBuffer, EMPTY_VALUE);
   ArrayInitialize(SuperTrendBuffer, EMPTY_VALUE);
   ArrayInitialize(SuperTrendUpperBuffer, EMPTY_VALUE);
   ArrayInitialize(SuperTrendLowerBuffer, EMPTY_VALUE);
   ArrayInitialize(RSIBuffer, EMPTY_VALUE);
   ArrayInitialize(MACDBuffer, EMPTY_VALUE);
   ArrayInitialize(MACDSignalBuffer, EMPTY_VALUE);
   ArrayInitialize(MACDHistogramBuffer, EMPTY_VALUE);
   ArrayInitialize(BBUpperBuffer, EMPTY_VALUE);
   ArrayInitialize(BBMiddleBuffer, EMPTY_VALUE);
   ArrayInitialize(BBLowerBuffer, EMPTY_VALUE);
   ArrayInitialize(StochasticKBuffer, EMPTY_VALUE);
   ArrayInitialize(StochasticDBuffer, EMPTY_VALUE);
   
   // Set indicator digits (precision)
   IndicatorSetInteger(INDICATOR_DIGITS, _Digits);
   
   // Configure plots - ALL plots must be configured, even if not shown
   // Plot 0: EMA 50
   PlotIndexSetInteger(0, PLOT_DRAW_TYPE, ShowEMA_50 ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(0, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(0, PLOT_LINE_WIDTH, 2);
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, clrOrange);
   PlotIndexSetString(0, PLOT_LABEL, "EMA(50)");
   
   // Plot 1: EMA 200
   PlotIndexSetInteger(1, PLOT_DRAW_TYPE, ShowEMA_200 ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(1, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(1, PLOT_LINE_WIDTH, 2);
   PlotIndexSetInteger(1, PLOT_LINE_COLOR, clrBlue);
   PlotIndexSetString(1, PLOT_LABEL, "EMA(200)");
   
   // Plot 2: VWAP
   PlotIndexSetInteger(2, PLOT_DRAW_TYPE, ShowVWAP ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(2, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(2, PLOT_LINE_WIDTH, 2);
   PlotIndexSetInteger(2, PLOT_LINE_COLOR, clrCyan);
   PlotIndexSetString(2, PLOT_LABEL, "VWAP");
   
   // Plot 3: SuperTrend
   PlotIndexSetInteger(3, PLOT_DRAW_TYPE, ShowSuperTrend ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(3, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(3, PLOT_LINE_WIDTH, 2);
   PlotIndexSetInteger(3, PLOT_LINE_COLOR, clrLime);
   PlotIndexSetString(3, PLOT_LABEL, "SuperTrend");
   
   // Plot 4: SuperTrend Upper
   PlotIndexSetInteger(4, PLOT_DRAW_TYPE, ShowSuperTrend ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(4, PLOT_LINE_STYLE, STYLE_DOT);
   PlotIndexSetInteger(4, PLOT_LINE_WIDTH, 1);
   PlotIndexSetInteger(4, PLOT_LINE_COLOR, clrGreen);
   PlotIndexSetString(4, PLOT_LABEL, "SuperTrend Upper");
   
   // Plot 5: SuperTrend Lower
   PlotIndexSetInteger(5, PLOT_DRAW_TYPE, ShowSuperTrend ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(5, PLOT_LINE_STYLE, STYLE_DOT);
   PlotIndexSetInteger(5, PLOT_LINE_WIDTH, 1);
   PlotIndexSetInteger(5, PLOT_LINE_COLOR, clrRed);
   PlotIndexSetString(5, PLOT_LABEL, "SuperTrend Lower");
   
   // Plot 6: RSI
   PlotIndexSetInteger(6, PLOT_DRAW_TYPE, ShowRSI ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(6, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(6, PLOT_LINE_WIDTH, 2);
   PlotIndexSetInteger(6, PLOT_LINE_COLOR, clrYellow);
   PlotIndexSetString(6, PLOT_LABEL, "RSI");
   
   // Plot 7: MACD
   PlotIndexSetInteger(7, PLOT_DRAW_TYPE, ShowMACD ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(7, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(7, PLOT_LINE_WIDTH, 2);
   PlotIndexSetInteger(7, PLOT_LINE_COLOR, clrBlue);
   PlotIndexSetString(7, PLOT_LABEL, "MACD");
   
   // Plot 8: MACD Signal
   PlotIndexSetInteger(8, PLOT_DRAW_TYPE, ShowMACD ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(8, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(8, PLOT_LINE_WIDTH, 1);
   PlotIndexSetInteger(8, PLOT_LINE_COLOR, clrRed);
   PlotIndexSetString(8, PLOT_LABEL, "MACD Signal");
   
   // Plot 9: MACD Histogram
   PlotIndexSetInteger(9, PLOT_DRAW_TYPE, ShowMACD ? DRAW_HISTOGRAM : DRAW_NONE);
   PlotIndexSetInteger(9, PLOT_LINE_WIDTH, 1);
   PlotIndexSetInteger(9, PLOT_LINE_COLOR, clrGray);
   PlotIndexSetString(9, PLOT_LABEL, "MACD Histogram");
   
   // Plot 10: BB Upper
   PlotIndexSetInteger(10, PLOT_DRAW_TYPE, ShowBB ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(10, PLOT_LINE_STYLE, STYLE_DOT);
   PlotIndexSetInteger(10, PLOT_LINE_WIDTH, 1);
   PlotIndexSetInteger(10, PLOT_LINE_COLOR, clrBlue);
   PlotIndexSetString(10, PLOT_LABEL, "BB Upper");
   
   // Plot 11: BB Middle
   PlotIndexSetInteger(11, PLOT_DRAW_TYPE, ShowBB ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(11, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(11, PLOT_LINE_WIDTH, 1);
   PlotIndexSetInteger(11, PLOT_LINE_COLOR, clrWhite);
   PlotIndexSetString(11, PLOT_LABEL, "BB Middle");
   
   // Plot 12: BB Lower
   PlotIndexSetInteger(12, PLOT_DRAW_TYPE, ShowBB ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(12, PLOT_LINE_STYLE, STYLE_DOT);
   PlotIndexSetInteger(12, PLOT_LINE_WIDTH, 1);
   PlotIndexSetInteger(12, PLOT_LINE_COLOR, clrBlue);
   PlotIndexSetString(12, PLOT_LABEL, "BB Lower");
   
   // Plot 13: Stochastic %K
   PlotIndexSetInteger(13, PLOT_DRAW_TYPE, ShowStochastic ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(13, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(13, PLOT_LINE_WIDTH, 2);
   PlotIndexSetInteger(13, PLOT_LINE_COLOR, clrMagenta);
   PlotIndexSetString(13, PLOT_LABEL, "Stochastic %K");
   
   // Plot 14: Stochastic %D
   PlotIndexSetInteger(14, PLOT_DRAW_TYPE, ShowStochastic ? DRAW_LINE : DRAW_NONE);
   PlotIndexSetInteger(14, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(14, PLOT_LINE_WIDTH, 1);
   PlotIndexSetInteger(14, PLOT_LINE_COLOR, clrYellow);
   PlotIndexSetString(14, PLOT_LABEL, "Stochastic %D");
   
   IndicatorSetString(INDICATOR_SHORTNAME, "Python Indicators");
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator iteration function                              |
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
   // Check file periodically (not on every tick to reduce I/O)
   datetime current_time = TimeCurrent();
   // Always check on first call (g_last_file_check == 0) or if enough time has passed
   if(g_last_file_check > 0 && (current_time - g_last_file_check) < g_file_check_interval_seconds)
   {
      // Return previous calculated to avoid recalculation
      return(rates_total);
   }
   
   g_last_file_check = current_time;
   
   // Read indicator values from JSON file
   int file_handle = FileOpen(g_filepath, FILE_READ|FILE_TXT);
   if(file_handle == INVALID_HANDLE)
   {
      // File doesn't exist or can't be read - fill with EMPTY_VALUE
      ArrayInitialize(EMA50Buffer, EMPTY_VALUE);
      ArrayInitialize(EMA200Buffer, EMPTY_VALUE);
      ArrayInitialize(VWAPBuffer, EMPTY_VALUE);
      ArrayInitialize(SuperTrendBuffer, EMPTY_VALUE);
      ArrayInitialize(SuperTrendUpperBuffer, EMPTY_VALUE);
      ArrayInitialize(SuperTrendLowerBuffer, EMPTY_VALUE);
      ArrayInitialize(RSIBuffer, EMPTY_VALUE);
      ArrayInitialize(MACDBuffer, EMPTY_VALUE);
      ArrayInitialize(MACDSignalBuffer, EMPTY_VALUE);
      ArrayInitialize(MACDHistogramBuffer, EMPTY_VALUE);
      ArrayInitialize(BBUpperBuffer, EMPTY_VALUE);
      ArrayInitialize(BBMiddleBuffer, EMPTY_VALUE);
      ArrayInitialize(BBLowerBuffer, EMPTY_VALUE);
      ArrayInitialize(StochasticKBuffer, EMPTY_VALUE);
      ArrayInitialize(StochasticDBuffer, EMPTY_VALUE);
      
      return(rates_total);
   }
   
   // Read JSON content (read entire file)
   string json_content = "";
   while(!FileIsEnding(file_handle))
   {
      string line = FileReadString(file_handle);
      if(StringLen(line) > 0)
         json_content += line + "\n";
   }
   FileClose(file_handle);
   
   // Parse JSON (simple parsing - MQL5 doesn't have built-in JSON parser)
   // First, find the "indicators" object in the JSON
   int indicators_start = StringFind(json_content, "\"indicators\"");
   if(indicators_start < 0)
   {
      // No indicators object found - fill with EMPTY_VALUE
      ArrayInitialize(EMA50Buffer, EMPTY_VALUE);
      ArrayInitialize(EMA200Buffer, EMPTY_VALUE);
      ArrayInitialize(VWAPBuffer, EMPTY_VALUE);
      ArrayInitialize(SuperTrendBuffer, EMPTY_VALUE);
      ArrayInitialize(SuperTrendUpperBuffer, EMPTY_VALUE);
      ArrayInitialize(SuperTrendLowerBuffer, EMPTY_VALUE);
      ArrayInitialize(RSIBuffer, EMPTY_VALUE);
      ArrayInitialize(MACDBuffer, EMPTY_VALUE);
      ArrayInitialize(MACDSignalBuffer, EMPTY_VALUE);
      ArrayInitialize(MACDHistogramBuffer, EMPTY_VALUE);
      ArrayInitialize(BBUpperBuffer, EMPTY_VALUE);
      ArrayInitialize(BBMiddleBuffer, EMPTY_VALUE);
      ArrayInitialize(BBLowerBuffer, EMPTY_VALUE);
      ArrayInitialize(StochasticKBuffer, EMPTY_VALUE);
      ArrayInitialize(StochasticDBuffer, EMPTY_VALUE);
      return(rates_total);
   }
   
   // Extract the indicators section
   int indicators_brace_start = StringFind(json_content, "{", indicators_start);
   if(indicators_brace_start < 0)
   {
      ArrayInitialize(EMA50Buffer, EMPTY_VALUE);
      return(rates_total);
   }
   
   // Extract indicator values from the indicators object
   double ema50 = ParseJSONValueFromObject(json_content, indicators_brace_start, "EMA_50");
   double ema200 = ParseJSONValueFromObject(json_content, indicators_brace_start, "EMA_200");
   double vwap = ParseJSONValueFromObject(json_content, indicators_brace_start, "VWAP");
   double supertrend = ParseJSONValueFromObject(json_content, indicators_brace_start, "SuperTrend");
   double supertrend_upper = ParseJSONValueFromObject(json_content, indicators_brace_start, "SuperTrend_Upper");
   double supertrend_lower = ParseJSONValueFromObject(json_content, indicators_brace_start, "SuperTrend_Lower");
   double rsi = ParseJSONValueFromObject(json_content, indicators_brace_start, "RSI");
   double macd = ParseJSONValueFromObject(json_content, indicators_brace_start, "MACD", "macd");
   double macd_signal = ParseJSONValueFromObject(json_content, indicators_brace_start, "MACD", "signal");
   double macd_histogram = ParseJSONValueFromObject(json_content, indicators_brace_start, "MACD", "histogram");
   double bb_upper = ParseJSONValueFromObject(json_content, indicators_brace_start, "BB_Upper");
   double bb_middle = ParseJSONValueFromObject(json_content, indicators_brace_start, "BB_Middle");
   double bb_lower = ParseJSONValueFromObject(json_content, indicators_brace_start, "BB_Lower");
   double stoch_k = ParseJSONValueFromObject(json_content, indicators_brace_start, "Stochastic_K");
   double stoch_d = ParseJSONValueFromObject(json_content, indicators_brace_start, "Stochastic_D");
   
   // Fill buffers with latest value (all bars get same value for simplicity)
   // In a more advanced version, we could store historical values
   for(int i = 0; i < rates_total; i++)
   {
      // Use proper validation - check if value is valid (not EMPTY_VALUE)
      // Note: Some indicators can be 0 or negative (like MACD), so we only check for EMPTY_VALUE
      EMA50Buffer[i] = (ShowEMA_50 && ema50 != EMPTY_VALUE) ? ema50 : EMPTY_VALUE;
      EMA200Buffer[i] = (ShowEMA_200 && ema200 != EMPTY_VALUE) ? ema200 : EMPTY_VALUE;
      VWAPBuffer[i] = (ShowVWAP && vwap != EMPTY_VALUE) ? vwap : EMPTY_VALUE;
      SuperTrendBuffer[i] = (ShowSuperTrend && supertrend != EMPTY_VALUE) ? supertrend : EMPTY_VALUE;
      SuperTrendUpperBuffer[i] = (ShowSuperTrend && supertrend_upper != EMPTY_VALUE) ? supertrend_upper : EMPTY_VALUE;
      SuperTrendLowerBuffer[i] = (ShowSuperTrend && supertrend_lower != EMPTY_VALUE) ? supertrend_lower : EMPTY_VALUE;
      RSIBuffer[i] = (ShowRSI && rsi != EMPTY_VALUE && rsi >= 0 && rsi <= 100) ? rsi : EMPTY_VALUE;
      MACDBuffer[i] = (ShowMACD && macd != EMPTY_VALUE) ? macd : EMPTY_VALUE;
      MACDSignalBuffer[i] = (ShowMACD && macd_signal != EMPTY_VALUE) ? macd_signal : EMPTY_VALUE;
      MACDHistogramBuffer[i] = (ShowMACD && macd_histogram != EMPTY_VALUE) ? macd_histogram : EMPTY_VALUE;
      BBUpperBuffer[i] = (ShowBB && bb_upper != EMPTY_VALUE) ? bb_upper : EMPTY_VALUE;
      BBMiddleBuffer[i] = (ShowBB && bb_middle != EMPTY_VALUE) ? bb_middle : EMPTY_VALUE;
      BBLowerBuffer[i] = (ShowBB && bb_lower != EMPTY_VALUE) ? bb_lower : EMPTY_VALUE;
      StochasticKBuffer[i] = (ShowStochastic && stoch_k != EMPTY_VALUE && stoch_k >= 0 && stoch_k <= 100) ? stoch_k : EMPTY_VALUE;
      StochasticDBuffer[i] = (ShowStochastic && stoch_d != EMPTY_VALUE && stoch_d >= 0 && stoch_d <= 100) ? stoch_d : EMPTY_VALUE;
   }
   
   // Force chart refresh
   ChartRedraw();
   
   return(rates_total);
}

//+------------------------------------------------------------------+
//| Parse JSON value from indicators object (improved parser)        |
//+------------------------------------------------------------------+
double ParseJSONValueFromObject(string json, int object_start, string key, string subkey = "")
{
   double empty_val = EMPTY_VALUE;
   
   // Search for the key within the object (starting from object_start)
   string search_key = "\"" + key + "\"";
   int pos = StringFind(json, search_key, object_start);
   if(pos < 0)
      return(empty_val);
   
   // Find the colon after the key
   int colon_pos = StringFind(json, ":", pos);
   if(colon_pos < 0)
      return(empty_val);
   
   // If subkey is provided, look for nested object (e.g., MACD.macd)
   if(subkey != "")
   {
      // Find the opening brace after the colon
      int brace_pos = StringFind(json, "{", colon_pos);
      if(brace_pos < 0)
         return(empty_val);
      
      // Find the subkey within the nested object
      string nested_search = "\"" + subkey + "\"";
      int nested_pos = StringFind(json, nested_search, brace_pos);
      if(nested_pos < 0)
         return(empty_val);
      
      // Find colon after nested key
      int nested_colon = StringFind(json, ":", nested_pos);
      if(nested_colon < 0)
         return(empty_val);
      
      // Extract value after nested colon
      int value_start = nested_colon + 1;
      int value_end = StringFind(json, ",", value_start);
      if(value_end < 0)
         value_end = StringFind(json, "}", value_start);
      if(value_end < 0)
         return(empty_val);
      
      string value_str = StringSubstr(json, value_start, value_end - value_start);
      StringTrimLeft(value_str);
      StringTrimRight(value_str);
      
      // Check if value is null or empty
      if(StringFind(value_str, "null") >= 0 || StringLen(value_str) == 0)
         return(empty_val);
      
      double result = StringToDouble(value_str);
      return(result);
   }
   
   // Extract value after colon (simple value, not nested)
   int value_start = colon_pos + 1;
   int value_end = StringFind(json, ",", value_start);
   if(value_end < 0)
      value_end = StringFind(json, "}", value_start);
   if(value_end < 0)
      value_end = StringFind(json, "\n", value_start);
   if(value_end < 0)
      value_end = StringLen(json);
   
   string value_str = StringSubstr(json, value_start, value_end - value_start);
   StringTrimLeft(value_str);
   StringTrimRight(value_str);
   
   // Check if value is null or empty
   if(StringFind(value_str, "null") >= 0 || StringLen(value_str) == 0)
      return(empty_val);
   
   double result = StringToDouble(value_str);
   return(result);
}

//+------------------------------------------------------------------+
//| Convert timeframe to string                                      |
//+------------------------------------------------------------------+
string TimeframeToString(int tf)
{
   switch(tf)
   {
      case PERIOD_M1:  return("M1");
      case PERIOD_M5:  return("M5");
      case PERIOD_M15: return("M15");
      case PERIOD_M30: return("M30");
      case PERIOD_H1:  return("H1");
      case PERIOD_H4:  return("H4");
      case PERIOD_D1:  return("D1");
      case PERIOD_W1:  return("W1");
      case PERIOD_MN1: return("MN1");
      default:         return("TF" + IntegerToString(tf));
   }
}

