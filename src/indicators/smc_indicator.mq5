//+------------------------------------------------------------------+
//|                                          SMC_Indicator.mq5       |
//|                        Smart Money Concepts (SMC) Indicator       |
//|                                                                  |
//| This indicator plots SMC elements on MT5 charts:                |
//| - Pivot Highs and Lows (fractal pivots)                         |
//| - BOS (Break of Structure) events                               |
//| - CHoCH (Change of Character) events                            |
//| - Current Market Bias (BULLISH/BEARISH)                         |
//| - Structure Levels (last pivot high/low)                        |
//+------------------------------------------------------------------+
#property copyright "SMC Indicator for Visual Monitoring"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 6
#property indicator_plots   6

//--- Input Parameters
input int    PivotLeft = 2;           // Pivot Left Bars
input int    PivotRight = 2;          // Pivot Right Bars
input string EmitOn = "NONE";        // Emit Signals On: NONE, CHoCH, BOS, BOTH
input color  PivotHighColor = clrGold;      // Pivot High Color
input color  PivotLowColor = clrDodgerBlue; // Pivot Low Color
input color  BOSColor = clrLime;            // BOS Event Color
input color  CHoCHColor = clrRed;           // CHoCH Event Color
input int    PivotSize = 3;                 // Pivot Marker Size
input int    EventSize = 5;                 // Event Marker Size
input bool   ShowBiasLabel = true;          // Show Bias Label
input bool   ShowStructureLevels = true;    // Show Structure Levels
input bool   ShowDebugInfo = false;         // Show Debug Info in Comments
input bool   ShowUnconfirmedPivots = false; // Show Unconfirmed Pivots (for M1)

//--- Indicator Buffers
double PivotHighBuffer[];
double PivotLowBuffer[];
double BOSBuffer[];
double CHoCHBuffer[];
double StructureHighBuffer[];
double StructureLowBuffer[];

//--- Global Variables
int lastPivotHighIndex = -1;
int lastPivotLowIndex = -1;
double lastPivotHighPrice = 0.0;
double lastPivotLowPrice = 0.0;
string currentBias = "NONE";  // "BULLISH", "BEARISH", "NONE"
int biasLabelObj = 0;

// Arrays to store all pivot prices for drawing horizontal lines
double pivotHighPrices[];
int pivotHighIndices[];
double pivotLowPrices[];
int pivotLowIndices[];

