"""
Export Ticks to CSV
Export tick data from PocketBase single 'ticks' collection to CSV files grouped by symbol
"""

import requests
import csv
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import sys

POCKETBASE_URL = "http://192.168.173.112:8090"
EXPORTS_DIR = Path("exports")


def get_all_records(collection_name="ticks", start_date=None, end_date=None):
    """
    Get all records from a tick collection with optional date filtering
    
    Args:
        collection_name: Name of the collection (e.g., 'ticks_XAUUSDm')
        start_date: Optional start date (datetime)
        end_date: Optional end date (datetime)
    
    Yields:
        Record dictionaries
    """
    page = 1
    per_page = 500
    
    while True:
        url = f"{POCKETBASE_URL}/api/collections/{collection_name}/records"
        
        params = {
            'page': page,
            'perPage': per_page,
            'sort': 'timestamp'
        }
        
        # Add date filter if provided
        if start_date or end_date:
            filters = []
            if start_date:
                start_ts = int(start_date.timestamp() * 1000)
                filters.append(f"timestamp >= {start_ts}")
            if end_date:
                end_ts = int(end_date.timestamp() * 1000)
                filters.append(f"timestamp <= {end_ts}")
            
            if filters:
                params['filter'] = ' && '.join(filters)
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            items = data.get('items', [])
            
            if not items:
                break
            
            for item in items:
                yield item
            
            # Check if more pages
            total_items = data.get('totalItems', 0)
            if page * per_page >= total_items:
                break
            
            page += 1
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch records: {e}")
            break


def export_symbol_to_csv(symbol, records):
    """
    Export records for a symbol to CSV file
    
    Args:
        symbol: Trading symbol
        records: List of tick records for this symbol
    
    Returns:
        Path to created CSV file
    """
    # Create exports directory if it doesn't exist
    EXPORTS_DIR.mkdir(exist_ok=True)
    
    # Generate filename
    date_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = EXPORTS_DIR / f"ticks_{symbol}_{date_suffix}.csv"
    
    # CSV headers
    headers = ['id', 'symbol', 'timestamp', 'datetime', 'bid', 'ask', 'last', 'volume', 'spread', 'created', 'updated']
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for item in records:
            # Convert timestamp to readable datetime
            timestamp = item.get('timestamp', 0)
            dt = datetime.fromtimestamp(timestamp / 1000) if timestamp else ''
            
            row = {
                'id': item.get('id', ''),
                'symbol': item.get('symbol', ''),
                'timestamp': timestamp,
                'datetime': dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] if dt else '',
                'bid': item.get('bid', ''),
                'ask': item.get('ask', ''),
                'last': item.get('last', ''),
                'volume': item.get('volume', ''),
                'spread': item.get('spread', ''),
                'created': item.get('created', ''),
                'updated': item.get('updated', '')
            }
            writer.writerow(row)
    
    return filename


def main():
    parser = argparse.ArgumentParser(
        description='Export tick data from PocketBase to CSV files (grouped by symbol)'
    )
    parser.add_argument(
        '--symbol',
        help='Export specific symbol only (e.g., XAUUSD)',
        default=None
    )
    parser.add_argument(
        '--from',
        dest='from_date',
        help='Start date (YYYY-MM-DD)',
        default=None
    )
    parser.add_argument(
        '--to',
        dest='to_date',
        help='End date (YYYY-MM-DD)',
        default=None
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available symbols and exit'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("  Export Ticks to CSV")
    print("=" * 70)
    print()
    
    # Parse dates if provided
    start_date = None
    end_date = None
    
    if args.from_date:
        try:
            start_date = datetime.strptime(args.from_date, '%Y-%m-%d')
            print(f"Start date: {start_date.strftime('%Y-%m-%d')}")
        except ValueError:
            print(f"[ERROR] Invalid start date format. Use YYYY-MM-DD")
            return
    
    if args.to_date:
        try:
            end_date = datetime.strptime(args.to_date, '%Y-%m-%d')
            # Set to end of day
            end_date = end_date.replace(hour=23, minute=59, second=59)
            print(f"End date: {end_date.strftime('%Y-%m-%d')}")
        except ValueError:
            print(f"[ERROR] Invalid end date format. Use YYYY-MM-DD")
            return
    
    if start_date or end_date:
        print()
    
    # Fetch all records and group by symbol
    print("Fetching records from 'ticks' collection...")
    
    records_by_symbol = defaultdict(list)
    total_records = 0
    
    for record in get_all_records('ticks', start_date, end_date):
        symbol = record.get('symbol', 'UNKNOWN')
        records_by_symbol[symbol].append(record)
        total_records += 1
        
        if total_records % 1000 == 0:
            print(f"  Fetched {total_records} records...", end='\r')
    
    if total_records == 0:
        print("[ERROR] No records found")
        print("Make sure PocketBase is running and ticks collection has data")
        return
    
    print(f"\n[OK] Fetched {total_records} records")
    print(f"[OK] Found {len(records_by_symbol)} unique symbols")
    print()
    
    # List mode
    if args.list:
        print("Available symbols:")
        for symbol, records in sorted(records_by_symbol.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  - {symbol}: {len(records)} records")
        print()
        return
    
    # Filter by symbol if specified
    if args.symbol:
        # Try to find matching symbol (case-insensitive)
        matching_symbols = {
            sym: recs for sym, recs in records_by_symbol.items()
            if sym.upper() == args.symbol.upper() or 
               sym.upper().startswith(args.symbol.upper())
        }
        
        if not matching_symbols:
            print(f"[ERROR] No data found for symbol: {args.symbol}")
            print(f"Available symbols: {', '.join(sorted(records_by_symbol.keys()))}")
            return
        
        records_by_symbol = matching_symbols
    
    
    # Export symbols
    print(f"Exporting {len(records_by_symbol)} symbol(s) to CSV...")
    print()
    
    total_exported = 0
    
    for symbol in sorted(records_by_symbol.keys()):
        records = records_by_symbol[symbol]
        print(f"Processing {symbol} ({len(records)} records)...")
        
        try:
            filename = export_symbol_to_csv(symbol, records)
            print(f"  [OK] Exported to: {filename}")
            total_exported += len(records)
        except Exception as e:
            print(f"  [ERROR] Failed to export {symbol}: {e}")
    
    print()
    print("=" * 70)
    print(f"Export completed!")
    print(f"Total records exported: {total_exported}")
    print(f"Files saved to: {EXPORTS_DIR.absolute()}")
    print("=" * 70)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Export cancelled by user")
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
