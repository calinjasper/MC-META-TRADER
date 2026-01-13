"""
Compare aggregated CSV data with MetaTrader 5's actual M1 candles
Fetches M1 data directly from MT5 and compares with our CSV aggregated values
"""
import sys
import os
import csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
from src.mt5_connector import MT5Connector, UTC

def load_csv_data(csv_file: str) -> List[Dict]:
    """Load CSV data from aggregated file"""
    candles = []
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                candles.append({
                    'timestamp': int(row['timestamp']),
                    'utc_time': row['utc_time'],
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'tick_count': int(row.get('tick_count', 0))
                })
    except Exception as e:
        print(f"[ERROR] Failed to load CSV: {e}")
    return candles

def resolve_mt5_symbol(mt5_connector: MT5Connector, symbol: str) -> Optional[str]:
    """Resolve symbol name to MT5's actual symbol name"""
    # Try the symbol as-is first
    if mt5_connector.get_symbol_info(symbol):
        return symbol
    
    # Try with 'm' suffix (micro account)
    symbol_with_m = f"{symbol}m"
    if mt5_connector.get_symbol_info(symbol_with_m):
        return symbol_with_m
    
    # Try uppercase
    symbol_upper = symbol.upper()
    if mt5_connector.get_symbol_info(symbol_upper):
        return symbol_upper
    
    # Try uppercase with 'm'
    symbol_upper_m = f"{symbol_upper}m"
    if mt5_connector.get_symbol_info(symbol_upper_m):
        return symbol_upper_m
    
    return None

def fetch_mt5_m1_candle(mt5_connector: MT5Connector, symbol: str, timestamp_ms: int) -> Optional[Dict]:
    """
    Fetch M1 candle from MT5 for a specific timestamp
    
    Args:
        mt5_connector: MT5Connector instance
        symbol: Trading symbol (e.g., 'XAUUSD')
        timestamp_ms: Unix timestamp in milliseconds
        
    Returns:
        Dictionary with MT5 OHLC data or None
    """
    try:
        # Resolve symbol name first
        resolved_symbol = resolve_mt5_symbol(mt5_connector, symbol)
        if not resolved_symbol:
            print(f"[WARNING] Could not resolve symbol {symbol} in MT5")
            return None
        
        # Convert timestamp to datetime
        timestamp_sec = timestamp_ms / 1000
        target_time = datetime.fromtimestamp(timestamp_sec, tz=UTC)
        
        # Get M1 rates around this time (fetch a few bars to find the exact one)
        rates = mt5_connector.get_rates(resolved_symbol, mt5.TIMEFRAME_M1, count=10, start_pos=0)
        
        if not rates:
            return None
        
        # Find the candle that matches our timestamp (within the same minute)
        target_minute = target_time.replace(second=0, microsecond=0)
        
        for rate in rates:
            rate_time = rate['time']
            if isinstance(rate_time, datetime):
                rate_minute = rate_time.replace(second=0, microsecond=0)
                if rate_minute == target_minute:
                    return {
                        'time': rate_time,
                        'open': rate['open'],
                        'high': rate['high'],
                        'low': rate['low'],
                        'close': rate['close'],
                        'tick_volume': rate.get('tick_volume', 0),
                        'spread': rate.get('spread', 0)
                    }
        
        # If exact match not found, try to get the closest one
        print(f"[WARNING] Exact minute match not found for {target_minute}, trying closest...")
        
        # Try fetching with copy_rates_from_pos
        try:
            import MetaTrader5 as mt5_lib
            # Calculate position from current time
            now = datetime.now(UTC)
            minutes_diff = int((now - target_minute).total_seconds() / 60)
            
            if minutes_diff >= 0 and minutes_diff < 1000:
                rates_array = mt5_lib.copy_rates_from_pos(resolved_symbol, mt5_lib.TIMEFRAME_M1, minutes_diff, 1)
                if rates_array is not None and len(rates_array) > 0:
                    rate = rates_array[0]
                    rate_time = datetime.fromtimestamp(rate[0], tz=UTC)
                    rate_minute = rate_time.replace(second=0, microsecond=0)
                    
                    if abs((rate_minute - target_minute).total_seconds()) < 60:
                        return {
                            'time': rate_time,
                            'open': float(rate[1]),
                            'high': float(rate[2]),
                            'low': float(rate[3]),
                            'close': float(rate[4]),
                            'tick_volume': int(rate[5]) if len(rate) > 5 else 0,
                            'spread': 0.0
                        }
        except Exception as e:
            print(f"[WARNING] Failed to fetch with copy_rates_from_pos: {e}")
        
        return None
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch MT5 candle: {e}")
        return None

