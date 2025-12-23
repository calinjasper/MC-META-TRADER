"""
Test MT5 Timezone
Check what timezone MT5 actually uses for timestamps
"""

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("[WARNING] MetaTrader5 not available for testing")

from datetime import datetime
import time

# Setup timezones
try:
    from zoneinfo import ZoneInfo
    UTC = ZoneInfo("UTC")
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    try:
        import pytz
        UTC = pytz.UTC
        IST = pytz.timezone("Asia/Kolkata")
    except ImportError:
        from datetime import timezone, timedelta
        UTC = timezone.utc
        IST = timezone(timedelta(hours=5, minutes=30))

print("=" * 70)
print("  Test MT5 Timezone")
print("=" * 70)
print()

if not MT5_AVAILABLE:
    print("[SKIP] MetaTrader5 not available")
    print()
    print("Manual check needed:")
    print("1. Check MT5 terminal timezone settings")
    print("2. Verify if MT5 timestamps are UTC or local time")
    print("3. Compare MT5 server time with system time")
    exit(0)

# Try to connect
if not mt5.initialize():
    print("[ERROR] Failed to initialize MT5")
    print(f"Error: {mt5.last_error()}")
    exit(1)

print("[OK] MT5 initialized")
print()

# Get server time
server_time = mt5.symbol_info_tick("EURUSD")
if server_time:
    print(f"MT5 Tick timestamp: {server_time.time}")
    print(f"Current system time: {time.time()}")
    print()
    
    # Interpret as UTC
    dt_utc = datetime.fromtimestamp(server_time.time, tz=UTC)
    print(f"Interpreted as UTC: {dt_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    # Interpret as local (no timezone)
    dt_local = datetime.fromtimestamp(server_time.time)
    print(f"Interpreted as local: {dt_local.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Current system time
    current_utc = datetime.now(UTC)
    current_local = datetime.now()
    
    print()
    print("Current times:")
    print(f"  System UTC: {current_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  System local: {current_local.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Compare
    diff_utc = abs((dt_utc - current_utc).total_seconds() / 3600)
    diff_local = abs((dt_local - current_local).total_seconds() / 3600)
    
    print("Time differences:")
    print(f"  MT5 as UTC vs Current UTC: {diff_utc:.2f} hours")
    print(f"  MT5 as local vs Current local: {diff_local:.2f} hours")
    print()
    
    if diff_utc < 1:
        print("[OK] MT5 timestamps appear to be in UTC")
    elif diff_local < 1:
        print("[WARNING] MT5 timestamps appear to be in LOCAL timezone!")
        print("         Need to adjust conversion logic")
    else:
        print("[WARNING] MT5 timestamps don't match either UTC or local time")
        print("         There may be a timezone configuration issue")

mt5.shutdown()

