"""
List SMMA Strategies Waiting for Entry
Shows all SMMA strategies that have signal candles detected and are waiting for entry conditions.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from src.mt5_connector import MT5Connector
from src.strategy.strategy_persistence import StrategyPersistence
from src.config import Config
from src.data_feed import DataFeed

logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def list_waiting_entries():
    """List all SMMA strategies waiting for entry"""
    print(f"\n{'='*80}")
    print("SMMA Strategies Waiting for Entry")
    print(f"{'='*80}\n")
    
    # Initialize MT5
    mt5 = MT5Connector()
    config = Config()
    mt5_path = config.get('mt5.path', '')
    mt5_login = config.get('mt5.login', 0)
    mt5_password = config.get('mt5.password', '')
    mt5_server = config.get('mt5.server', '')
    
    if not mt5.initialize(mt5_path, mt5_login, mt5_password, mt5_server):
        print("[ERROR] MT5 not connected")
        return
    
    if not mt5.is_connected():
        print("[ERROR] MT5 initialization failed")
        return
    
    print("[OK] MT5 connected\n")
    
    # Initialize data feed
    data_feed = DataFeed(mt5, update_interval=0.1)
    data_feed.start()
    
    # Load all strategies
    persistence = StrategyPersistence()
    all_strategies = persistence.load_all_strategies()
    
    # Filter SMMA strategies
    # SMMA strategy has been removed - filter removed
    smma_strategies = []
    
    if not smma_strategies:
        print("No SMMA strategies found.")
        mt5.shutdown()
        return
    
    print(f"Found {len(smma_strategies)} SMMA strategy(ies):\n")
    
    waiting_strategies = []
    
    for strategy in smma_strategies:
        strategy_name = strategy.name
        symbol = strategy.symbol
        
        # Set MT5 connector
        if hasattr(strategy, 'set_mt5_connector'):
            strategy.set_mt5_connector(mt5)
        
        # Get current market data
        data_feed.add_symbol(symbol)
        tick = data_feed.get_latest_tick(symbol)
        
        if not tick:
            print(f"[SKIP] {strategy_name}: No tick data for {symbol}")
            continue
        
        # Get current price
        current_price = (tick.get('bid', 0) + tick.get('ask', 0)) / 2.0
        if current_price == 0:
            current_price = tick.get('bid', tick.get('ask', 0))
        
        # Create market data
        import MetaTrader5 as mt5_module
        rates = mt5.get_rates(symbol, strategy.timeframe if hasattr(strategy, 'timeframe') else mt5_module.TIMEFRAME_M1, 300)
        
        market_data = {
            'tick': tick,
            'current_price': current_price,
            'rates': rates
        }
        
        # Generate signal to update state
        signal = strategy.generate_signal(market_data)
        
        # Check strategy state
        valid_buy = getattr(strategy, 'valid_buy', False)
        valid_sell = getattr(strategy, 'valid_sell', False)
        High = getattr(strategy, 'High', 0.0)
        Low = getattr(strategy, 'Low', 0.0)
        High_s = getattr(strategy, 'High_s', 0.0)
        Low_s = getattr(strategy, 'Low_s', 0.0)
        f1 = getattr(strategy, 'f1', False)
        f2 = getattr(strategy, 'f2', False)
        trade_direction = getattr(strategy, 'trade_direction', 'both')
        
        # Determine waiting status
        waiting_for_buy = False
        waiting_for_sell = False
        buy_status = ""
        sell_status = ""
        has_signal_candle = False
        
        if trade_direction in ("both", "long") and High > 0.0:
            has_signal_candle = True
            if not f1:
                waiting_for_buy = True
                if current_price > High:
                    buy_status = f"Price above High ({current_price:.5f} > {High:.5f}) - waiting for cross"
                elif current_price <= High:
                    buy_status = f"Price below High ({current_price:.5f} <= {High:.5f}) - waiting for price to rise"
            else:
                buy_status = f"Entry already triggered (f1=True)"
        
        if trade_direction in ("both", "short") and Low_s > 0.0:
            has_signal_candle = True
            if not f2:
                waiting_for_sell = True
                if current_price < Low_s:
                    sell_status = f"Price below Low_s ({current_price:.5f} < {Low_s:.5f}) - waiting for cross"
                elif current_price >= Low_s:
                    sell_status = f"Price above Low_s ({current_price:.5f} >= {Low_s:.5f}) - waiting for price to drop"
            else:
                sell_status = f"Entry already triggered (f2=True)"
        
        if has_signal_candle:
            waiting_strategies.append({
                'name': strategy_name,
                'symbol': symbol,
                'direction': trade_direction,
                'enabled': getattr(strategy, 'enabled', False),
                'waiting_for_buy': waiting_for_buy,
                'waiting_for_sell': waiting_for_sell,
                'buy_status': buy_status,
                'sell_status': sell_status,
                'High': High,
                'Low': Low,
                'High_s': High_s,
                'Low_s': Low_s,
                'current_price': current_price,
                'f1': f1,
                'f2': f2,
                'valid_buy': valid_buy,
                'valid_sell': valid_sell,
                'signal': signal
            })
    
    # Print results
    if waiting_strategies:
        waiting_list = [s for s in waiting_strategies if s['waiting_for_buy'] or s['waiting_for_sell']]
        triggered_list = [s for s in waiting_strategies if not (s['waiting_for_buy'] or s['waiting_for_sell'])]
        
        print(f"Found {len(waiting_strategies)} SMMA strategy(ies) with signal candles:\n")
        
        if waiting_list:
            print(f"[WAITING FOR ENTRY] {len(waiting_list)} strategy(ies):\n")
            for i, strat in enumerate(waiting_list, 1):
                print(f"{i}. {strat['name']} ({strat['symbol']})")
                print(f"   Direction: {strat['direction']}, Enabled: {strat['enabled']}")
                print(f"   Current Price: {strat['current_price']:.5f}")
                
                if strat['waiting_for_buy']:
                    print(f"   [BUY] Signal Candle:")
                    print(f"      High: {strat['High']:.5f}, Low: {strat['Low']:.5f}")
                    print(f"      valid_buy: {strat['valid_buy']}, f1: {strat['f1']}")
                    print(f"      Status: {strat['buy_status']}")
                    print(f"      Entry Condition: Close crosses above High={strat['High']:.5f}")
                    distance = strat['High'] - strat['current_price']
                    print(f"      Distance: {distance:.5f} points ({'above' if distance < 0 else 'below'} level)")
                
                if strat['waiting_for_sell']:
                    print(f"   [SELL] Signal Candle:")
                    print(f"      High_s: {strat['High_s']:.5f}, Low_s: {strat['Low_s']:.5f}")
                    print(f"      valid_sell: {strat['valid_sell']}, f2: {strat['f2']}")
                    print(f"      Status: {strat['sell_status']}")
                    print(f"      Entry Condition: Close crosses below Low_s={strat['Low_s']:.5f}")
                    distance = strat['current_price'] - strat['Low_s']
                    print(f"      Distance: {distance:.5f} points ({'above' if distance > 0 else 'below'} level)")
                
                if strat['signal']:
                    print(f"   [SIGNAL] {strat['signal']}")
                print()
        
        if triggered_list:
            print(f"[ENTRY ALREADY TRIGGERED] {len(triggered_list)} strategy(ies):\n")
            for i, strat in enumerate(triggered_list, 1):
                print(f"{i}. {strat['name']} ({strat['symbol']})")
                print(f"   Direction: {strat['direction']}, Enabled: {strat['enabled']}")
                print(f"   Current Price: {strat['current_price']:.5f}")
                
                if strat['High'] > 0.0 and strat['direction'] in ('both', 'long'):
                    print(f"   [BUY] Signal Candle: High={strat['High']:.5f}, Low={strat['Low']:.5f}")
                    print(f"      f1={strat['f1']}, valid_buy={strat['valid_buy']} - Entry already triggered")
                
                if strat['Low_s'] > 0.0 and strat['direction'] in ('both', 'short'):
                    print(f"   [SELL] Signal Candle: High_s={strat['High_s']:.5f}, Low_s={strat['Low_s']:.5f}")
                    print(f"      f2={strat['f2']}, valid_sell={strat['valid_sell']} - Entry already triggered")
                
                if strat['signal']:
                    print(f"   [SIGNAL] {strat['signal']}")
                print()
    else:
        print("No SMMA strategies with signal candles detected.")
        print("\nThis could mean:")
        print("  - No signal candles have been detected yet (close hasn't crossed SMMA)")
        print("  - Strategies need to wait for signal candle (crossover/crossunder with SMMA)")
        print("  - Check MT5 chart to see if SMMA indicator shows any signal candles")
    
    print(f"{'='*80}\n")
    
    # Cleanup
    data_feed.stop()
    mt5.shutdown()


if __name__ == "__main__":
    list_waiting_entries()
