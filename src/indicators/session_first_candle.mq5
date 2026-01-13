//+------------------------------------------------------------------+
//|                                    Session_First_Candle.mq5      |
//|                        Session First Candle High/Low Indicator    |
//|                                                                  |
//| Plots High and Low of first candle of each trading session      |
//| as continuous lines until next session begins                   |
//+------------------------------------------------------------------+
#property copyright "Session First Candle Indicator"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots   2

//--- Input Parameters
input int    Session1StartHour = 0;        // Session 1 Start Hour (0-23)
input int    Session1EndHour = 9;          // Session 1 End Hour (0-23)
input int    Session2StartHour = 8;        // Session 2 Start Hour (-1 to disable)
input int    Session2EndHour = 17;        // Session 2 End Hour (0-23)
input int    Session3StartHour = 13;      // Session 3 Start Hour (-1 to disable)
input int    Session3EndHour = 22;        // Session 3 End Hour (0-23)
input color  HighLineColor = clrGreen;     // High Line Color
input color  LowLineColor = clrRed;       // Low Line Color
input int    LineWidth = 1;               // Line Width
input ENUM_LINE_STYLE LineStyle = STYLE_SOLID;  // Line Style

//--- Indicator Buffers
double SessionHighBuffer[];
double SessionLowBuffer[];

//--- Global Variables
int current_session = 0;      // Current session number (0, 1, 2, or 3)
double session_high = 0.0;    // High of current session's first candle
double session_low = 0.0;     // Low of current session's first candle
int last_session = 0;         // Previous session number for change detection
datetime last_session_time = 0;  // Time of last session change

