//+------------------------------------------------------------------+
//|                                          SMA_Indicator.mq5      |
//|                        Simple Moving Average (SMA)                |
//|                                                                  |
//| This indicator plots Simple Moving Average:                      |
//| - Configurable period                                           |
//| - Customizable color and line width                             |
//| - Calculates SMA using close prices                              |
//+------------------------------------------------------------------+
#property copyright "SMA Indicator for Visual Monitoring"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 1
#property indicator_plots   1

//--- Input Parameters
input int    SMAPeriod = 14;           // SMA Period
input color  SMAColor = clrYellow;     // SMA Line Color
input int    SMAWidth = 2;             // SMA Line Width
input int    SMAStyle = 0;             // Line Style: 0=Solid, 1=Dash, 2=Dot, 3=DashDot, 4=DashDotDot
input bool   ShowDebugInfo = false;    // Show Debug Info in Comments

//--- Indicator Buffers
double SMABuffer[];

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Validate period
   if(SMAPeriod < 1)
   {
      Print("SMA Indicator: Invalid period. Must be >= 1. Using default 14.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   
   // Validate line style
   if(SMAStyle < 0 || SMAStyle > 4)
   {
      Print("SMA Indicator: Invalid line style. Must be 0-4. Using default 0 (Solid).");
   }
   
   // Set indicator buffer
   SetIndexBuffer(0, SMABuffer, INDICATOR_DATA);
   
   // Set plot properties
   PlotIndexSetInteger(0, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, SMAColor);
   PlotIndexSetInteger(0, PLOT_LINE_STYLE, SMAStyle);
   PlotIndexSetInteger(0, PLOT_LINE_WIDTH, SMAWidth);
   PlotIndexSetString(0, PLOT_LABEL, "SMA(" + IntegerToString(SMAPeriod) + ")");
   
   // Set empty values
   ArraySetAsSeries(SMABuffer, true);
   ArrayInitialize(SMABuffer, EMPTY_VALUE);
   
   IndicatorSetString(INDICATOR_SHORTNAME, "SMA(" + IntegerToString(SMAPeriod) + ")");
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
//| Custom indicator iteration function                            |
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
   if(rates_total < SMAPeriod)
      return(0);
   
   // Set arrays as series
   ArraySetAsSeries(close, true);
   ArraySetAsSeries(SMABuffer, true);
   
   // Determine calculation range
   int limit = rates_total - prev_calculated;
   if(prev_calculated == 0)
   {
      limit = rates_total - SMAPeriod;
   }
   else
   {
      limit++;
   }
   
   // Calculate SMA
   for(int i = limit - 1; i >= 0; i--)
   {
      if(i + SMAPeriod - 1 >= rates_total)
         continue;
      
      // Calculate sum of closes for the period
      double sum = 0.0;
      for(int j = 0; j < SMAPeriod; j++)
      {
         sum += close[i + j];
      }
      
      // Calculate SMA
      SMABuffer[i] = sum / SMAPeriod;
   }
   
   // Debug info
   if(ShowDebugInfo)
   {
      string symbolName = _Symbol;
      int digits = (int)SymbolInfoInteger(symbolName, SYMBOL_DIGITS);
      string debugInfo = StringFormat("SMA(%d): %.*f | Period: %d", 
                                      SMAPeriod,
                                      digits,
                                      SMABuffer[0],
                                      SMAPeriod);
      Comment(debugInfo);
   }
   
   return(rates_total);
}

//+------------------------------------------------------------------+
