"""Check recent candles for SELL strategy"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.mt5_connector import MT5Connector
from src.config import Config
import MetaTrader5 as mt5

mt5_conn = MT5Connector()
config = Config()
mt5_conn.initialize(config.get('mt5.path', ''), config.get('mt5.login', 0), 
                    config.get('mt5.password', ''), config.get('mt5.server', ''))

rates = mt5_conn.get_rates('XAUUSDm', mt5.TIMEFRAME_M1, 50)
print('\nLast 10 candles for XAUUSDm M1:')
print('='*80)
for i, r in enumerate(rates[-10:], len(rates)-10):
    print(f"Bar {i}: Time={r['time']}, O={r['open']:.2f}, H={r['high']:.2f}, L={r['low']:.2f}, C={r['close']:.2f}")

mt5_conn.shutdown()
