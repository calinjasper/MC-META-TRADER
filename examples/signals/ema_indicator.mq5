//+------------------------------------------------------------------+
//|                                          EMA_Indicator.mq5       |
//|                        Exponential Moving Average (EMA)          |
//|                                                                  |
//| This indicator plots 4 Exponential Moving Averages:            |
//| - EMA 1, EMA 2, EMA 3, EMA 4 with configurable periods         |
//| - Customizable colors and line width                            |
//| - Calculates EMA using close prices                              |
//+------------------------------------------------------------------+
#property copyright "EMA Indicator for Visual Monitoring"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 4
#property indicator_plots   4

//--- Input Parameters
input int    EMA1Period = 20;          // EMA 1 Period
input int    EMA2Period = 50;          // EMA 2 Period
input int    EMA3Period = 100;         // EMA 3 Period
input int    EMA4Period = 200;         // EMA 4 Period
input color  EMA1Color = clrOrange;     // EMA 1 Color
input color  EMA2Color = clrDodgerBlue; // EMA 2 Color
input color  EMA3Color = clrMediumPurple; // EMA 3 Color
input color  EMA4Color = clrLimeGreen;  // EMA 4 Color
input int    EMAWidth = 2;             // EMA Line Width
input int    EMAStyle = 0;             // Line Style: 0=Solid, 1=Dash, 2=Dot, 3=DashDot, 4=DashDotDot
input bool   ShowDebugInfo = false;    // Show Debug Info in Comments

//--- Indicator Buffers
double EMA1Buffer[];
double EMA2Buffer[];
double EMA3Buffer[];
double EMA4Buffer[];