//+------------------------------------------------------------------+
//| Custom indicator initialization function                         |
//+------------------------------------------------------------------+
int OnInit()
{
   // Validate session time inputs
   if(Session1StartHour < 0 || Session1StartHour > 23 || Session1EndHour < 0 || Session1EndHour > 23)
   {
      Print("Session First Candle: Invalid Session 1 times. Hours must be 0-23.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   
   if(Session2StartHour != -1)
   {
      if(Session2StartHour < 0 || Session2StartHour > 23 || Session2EndHour < 0 || Session2EndHour > 23)
      {
         Print("Session First Candle: Invalid Session 2 times. Hours must be 0-23.");
         return(INIT_PARAMETERS_INCORRECT);
      }
   }
   
   if(Session3StartHour != -1)
   {
      if(Session3StartHour < 0 || Session3StartHour > 23 || Session3EndHour < 0 || Session3EndHour > 23)
      {
         Print("Session First Candle: Invalid Session 3 times. Hours must be 0-23.");
         return(INIT_PARAMETERS_INCORRECT);
      }
   }
   
   // Set indicator buffers
   SetIndexBuffer(0, SessionHighBuffer, INDICATOR_DATA);
   SetIndexBuffer(1, SessionLowBuffer, INDICATOR_DATA);
   
   // Set plot properties - High Line
   PlotIndexSetInteger(0, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, HighLineColor);
   PlotIndexSetInteger(0, PLOT_LINE_STYLE, LineStyle);
   PlotIndexSetInteger(0, PLOT_LINE_WIDTH, LineWidth);
   PlotIndexSetString(0, PLOT_LABEL, "Session High");
   
   // Set plot properties - Low Line
   PlotIndexSetInteger(1, PLOT_DRAW_TYPE, DRAW_LINE);
   PlotIndexSetInteger(1, PLOT_LINE_COLOR, LowLineColor);
   PlotIndexSetInteger(1, PLOT_LINE_STYLE, LineStyle);
   PlotIndexSetInteger(1, PLOT_LINE_WIDTH, LineWidth);
   PlotIndexSetString(1, PLOT_LABEL, "Session Low");
   
   // Set empty values
   ArraySetAsSeries(SessionHighBuffer, true);
   ArraySetAsSeries(SessionLowBuffer, true);
   
   // Initialize buffers
   ArrayInitialize(SessionHighBuffer, EMPTY_VALUE);
   ArrayInitialize(SessionLowBuffer, EMPTY_VALUE);
   
   // Initialize tracking variables
   current_session = 0;
   session_high = 0.0;
   session_low = 0.0;
   last_session = 0;
   last_session_time = 0;
   
   IndicatorSetString(INDICATOR_SHORTNAME, "Session First Candle");
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
//| Get session number for a given hour                              |
//+------------------------------------------------------------------+
int GetSessionNumber(int hour)
{
   // Check Session 1
   if(Session1StartHour <= Session1EndHour)
   {
      // Normal session (doesn't cross midnight)
      if(hour >= Session1StartHour && hour < Session1EndHour)
         return 1;
   }
   else
   {
      // Session crosses midnight (e.g., 22:00-06:00)
      if(hour >= Session1StartHour || hour < Session1EndHour)
         return 1;
   }
   
   // Check Session 2 (if enabled)
   if(Session2StartHour >= 0)
   {
      if(Session2StartHour <= Session2EndHour)
      {
         // Normal session
         if(hour >= Session2StartHour && hour < Session2EndHour)
            return 2;
      }
      else
      {
         // Session crosses midnight
         if(hour >= Session2StartHour || hour < Session2EndHour)
            return 2;
      }
   }
   
   // Check Session 3 (if enabled)
   if(Session3StartHour >= 0)
   {
      if(Session3StartHour <= Session3EndHour)
      {
         // Normal session
         if(hour >= Session3StartHour && hour < Session3EndHour)
            return 3;
      }
      else
      {
         // Session crosses midnight
         if(hour >= Session3StartHour || hour < Session3EndHour)
            return 3;
      }
   }
   
   return 0; // No session
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
   if(rates_total < 1)
      return(0);
   
   // Set arrays as series
   ArraySetAsSeries(time, true);
   ArraySetAsSeries(high, true);
   ArraySetAsSeries(low, true);
   ArraySetAsSeries(SessionHighBuffer, true);
   ArraySetAsSeries(SessionLowBuffer, true);
   
   // Determine processing limit
   int limit = rates_total - prev_calculated;
   if(prev_calculated == 0)
   {
      // First calculation - process all bars
      limit = rates_total;
      // Reset tracking variables
      current_session = 0;
      session_high = 0.0;
      session_low = 0.0;
      last_session = 0;
      last_session_time = 0;
   }
   else
   {
      // Incremental update - process new bars only
      limit = MathMin(limit + 1, rates_total);
   }
   
   // Process bars from oldest to newest (going backwards in array since it's series)
   // Array is series: index 0 = most recent, higher index = older
   for(int i = limit - 1; i >= 0; i--)
   {
      // Get bar time and extract hour
      MqlDateTime dt;
      TimeToStruct(time[i], dt);
      int hour = dt.hour;
      
      // Determine which session this bar belongs to
      int bar_session = GetSessionNumber(hour);
      
      // Check if this is the first candle of a new session
      bool is_new_session = false;
      int prev_session = 0;
      
      // Get previous bar's session (next index in series array = previous in time)
      if(i + 1 < rates_total)
      {
         MqlDateTime prev_dt;
         TimeToStruct(time[i + 1], prev_dt);
         int prev_hour = prev_dt.hour;
         prev_session = GetSessionNumber(prev_hour);
         
         // Session changed if current bar's session differs from previous bar's session
         if(bar_session != prev_session && bar_session > 0)
         {
            is_new_session = true;
            session_high = high[i];
            session_low = low[i];
            current_session = bar_session;
         }
      }
      else
      {
         // First bar in history (oldest bar)
         if(bar_session > 0)
         {
            is_new_session = true;
            session_high = high[i];
            session_low = low[i];
            current_session = bar_session;
         }
      }
      
      // Plot values
      if(bar_session > 0)
      {
         if(is_new_session)
         {
            // New session - plot first candle's High/Low
            SessionHighBuffer[i] = session_high;
            SessionLowBuffer[i] = session_low;
         }
         else
         {
            // Same session - continue plotting the stored High/Low values
            // Copy from next bar (previous in time) if it has a value
            if(i + 1 < rates_total)
            {
               if(SessionHighBuffer[i + 1] != EMPTY_VALUE)
               {
                  SessionHighBuffer[i] = SessionHighBuffer[i + 1];
               }
               else if(session_high > 0.0)
               {
                  SessionHighBuffer[i] = session_high;
               }
               else
               {
                  SessionHighBuffer[i] = EMPTY_VALUE;
               }
               
               if(SessionLowBuffer[i + 1] != EMPTY_VALUE)
               {
                  SessionLowBuffer[i] = SessionLowBuffer[i + 1];
               }
               else if(session_low > 0.0)
               {
                  SessionLowBuffer[i] = session_low;
               }
               else
               {
                  SessionLowBuffer[i] = EMPTY_VALUE;
               }
            }
            else
            {
               // First bar in history - use stored values
               if(session_high > 0.0 && session_low > 0.0)
               {
                  SessionHighBuffer[i] = session_high;
                  SessionLowBuffer[i] = session_low;
               }
               else
               {
                  SessionHighBuffer[i] = EMPTY_VALUE;
                  SessionLowBuffer[i] = EMPTY_VALUE;
               }
            }
         }
      }
      else
      {
         // No active session - set empty values
         SessionHighBuffer[i] = EMPTY_VALUE;
         SessionLowBuffer[i] = EMPTY_VALUE;
      }
   }
   
   return(rates_total);
}

//+------------------------------------------------------------------+
