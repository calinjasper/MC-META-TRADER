"""
Validate OHLC CSV output
Checks OHLC relationships and data integrity
"""

import sys
import csv
from pathlib import Path

def validate_csv(csv_file: str):
    """Validate OHLC CSV file"""
    print("=" * 70)
    print("  OHLC CSV Validation")
    print("=" * 70)
    print(f"File: {csv_file}")
    print()
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        print("[ERROR] CSV file is empty")
        return False
    
    print(f"[INFO] Total candles: {len(rows)}")
    print()
    
    # Validation checks
    invalid_count = 0
    issues = []
    
    for i, row in enumerate(rows):
        try:
            open_price = float(row['open'])
            high_price = float(row['high'])
            low_price = float(row['low'])
            close_price = float(row['close'])
            tick_count = int(row['tick_count'])
            
            # Check 1: High >= all prices
            if high_price < open_price or high_price < close_price or high_price < low_price:
                invalid_count += 1
                issues.append(f"Row {i+2}: High ({high_price}) is not >= all prices")
            
            # Check 2: Low <= all prices
            if low_price > open_price or low_price > close_price or low_price > high_price:
                invalid_count += 1
                issues.append(f"Row {i+2}: Low ({low_price}) is not <= all prices")
            
            # Check 3: All prices positive
            if any(p <= 0 for p in [open_price, high_price, low_price, close_price]):
                invalid_count += 1
                issues.append(f"Row {i+2}: Non-positive price found")
            
            # Check 4: Tick count > 0
            if tick_count <= 0:
                invalid_count += 1
                issues.append(f"Row {i+2}: Invalid tick count ({tick_count})")
            
        except (ValueError, KeyError) as e:
            invalid_count += 1
            issues.append(f"Row {i+2}: Data format error - {e}")
    
    # Check time boundaries (no gaps, no overlaps)
    print("[INFO] Checking time boundaries...")
    timestamps = [int(row['timestamp']) for row in rows]
    timestamps_sorted = sorted(timestamps)
    
    if timestamps != timestamps_sorted:
        print("[WARNING] Timestamps are not in ascending order")
    
    # Check for gaps (should be exactly 60 seconds = 60000 ms between minutes)
    gaps = []
    for i in range(len(timestamps_sorted) - 1):
        diff = timestamps_sorted[i+1] - timestamps_sorted[i]
        if diff != 60000:  # 1 minute in milliseconds
            gaps.append(f"Gap between {timestamps_sorted[i]} and {timestamps_sorted[i+1]}: {diff}ms")
    
    if gaps:
        print(f"[WARNING] Found {len(gaps)} time gaps:")
        for gap in gaps[:5]:  # Show first 5
            print(f"  - {gap}")
        if len(gaps) > 5:
            print(f"  ... and {len(gaps) - 5} more")
    else:
        print("[OK] No time gaps found (consecutive minutes)")
    
    # Summary
    print()
    print("=" * 70)
    print("  Validation Summary")
    print("=" * 70)
    
    if invalid_count == 0:
        print("[OK] All candles are valid!")
        print(f"  - {len(rows)} candles validated")
        print("  - All OHLC relationships correct")
        print("  - All prices positive")
        print("  - All tick counts valid")
        return True
    else:
        print(f"[ERROR] Found {invalid_count} invalid candles")
        print("\nIssues found:")
        for issue in issues[:10]:  # Show first 10
            print(f"  - {issue}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_csv_ohlc.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    if not Path(csv_file).exists():
        print(f"[ERROR] File not found: {csv_file}")
        sys.exit(1)
    
    success = validate_csv(csv_file)
    sys.exit(0 if success else 1)

