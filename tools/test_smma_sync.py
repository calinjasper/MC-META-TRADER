"""
Test script to verify SMMA strategy sync with MT5 indicator
Compares Python strategy signals with MT5 indicator arrows
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.mt5_connector import MT5Connector
from src.strategy.smma_strategy import SMMAStrategy
import MetaTrader5 as mt5

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_mt5_indicator_values(symbol: str, timeframe: int, length: int = 7, count: int = 100) -> List[Dict]:
    """
    Get SMMA indicator values from MT5
    Note: This requires the indicator to be compiled and available in MT5
    """
    try:
        # Get rates
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None or len(rates) == 0:
            logger.warning(f"Failed to get rates for {symbol}")
            return []
        
        # Note: To get actual indicator buffer values, we'd need to use iCustom()
        # For now, we'll simulate by calculating SMMA ourselves
        # In a real test, you'd use: iCustom(symbol, timeframe, "SMMA_Indicator", length, ...)
        
        logger.info(f"Retrieved {len(rates)} rates for {symbol}")
        return rates.tolist() if hasattr(rates, 'tolist') else list(rates)
    except Exception as e:
        logger.error(f"Error getting MT5 indicator values: {e}")
        return []


def test_strategy_sync(symbol: str, timeframe: int, length: int = 7, test_candles: int = 50):
    """
    Test SMMA strategy sync with MT5 indicator
    
    Args:
        symbol: Trading symbol (e.g., "XAUUSDm")
        timeframe: MT5 timeframe (e.g., mt5.TIMEFRAME_M15)
        length: SMMA period
        test_candles: Number of recent candles to test
    """
    logger.info("=" * 80)
    logger.info(f"Testing SMMA Strategy Sync")
    logger.info(f"Symbol: {symbol}, Timeframe: {timeframe}, Length: {length}")
    logger.info("=" * 80)
    
    # Connect to MT5
    mt5_connector = MT5Connector()
    if not mt5_connector.initialize():
        logger.error("Failed to connect to MT5")
        return False
    
    try:
        # Create strategy
        strategy = SMMAStrategy(
            name=f"TEST_{symbol}",
            symbol=symbol,
            timeframe=timeframe,
            length=length,
            source_price="close"
        )
        strategy.set_mt5_connector(mt5_connector)
        
        # Get recent candles
        candles = strategy._get_candles(count=test_candles + 50)  # Get extra for SMMA calculation
        if not candles or len(candles) < length + 1:
            logger.error(f"Not enough candles: {len(candles) if candles else 0}")
            return False
        
        logger.info(f"Retrieved {len(candles)} candles")
        
        # Get SMMA values
        smma_values = strategy._compute_smma_values(candles)
        if not smma_values or len(smma_values) < 2:
            logger.error("Failed to compute SMMA values")
            return False
        
        # Test signal generation for recent candles
        signals_detected = []
        test_range = min(test_candles, len(candles) - length - 1)
        
        logger.info(f"\nTesting {test_range} recent candles...")
        logger.info("-" * 80)
        
        for i in range(len(candles) - test_range, len(candles)):
            if i < length or i >= len(smma_values):
                continue
            
            candle = candles[i]
            prev_candle = candles[i - 1] if i > 0 else candle
            
            current_close = float(candle["close"])
            prev_close = float(prev_candle["close"])
            current_high = float(candle["high"])
            current_low = float(candle["low"])
            
            current_smma = smma_values[i]
            prev_smma = smma_values[i - 1] if i > 0 else current_smma
            
            if current_smma is None or prev_smma is None:
                continue
            
            # Create market data for strategy
            market_data = {
                "tick": {
                    "bid": current_close,
                    "ask": current_close,
                    "time": candle.get("time")
                },
                "close": current_close,
                "high": current_high,
                "low": current_low,
                "open": float(candle["open"])
            }
            
            # Get signal from strategy
            signal = strategy.generate_signal(market_data)
            
            # Detect crossover/crossunder
            signal_candle = strategy._is_crossover(current_close, prev_close, current_smma, prev_smma)
            sig_candle = strategy._is_crossunder(current_close, prev_close, current_smma, prev_smma)
            
            # Log state
            candle_time = candle.get("time", "N/A")
            state_info = (
                f"Candle {i}: Time={candle_time}, Close={current_close:.5f}, "
                f"SMMA={current_smma:.5f}, "
                f"High={strategy.high:.5f if strategy.high > 0 else 0}, "
                f"Low_s={strategy.low_s:.5f if strategy.low_s > 0 else 0}, "
                f"valid_buy={strategy.valid_buy}, valid_sell={strategy.valid_sell}, "
                f"f1={strategy.f1}, f2={strategy.f2}"
            )
            
            if signal_candle:
                logger.info(f"{state_info} | CROSSOVER detected")
            if sig_candle:
                logger.info(f"{state_info} | CROSSUNDER detected")
            if signal:
                logger.info(f"{state_info} | SIGNAL: {signal}")
                signals_detected.append({
                    "candle": i,
                    "time": candle_time,
                    "signal": signal,
                    "price": current_close,
                    "high": strategy.high if signal == "BUY" else 0,
                    "low_s": strategy.low_s if signal == "SELL" else 0
                })
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total candles tested: {test_range}")
        logger.info(f"Signals detected: {len(signals_detected)}")
        
        if signals_detected:
            logger.info("\nDetected Signals:")
            for sig in signals_detected:
                logger.info(
                    f"  {sig['signal']} at candle {sig['candle']} "
                    f"(Time: {sig['time']}, Price: {sig['price']:.5f})"
                )
        else:
            logger.info("No signals detected in test range")
        
        # Strategy state summary
        logger.info("\nFinal Strategy State:")
        logger.info(f"  valid_buy: {strategy.valid_buy}")
        logger.info(f"  valid_sell: {strategy.valid_sell}")
        logger.info(f"  f1 (buy entered): {strategy.f1}")
        logger.info(f"  f2 (sell entered): {strategy.f2}")
        logger.info(f"  High: {strategy.high:.5f if strategy.high > 0 else 0}")
        logger.info(f"  Low: {strategy.low:.5f if strategy.low > 0 else 0}")
        logger.info(f"  High_s: {strategy.high_s:.5f if strategy.high_s > 0 else 0}")
        logger.info(f"  Low_s: {strategy.low_s:.5f if strategy.low_s > 0 else 0}")
        logger.info(f"  entry_high: {strategy.entry_high:.5f if strategy.entry_high > 0 else 0}")
        logger.info(f"  entry_low: {strategy.entry_low:.5f if strategy.entry_low > 0 else 0}")
        logger.info(f"  entry_high_s: {strategy.entry_high_s:.5f if strategy.entry_high_s > 0 else 0}")
        logger.info(f"  entry_low_s: {strategy.entry_low_s:.5f if strategy.entry_low_s > 0 else 0}")
        
        logger.info("\n" + "=" * 80)
        logger.info("SYNC VERIFICATION INSTRUCTIONS:")
        logger.info("=" * 80)
        logger.info("1. Open MT5 and add SMMA_Indicator to the chart")
        logger.info(f"2. Set symbol: {symbol}, timeframe: {timeframe}")
        logger.info(f"3. Set Length: {length}")
        logger.info("4. Compare the buy/sell entry arrows in MT5 with the signals above")
        logger.info("5. Verify that:")
        logger.info("   - Every MT5 buy entry arrow has a corresponding BUY signal")
        logger.info("   - Every MT5 sell entry arrow has a corresponding SELL signal")
        logger.info("   - No false signals (Python signals without MT5 arrows)")
        logger.info("   - No missed signals (MT5 arrows without Python signals)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        return False
    finally:
        mt5_connector.shutdown()


def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test SMMA strategy sync with MT5")
    parser.add_argument("--symbol", default="XAUUSDm", help="Trading symbol (default: XAUUSDm)")
    parser.add_argument("--timeframe", type=int, default=mt5.TIMEFRAME_M15, help="MT5 timeframe (default: M15)")
    parser.add_argument("--length", type=int, default=7, help="SMMA period (default: 7)")
    parser.add_argument("--candles", type=int, default=50, help="Number of candles to test (default: 50)")
    
    args = parser.parse_args()
    
    success = test_strategy_sync(
        symbol=args.symbol,
        timeframe=args.timeframe,
        length=args.length,
        test_candles=args.candles
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