def compare_candles(our_candle: Dict, mt5_candle: Dict) -> Dict:
    """Compare our aggregated candle with MT5's candle"""
    comparison = {
        'time': our_candle['utc_time'],
        'our_open': our_candle['open'],
        'mt5_open': mt5_candle['open'],
        'open_diff': abs(our_candle['open'] - mt5_candle['open']),
        'our_high': our_candle['high'],
        'mt5_high': mt5_candle['high'],
        'high_diff': abs(our_candle['high'] - mt5_candle['high']),
        'our_low': our_candle['low'],
        'mt5_low': mt5_candle['low'],
        'low_diff': abs(our_candle['low'] - mt5_candle['low']),
        'our_close': our_candle['close'],
        'mt5_close': mt5_candle['close'],
        'close_diff': abs(our_candle['close'] - mt5_candle['close']),
        'our_tick_count': our_candle.get('tick_count', 0),
        'mt5_tick_volume': mt5_candle.get('tick_volume', 0)
    }
    
    # Calculate match percentage (within 0.01 tolerance)
    tolerance = 0.01
    matches = 0
    total = 4
    
    if comparison['open_diff'] <= tolerance:
        matches += 1
    if comparison['high_diff'] <= tolerance:
        matches += 1
    if comparison['low_diff'] <= tolerance:
        matches += 1
    if comparison['close_diff'] <= tolerance:
        matches += 1
    
    comparison['match_percentage'] = (matches / total) * 100
    comparison['matches'] = matches
    
    return comparison

def print_comparison(comparison: Dict):
    """Print formatted comparison results"""
    print(f"\n{'='*70}")
    print(f"Comparison for {comparison['time']}")
    print(f"{'='*70}")
    print(f"\n{'Field':<12} {'Our Value':<15} {'MT5 Value':<15} {'Difference':<15} {'Match':<10}")
    print(f"{'-'*70}")
    
    fields = [
        ('Open', 'our_open', 'mt5_open', 'open_diff'),
        ('High', 'our_high', 'mt5_high', 'high_diff'),
        ('Low', 'our_low', 'mt5_low', 'low_diff'),
        ('Close', 'our_close', 'mt5_close', 'close_diff')
    ]
    
    for field_name, our_key, mt5_key, diff_key in fields:
        our_val = comparison[our_key]
        mt5_val = comparison[mt5_key]
        diff = comparison[diff_key]
        match = "YES" if diff <= 0.01 else "NO"
        print(f"{field_name:<12} {our_val:<15.5f} {mt5_val:<15.5f} {diff:<15.5f} {match:<10}")
    
    print(f"\n{'Tick Count':<12} {'Our':<15} {'MT5':<15}")
    print(f"{'-'*40}")
    print(f"{'':<12} {comparison['our_tick_count']:<15} {comparison['mt5_tick_volume']:<15}")
    
    print(f"\nMatch: {comparison['matches']}/4 fields ({comparison['match_percentage']:.1f}%)")
    print(f"{'='*70}\n")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Compare aggregated CSV with MT5 M1 candles')
    parser.add_argument('--csv', required=True, help='Path to aggregated CSV file')
    parser.add_argument('--symbol', required=True, help='Symbol to compare (e.g., XAUUSD)')
    parser.add_argument('--limit', type=int, default=10, help='Number of candles to compare (default: 10)')
    
    args = parser.parse_args()
    
    print("="*70)
    print("  MT5 OHLC Comparison Tool")
    print("="*70)
    print(f"CSV File: {args.csv}")
    print(f"Symbol: {args.symbol}")
    print(f"Limit: {args.limit} candles")
    print()
    
    # Initialize MT5
    mt5_connector = MT5Connector()
    if not mt5_connector.initialize():
        print("[ERROR] Failed to initialize MT5. Please ensure MT5 is running.")
        sys.exit(1)
    
    if not mt5_connector.is_connected():
        print("[ERROR] MT5 not connected. Please check MT5 terminal.")
        sys.exit(1)
    
    print("[OK] Connected to MetaTrader 5")
    
    # Load CSV data
    csv_candles = load_csv_data(args.csv)
    if not csv_candles:
        print("[ERROR] No data loaded from CSV")
        sys.exit(1)
    
    print(f"[OK] Loaded {len(csv_candles)} candles from CSV")
    print()
    
    # Compare candles
    comparisons = []
    for i, our_candle in enumerate(csv_candles[:args.limit]):
        print(f"[INFO] Comparing candle {i+1}/{min(len(csv_candles), args.limit)}: {our_candle['utc_time']}")
        
        mt5_candle = fetch_mt5_m1_candle(mt5_connector, args.symbol, our_candle['timestamp'])
        
        if mt5_candle:
            comparison = compare_candles(our_candle, mt5_candle)
            comparisons.append(comparison)
            print_comparison(comparison)
        else:
            print(f"[WARNING] Could not fetch MT5 candle for {our_candle['utc_time']}")
            print()
    
    # Summary
    if comparisons:
        print("="*70)
        print("  Summary")
        print("="*70)
        
        total_matches = sum(c['matches'] for c in comparisons)
        total_possible = len(comparisons) * 4
        avg_match_pct = sum(c['match_percentage'] for c in comparisons) / len(comparisons)
        
        print(f"Total candles compared: {len(comparisons)}")
        print(f"Total fields matched: {total_matches}/{total_possible}")
        print(f"Average match percentage: {avg_match_pct:.1f}%")
        print()
        
        if avg_match_pct < 100:
            print("[ANALYSIS] Values do not match exactly. Possible causes:")
            print("  1. Different price selection method (bid vs ask vs last)")
            print("  2. Different time window boundaries")
            print("  3. Different tick data source")
            print("  4. MT5 server time offset")
        else:
            print("[SUCCESS] All values match MT5 exactly!")
    
    # MT5Connector doesn't have disconnect, connection is managed by MT5 library
    pass

if __name__ == "__main__":
    main()

