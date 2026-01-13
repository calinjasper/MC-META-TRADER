"""
Test different price selection methods to find which matches MT5
Tests: bid only, ask only, last only, mid price, and current method
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import mysql.connector
from mysql.connector import Error
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")

def get_ticks_for_minute(conn, symbol: str, minute_start: datetime, minute_end: datetime) -> List[Dict]:
    """Fetch all ticks for a specific minute"""
    start_ms = int(minute_start.timestamp() * 1000)
    end_ms = int(minute_end.timestamp() * 1000)
    
    table_name = f"{symbol.lower()}_tick_level"
    
    query = f"""
    SELECT timestamp, bid, ask, last 
    FROM `{table_name}`
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
                'bid': float(row[1]),
                'ask': float(row[2]),
                'last': float(row[3]) if row[3] is not None else None
            })
        
        return ticks
    except Error as e:
        print(f"[ERROR] Failed to fetch ticks: {e}")
        return []

def calculate_ohlc_bid_only(ticks: List[Dict]) -> Optional[Dict]:
    """Calculate OHLC using only bid prices"""
    if not ticks:
        return None
    
    bids = [t['bid'] for t in ticks if t['bid'] > 0]
    if not bids:
        return None
    
    return {
        'open': bids[0],
        'high': max(bids),
        'low': min(bids),
        'close': bids[-1]
    }

def calculate_ohlc_ask_only(ticks: List[Dict]) -> Optional[Dict]:
    """Calculate OHLC using only ask prices"""
    if not ticks:
        return None
    
    asks = [t['ask'] for t in ticks if t['ask'] > 0]
    if not asks:
        return None
    
    return {
        'open': asks[0],
        'high': max(asks),
        'low': min(asks),
        'close': asks[-1]
    }

def calculate_ohlc_last_only(ticks: List[Dict]) -> Optional[Dict]:
    """Calculate OHLC using only last prices"""
    if not ticks:
        return None
    
    lasts = [t['last'] for t in ticks if t.get('last') is not None and t['last'] > 0]
    if not lasts:
        return None
    
    return {
        'open': lasts[0],
        'high': max(lasts),
        'low': min(lasts),
        'close': lasts[-1]
    }

def calculate_ohlc_mid_price(ticks: List[Dict]) -> Optional[Dict]:
    """Calculate OHLC using mid prices (bid + ask) / 2"""
    if not ticks:
        return None
    
    mid_prices = []
    for t in ticks:
        if t['bid'] > 0 and t['ask'] > 0:
            mid_prices.append((t['bid'] + t['ask']) / 2.0)
    
    if not mid_prices:
        return None
    
    return {
        'open': mid_prices[0],
        'high': max(mid_prices),
        'low': min(mid_prices),
        'close': mid_prices[-1]
    }

def calculate_ohlc_current_method(ticks: List[Dict]) -> Optional[Dict]:
    """Calculate OHLC using current method: last > mid > bid"""
    if not ticks:
        return None
    
    prices = []
    for t in ticks:
        # Priority: last > mid > bid
        if t.get('last') is not None and t['last'] > 0:
            prices.append(t['last'])
        elif t['bid'] > 0 and t['ask'] > 0:
            prices.append((t['bid'] + t['ask']) / 2.0)
        elif t['bid'] > 0:
            prices.append(t['bid'])
    
    if not prices:
        return None
    
    return {
        'open': prices[0],
        'high': max(prices),
        'low': min(prices),
        'close': prices[-1]
    }

