//+------------------------------------------------------------------+
//|                                          VWAP_Indicator.mq5      |
//|                        Volume Weighted Average Price (VWAP)       |
//|                                                                  |
//| This indicator plots VWAP with standard deviation bands:        |
//| - VWAP line (session-based)                                     |
//| - Standard deviation bands (configurable levels)                |
//| - Session reset support (NY, London, Asia, All)                |
//+------------------------------------------------------------------+
#property copyright "VWAP Indicator for Visual Monitoring"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 7
#property indicator_plots   7

//--- Input Parameters
input string SessionType = "NY";           // Session Type: NY, London, Asia, All
input bool   UseTypicalPrice = true;      // Use Typical Price (H+L+C)/3, else Close
input string StdBands = "1.0,1.5,2.0";   // Standard Deviation Bands (comma-separated)
input color  VWAPColor = clrYellow;       // VWAP Line Color
input int    VWAPWidth = 2;               // VWAP Line Width
input color  Band1Color = clrDodgerBlue;  // Band 1 Color
input color  Band2Color = clrOrange;      // Band 2 Color
input color  Band3Color = clrRed;         // Band 3 Color
input int    BandWidth = 1;               // Band Line Width
input bool   ShowBands = true;            // Show Standard Deviation Bands
input bool   ShowDebugInfo = false;       // Show Debug Info in Comments

//--- Indicator Buffers
double VWAPBuffer[];
double UpperBand1Buffer[];
double LowerBand1Buffer[];
double UpperBand2Buffer[];
double LowerBand2Buffer[];
double UpperBand3Buffer[];
double LowerBand3Buffer[];

