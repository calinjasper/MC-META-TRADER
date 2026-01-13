"""
Standalone Tick to 1-Minute OHLC Aggregator (CSV Output)
Converts tick data from MySQL to 1-minute candles with maximum precision
Outputs to CSV for validation before database storage
"""

import sys
import argparse
import csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import mysql.connector
from mysql.connector import Error

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import Config
from src.data.minute_ohlc_manager import MinuteOHLCManager

# Timezone support
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
    UTC = ZoneInfo("UTC")
except ImportError:
    try:
        import pytz
        IST = pytz.timezone("Asia/Kolkata")
        UTC = pytz.UTC
    except ImportError:
        from datetime import timezone, timedelta
        IST = timezone(timedelta(hours=5, minutes=30))
        UTC = timezone.utc

ALLOWED_SYMBOLS = ['XAUUSD', 'EURUSD', 'EURJPY', 'USDJPY', 'BTCUSD']


def get_price_for_ohlc(tick: Dict) -> Optional[float]:
    """
    Price selection for OHLC calculation - matches MetaTrader 5 method
    MT5 uses BID prices exclusively for OHLC calculation
    
    Args:
        tick: Dictionary with bid, ask, last prices
        
    Returns:
        Bid price value or None if invalid
    """
    bid = float(tick.get('bid', 0))
    
    # MT5 uses bid price only for OHLC
    if bid > 0:
        return bid
    
    return None


def calculate_ohlc_from_ticks(ticks: List[Dict]) -> Optional[Dict]:
    """
    Universal OHLC calculation - industry standard method
    
    Rules:
    - Open: First valid price in the minute window
    - High: Maximum price during the minute
    - Low: Minimum price during the minute
    - Close: Last valid price in the minute window
    
    Args:
        ticks: List of tick dictionaries with timestamp, bid, ask, last
        
    Returns:
        Dictionary with open, high, low, close, tick_count or None
    """
    if not ticks:
        return None
    
    # Sort by timestamp (critical for accuracy)
    sorted_ticks = sorted(ticks, key=lambda t: t.get('timestamp', 0))
    
    # Extract bid prices only (MT5 uses bid prices exclusively for OHLC)
    bid_prices = []
    for tick in sorted_ticks:
        bid = float(tick.get('bid', 0))
        if bid > 0:
            bid_prices.append(bid)
    
    if not bid_prices:
        return None
    
    # Calculate OHLC using bid prices (MT5 standard method)
    ohlc = {
        'open': bid_prices[0],      # First bid price
        'high': max(bid_prices),   # Maximum bid price
        'low': min(bid_prices),    # Minimum bid price
        'close': bid_prices[-1],   # Last bid price
        'tick_count': len(ticks)  # Track number of ticks used
    }
    
    return ohlc


