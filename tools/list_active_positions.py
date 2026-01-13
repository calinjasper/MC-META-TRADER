"""
List Active Open Positions with SL and TP
Shows all currently open positions with their stop loss and take profit levels
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from src.mt5_connector import MT5Connector
from src.config import Config
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def list_active_positions():
    """List all active open positions with SL and TP"""
    print(f"\n{'='*100}")
    print("Active Open Positions - Stop Loss & Take Profit")
    print(f"{'='*100}\n")
    
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
    
    # Get all open positions
    positions = mt5_conn.get_positions()
    
    if not positions:
        print("No open positions found.")
        mt5_conn.shutdown()
        return
    
    print(f"Found {len(positions)} open position(s):\n")
    
    # Header
    print(f"{'Ticket':<12} {'Symbol':<12} {'Type':<6} {'Volume':<10} {'Entry Price':<12} {'Current Price':<14} {'SL':<12} {'TP':<12} {'Profit':<12} {'Strategy':<15}")
    print("-" * 100)
    
    total_profit = 0.0
    
    for pos in positions:
        ticket = pos.get('ticket', 0)
        symbol = pos.get('symbol', 'UNKNOWN')
        pos_type = pos.get('type', 0)  # 0 = BUY, 1 = SELL
        volume = pos.get('volume', 0.0)
        entry_price = pos.get('price_open', 0.0)
        current_price = pos.get('price_current', 0.0)
        sl = pos.get('sl', 0.0)
        tp = pos.get('tp', 0.0)
        profit = pos.get('profit', 0.0)
        comment = pos.get('comment', '')
        
        # Extract strategy name from comment
        strategy_name = "--"
        if comment and 'Strategy:' in comment:
            strategy_name = comment.replace('Strategy:', '').strip()
        elif comment:
            strategy_name = comment
        
        # Format type
        type_str = "BUY" if pos_type == 0 else "SELL"
        
        # Format SL/TP
        sl_str = f"{sl:.5f}" if sl > 0 else "--"
        tp_str = f"{tp:.5f}" if tp > 0 else "--"
        
        # Format profit with color indicator
        profit_str = f"${profit:.2f}"
        if profit >= 0:
            profit_str = f"+{profit_str}"
        
        total_profit += profit
        
        print(f"{ticket:<12} {symbol:<12} {type_str:<6} {volume:<10.2f} {entry_price:<12.5f} {current_price:<14.5f} "
              f"{sl_str:<12} {tp_str:<12} {profit_str:<12} {strategy_name:<15}")
        
        # Get symbol info for pip calculations
        symbol_info = mt5_conn.get_symbol_info(symbol)
        point = symbol_info.get('point', 0.0001) if symbol_info else 0.0001
        digits = symbol_info.get('digits', 5) if symbol_info else 5
        
        # Calculate distance to SL/TP for BUY positions
        if pos_type == 0 and current_price > 0:  # BUY
            if sl > 0:
                sl_distance = entry_price - sl
                pip_size = point * (10 if digits == 5 else 1)
                sl_pips = sl_distance / pip_size if pip_size > 0 else 0
                current_to_sl = current_price - sl
                print(f"  -> SL Distance: {sl_distance:.5f} ({sl_pips:.1f} pips), Current to SL: {current_to_sl:.5f}")
            if tp > 0:
                tp_distance = tp - entry_price
                pip_size = point * (10 if digits == 5 else 1)
                tp_pips = tp_distance / pip_size if pip_size > 0 else 0
                current_to_tp = tp - current_price
                print(f"  -> TP Distance: {tp_distance:.5f} ({tp_pips:.1f} pips), Current to TP: {current_to_tp:.5f}")
        
        # Calculate distance to SL/TP for SELL positions
        elif pos_type == 1 and current_price > 0:  # SELL
            if sl > 0:
                sl_distance = sl - entry_price
                pip_size = point * (10 if digits == 5 else 1)
                sl_pips = sl_distance / pip_size if pip_size > 0 else 0
                current_to_sl = sl - current_price
                print(f"  -> SL Distance: {sl_distance:.5f} ({sl_pips:.1f} pips), Current to SL: {current_to_sl:.5f}")
            if tp > 0:
                tp_distance = entry_price - tp
                pip_size = point * (10 if digits == 5 else 1)
                tp_pips = tp_distance / pip_size if pip_size > 0 else 0
                current_to_tp = current_price - tp
                print(f"  -> TP Distance: {tp_distance:.5f} ({tp_pips:.1f} pips), Current to TP: {current_to_tp:.5f}")
    
    print("-" * 100)
    print(f"{'TOTAL PROFIT:':<60} ${total_profit:.2f}")
    print(f"{'='*100}\n")
    
    mt5_conn.shutdown()


if __name__ == "__main__":
    list_active_positions()