// Arrays to store all event prices for drawing horizontal lines
double bosEventPrices[];
int bosEventIndices[];
double chochEventPrices[];
int chochEventIndices[];

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Set indicator buffers
   SetIndexBuffer(0, PivotHighBuffer, INDICATOR_DATA);
   SetIndexBuffer(1, PivotLowBuffer, INDICATOR_DATA);
   SetIndexBuffer(2, BOSBuffer, INDICATOR_DATA);
   SetIndexBuffer(3, CHoCHBuffer, INDICATOR_DATA);
   SetIndexBuffer(4, StructureHighBuffer, INDICATOR_DATA);
   SetIndexBuffer(5, StructureLowBuffer, INDICATOR_DATA);
   
   // Set plot properties - Horizontal lines for pivot levels
   PlotIndexSetInteger(0, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, PivotHighColor);
   PlotIndexSetInteger(0, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(0, PLOT_LINE_WIDTH, PivotSize);
   PlotIndexSetString(0, PLOT_LABEL, "Pivot Highs");
   
   PlotIndexSetInteger(1, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(1, PLOT_LINE_COLOR, PivotLowColor);
   PlotIndexSetInteger(1, PLOT_LINE_STYLE, STYLE_SOLID);
   PlotIndexSetInteger(1, PLOT_LINE_WIDTH, PivotSize);
   PlotIndexSetString(1, PLOT_LABEL, "Pivot Lows");
   
   PlotIndexSetInteger(2, PLOT_DRAW_TYPE, DRAW_ARROW);
   PlotIndexSetInteger(2, PLOT_ARROW, 108);  // Up arrow for BOS
   PlotIndexSetInteger(2, PLOT_LINE_COLOR, BOSColor);
   PlotIndexSetInteger(2, PLOT_LINE_WIDTH, EventSize);
   PlotIndexSetString(2, PLOT_LABEL, "BOS");
   
   PlotIndexSetInteger(3, PLOT_DRAW_TYPE, DRAW_ARROW);
   PlotIndexSetInteger(3, PLOT_ARROW, 108);  // Up arrow for CHoCH
   PlotIndexSetInteger(3, PLOT_LINE_COLOR, CHoCHColor);
   PlotIndexSetInteger(3, PLOT_LINE_WIDTH, EventSize);
   PlotIndexSetString(3, PLOT_LABEL, "CHoCH");
   
   PlotIndexSetInteger(4, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(4, PLOT_LINE_COLOR, clrYellow);
   PlotIndexSetInteger(4, PLOT_LINE_STYLE, STYLE_DOT);
   PlotIndexSetInteger(4, PLOT_LINE_WIDTH, 1);
   PlotIndexSetString(4, PLOT_LABEL, "Structure High");
   
   PlotIndexSetInteger(5, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(5, PLOT_LINE_COLOR, clrCyan);
   PlotIndexSetInteger(5, PLOT_LINE_STYLE, STYLE_DOT);
   PlotIndexSetInteger(5, PLOT_LINE_WIDTH, 1);
   PlotIndexSetString(5, PLOT_LABEL, "Structure Low");
   
   // Set empty values
   ArraySetAsSeries(PivotHighBuffer, true);
   ArraySetAsSeries(PivotLowBuffer, true);
   ArraySetAsSeries(BOSBuffer, true);
   ArraySetAsSeries(CHoCHBuffer, true);
   ArraySetAsSeries(StructureHighBuffer, true);
   ArraySetAsSeries(StructureLowBuffer, true);
   
   // Initialize arrays
   ArrayInitialize(PivotHighBuffer, EMPTY_VALUE);
   ArrayInitialize(PivotLowBuffer, EMPTY_VALUE);
   ArrayInitialize(BOSBuffer, EMPTY_VALUE);
   ArrayInitialize(CHoCHBuffer, EMPTY_VALUE);
   ArrayInitialize(StructureHighBuffer, EMPTY_VALUE);
   ArrayInitialize(StructureLowBuffer, EMPTY_VALUE);
   
   IndicatorSetString(INDICATOR_SHORTNAME, "SMC Indicator (Pivot: " + 
                      IntegerToString(PivotLeft) + "/" + IntegerToString(PivotRight) + ")");
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Custom indicator deinitialization function                       |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Remove bias label
   if(biasLabelObj != 0)
   {
      ObjectDelete(0, "SMC_Bias_Label");
      biasLabelObj = 0;
   }
}

//+------------------------------------------------------------------+
//| Check if index is a fractal pivot high                           |
//+------------------------------------------------------------------+
bool IsFractalPivotHigh(int index, int left, int right, int totalBars, const double &highArray[])
{
   if(index - left < 0 || index + right >= totalBars)
      return false;
   
   if(index < 0 || index >= totalBars)
      return false;
   
   double high = highArray[index];
   
   // Check left side
   for(int i = index - left; i < index; i++)
   {
      if(i < 0 || i >= totalBars)
         return false;
      if(high <= highArray[i])
         return false;
   }
   
   // Check right side
   for(int i = index + 1; i <= index + right; i++)
   {
      if(i < 0 || i >= totalBars)
         return false;
      if(high < highArray[i])
         return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Check if index is a fractal pivot low                            |
//+------------------------------------------------------------------+
bool IsFractalPivotLow(int index, int left, int right, int totalBars, const double &lowArray[])
{
   if(index - left < 0 || index + right >= totalBars)
      return false;
   
   if(index < 0 || index >= totalBars)
      return false;
   
   double low = lowArray[index];
   
   // Check left side
   for(int i = index - left; i < index; i++)
   {
      if(i < 0 || i >= totalBars)
         return false;
      if(low >= lowArray[i])
         return false;
   }
   
   // Check right side
   for(int i = index + 1; i <= index + right; i++)
   {
      if(i < 0 || i >= totalBars)
         return false;
      if(low > lowArray[i])
         return false;
   }
   
   return true;
}

//+------------------------------------------------------------------+
//| Update pivot tracking                                            |
//+------------------------------------------------------------------+
void UpdatePivots(int bars, const double &highArray[], const double &lowArray[])
{
   // highArray and lowArray are set as series (index 0 = newest bar)
   // We need to work with forward indexing (0 = oldest) for pivot detection
   // So we convert: forwardIndex = bars - 1 - seriesIndex
   
   int start = MathMax(PivotLeft, bars - PivotRight - 50);
   int end = bars - PivotRight;
   
   if(start < 0) start = 0;
   if(end > bars) end = bars;
   if(start >= end) return;
   
   // Create temporary forward-indexed arrays for pivot detection
   double highForward[];
   double lowForward[];
   ArrayResize(highForward, bars);
   ArrayResize(lowForward, bars);
   
   // Convert series arrays to forward arrays
   for(int i = 0; i < bars; i++)
   {
      int seriesIdx = bars - 1 - i;  // Convert forward index to series index
      highForward[i] = highArray[seriesIdx];
      lowForward[i] = lowArray[seriesIdx];
   }
   
   for(int i = start; i < end; i++)
   {
      if(IsFractalPivotHigh(i, PivotLeft, PivotRight, bars, highForward))
      {
         double high = highForward[i];
         if(lastPivotHighIndex == -1 || i > lastPivotHighIndex)
         {
            lastPivotHighIndex = i;
            lastPivotHighPrice = high;
         }
      }
      
      if(IsFractalPivotLow(i, PivotLeft, PivotRight, bars, lowForward))
      {
         double low = lowForward[i];
         if(lastPivotLowIndex == -1 || i > lastPivotLowIndex)
         {
            lastPivotLowIndex = i;
            lastPivotLowPrice = low;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Detect structure events (BOS/CHoCH)                              |
//+------------------------------------------------------------------+
string DetectStructure(int currentBar)
{
   if(lastPivotHighIndex == -1 && lastPivotLowIndex == -1)
      return "NONE";
   
   double close = iClose(_Symbol, _Period, currentBar);
   string event = "NONE";
   string direction = "NONE";
   
   // Check for pivot high break
   if(lastPivotHighPrice > 0 && close > lastPivotHighPrice)
   {
      if(currentBias == "BEARISH")
      {
         event = "CHoCH";
         direction = "UP";
         currentBias = "BULLISH";
      }
      else if(currentBias == "BULLISH")
      {
         event = "BOS";
         direction = "UP";
      }
      else
      {
         event = "BOS";
         direction = "UP";
         currentBias = "BULLISH";
      }
   }
   // Check for pivot low break
   else if(lastPivotLowPrice > 0 && close < lastPivotLowPrice)
   {
      if(currentBias == "BULLISH")
      {
         event = "CHoCH";
         direction = "DOWN";
         currentBias = "BEARISH";
      }
      else if(currentBias == "BEARISH")
      {
         event = "BOS";
         direction = "DOWN";
      }
      else
      {
         event = "BOS";
         direction = "DOWN";
         currentBias = "BEARISH";
      }
   }
   
   return event;
}

//+------------------------------------------------------------------+
//| Update bias label on chart                                        |
//+------------------------------------------------------------------+
void UpdateBiasLabel()
{
   if(!ShowBiasLabel)
      return;
   
   string labelName = "SMC_Bias_Label";
   string biasText = "Bias: " + currentBias;
   color biasColor = clrWhite;
   
   if(currentBias == "BULLISH")
      biasColor = clrLime;
   else if(currentBias == "BEARISH")
      biasColor = clrRed;
   
   if(ObjectFind(0, labelName) < 0)
   {
      ObjectCreate(0, labelName, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, labelName, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, labelName, OBJPROP_XDISTANCE, 10);
      ObjectSetInteger(0, labelName, OBJPROP_YDISTANCE, 30);
      ObjectSetInteger(0, labelName, OBJPROP_COLOR, biasColor);
      ObjectSetInteger(0, labelName, OBJPROP_FONTSIZE, 10);
      ObjectSetString(0, labelName, OBJPROP_FONT, "Arial Bold");
      biasLabelObj = 1;
   }
   
   ObjectSetString(0, labelName, OBJPROP_TEXT, biasText);
   ObjectSetInteger(0, labelName, OBJPROP_COLOR, biasColor);
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
   // Need enough bars for pivot detection
   int minBars = PivotLeft + PivotRight + 5;
   if(rates_total < minBars)
      return(0);
   
   // Set arrays as series
   ArraySetAsSeries(time, true);
   ArraySetAsSeries(open, true);
   ArraySetAsSeries(high, true);
   ArraySetAsSeries(low, true);
   ArraySetAsSeries(close, true);
   
   // Determine calculation range - process all bars that can have confirmed pivots
   int limit = rates_total - prev_calculated;
   if(prev_calculated == 0)
   {
      // First calculation - process all bars
      limit = rates_total - PivotRight;
   }
   else
   {
      // Update only new bars
      limit = rates_total - prev_calculated + 1;
      if(limit > rates_total - PivotRight)
         limit = rates_total - PivotRight;
   }
   
   // Reset pivot tracking on first run
   if(prev_calculated == 0)
   {
      lastPivotHighIndex = -1;
      lastPivotLowIndex = -1;
      lastPivotHighPrice = 0.0;
      lastPivotLowPrice = 0.0;
      currentBias = "NONE";
      
      // Initialize pivot arrays
      ArrayResize(pivotHighPrices, 0);
      ArrayResize(pivotHighIndices, 0);
      ArrayResize(pivotLowPrices, 0);
      ArrayResize(pivotLowIndices, 0);
      
      // Initialize event arrays
      ArrayResize(bosEventPrices, 0);
      ArrayResize(bosEventIndices, 0);
      ArrayResize(chochEventPrices, 0);
      ArrayResize(chochEventIndices, 0);
   }
   else
   {
      // On update, clear old pivot arrays to rebuild
      ArrayResize(pivotHighPrices, 0);
      ArrayResize(pivotHighIndices, 0);
      ArrayResize(pivotLowPrices, 0);
      ArrayResize(pivotLowIndices, 0);
      
      // Clear event arrays to rebuild
      ArrayResize(bosEventPrices, 0);
      ArrayResize(bosEventIndices, 0);
      ArrayResize(chochEventPrices, 0);
      ArrayResize(chochEventIndices, 0);
   }
   
   // Update pivots - scan for confirmed pivots
   // Note: high[] and low[] are already set as series, so index 0 = current bar
   // We need to work with forward indexing for pivot detection
   UpdatePivots(rates_total, high, low);
   
   // Get current timeframe period
   ENUM_TIMEFRAMES currentPeriod = _Period;
   bool isM1 = (currentPeriod == PERIOD_M1);
   
   // For M1, we might want to show unconfirmed pivots or use different settings
   int effectivePivotRight = PivotRight;
   if(isM1 && ShowUnconfirmedPivots)
   {
      effectivePivotRight = 0;  // Show pivots immediately on M1
   }
   
   // Process bars from oldest to newest
   for(int i = limit - 1; i >= 0; i--)
   {
      int barIndex = rates_total - 1 - i;
      
      // Reset buffers
      PivotHighBuffer[i] = EMPTY_VALUE;
      PivotLowBuffer[i] = EMPTY_VALUE;
      BOSBuffer[i] = EMPTY_VALUE;
      CHoCHBuffer[i] = EMPTY_VALUE;
      
      // Check for pivots - adjust range based on timeframe
      bool canShowPivot = false;
      if(ShowUnconfirmedPivots && isM1)
      {
         // M1: Show pivots even if not fully confirmed (for immediate feedback)
         canShowPivot = (barIndex >= PivotLeft && barIndex < rates_total - 1);
      }
      else
      {
         // Normal: Only show confirmed pivots
         canShowPivot = (barIndex >= PivotLeft && barIndex < rates_total - PivotRight);
      }
      
      if(canShowPivot)
      {
         // Create forward-indexed arrays for this check
         // high[] and low[] are series arrays (0 = newest), barIndex is forward (0 = oldest)
         // Convert barIndex to series index: seriesIdx = rates_total - 1 - barIndex
         
         // For pivot detection, we need forward indexing
         // Check if this bar is a pivot using forward-indexed comparison
         bool isPivotHigh = true;
         bool isPivotLow = true;
         int seriesIdx = rates_total - 1 - barIndex;
         
         if(seriesIdx >= 0 && seriesIdx < rates_total)
         {
            double currentHigh = high[seriesIdx];
            double currentLow = low[seriesIdx];
            
            // Check left side (newer bars in series array = lower indices)
            for(int j = 1; j <= PivotLeft; j++)
            {
               int leftIdx = seriesIdx + j;  // Newer bars
               if(leftIdx < rates_total)
               {
                  if(currentHigh <= high[leftIdx]) isPivotHigh = false;
                  if(currentLow >= low[leftIdx]) isPivotLow = false;
               }
               else
               {
                  isPivotHigh = false;
                  isPivotLow = false;
               }
            }
            
            // Check right side (older bars in series array = higher indices)
            for(int j = 1; j <= PivotRight; j++)
            {
               int rightIdx = seriesIdx - j;  // Older bars
               if(rightIdx >= 0)
               {
                  if(currentHigh < high[rightIdx]) isPivotHigh = false;
                  if(currentLow > low[rightIdx]) isPivotLow = false;
               }
               else
               {
                  isPivotHigh = false;
                  isPivotLow = false;
               }
            }
            
            if(isPivotHigh)
            {
               // Store pivot high for horizontal line drawing
               int pivotCount = ArraySize(pivotHighPrices);
               ArrayResize(pivotHighPrices, pivotCount + 1);
               ArrayResize(pivotHighIndices, pivotCount + 1);
               pivotHighPrices[pivotCount] = currentHigh;
               pivotHighIndices[pivotCount] = barIndex;
            }
            
            if(isPivotLow)
            {
               // Store pivot low for horizontal line drawing
               int pivotCount = ArraySize(pivotLowPrices);
               ArrayResize(pivotLowPrices, pivotCount + 1);
               ArrayResize(pivotLowIndices, pivotCount + 1);
               pivotLowPrices[pivotCount] = currentLow;
               pivotLowIndices[pivotCount] = barIndex;
            }
         }
      }
      
      // Draw horizontal lines based on EmitOn setting
      double currentHighPrice = EMPTY_VALUE;
      double currentLowPrice = EMPTY_VALUE;
      
      if(EmitOn == "NONE")
      {
         // Draw lines at pivot points (current behavior)
         
         // Draw horizontal lines for pivot highs with breaks
         int bestPivotHighIdx = -1;
         int bestPivotHighSeriesIdx = -1;
         
         // Find the most recent pivot high that is at or before this bar
         for(int p = 0; p < ArraySize(pivotHighPrices); p++)
         {
            int pivotBarIdx = pivotHighIndices[p];
            int pivotSeriesIdx = rates_total - 1 - pivotBarIdx;
            
            if(i <= pivotSeriesIdx)
            {
               if(bestPivotHighSeriesIdx == -1 || pivotSeriesIdx < bestPivotHighSeriesIdx)
               {
                  bestPivotHighIdx = p;
                  bestPivotHighSeriesIdx = pivotSeriesIdx;
               }
            }
         }
         
         // If we found a pivot, check if we should draw it
         if(bestPivotHighIdx >= 0)
         {
            // Find the next pivot high (newer than this one)
            int nextPivotSeriesIdx = -1;
            for(int p = 0; p < ArraySize(pivotHighPrices); p++)
            {
               if(p == bestPivotHighIdx) continue;
               int pivotBarIdx = pivotHighIndices[p];
               int pivotSeriesIdx = rates_total - 1 - pivotBarIdx;
               if(pivotSeriesIdx < bestPivotHighSeriesIdx)
               {
                  if(nextPivotSeriesIdx == -1 || pivotSeriesIdx > nextPivotSeriesIdx)
                  {
                     nextPivotSeriesIdx = pivotSeriesIdx;
                  }
               }
            }
            
            // Draw line from this pivot until the next pivot (or current bar)
            if(nextPivotSeriesIdx == -1)
            {
               currentHighPrice = pivotHighPrices[bestPivotHighIdx];
            }
            else
            {
               if(i > nextPivotSeriesIdx)
               {
                  currentHighPrice = pivotHighPrices[bestPivotHighIdx];
               }
               else if(i == bestPivotHighSeriesIdx)
               {
                  currentHighPrice = pivotHighPrices[bestPivotHighIdx];
               }
            }
         }
         
         // Draw horizontal lines for pivot lows with breaks
         int bestPivotLowIdx = -1;
         int bestPivotLowSeriesIdx = -1;
         
         // Find the most recent pivot low that is at or before this bar
         for(int p = 0; p < ArraySize(pivotLowPrices); p++)
         {
            int pivotBarIdx = pivotLowIndices[p];
            int pivotSeriesIdx = rates_total - 1 - pivotBarIdx;
            
            if(i <= pivotSeriesIdx)
            {
               if(bestPivotLowSeriesIdx == -1 || pivotSeriesIdx < bestPivotLowSeriesIdx)
               {
                  bestPivotLowIdx = p;
                  bestPivotLowSeriesIdx = pivotSeriesIdx;
               }
            }
         }
         
         // If we found a pivot, check if we should draw it
         if(bestPivotLowIdx >= 0)
         {
            // Find the next pivot low (newer than this one)
            int nextPivotSeriesIdx = -1;
            for(int p = 0; p < ArraySize(pivotLowPrices); p++)
            {
               if(p == bestPivotLowIdx) continue;
               int pivotBarIdx = pivotLowIndices[p];
               int pivotSeriesIdx = rates_total - 1 - pivotBarIdx;
               if(pivotSeriesIdx < bestPivotLowSeriesIdx)
               {
                  if(nextPivotSeriesIdx == -1 || pivotSeriesIdx > nextPivotSeriesIdx)
                  {
                     nextPivotSeriesIdx = pivotSeriesIdx;
                  }
               }
            }
            
            // Draw line from this pivot until the next pivot (or current bar)
            if(nextPivotSeriesIdx == -1)
            {
               currentLowPrice = pivotLowPrices[bestPivotLowIdx];
            }
            else
            {
               if(i > nextPivotSeriesIdx)
               {
                  currentLowPrice = pivotLowPrices[bestPivotLowIdx];
               }
               else if(i == bestPivotLowSeriesIdx)
               {
                  currentLowPrice = pivotLowPrices[bestPivotLowIdx];
               }
            }
         }
      }
      else
      {
         // Draw lines at event prices (BOS/CHoCH)
         
         // Draw CHoCH event lines (use PivotHighBuffer for CHoCH)
         if(EmitOn == "CHoCH" || EmitOn == "BOTH")
         {
            int bestCHoCHIdx = -1;
            int bestCHoCHSeriesIdx = -1;
            
            // Find the most recent CHoCH event that is at or before this bar
            for(int p = 0; p < ArraySize(chochEventPrices); p++)
            {
               int eventBarIdx = chochEventIndices[p];
               int eventSeriesIdx = rates_total - 1 - eventBarIdx;
               
               if(i <= eventSeriesIdx)
               {
                  if(bestCHoCHSeriesIdx == -1 || eventSeriesIdx < bestCHoCHSeriesIdx)
                  {
                     bestCHoCHIdx = p;
                     bestCHoCHSeriesIdx = eventSeriesIdx;
                  }
               }
            }
            
            // If we found an event, check if we should draw it
            if(bestCHoCHIdx >= 0)
            {
               // Find the next CHoCH event (newer than this one)
               int nextEventSeriesIdx = -1;
               for(int p = 0; p < ArraySize(chochEventPrices); p++)
               {
                  if(p == bestCHoCHIdx) continue;
                  int eventBarIdx = chochEventIndices[p];
                  int eventSeriesIdx = rates_total - 1 - eventBarIdx;
                  if(eventSeriesIdx < bestCHoCHSeriesIdx)
                  {
                     if(nextEventSeriesIdx == -1 || eventSeriesIdx > nextEventSeriesIdx)
                     {
                        nextEventSeriesIdx = eventSeriesIdx;
                     }
                  }
               }
               
               // Draw line from this event until the next event (or current bar)
               if(nextEventSeriesIdx == -1)
               {
                  currentHighPrice = chochEventPrices[bestCHoCHIdx];
               }
               else
               {
                  if(i > nextEventSeriesIdx)
                  {
                     currentHighPrice = chochEventPrices[bestCHoCHIdx];
                  }
                  else if(i == bestCHoCHSeriesIdx)
                  {
                     currentHighPrice = chochEventPrices[bestCHoCHIdx];
                  }
               }
            }
         }
         
         // Draw BOS event lines (use PivotLowBuffer for BOS)
         if(EmitOn == "BOS" || EmitOn == "BOTH")
         {
            int bestBOSIdx = -1;
            int bestBOSSeriesIdx = -1;
            
            // Find the most recent BOS event that is at or before this bar
            for(int p = 0; p < ArraySize(bosEventPrices); p++)
            {
               int eventBarIdx = bosEventIndices[p];
               int eventSeriesIdx = rates_total - 1 - eventBarIdx;
               
               if(i <= eventSeriesIdx)
               {
                  if(bestBOSSeriesIdx == -1 || eventSeriesIdx < bestBOSSeriesIdx)
                  {
                     bestBOSIdx = p;
                     bestBOSSeriesIdx = eventSeriesIdx;
                  }
               }
            }
            
            // If we found an event, check if we should draw it
            if(bestBOSIdx >= 0)
            {
               // Find the next BOS event (newer than this one)
               int nextEventSeriesIdx = -1;
               for(int p = 0; p < ArraySize(bosEventPrices); p++)
               {
                  if(p == bestBOSIdx) continue;
                  int eventBarIdx = bosEventIndices[p];
                  int eventSeriesIdx = rates_total - 1 - eventBarIdx;
                  if(eventSeriesIdx < bestBOSSeriesIdx)
                  {
                     if(nextEventSeriesIdx == -1 || eventSeriesIdx > nextEventSeriesIdx)
                     {
                        nextEventSeriesIdx = eventSeriesIdx;
                     }
                  }
               }
               
               // Draw line from this event until the next event (or current bar)
               if(nextEventSeriesIdx == -1)
               {
                  currentLowPrice = bosEventPrices[bestBOSIdx];
               }
               else
               {
                  if(i > nextEventSeriesIdx)
                  {
                     currentLowPrice = bosEventPrices[bestBOSIdx];
                  }
                  else if(i == bestBOSSeriesIdx)
                  {
                     currentLowPrice = bosEventPrices[bestBOSIdx];
                  }
               }
            }
         }
      }
      
      PivotHighBuffer[i] = currentHighPrice;
      PivotLowBuffer[i] = currentLowPrice;
      
      // Detect structure events for all bars (to track historical events for line drawing)
      // Events are detected in chronological order (oldest to newest) to maintain correct bias
      // For each bar, find the most recent pivot that occurred BEFORE this bar
      if(barIndex > 0)
      {
         double currentClose = close[i];
         string event = "NONE";
         
         // Find the most recent pivot high that occurred before this bar
         double relevantPivotHigh = 0.0;
         int relevantPivotHighIdx = -1;
         for(int p = 0; p < ArraySize(pivotHighPrices); p++)
         {
            if(pivotHighIndices[p] < barIndex)  // Pivot occurred before current bar
            {
               if(relevantPivotHighIdx == -1 || pivotHighIndices[p] > relevantPivotHighIdx)
               {
                  relevantPivotHigh = pivotHighPrices[p];
                  relevantPivotHighIdx = pivotHighIndices[p];
               }
            }
         }
         
         // Find the most recent pivot low that occurred before this bar
         double relevantPivotLow = 0.0;
         int relevantPivotLowIdx = -1;
         for(int p = 0; p < ArraySize(pivotLowPrices); p++)
         {
            if(pivotLowIndices[p] < barIndex)  // Pivot occurred before current bar
            {
               if(relevantPivotLowIdx == -1 || pivotLowIndices[p] > relevantPivotLowIdx)
               {
                  relevantPivotLow = pivotLowPrices[p];
                  relevantPivotLowIdx = pivotLowIndices[p];
               }
            }
         }
         
         // Check if current bar breaks the relevant pivot high
         if(relevantPivotHigh > 0 && currentClose > relevantPivotHigh)
         {
            if(currentBias == "BEARISH")
            {
               event = "CHoCH";
               currentBias = "BULLISH";
            }
            else if(currentBias == "BULLISH")
            {
               event = "BOS";
            }
            else
            {
               event = "BOS";
               currentBias = "BULLISH";
            }
         }
         // Check if current bar breaks the relevant pivot low
         else if(relevantPivotLow > 0 && currentClose < relevantPivotLow)
         {
            if(currentBias == "BULLISH")
            {
               event = "CHoCH";
               currentBias = "BEARISH";
            }
            else if(currentBias == "BEARISH")
            {
               event = "BOS";
            }
            else
            {
               event = "BOS";
               currentBias = "BEARISH";
            }
         }
         
         // Store events in tracking arrays for line drawing
         if(event == "BOS")
         {
            int eventCount = ArraySize(bosEventPrices);
            ArrayResize(bosEventPrices, eventCount + 1);
            ArrayResize(bosEventIndices, eventCount + 1);
            bosEventPrices[eventCount] = currentClose;
            bosEventIndices[eventCount] = barIndex;
            
            // Also set buffer for visual markers (if EmitOn allows)
            if(EmitOn == "BOS" || EmitOn == "BOTH")
            {
               BOSBuffer[i] = currentClose;
            }
         }
         else if(event == "CHoCH")
         {
            // IMPORTANT: CHoCH price is the CLOSE price of the candle that broke the pivot
            // This is the confirmation level where the structure change was confirmed
            // NOT the pivot price itself, but the close price when the pivot was broken
            int eventCount = ArraySize(chochEventPrices);
            ArrayResize(chochEventPrices, eventCount + 1);
            ArrayResize(chochEventIndices, eventCount + 1);
            chochEventPrices[eventCount] = currentClose;  // Close price of candle that broke pivot
            chochEventIndices[eventCount] = barIndex;
            
            // Also set buffer for visual markers (if EmitOn allows)
            if(EmitOn == "CHoCH" || EmitOn == "BOTH")
            {
               CHoCHBuffer[i] = currentClose;
            }
         }
      }
      
      // Draw structure levels (horizontal lines from pivot point to current bar)
      if(ShowStructureLevels)
      {
         // Draw structure high level if we have a confirmed pivot high
         // Draw from the pivot point to the current bar
         if(lastPivotHighPrice > 0 && lastPivotHighIndex >= 0)
         {
            // Convert pivot index to series index
            int pivotSeriesIndex = rates_total - 1 - lastPivotHighIndex;
            // Draw from pivot to current (i = 0 is current bar)
            if(i <= pivotSeriesIndex)
            {
               StructureHighBuffer[i] = lastPivotHighPrice;
            }
            else
            {
               StructureHighBuffer[i] = EMPTY_VALUE;
            }
         }
         else
         {
            StructureHighBuffer[i] = EMPTY_VALUE;
         }
         
         // Draw structure low level if we have a confirmed pivot low
         if(lastPivotLowPrice > 0 && lastPivotLowIndex >= 0)
         {
            // Convert pivot index to series index
            int pivotSeriesIndex = rates_total - 1 - lastPivotLowIndex;
            // Draw from pivot to current (i = 0 is current bar)
            if(i <= pivotSeriesIndex)
            {
               StructureLowBuffer[i] = lastPivotLowPrice;
            }
            else
            {
               StructureLowBuffer[i] = EMPTY_VALUE;
            }
         }
         else
         {
            StructureLowBuffer[i] = EMPTY_VALUE;
         }
      }
      else
      {
         StructureHighBuffer[i] = EMPTY_VALUE;
         StructureLowBuffer[i] = EMPTY_VALUE;
      }
   }
   
   // Update bias label
   UpdateBiasLabel();
   
   // Debug info
   if(ShowDebugInfo)
   {
      string symbolName = _Symbol;
      int digits = (int)SymbolInfoInteger(symbolName, SYMBOL_DIGITS);
      string periodName = EnumToString(currentPeriod);
      string debugText = StringFormat("Symbol: %s | TF: %s | Bars: %d | PivotH: %.*f | PivotL: %.*f | Bias: %s | Unconfirmed: %s", 
                                      symbolName,
                                      periodName,
                                      rates_total, 
                                      digits,
                                      lastPivotHighPrice, 
                                      digits,
                                      lastPivotLowPrice, 
                                      currentBias,
                                      (ShowUnconfirmedPivots && isM1) ? "ON" : "OFF");
      Comment(debugText);
   }
   
   return(rates_total);
}

//+------------------------------------------------------------------+
