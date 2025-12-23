"""
Validation Script: Verify Database Storage is Disabled

This script validates that all database storage operations are properly disabled
and no data is being stored to PocketBase.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.data.pocketbase_manager import PocketBaseManager
from datetime import datetime
import time
import requests

def get_collection_count(base_url: str, collection_name: str) -> int:
    """Get current record count for a collection"""
    try:
        response = requests.get(
            f"{base_url}/api/collections/{collection_name}/records",
            params={'perPage': 1},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('totalItems', 0)
        return -1
    except Exception as e:
        print(f"  Error getting count for {collection_name}: {e}")
        return -1

def test_storage_methods(pb_manager: PocketBaseManager):
    """Test that all storage methods return immediately without storing"""
    print("\n" + "="*70)
    print("TEST 1: Direct Method Calls")
    print("="*70)
    
    # Test data
    test_tick = {
        'time': datetime.now(),
        'bid': 1.0850,
        'ask': 1.0852,
        'last': 1.0851,
        'volume': 1000
    }
    
    test_trade = {
        'ticket': 999999,
        'symbol': 'EURUSD',
        'direction': 'BUY',
        'entry_time': datetime.now(),
        'entry_price': 1.0850,
        'volume': 0.01,
        'sl': 1.0800,
        'tp': 1.0900
    }
    
    test_signal = {
        'symbol': 'EURUSD',
        'type': 'BUY',
        'time': datetime.now(),
        'strategy_name': 'TEST_VALIDATION',
        'price': 1.0850
    }
    
    # Get initial queue size
    initial_queue_size = pb_manager.write_queue.qsize()
    print(f"Initial queue size: {initial_queue_size}")
    
    # Call all storage methods
    print("\nCalling storage methods...")
    pb_manager.store_tick('EURUSD', test_tick)
    pb_manager.store_ohlc('EURUSD', 'M1', {
        'time': datetime.now(),
        'open': 1.0850,
        'high': 1.0852,
        'low': 1.0848,
        'close': 1.0851
    })
    pb_manager.store_trade(test_trade)
    pb_manager.store_signal(test_signal)
    pb_manager.store_indicator('EURUSD', 'M1', datetime.now(), 'RSI_14', 65.5)
    
    # Check queue size after calls
    final_queue_size = pb_manager.write_queue.qsize()
    print(f"Final queue size: {final_queue_size}")
    
    # Get validation stats
    stats = pb_manager.get_storage_validation_stats()
    print(f"\nStorage Attempts:")
    for key, count in stats['storage_attempts'].items():
        print(f"  {key}: {count} attempts")
    
    # Validate
    if final_queue_size == initial_queue_size == 0:
        print("\n[PASS] Queue remains empty after storage method calls")
        return True
    else:
        print(f"\n[FAIL] Queue size changed from {initial_queue_size} to {final_queue_size}")
        return False

def test_pocketbase_collections(base_url: str):
    """Test that PocketBase collections don't have new records"""
    print("\n" + "="*70)
    print("TEST 2: PocketBase Collection Verification")
    print("="*70)
    
    collections = ['ticks', 'ohlc', 'trades', 'signals', 'indicators']
    
    print("\nCurrent collection counts:")
    initial_counts = {}
    for coll in collections:
        count = get_collection_count(base_url, coll)
        initial_counts[coll] = count
        if count >= 0:
            print(f"  {coll}: {count} records")
        else:
            print(f"  {coll}: Unable to query (collection may not exist)")
    
    print("\n[OK] Collection counts retrieved (note these for comparison)")
    return initial_counts

def validate_storage_disabled(pb_manager: PocketBaseManager):
    """Run comprehensive validation"""
    print("\n" + "="*70)
    print("COMPREHENSIVE VALIDATION")
    print("="*70)
    
    validation = pb_manager.validate_storage_disabled()
    
    print(f"\n{validation['message']}")
    print(f"\nDetails:")
    print(f"  Storage Disabled Flag: {validation['storage_disabled']}")
    print(f"  Queue Size: {validation['queue_size']}")
    print(f"  Queue Empty: {validation['queue_empty']}")
    print(f"  Total Storage Attempts: {validation['total_storage_attempts']}")
    print(f"  Storage Attempts by Type:")
    for key, count in validation['storage_attempts_by_type'].items():
        print(f"    {key}: {count}")
    
    return validation['validation_passed']

def main():
    """Main validation function"""
    print("="*70)
    print("DATABASE STORAGE DISABLED - VALIDATION SCRIPT")
    print("="*70)
    
    base_url = 'http://192.168.173.112:8090'
    
    # Initialize PocketBase Manager
    print("\nInitializing PocketBase Manager...")
    try:
        pb_manager = PocketBaseManager(base_url)
        print("[OK] PocketBase Manager initialized")
    except Exception as e:
        print(f"[FAIL] Failed to initialize PocketBase Manager: {e}")
        return False
    
    # Test 1: Direct method calls
    test1_passed = test_storage_methods(pb_manager)
    
    # Test 2: PocketBase collection verification
    initial_counts = test_pocketbase_collections(base_url)
    
    # Test 3: Comprehensive validation
    test3_passed = validate_storage_disabled(pb_manager)
    
    # Final Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    all_passed = test1_passed and test3_passed
    
    print(f"\nTest 1 (Direct Method Calls): {'[PASS]' if test1_passed else '[FAIL]'}")
    print(f"Test 2 (Collection Verification): [INFO] (check counts manually)")
    print(f"Test 3 (Comprehensive Validation): {'[PASS]' if test3_passed else '[FAIL]'}")
    
    if all_passed:
        print("\n" + "="*70)
        print("[PASS] ALL VALIDATION TESTS PASSED")
        print("="*70)
        print("\nDatabase storage is properly disabled:")
        print("  - All store_* methods return immediately")
        print("  - No data is queued for storage")
        print("  - Write queue remains empty")
        print("\nTo verify no data is stored during runtime:")
        print("  1. Note the collection counts above")
        print("  2. Run your trading system for a period")
        print("  3. Re-run this script and compare counts")
        print("  4. Counts should remain the same")
    else:
        print("\n" + "="*70)
        print("[FAIL] VALIDATION FAILED")
        print("="*70)
        print("\nSome validation tests failed. Please review the output above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