def format_utc_timestamp(dt: datetime) -> str:
    """Format datetime as UTC timestamp string"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    # Ensure it's in UTC
    utc_time = dt.astimezone(UTC) if dt.tzinfo != UTC else dt
    return utc_time.strftime("%Y-%m-%d %H:%M:%S UTC")


def get_ticks_for_minute(conn, symbol: str, minute_start: datetime, minute_end: datetime) -> List[Dict]:
    """
    Fetch all ticks for a specific minute from MySQL
    
    Args:
        conn: MySQL connection
        symbol: Trading symbol (normalized, e.g., 'XAUUSD')
        minute_start: Minute start datetime (inclusive)
        minute_end: Minute end datetime (exclusive)
        
    Returns:
        List of tick dictionaries
    """
    # Convert to milliseconds
    start_ms = int(minute_start.timestamp() * 1000)
    end_ms = int(minute_end.timestamp() * 1000)
    
    table_name = f"{symbol.lower()}_tick_level"
    
    query = f"""
    SELECT timestamp, utc_time, bid, ask, last 
    FROM {table_name}
    WHERE timestamp >= %s AND timestamp < %s
    ORDER BY timestamp ASC
    """
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, (start_ms, end_ms))
        results = cursor.fetchall()
        cursor.close()
        
        ticks = []
        for row in results:
            ticks.append({
                'timestamp': row[0],
                'utc_time': row[1],
                'bid': float(row[2]),
                'ask': float(row[3]),
                'last': float(row[4]) if row[4] is not None else None
            })
        
        return ticks
    except Error as e:
        print(f"[ERROR] Failed to fetch ticks: {e}")
        return []


def aggregate_ticks_to_minutes(conn, symbol: str, start_time: datetime, end_time: datetime) -> List[Dict]:
    """
    Aggregate ticks to 1-minute OHLC candles for a time range
    
    Args:
        conn: MySQL connection
        symbol: Trading symbol (normalized)
        start_time: Start datetime
        end_time: End datetime
        
    Returns:
        List of minute candle dictionaries
    """
    candles = []
    
    # Normalize start time to minute boundary
    current_minute = start_time.replace(second=0, microsecond=0)
    
    # Process each minute
    while current_minute < end_time:
        minute_end = current_minute + timedelta(minutes=1)
        
        # Fetch ticks for this minute
        ticks = get_ticks_for_minute(conn, symbol, current_minute, minute_end)
        
        if ticks:
            # Calculate OHLC
            ohlc = calculate_ohlc_from_ticks(ticks)
            
            if ohlc:
                timestamp_ms = int(current_minute.timestamp() * 1000)
                candle = {
                    'timestamp': timestamp_ms,
                    'utc_time': format_utc_timestamp(current_minute),
                    'open': ohlc['open'],
                    'high': ohlc['high'],
                    'low': ohlc['low'],
                    'close': ohlc['close'],
                    'tick_count': ohlc['tick_count']
                }
                candles.append(candle)
        
        # Move to next minute
        current_minute = minute_end
    
    return candles


def validate_ohlc_candle(candle: Dict) -> bool:
    """Validate OHLC candle for correctness"""
    open_price = candle['open']
    high_price = candle['high']
    low_price = candle['low']
    close_price = candle['close']
    
    # Rule 1: High must be >= all other prices
    if high_price < max(open_price, close_price, low_price):
        return False
    
    # Rule 2: Low must be <= all other prices
    if low_price > min(open_price, close_price, high_price):
        return False
    
    # Rule 3: All prices must be positive
    if any(p <= 0 for p in [open_price, high_price, low_price, close_price]):
        return False
    
    return True


def write_candles_to_csv(candles: List[Dict], output_file: str):
    """
    Write minute candles to CSV file
    
    Args:
        candles: List of candle dictionaries
        output_file: Output CSV file path
    """
    if not candles:
        print("[WARNING] No candles to write to CSV")
        return
    
    fieldnames = ['timestamp', 'utc_time', 'open', 'high', 'low', 'close', 'tick_count']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for candle in candles:
            # Validate before writing
            if validate_ohlc_candle(candle):
                writer.writerow(candle)
            else:
                print(f"[WARNING] Invalid candle skipped: {candle['utc_time']}")
    
    print(f"[OK] Wrote {len(candles)} candles to {output_file}")


def parse_datetime(date_str: str) -> datetime:
    """Parse date string to datetime (UTC)"""
    try:
        # Try YYYY-MM-DD format
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=UTC, hour=0, minute=0, second=0, microsecond=0)
    except ValueError:
        try:
            # Try YYYY-MM-DD HH:MM:SS format
            dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            return dt.replace(tzinfo=UTC)
        except ValueError:
            # Try timestamp (milliseconds)
            try:
                ts_ms = int(date_str)
                return datetime.fromtimestamp(ts_ms / 1000, tz=UTC)
            except ValueError:
                raise ValueError(f"Invalid date format: {date_str}")


def main():
    parser = argparse.ArgumentParser(
        description='Aggregate tick data to 1-minute OHLC candles (CSV output)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Last 24 hours
  python ticks_to_minute_csv.py --symbol XAUUSD --hours 24
  
  # Specific date range
  python ticks_to_minute_csv.py --symbol EURUSD --start-date 2025-12-30 --end-date 2025-12-31
  
  # Custom output file
  python ticks_to_minute_csv.py --symbol BTCUSD --hours 12 --output btc_minute.csv
        """
    )
    
    parser.add_argument('--symbol', required=False, choices=ALLOWED_SYMBOLS,
                       help='Symbol to process (XAUUSD, EURUSD, EURJPY, USDJPY, BTCUSD). If not specified, all symbols will be processed.')
    parser.add_argument('--start-date', type=str,
                       help='Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS or timestamp ms). Required if --hours not specified.')
    parser.add_argument('--end-date', type=str,
                       help='End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS or timestamp ms). If not specified, uses current time.')
    parser.add_argument('--hours', type=int,
                       help='Number of hours to process from now (backwards). Alternative to --start-date.')
    parser.add_argument('--output', type=str,
                       help='Output CSV file path (default: {symbol}_minute.csv). Ignored if --no-csv is set.')
    parser.add_argument('--store-db', action='store_true',
                       help='Store aggregated candles in MySQL database (minute_data schema)')
    parser.add_argument('--schema', type=str, default='minute_data',
                       help='Database schema name for storing minute data (default: minute_data)')
    parser.add_argument('--no-csv', action='store_true',
                       help='Disable CSV output (only store in database if --store-db is set)')
    
    args = parser.parse_args()
    
    # Determine time range
    end_time = datetime.now(UTC)
    
    if args.hours:
        start_time = end_time - timedelta(hours=args.hours)
    elif args.start_date:
        start_time = parse_datetime(args.start_date)
        if args.end_date:
            end_time = parse_datetime(args.end_date)
            # If end_date is just a date (no time specified), set it to end of day
            # Check if the original string was just a date (YYYY-MM-DD format)
            if len(args.end_date.split()) == 1 and ':' not in args.end_date:
                # It's just a date, set to end of day (23:59:59.999999)
                end_time = end_time.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        print("[ERROR] Must specify either --hours or --start-date")
        sys.exit(1)
    
    # Determine which symbols to process
    symbols_to_process = [args.symbol] if args.symbol else ALLOWED_SYMBOLS
    
    print("=" * 70)
    print("  Tick to 1-Minute OHLC Aggregator")
    print("=" * 70)
    if args.symbol:
        print(f"Symbol: {args.symbol}")
    else:
        print(f"Symbols: {', '.join(symbols_to_process)} (all symbols)")
    print(f"Start: {format_utc_timestamp(start_time)}")
    print(f"End: {format_utc_timestamp(end_time)}")
    if args.store_db:
        print(f"Database Storage: Enabled (schema: {args.schema})")
    if not args.no_csv:
        print(f"CSV Output: Enabled")
    print()
    
    # Load MySQL config
    config_loader = Config()
    mysql_config = config_loader.get('mysql', {})
    
    db_config = {
        'host': mysql_config.get('host', '127.0.0.1'),
        'port': mysql_config.get('port', 3306),
        'user': mysql_config.get('username', 'root'),
        'password': mysql_config.get('password', 'lokesh'),
        'database': mysql_config.get('database', 'forex')
    }
    
    # Initialize minute OHLC manager if database storage is enabled
    minute_manager = None
    if args.store_db:
        try:
            minute_manager = MinuteOHLCManager(
                host=db_config['host'],
                port=db_config['port'],
                username=db_config['user'],
                password=db_config['password'],
                schema=args.schema
            )
            if not minute_manager.initialize():
                print("[ERROR] Failed to initialize minute OHLC manager")
                sys.exit(1)
            print(f"[OK] Minute OHLC manager initialized (schema: {args.schema})")
        except Exception as e:
            print(f"[ERROR] Failed to initialize minute OHLC manager: {e}")
            sys.exit(1)
    
    # Connect to MySQL for tick data retrieval
    try:
        conn = mysql.connector.connect(**db_config)
        print(f"[OK] Connected to MySQL: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    except Error as e:
        print(f"[ERROR] Failed to connect to MySQL: {e}")
        sys.exit(1)
    
    try:
        # Process each symbol
        total_candles = 0
        total_stored = 0
        results = []
        
        for symbol in symbols_to_process:
            print()
            print("-" * 70)
            print(f"Processing {symbol}...")
            print("-" * 70)
            
            # Aggregate ticks to minutes
            print(f"[INFO] Aggregating ticks to 1-minute candles for {symbol}...")
            candles = aggregate_ticks_to_minutes(conn, symbol, start_time, end_time)
            
            if not candles:
                print(f"[WARNING] No candles generated for {symbol}. Check if tick data exists for the specified time range.")
                results.append({
                    'symbol': symbol,
                    'generated': 0,
                    'stored': 0,
                    'skipped': True
                })
                continue
            
            print(f"[OK] Generated {len(candles)} minute candles for {symbol}")
            
            # Validate candles
            valid_candles = [c for c in candles if validate_ohlc_candle(c)]
            invalid_count = len(candles) - len(valid_candles)
            if invalid_count > 0:
                print(f"[WARNING] {invalid_count} invalid candles found for {symbol} (will be skipped)")
            
            # Store in database if enabled
            stored_count = 0
            if args.store_db and minute_manager:
                print(f"[INFO] Storing {len(valid_candles)} candles in database for {symbol}...")
                stored_count = minute_manager.store_minute_candles_batch(symbol, valid_candles)
                print(f"[OK] Stored {stored_count} candles in database for {symbol} (schema: {args.schema})")
                total_stored += stored_count
            
            # Write to CSV if enabled
            if not args.no_csv:
                output_file = args.output if args.output and args.symbol else f"{symbol.lower()}_minute.csv"
                write_candles_to_csv(valid_candles, output_file)
            
            total_candles += len(valid_candles)
            results.append({
                'symbol': symbol,
                'generated': len(valid_candles),
                'stored': stored_count,
                'skipped': False
            })
        
        # Summary
        print()
        print("=" * 70)
        print("  Summary")
        print("=" * 70)
        print(f"Time range: {format_utc_timestamp(start_time)} to {format_utc_timestamp(end_time)}")
        print()
        print("Results by symbol:")
        for result in results:
            if result['skipped']:
                print(f"  {result['symbol']:8s}: No data found")
            else:
                print(f"  {result['symbol']:8s}: {result['generated']:6d} candles generated, {result['stored']:6d} stored")
        print()
        print(f"Total candles generated: {total_candles}")
        if args.store_db:
            print(f"Total candles stored: {total_stored}")
        print()
        print("Validation checks:")
        print(f"  - All candles have valid OHLC relationships")
        print(f"  - High >= Open, High >= Close, High >= Low")
        print(f"  - Low <= Open, Low <= Close, Low <= High")
        print()
        if args.store_db:
            print("[OK] Data stored in database and ready for use!")
        elif not args.no_csv:
            print("[OK] CSV files ready for validation!")
        print("=" * 70)
        
    except Exception as e:
        print(f"[ERROR] Aggregation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()
        if minute_manager:
            minute_manager.close()


if __name__ == "__main__":
    main()

