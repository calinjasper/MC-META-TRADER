"""
Check XABUY Strategy Status
Diagnoses why the SMMA strategy is not taking trades
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from src.mt5_connector import MT5Connector
from src.strategy.strategy_persistence import StrategyPersistence
from src.config import Config
import MetaTrader5 as mt5

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_xabuy():
    """Check XABUY strategy status"""
    print(f"\n{'='*80}")
    print("XABUY Strategy Diagnostic")
    print(f"{'='*80}\n")
    
    # Initialize MT5
    mt5_conn = MT5Connector()
    config = Config()
    mt5_path = config.get('mt5.path', '')
    mt5_login = config.get('mt5.login', 0)
    mt5_password = config.get('mt5.password', '')
    mt5_server = config.get('mt5.server', '')
    
    if not mt5_conn.initialize(mt5_path, mt5_login, mt5_password, mt5_server):
        print("[ERROR] MT5 not connected")
        return
    
    if not mt5_conn.is_connected():
        print("[ERROR] MT5 initialization failed")
        return
    
    print("[OK] MT5 connected\n")
    
    # Load strategy
    persistence = StrategyPersistence()
    strategy = persistence.load_strategy("strategies/XABUY.json")
    
    if not strategy:
        print("[ERROR] Could not load XABUY strategy")
        mt5_conn.shutdown()
        return
    
    strategy.set_mt5_connector(mt5_conn)
    
    print(f"Strategy: {strategy.name}")
    print(f"Type: SMMA Strategy")
    print(f"Symbol: {strategy.symbol}")
    print(f"Timeframe: M{strategy.timeframe}")
    print(f"Enabled: {strategy.enabled}")
    print(f"SMMA Length: {strategy.length}")
    print(f"Source Price: {strategy.source_price}")
    print(f"Trade Direction: {strategy.trade_direction}")
    print()
    
    # Get current market data
    tick = mt5_conn.get_tick(strategy.symbol)
    if not tick:
        print(f"[ERROR] Could not get tick data for {strategy.symbol}")
        mt5_conn.shutdown()
        return
    
    current_price = (tick.get('bid', 0) + tick.get('ask', 0)) / 2.0
    if current_price == 0:
        current_price = tick.get('bid', tick.get('ask', 0))
    
    print(f"Current Price (LTP): {current_price:.2f}")
    print(f"Bid: {tick.get('bid', 0):.2f}, Ask: {tick.get('ask', 0):.2f}")
    print()
    
    # Get candles
    timeframe_map = {
        1: mt5.TIMEFRAME_M1,
        5: mt5.TIMEFRAME_M5,
        15: mt5.TIMEFRAME_M15,
        30: mt5.TIMEFRAME_M30,
        60: mt5.TIMEFRAME_H1,
        240: mt5.TIMEFRAME_H4,
        1440: mt5.TIMEFRAME_D1
    }
    mt5_timeframe = timeframe_map.get(strategy.timeframe, mt5.TIMEFRAME_M1)
    
    rates = mt5_conn.get_rates(strategy.symbol, mt5_timeframe, 300)
    if not rates:
        print(f"[ERROR] Could not get rates for {strategy.symbol}")
        mt5_conn.shutdown()
        return
    
    print(f"Loaded {len(rates)} candles")
    print(f"Last candle: O={rates[-1]['open']:.2f}, H={rates[-1]['high']:.2f}, L={rates[-1]['low']:.2f}, C={rates[-1]['close']:.2f}")
    print()
    
    # Create market data
    market_data = {
        'tick': tick,
        'current_price': current_price,
        'rates': rates
    }
    
    # Generate signal to update state
    signal = strategy.generate_signal(market_data)
    
    print(f"{'='*80}")
    print("SMMA Strategy State:")
    print(f"{'='*80}")
    print(f"High (Buy Signal Candle): {strategy.High:.2f}")
    print(f"Low (Buy Signal Candle): {strategy.Low:.2f}")
    print(f"High_s (Sell Signal Candle): {strategy.High_s:.2f}")
    print(f"Low_s (Sell Signal Candle): {strategy.Low_s:.2f}")
    print(f"valid_buy: {strategy.valid_buy}")
    print(f"valid_sell: {strategy.valid_sell}")
    print(f"f1 (Buy Entry Triggered): {strategy.f1}")
    print(f"f2 (Sell Entry Triggered): {strategy.f2}")
    print(f"entry_high: {strategy.entry_high:.2f}")
    print(f"entry_low: {strategy.entry_low:.2f}")
    print(f"entry_high_s: {strategy.entry_high_s:.2f}")
    print(f"entry_low_s: {strategy.entry_low_s:.2f}")
    print()
    
    # Calculate SMMA for display
    if hasattr(strategy, '_calculate_smma'):
        smma_values = strategy._calculate_smma(rates)
        if smma_values:
            print(f"Current SMMA: {smma_values[-1]:.2f}")
            print(f"Previous SMMA: {smma_values[-2] if len(smma_values) > 1 else 'N/A':.2f}")
            print()
    
    # Check entry conditions
    print(f"{'='*80}")
    print("Entry Conditions:")
    print(f"{'='*80}")
    
    if strategy.trade_direction in ("both", "long"):
        if strategy.High > 0.0:
            print(f"BUY Entry Condition: Price crosses above High={strategy.High:.2f}")
            print(f"  Current Price: {current_price:.2f}")
            print(f"  High Level: {strategy.High:.2f}")
            if current_price > strategy.High:
                print(f"  [STATUS] Price is ABOVE High - waiting for cross (price was below, now above)")
            elif current_price < strategy.High:
                distance = strategy.High - current_price
                print(f"  [STATUS] Price is BELOW High - waiting for price to rise {distance:.2f} points")
            else:
                print(f"  [STATUS] Price is AT High level")
        else:
            print(f"BUY Entry Condition: No buy signal candle detected yet (High=0.0)")
            print(f"  Waiting for: Close price to cross ABOVE SMMA")
    else:
        print(f"BUY Entry: Disabled (trade_direction={strategy.trade_direction})")
    
    print()
    
    if strategy.trade_direction in ("both", "short"):
        if strategy.Low_s > 0.0:
            print(f"SELL Entry Condition: Price crosses below Low_s={strategy.Low_s:.2f}")
            print(f"  Current Price: {current_price:.2f}")
            print(f"  Low_s Level: {strategy.Low_s:.2f}")
            if current_price < strategy.Low_s:
                print(f"  [STATUS] Price is BELOW Low_s - waiting for cross (price was above, now below)")
            elif current_price > strategy.Low_s:
                distance = current_price - strategy.Low_s
                print(f"  [STATUS] Price is ABOVE Low_s - waiting for price to drop {distance:.2f} points")
            else:
                print(f"  [STATUS] Price is AT Low_s level")
        else:
            print(f"SELL Entry Condition: No sell signal candle detected yet (Low_s=0.0)")
            print(f"  Waiting for: Close price to cross BELOW SMMA")
    else:
        print(f"SELL Entry: Disabled (trade_direction={strategy.trade_direction})")
    
    print()
    
    print(f"{'='*80}")
    print("Signal Status:")
    print(f"{'='*80}")
    print(f"Generated Signal: {signal}")
    print()
    
    if signal is None:
        print("Reason: Entry conditions not met")
        if strategy.trade_direction in ("both", "long"):
            if strategy.High == 0.0:
                print("  - No buy signal candle detected yet (waiting for close to cross above SMMA)")
            elif strategy.High > 0.0:
                if current_price < strategy.High:
                    print(f"  - Price ({current_price:.2f}) is below High ({strategy.High:.2f}) - waiting for cross")
                elif current_price > strategy.High:
                    print(f"  - Price ({current_price:.2f}) is above High ({strategy.High:.2f}) but cross not detected yet")
                    print(f"  - Previous price tracking may need reset")
    
    print(f"{'='*80}\n")
    
    mt5_conn.shutdown()


if __name__ == "__main__":
    check_xabuy()
