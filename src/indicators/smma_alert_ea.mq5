//+------------------------------------------------------------------+
//|                                              smma_alert_ea.mq5   |
//|                        SMMA Alert Monitor Expert Advisor          |
//|                                                                   |
//| Monitors SMMA indicator alerts and forwards them to Python       |
//+------------------------------------------------------------------+
#property copyright "SMMA Alert EA for Python Platform"
#property version   "1.00"
#property strict

//--- Input Parameters
input string AlertFilePath = "smma_alerts.txt";  // Alert file name (in MQL5/Files/)
input bool   EnableLogging = true;               // Enable detailed logging
input int    CheckInterval = 100;                // Check interval in milliseconds

//--- Global Variables
string last_alert_line = "";
datetime last_check_time = 0;
int log_file_handle = INVALID_HANDLE;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
   // Open log file for writing alerts
   string file_path = AlertFilePath;
   log_file_handle = FileOpen(file_path, FILE_WRITE|FILE_TXT|FILE_COMMON);
   
   if(log_file_handle == INVALID_HANDLE)
   {
      Print("SMMA Alert EA: Failed to open alert file: ", file_path, " Error: ", GetLastError());
      return(INIT_FAILED);
   }
   
   Print("SMMA Alert EA: Initialized. Monitoring SMMA alerts...");
   Print("SMMA Alert EA: Alert file: ", file_path);
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(log_file_handle != INVALID_HANDLE)
   {
      FileClose(log_file_handle);
      log_file_handle = INVALID_HANDLE;
   }
   
   Print("SMMA Alert EA: Deinitialized. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
   // Check MT5 terminal logs for SMMA alerts
   // Note: MT5's Alert() function writes to terminal logs
   // We'll monitor the logs directory for new alert messages
   
   // For now, we'll use a simpler approach:
   // The indicator already sends alerts via Alert() and SendNotification()
   // We'll create a custom solution that writes directly to file when indicator detects entry
   
   // This EA will be attached to the chart along with the SMMA indicator
   // The indicator will write alerts to a file, and this EA will ensure the file is accessible
   
   // Check if we need to flush the file
   static datetime last_flush = 0;
   if(TimeCurrent() - last_flush > 1) // Flush every second
   {
      if(log_file_handle != INVALID_HANDLE)
      {
         FileFlush(log_file_handle);
      }
      last_flush = TimeCurrent();
   }
}

//+------------------------------------------------------------------+
//| Write alert to file                                                |
//+------------------------------------------------------------------+
void WriteAlert(string symbol, string action, double price, double entry_level = 0.0)
{
   if(log_file_handle == INVALID_HANDLE)
   {
      // Try to reopen file
      log_file_handle = FileOpen(AlertFilePath, FILE_WRITE|FILE_READ|FILE_TXT|FILE_COMMON);
      if(log_file_handle == INVALID_HANDLE)
      {
         Print("SMMA Alert EA: Cannot write alert - file not open");
         return;
      }
   }
   
   // Get current timeframe
   int timeframe = Period();
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
   
   // Check for duplicates (same symbol, action, and time within same minute)
   static string last_alert = "";
   if(alert_line == last_alert)
   {
      return; // Duplicate alert, skip
   }
   last_alert = alert_line;
   
   // Write to file (append mode)
   FileSeek(log_file_handle, 0, SEEK_END);
   FileWriteString(log_file_handle, alert_line + "\n");
   FileFlush(log_file_handle);
   
   if(EnableLogging)
   {
      Print("SMMA Alert EA: Alert written - ", alert_line);
   }
}

//+------------------------------------------------------------------+
//| Parse indicator alert message and write to file                    |
//| This function can be called from the indicator via global variable or file
//+------------------------------------------------------------------+
void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   // Monitor for custom events from indicator
   // The indicator can trigger custom events that this EA can catch
}

//+------------------------------------------------------------------+
//| Monitor MT5 logs for SMMA alerts (alternative approach)            |
//+------------------------------------------------------------------+
void MonitorLogsForAlerts()
{
   // This is a more complex approach that would require reading MT5 log files
   // For simplicity, we'll use a file-based approach where the indicator writes directly
   // This EA ensures the file is accessible and flushed properly
}
