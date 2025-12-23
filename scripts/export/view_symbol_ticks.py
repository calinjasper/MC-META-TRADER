"""
View Symbol Ticks - Quick CLI Tool
Quickly view tick data for a specific symbol from the command line
"""

import requests
import argparse
from datetime import datetime, timedelta
from tabulate import tabulate

POCKETBASE_URL = "http://192.168.173.112:8090"


def get_symbol_ticks(symbol, limit=100, start_date=None, end_date=None):
    """
    Get ticks for a specific symbol from single ticks collection
    
    Args:
        symbol: Trading symbol (e.g., XAUUSD)
        limit: Maximum number of records to return
        start_date: Optional start date
        end_date: Optional end date
    
    Returns:
        List of tick records
    """
    url = f"{POCKETBASE_URL}/api/collections/ticks/records"
    
    # Build filter
    filters = []
    
    # Symbol filter (case-insensitive matching)
    filters.append(f'symbol ~ "{symbol}"')
    
    # Date filters
    if start_date:
        start_ts = int(start_date.timestamp() * 1000)
        filters.append(f"timestamp >= {start_ts}")
    if end_date:
        end_ts = int(end_date.timestamp() * 1000)
        filters.append(f"timestamp <= {end_ts}")
    
    params = {
        'filter': ' && '.join(filters),
        'sort': '-timestamp',  # Newest first
        'perPage': min(limit, 500),  # PocketBase max is 500
        'page': 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('items', [])
    except Exception as e:
        print(f"[ERROR] Failed to fetch ticks: {e}")
        return []


def format_tick_table(ticks):
    """
    Format ticks as a readable table
    
    Args:
        ticks: List of tick records
    
    Returns:
        Formatted table string
    """
    if not ticks:
        return "No ticks found"
    
    # Prepare table data
    headers = ['Time', 'Symbol', 'Bid', 'Ask', 'Last', 'Spread', 'Volume']
    rows = []
    
    for tick in ticks:
        # Convert timestamp to readable datetime
        timestamp = tick.get('timestamp', 0)
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000)
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            time_str = 'N/A'
        
        rows.append([
            time_str,
            tick.get('symbol', ''),
            f"{tick.get('bid', 0):.5f}",
            f"{tick.get('ask', 0):.5f}",
            f"{tick.get('last', 0):.5f}",
            f"{tick.get('spread', 0):.5f}",
            tick.get('volume', 0)
        ])
    
    return tabulate(rows, headers=headers, tablefmt='grid')


def get_symbol_stats(ticks):
    """
    Calculate statistics for ticks
    
    Args:
        ticks: List of tick records
    
    Returns:
        Dictionary of statistics
    """
    if not ticks:
        return {}
    
    bids = [t.get('bid', 0) for t in ticks if t.get('bid')]
    asks = [t.get('ask', 0) for t in ticks if t.get('ask')]
    spreads = [t.get('spread', 0) for t in ticks if t.get('spread')]
    
    stats = {
        'count': len(ticks),
        'avg_bid': sum(bids) / len(bids) if bids else 0,
        'min_bid': min(bids) if bids else 0,
        'max_bid': max(bids) if bids else 0,
        'avg_ask': sum(asks) / len(asks) if asks else 0,
        'min_ask': min(asks) if asks else 0,
        'max_ask': max(asks) if asks else 0,
        'avg_spread': sum(spreads) / len(spreads) if spreads else 0,
        'min_spread': min(spreads) if spreads else 0,
        'max_spread': max(spreads) if spreads else 0,
    }
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Quick view of tick data for a specific symbol'
    )
    parser.add_argument(
        '--symbol',
        required=True,
        help='Trading symbol (e.g., XAUUSD, EURUSD)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Maximum number of records to show (default: 100)'
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
        '--stats',
        action='store_true',
        help='Show statistics only (no table)'
    )
    parser.add_argument(
        '--no-table',
        action='store_true',
        help='Show statistics without table'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(f"  Viewing Ticks: {args.symbol}")
    print("=" * 80)
    print()
    
    # Parse dates if provided
    start_date = None
    end_date = None
    
    if args.from_date:
        try:
            start_date = datetime.strptime(args.from_date, '%Y-%m-%d')
            print(f"From: {start_date.strftime('%Y-%m-%d')}")
        except ValueError:
            print(f"[ERROR] Invalid start date format. Use YYYY-MM-DD")
            return
    
    if args.to_date:
        try:
            end_date = datetime.strptime(args.to_date, '%Y-%m-%d')
            end_date = end_date.replace(hour=23, minute=59, second=59)
            print(f"To: {end_date.strftime('%Y-%m-%d')}")
        except ValueError:
            print(f"[ERROR] Invalid end date format. Use YYYY-MM-DD")
            return
    
    if start_date or end_date:
        print()
    
    # Fetch ticks
    print(f"Fetching up to {args.limit} ticks...")
    ticks = get_symbol_ticks(args.symbol, args.limit, start_date, end_date)
    
    if not ticks:
        print(f"[ERROR] No ticks found for symbol: {args.symbol}")
        print()
        print("Tips:")
        print("  - Check symbol spelling (e.g., XAUUSDm, EURUSDm)")
        print("  - Verify PocketBase is running: http://192.168.173.112:8090")
        print("  - Check date range if specified")
        return
    
    print(f"[OK] Found {len(ticks)} tick(s)")
    print()
    
    # Calculate statistics
    stats = get_symbol_stats(ticks)
    
    # Show statistics
    if args.stats or args.no_table or len(ticks) > 50:
        print("Statistics:")
        print("=" * 80)
        print(f"Total Ticks:    {stats['count']}")
        print()
        print(f"Bid Price:")
        print(f"  Average:      {stats['avg_bid']:.5f}")
        print(f"  Min:          {stats['min_bid']:.5f}")
        print(f"  Max:          {stats['max_bid']:.5f}")
        print()
        print(f"Ask Price:")
        print(f"  Average:      {stats['avg_ask']:.5f}")
        print(f"  Min:          {stats['min_ask']:.5f}")
        print(f"  Max:          {stats['max_ask']:.5f}")
        print()
        print(f"Spread:")
        print(f"  Average:      {stats['avg_spread']:.5f}")
        print(f"  Min:          {stats['min_spread']:.5f}")
        print(f"  Max:          {stats['max_spread']:.5f}")
        print("=" * 80)
        print()
    
    # Show table (unless --stats or --no-table)
    if not args.stats and not args.no_table:
        if len(ticks) > 50:
            print(f"Showing first 50 of {len(ticks)} ticks:")
            print()
            print(format_tick_table(ticks[:50]))
            print()
            print(f"... {len(ticks) - 50} more ticks (use --limit to adjust)")
        else:
            print(format_tick_table(ticks))
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Cancelled by user")
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()