//--- Global Variables
double cumulativePriceVolume = 0.0;
double cumulativeVolume = 0.0;
datetime sessionStartTime = 0;
double stdLevels[3] = {1.0, 1.5, 2.0};  // Default bands
int numBands = 3;
double priceArray[];
double volumeArray[];
int arraySize = 0;

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Parse standard deviation bands
   string bands[];
   int count = StringSplit(StdBands, ',', bands);
   if(count > 0 && count <= 3)
   {
      numBands = count;
      for(int i = 0; i < count; i++)
      {
         stdLevels[i] = (double)StringToDouble(bands[i]);
      }
   }
   
   // Set indicator buffers
   SetIndexBuffer(0, VWAPBuffer, INDICATOR_DATA);
   SetIndexBuffer(1, UpperBand1Buffer, INDICATOR_DATA);
   SetIndexBuffer(2, LowerBand1Buffer, INDICATOR_DATA);
   SetIndexBuffer(3, UpperBand2Buffer, INDICATOR_DATA);
   SetIndexBuffer(4, LowerBand2Buffer, INDICATOR_DATA);
   SetIndexBuffer(5, UpperBand3Buffer, INDICATOR_DATA);
   SetIndexBuffer(6, LowerBand3Buffer, INDICATOR_DATA);
   
   // Set plot properties - VWAP line
   PlotIndexSetInteger(0, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, VWAPColor);
   PlotIndexSetInteger(0, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(0, PLOT_LINE_WIDTH, VWAPWidth);
   PlotIndexSetString(0, PLOT_LABEL, "VWAP");
   
   // Set plot properties - Band 1
   PlotIndexSetInteger(1, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(1, PLOT_LINE_COLOR, Band1Color);
   PlotIndexSetInteger(1, PLOT_LINE_STYLE, STYLE_DOT);
   PlotIndexSetInteger(1, PLOT_LINE_WIDTH, BandWidth);
   PlotIndexSetString(1, PLOT_LABEL, "Upper Band 1");
   
   PlotIndexSetInteger(2, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(2, PLOT_LINE_COLOR, Band1Color);
   PlotIndexSetInteger(2, PLOT_LINE_STYLE, STYLE_DOT);
   PlotIndexSetInteger(2, PLOT_LINE_WIDTH, BandWidth);
   PlotIndexSetString(2, PLOT_LABEL, "Lower Band 1");
   
   // Set plot properties - Band 2
   PlotIndexSetInteger(3, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(3, PLOT_LINE_COLOR, Band2Color);
   PlotIndexSetInteger(3, PLOT_LINE_STYLE, STYLE_DOT);
   PlotIndexSetInteger(3, PLOT_LINE_WIDTH, BandWidth);
   PlotIndexSetString(3, PLOT_LABEL, "Upper Band 2");
   
   PlotIndexSetInteger(4, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(4, PLOT_LINE_COLOR, Band2Color);
   PlotIndexSetInteger(4, PLOT_LINE_STYLE, STYLE_DOT);
   PlotIndexSetInteger(4, PLOT_LINE_WIDTH, BandWidth);
   PlotIndexSetString(4, PLOT_LABEL, "Lower Band 2");
   
   // Set plot properties - Band 3
   PlotIndexSetInteger(5, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(5, PLOT_LINE_COLOR, Band3Color);
   PlotIndexSetInteger(5, PLOT_LINE_STYLE, STYLE_DOT);
   PlotIndexSetInteger(5, PLOT_LINE_WIDTH, BandWidth);
   PlotIndexSetString(5, PLOT_LABEL, "Upper Band 3");
   
   PlotIndexSetInteger(6, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(6, PLOT_LINE_COLOR, Band3Color);
   PlotIndexSetInteger(6, PLOT_LINE_STYLE, STYLE_DOT);
   PlotIndexSetInteger(6, PLOT_LINE_WIDTH, BandWidth);
   PlotIndexSetString(6, PLOT_LABEL, "Lower Band 3");
   
   // Set empty values
   ArraySetAsSeries(VWAPBuffer, true);
   ArraySetAsSeries(UpperBand1Buffer, true);
   ArraySetAsSeries(LowerBand1Buffer, true);
   ArraySetAsSeries(UpperBand2Buffer, true);
   ArraySetAsSeries(LowerBand2Buffer, true);
   ArraySetAsSeries(UpperBand3Buffer, true);
   ArraySetAsSeries(LowerBand3Buffer, true);
   
   // Initialize arrays
   ArrayInitialize(VWAPBuffer, EMPTY_VALUE);
   ArrayInitialize(UpperBand1Buffer, EMPTY_VALUE);
   ArrayInitialize(LowerBand1Buffer, EMPTY_VALUE);
   ArrayInitialize(UpperBand2Buffer, EMPTY_VALUE);
   ArrayInitialize(LowerBand2Buffer, EMPTY_VALUE);
   ArrayInitialize(UpperBand3Buffer, EMPTY_VALUE);
   ArrayInitialize(LowerBand3Buffer, EMPTY_VALUE);
   
   // Initialize price and volume arrays
   ArrayResize(priceArray, 10000);
   ArrayResize(volumeArray, 10000);
   arraySize = 0;
   
   IndicatorSetString(INDICATOR_SHORTNAME, "VWAP (" + SessionType + " Session)");
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Cleanup
   ArrayFree(priceArray);
   ArrayFree(volumeArray);
}

//+------------------------------------------------------------------+
//| Get session start time for current bar                           |
//+------------------------------------------------------------------+
datetime GetSessionStartTime(datetime currentTime)
{
   if(SessionType == "All")
   {
      return currentTime;  // Continuous, no reset
   }
   
   MqlDateTime dt;
   TimeToStruct(currentTime, dt);
   
   int sessionHour = 0;
   int sessionMinute = 0;
   
   if(SessionType == "NY")
   {
      sessionHour = 13;  // 8:00 AM ET = 13:00 UTC
      sessionMinute = 0;
   }
   else if(SessionType == "London")
   {
      sessionHour = 8;   // 8:00 AM GMT = 8:00 UTC
      sessionMinute = 0;
   }
   else if(SessionType == "Asia")
   {
      sessionHour = 0;   // 00:00 JST = 0:00 UTC (approximate)
      sessionMinute = 0;
   }
   
   // Create session start time for today
   MqlDateTime sessionDt;
   sessionDt.year = dt.year;
   sessionDt.mon = dt.mon;
   sessionDt.day = dt.day;
   sessionDt.hour = sessionHour;
   sessionDt.min = sessionMinute;
   sessionDt.sec = 0;
   sessionDt.day_of_week = dt.day_of_week;
   sessionDt.day_of_year = dt.day_of_year;
   
   datetime sessionStart = StructToTime(sessionDt);
   
   // If current time is before session start today, use yesterday's session
   if(currentTime < sessionStart)
   {
      sessionStart = sessionStart - PeriodSeconds(PERIOD_D1);
   }
   
   return sessionStart;
}

//+------------------------------------------------------------------+
//| Check if session should reset                                    |
//+------------------------------------------------------------------+
bool ShouldResetSession(datetime currentTime)
{
   if(SessionType == "All")
      return false;
   
   if(sessionStartTime == 0)
      return true;
   
   datetime newSessionStart = GetSessionStartTime(currentTime);
   return newSessionStart > sessionStartTime;
}

//+------------------------------------------------------------------+
//| Reset VWAP calculation for new session                           |
//+------------------------------------------------------------------+
void ResetSession(datetime newSessionStart)
{
   cumulativePriceVolume = 0.0;
   cumulativeVolume = 0.0;
   sessionStartTime = newSessionStart;
   arraySize = 0;
   ArrayResize(priceArray, 10000);
   ArrayResize(volumeArray, 10000);
}

//+------------------------------------------------------------------+
//| Get price for VWAP calculation                                   |
//+------------------------------------------------------------------+
double GetPrice(int index, const double &open[], const double &high[], 
                const double &low[], const double &close[])
{
   if(UseTypicalPrice)
   {
      return (high[index] + low[index] + close[index]) / 3.0;
   }
   else
   {
      return close[index];
   }
}

//+------------------------------------------------------------------+
//| Calculate standard deviation                                     |
//+------------------------------------------------------------------+
double CalculateStdDev(double vwap)
{
   if(arraySize < 2)
      return 0.0;
   
   double sumSquaredDeviations = 0.0;
   for(int i = 0; i < arraySize; i++)
   {
      double deviation = priceArray[i] - vwap;
      sumSquaredDeviations += deviation * deviation;
   }
   
   double variance = sumSquaredDeviations / arraySize;
   return MathSqrt(variance);
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
   if(rates_total < 2)
      return(0);
   
   // Set arrays as series
   ArraySetAsSeries(time, true);
   ArraySetAsSeries(open, true);
   ArraySetAsSeries(high, true);
   ArraySetAsSeries(low, true);
   ArraySetAsSeries(close, true);
   ArraySetAsSeries(tick_volume, true);
   ArraySetAsSeries(volume, true);
   
   // Determine calculation range
   int limit = rates_total - prev_calculated;
   if(prev_calculated == 0)
   {
      limit = rates_total;
      // Reset on first calculation
      cumulativePriceVolume = 0.0;
      cumulativeVolume = 0.0;
      sessionStartTime = 0;
      arraySize = 0;
   }
   else
   {
      limit++;
   }
   
   // Process bars from oldest to newest
   for(int i = limit - 1; i >= 0; i--)
   {
      datetime barTime = time[i];
      
      // Check if session should reset
      if(ShouldResetSession(barTime))
      {
         datetime newSessionStart = GetSessionStartTime(barTime);
         ResetSession(newSessionStart);
      }
      
      // Get price and volume
      double price = GetPrice(i, open, high, low, close);
      double vol = (double)tick_volume[i];
      if(vol <= 0)
         vol = (double)volume[i];
      if(vol <= 0)
         vol = 1.0;  // Minimum volume
      
      // Update cumulative values
      cumulativePriceVolume += price * vol;
      cumulativeVolume += vol;
      
      // Calculate VWAP
      double vwap = 0.0;
      if(cumulativeVolume > 0)
      {
         vwap = cumulativePriceVolume / cumulativeVolume;
         VWAPBuffer[i] = vwap;
         
         // Store price and volume for STD calculation
         if(arraySize < 10000)
         {
            priceArray[arraySize] = price;
            volumeArray[arraySize] = vol;
            arraySize++;
         }
         
         // Calculate standard deviation bands
         if(ShowBands && arraySize >= 2)
         {
            double std = CalculateStdDev(vwap);
            
            // Band 1
            if(numBands >= 1)
            {
               UpperBand1Buffer[i] = vwap + (stdLevels[0] * std);
               LowerBand1Buffer[i] = vwap - (stdLevels[0] * std);
            }
            else
            {
               UpperBand1Buffer[i] = EMPTY_VALUE;
               LowerBand1Buffer[i] = EMPTY_VALUE;
            }
            
            // Band 2
            if(numBands >= 2)
            {
               UpperBand2Buffer[i] = vwap + (stdLevels[1] * std);
               LowerBand2Buffer[i] = vwap - (stdLevels[1] * std);
            }
            else
            {
               UpperBand2Buffer[i] = EMPTY_VALUE;
               LowerBand2Buffer[i] = EMPTY_VALUE;
            }
            
            // Band 3
            if(numBands >= 3)
            {
               UpperBand3Buffer[i] = vwap + (stdLevels[2] * std);
               LowerBand3Buffer[i] = vwap - (stdLevels[2] * std);
            }
            else
            {
               UpperBand3Buffer[i] = EMPTY_VALUE;
               LowerBand3Buffer[i] = EMPTY_VALUE;
            }
         }
         else
         {
            // Not enough data for bands
            UpperBand1Buffer[i] = EMPTY_VALUE;
            LowerBand1Buffer[i] = EMPTY_VALUE;
            UpperBand2Buffer[i] = EMPTY_VALUE;
            LowerBand2Buffer[i] = EMPTY_VALUE;
            UpperBand3Buffer[i] = EMPTY_VALUE;
            LowerBand3Buffer[i] = EMPTY_VALUE;
         }
      }
      else
      {
         VWAPBuffer[i] = EMPTY_VALUE;
         UpperBand1Buffer[i] = EMPTY_VALUE;
         LowerBand1Buffer[i] = EMPTY_VALUE;
         UpperBand2Buffer[i] = EMPTY_VALUE;
         LowerBand2Buffer[i] = EMPTY_VALUE;
         UpperBand3Buffer[i] = EMPTY_VALUE;
         LowerBand3Buffer[i] = EMPTY_VALUE;
      }
   }
   
   // Debug info
   if(ShowDebugInfo)
   {
      string symbolName = _Symbol;
      int digits = (int)SymbolInfoInteger(symbolName, SYMBOL_DIGITS);
      string sessionInfo = StringFormat("Session: %s | VWAP: %.*f | Volume: %.0f", 
                                       SessionType,
                                       digits,
                                       VWAPBuffer[0],
                                       cumulativeVolume);
      Comment(sessionInfo);
   }
   
   return(rates_total);
}

//+------------------------------------------------------------------+