//--- Global Variables
double multiplier1 = 0.0;
double multiplier2 = 0.0;
double multiplier3 = 0.0;
double multiplier4 = 0.0;

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Validate periods
   if(EMA1Period < 1 || EMA2Period < 1 || EMA3Period < 1 || EMA4Period < 1)
   {
      Print("EMA Indicator: Invalid period. All periods must be >= 1.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   
   // Validate line style
   if(EMAStyle < 0 || EMAStyle > 4)
   {
      Print("EMA Indicator: Invalid line style. Must be 0-4. Using default 0 (Solid).");
   }
   
   // Calculate multipliers: 2.0 / (period + 1.0)
   multiplier1 = 2.0 / (EMA1Period + 1.0);
   multiplier2 = 2.0 / (EMA2Period + 1.0);
   multiplier3 = 2.0 / (EMA3Period + 1.0);
   multiplier4 = 2.0 / (EMA4Period + 1.0);
   
   // Set indicator buffers
   SetIndexBuffer(0, EMA1Buffer, INDICATOR_DATA);
   SetIndexBuffer(1, EMA2Buffer, INDICATOR_DATA);
   SetIndexBuffer(2, EMA3Buffer, INDICATOR_DATA);
   SetIndexBuffer(3, EMA4Buffer, INDICATOR_DATA);
   
   // Set plot properties - EMA 1
   PlotIndexSetInteger(0, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, EMA1Color);
   PlotIndexSetInteger(0, PLOT_LINE_STYLE, EMAStyle);
   PlotIndexSetInteger(0, PLOT_LINE_WIDTH, EMAWidth);
   PlotIndexSetString(0, PLOT_LABEL, "EMA(" + IntegerToString(EMA1Period) + ")");
   
   // Set plot properties - EMA 2
   PlotIndexSetInteger(1, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(1, PLOT_LINE_COLOR, EMA2Color);
   PlotIndexSetInteger(1, PLOT_LINE_STYLE, EMAStyle);
   PlotIndexSetInteger(1, PLOT_LINE_WIDTH, EMAWidth);
   PlotIndexSetString(1, PLOT_LABEL, "EMA(" + IntegerToString(EMA2Period) + ")");
   
   // Set plot properties - EMA 3
   PlotIndexSetInteger(2, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(2, PLOT_LINE_COLOR, EMA3Color);
   PlotIndexSetInteger(2, PLOT_LINE_STYLE, EMAStyle);
   PlotIndexSetInteger(2, PLOT_LINE_WIDTH, EMAWidth);
   PlotIndexSetString(2, PLOT_LABEL, "EMA(" + IntegerToString(EMA3Period) + ")");
   
   // Set plot properties - EMA 4
   PlotIndexSetInteger(3, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(3, PLOT_LINE_COLOR, EMA4Color);
   PlotIndexSetInteger(3, PLOT_LINE_STYLE, EMAStyle);
   PlotIndexSetInteger(3, PLOT_LINE_WIDTH, EMAWidth);
   PlotIndexSetString(3, PLOT_LABEL, "EMA(" + IntegerToString(EMA4Period) + ")");
   
   // Set empty values
   ArraySetAsSeries(EMA1Buffer, true);
   ArraySetAsSeries(EMA2Buffer, true);
   ArraySetAsSeries(EMA3Buffer, true);
   ArraySetAsSeries(EMA4Buffer, true);
   ArrayInitialize(EMA1Buffer, EMPTY_VALUE);
   ArrayInitialize(EMA2Buffer, EMPTY_VALUE);
   ArrayInitialize(EMA3Buffer, EMPTY_VALUE);
   ArrayInitialize(EMA4Buffer, EMPTY_VALUE);
   
   IndicatorSetString(INDICATOR_SHORTNAME, "EMA(" + IntegerToString(EMA1Period) + "," + 
                     IntegerToString(EMA2Period) + "," + IntegerToString(EMA3Period) + "," + 
                     IntegerToString(EMA4Period) + ")");
   IndicatorSetInteger(INDICATOR_DIGITS, _Digits);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Cleanup if needed
}

//+------------------------------------------------------------------+
//| Calculate EMA for a specific period                               |
//+------------------------------------------------------------------+
void CalculateEMA(double &buffer[], const double &close[], int period, double multiplier, int rates_total, int prev_calculated)
{
   if(rates_total < period)
      return;
   
   int limit = rates_total - prev_calculated;
   if(prev_calculated == 0)
   {
      limit = rates_total - period;
      
      // Initialize first EMA value with SMA (oldest bar in the period)
      double sum = 0.0;
      for(int j = 0; j < period; j++)
      {
         sum += close[rates_total - period + j];
      }
      buffer[rates_total - period] = sum / period;
      
      // Calculate EMA for remaining values (going forward in time, which is backwards in array index)
      for(int i = rates_total - period - 1; i >= 0; i--)
      {
         double prevEMA = buffer[i + 1];
         buffer[i] = (close[i] - prevEMA) * multiplier + prevEMA;
      }
   }
   else
   {
      limit++;
      
      // Calculate EMA for new bars only
      for(int i = limit - 1; i >= 0; i--)
      {
         if(i + 1 >= rates_total)
         {
            // This is the oldest bar we're calculating - need to check if we have enough history
            if(rates_total >= period)
            {
               double sum = 0.0;
               for(int j = 0; j < period; j++)
               {
                  sum += close[i + j];
               }
               buffer[i] = sum / period;
            }
         }
         else
         {
            // Use previous EMA value (which is at i+1 since we're going backwards)
            double prevEMA = buffer[i + 1];
            if(prevEMA != EMPTY_VALUE)
            {
               buffer[i] = (close[i] - prevEMA) * multiplier + prevEMA;
            }
            else
            {
               // Fallback: use SMA if previous EMA not available
               if(i + period <= rates_total)
               {
                  double sum = 0.0;
                  for(int j = 0; j < period; j++)
                  {
                     sum += close[i + j];
                  }
                  buffer[i] = sum / period;
               }
            }
         }
      }
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
   // Set arrays as series
   ArraySetAsSeries(close, true);
   ArraySetAsSeries(EMA1Buffer, true);
   ArraySetAsSeries(EMA2Buffer, true);
   ArraySetAsSeries(EMA3Buffer, true);
   ArraySetAsSeries(EMA4Buffer, true);
   
   // Calculate all 4 EMAs
   CalculateEMA(EMA1Buffer, close, EMA1Period, multiplier1, rates_total, prev_calculated);
   CalculateEMA(EMA2Buffer, close, EMA2Period, multiplier2, rates_total, prev_calculated);
   CalculateEMA(EMA3Buffer, close, EMA3Period, multiplier3, rates_total, prev_calculated);
   CalculateEMA(EMA4Buffer, close, EMA4Period, multiplier4, rates_total, prev_calculated);
   
   // Debug info
   if(ShowDebugInfo)
   {
      string symbolName = _Symbol;
      int digits = (int)SymbolInfoInteger(symbolName, SYMBOL_DIGITS);
      string debugInfo = StringFormat("EMA1(%d): %.*f | EMA2(%d): %.*f | EMA3(%d): %.*f | EMA4(%d): %.*f", 
                                      EMA1Period, digits, EMA1Buffer[0],
                                      EMA2Period, digits, EMA2Buffer[0],
                                      EMA3Period, digits, EMA3Buffer[0],
                                      EMA4Period, digits, EMA4Buffer[0]);
      Comment(debugInfo);
   }
   
   return(rates_total);
}

//+------------------------------------------------------------------+