def compare_with_mt5(our_ohlc: Dict, mt5_ohlc: Dict) -> Dict:
    """Compare our OHLC with MT5's OHLC"""
    return {
        'open_diff': abs(our_ohlc['open'] - mt5_ohlc['open']),
        'high_diff': abs(our_ohlc['high'] - mt5_ohlc['high']),
        'low_diff': abs(our_ohlc['low'] - mt5_ohlc['low']),
        'close_diff': abs(our_ohlc['close'] - mt5_ohlc['close']),
        'total_diff': abs(our_ohlc['open'] - mt5_ohlc['open']) + 
                     abs(our_ohlc['high'] - mt5_ohlc['high']) +
                     abs(our_ohlc['low'] - mt5_ohlc['low']) +
                     abs(our_ohlc['close'] - mt5_ohlc['close'])
    }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test different price selection methods')
    parser.add_argument('--symbol', required=True, help='Symbol to test (e.g., XAUUSD)')
    parser.add_argument('--timestamp', type=int, help='Timestamp in milliseconds (default: latest)')
    parser.add_argument('--mt5-open', type=float, help='MT5 Open price for comparison')
    parser.add_argument('--mt5-high', type=float, help='MT5 High price for comparison')
    parser.add_argument('--mt5-low', type=float, help='MT5 Low price for comparison')
    parser.add_argument('--mt5-close', type=float, help='MT5 Close price for comparison')
    
    args = parser.parse_args()
    
    # Connect to MySQL
    conn = mysql.connector.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='lokesh',
        database='forex'
    )
    
    # Get timestamp
    if args.timestamp:
        timestamp_ms = args.timestamp
    else:
        # Get latest timestamp
        cursor = conn.cursor()
        table_name = f"{args.symbol.lower()}_tick_level"
        cursor.execute(f"SELECT MAX(timestamp) FROM `{table_name}`")
        result = cursor.fetchone()
        timestamp_ms = result[0] if result[0] else None
        cursor.close()
        
        if not timestamp_ms:
            print(f"[ERROR] No data found for {args.symbol}")
            conn.close()
            return
    
    # Convert to datetime
    timestamp_sec = timestamp_ms / 1000
    target_time = datetime.fromtimestamp(timestamp_sec, tz=UTC)
    minute_start = target_time.replace(second=0, microsecond=0)
    minute_end = minute_start + timedelta(minutes=1)
    
    print("="*70)
    print("  Price Selection Method Test")
    print("="*70)
    print(f"Symbol: {args.symbol}")
    print(f"Minute: {minute_start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    # Fetch ticks
    ticks = get_ticks_for_minute(conn, args.symbol, minute_start, minute_end)
    print(f"[INFO] Fetched {len(ticks)} ticks")
    
    if not ticks:
        print("[ERROR] No ticks found for this minute")
        conn.close()
        return
    
    # Test different methods
    methods = {
        'Bid Only': calculate_ohlc_bid_only,
        'Ask Only': calculate_ohlc_ask_only,
        'Last Only': calculate_ohlc_last_only,
        'Mid Price': calculate_ohlc_mid_price,
        'Current Method (last>mid>bid)': calculate_ohlc_current_method
    }
    
    results = {}
    for method_name, method_func in methods.items():
        ohlc = method_func(ticks)
        if ohlc:
            results[method_name] = ohlc
    
    # Print results
    print("\n" + "="*70)
    print("  OHLC Results by Method")
    print("="*70)
    print(f"\n{'Method':<30} {'Open':<12} {'High':<12} {'Low':<12} {'Close':<12}")
    print("-"*70)
    
    for method_name, ohlc in results.items():
        print(f"{method_name:<30} {ohlc['open']:<12.5f} {ohlc['high']:<12.5f} {ohlc['low']:<12.5f} {ohlc['close']:<12.5f}")
    
    # Compare with MT5 if provided
    if args.mt5_open and args.mt5_high and args.mt5_low and args.mt5_close:
        mt5_ohlc = {
            'open': args.mt5_open,
            'high': args.mt5_high,
            'low': args.mt5_low,
            'close': args.mt5_close
        }
        
        print("\n" + "="*70)
        print("  Comparison with MT5")
        print("="*70)
        print(f"\nMT5 Values: O={mt5_ohlc['open']:.5f}, H={mt5_ohlc['high']:.5f}, L={mt5_ohlc['low']:.5f}, C={mt5_ohlc['close']:.5f}")
        print()
        print(f"{'Method':<30} {'Total Diff':<15} {'Open Diff':<12} {'High Diff':<12} {'Low Diff':<12} {'Close Diff':<12}")
        print("-"*90)
        
        best_method = None
        best_diff = float('inf')
        
        for method_name, ohlc in results.items():
            comparison = compare_with_mt5(ohlc, mt5_ohlc)
            print(f"{method_name:<30} {comparison['total_diff']:<15.5f} {comparison['open_diff']:<12.5f} {comparison['high_diff']:<12.5f} {comparison['low_diff']:<12.5f} {comparison['close_diff']:<12.5f}")
            
            if comparison['total_diff'] < best_diff:
                best_diff = comparison['total_diff']
                best_method = method_name
        
        print()
        print(f"[BEST MATCH] {best_method} (Total difference: {best_diff:.5f})")
    
    conn.close()

if __name__ == "__main__":
    main()

