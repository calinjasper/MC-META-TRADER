"""
Check BUYEU Strategy Trades
Analyze why BUYEU strategy entered and exited trades
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
from src.config import Config
from src.strategy.strategy_persistence import StrategyPersistence


def check_buyeu_trades():
    """Check BUYEU strategy trades and exit reasons"""
    print("=" * 70)
    print("  BUYEU Strategy Trade Analysis")
    print("=" * 70)
    print()
    
    # Load config
    config = Config()
    mt5_config = config.get('mt5', {})
    
    # Initialize MT5
    print("Initializing MT5...")
    if not mt5.initialize(
        path=mt5_config.get('path', ''),
        login=mt5_config.get('login', 0),
        password=mt5_config.get('password', ''),
        server=mt5_config.get('server', ''),
        timeout=mt5_config.get('timeout', 10000)
    ):
        error = mt5.last_error()
        print(f"[ERROR] MT5 initialization failed: {error}")
        return
    
    print("[OK] MT5 connected")
    print()
    
    # Get all positions
    all_positions = mt5.positions_get()
    if all_positions is None:
        all_positions = []
    
    # Get historical deals for BUYEU strategy
    print("Checking for BUYEU strategy trades...")
    print()
    
    # Check open positions
    buyeu_open_positions = []
    for pos in all_positions:
        comment = pos.comment if hasattr(pos, 'comment') else ''
        if 'BUYEU' in comment or 'Strategy: BUYEU' in comment:
            buyeu_open_positions.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'BUY' if pos.type == 0 else 'SELL',
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'comment': comment
            })
    
    if buyeu_open_positions:
        print(f"Open BUYEU Positions: {len(buyeu_open_positions)}")
        for pos in buyeu_open_positions:
            print(f"  Ticket: {pos['ticket']}, Symbol: {pos['symbol']}, Type: {pos['type']}")
            print(f"    Entry: {pos['price_open']:.5f}, Current: {pos['price_current']:.5f}")
            print(f"    SL: {pos['sl']:.5f}, TP: {pos['tp']:.5f}, Profit: {pos['profit']:.2f}")
        print()
    else:
        print("No open BUYEU positions found")
        print()
    
    # Get historical deals (closed positions)
    print("Checking historical deals for BUYEU strategy...")
    date_from = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    date_to = datetime.now()
    
    all_deals = mt5.history_deals_get(date_from, date_to)
    if all_deals is None:
        all_deals = []
    
    buyeu_deals = []
    for deal in all_deals:
        comment = deal.comment if hasattr(deal, 'comment') else ''
        if 'BUYEU' in comment or 'Strategy: BUYEU' in comment:
            buyeu_deals.append({
                'ticket': deal.ticket,
                'position_id': deal.position_id,
                'symbol': deal.symbol,
                'type': 'BUY' if deal.type == 0 else 'SELL',
                'entry': deal.entry,
                'volume': deal.volume,
                'price': deal.price,
                'profit': deal.profit,
                'time': datetime.fromtimestamp(deal.time),
                'comment': comment
            })
    
    if buyeu_deals:
        print(f"Found {len(buyeu_deals)} BUYEU deals")
        print()
        
        # Group by position_id to see entry/exit pairs
        positions = {}
        for deal in buyeu_deals:
            pos_id = deal['position_id']
            if pos_id not in positions:
                positions[pos_id] = {'entry': None, 'exit': None}
            
            if deal['entry'] == 0:  # Entry deal
                positions[pos_id]['entry'] = deal
            elif deal['entry'] == 1:  # Exit deal
                positions[pos_id]['exit'] = deal
        
        print("=" * 70)
        print("BUYEU Trade History:")
        print("=" * 70)
        print()
        
        for pos_id, trades in positions.items():
            entry = trades['entry']
            exit_deal = trades['exit']
            
            if entry:
                print(f"Position ID: {pos_id}")
                print(f"  Entry:")
                print(f"    Time: {entry['time']}")
                print(f"    Type: {entry['type']}")
                print(f"    Symbol: {entry['symbol']}")
                print(f"    Volume: {entry['volume']}")
                print(f"    Price: {entry['price']:.5f}")
                print(f"    Comment: {entry['comment']}")
                
                if exit_deal:
                    print(f"  Exit:")
                    print(f"    Time: {exit_deal['time']}")
                    print(f"    Price: {exit_deal['price']:.5f}")
                    print(f"    Profit: {exit_deal['profit']:.2f}")
                    print(f"    Comment: {exit_deal['comment']}")
                    
                    # Try to determine exit reason from comment
                    exit_comment = exit_deal['comment'].upper()
                    if 'SL' in exit_comment or 'STOP' in exit_comment:
                        exit_reason = "Stop Loss"
                    elif 'TP' in exit_comment or 'TAKE' in exit_comment or 'PROFIT' in exit_comment:
                        exit_reason = "Take Profit"
                    elif 'MANUAL' in exit_comment or 'CLOSE' in exit_comment:
                        exit_reason = "Manual Close"
                    else:
                        exit_reason = "Unknown (check MT5 deal history)"
                    
                    print(f"    Exit Reason: {exit_reason}")
                    
                    # Calculate duration
                    duration = exit_deal['time'] - entry['time']
                    print(f"    Duration: {duration}")
                    
                    # Calculate P&L
                    pnl_pips = (exit_deal['price'] - entry['price']) if entry['type'] == 'BUY' else (entry['price'] - exit_deal['price'])
                    print(f"    Price Movement: {pnl_pips:.5f} points")
                else:
                    print(f"  Exit: Still open or exit deal not found")
                    # Check if position is actually still open
                    current_pos = mt5.positions_get(ticket=pos_id)
                    if current_pos and len(current_pos) > 0:
                        pos = current_pos[0]
                        print(f"    [STATUS] Position is still OPEN")
                        print(f"    Current Price: {pos.price_current:.5f}")
                        print(f"    Current Profit: {pos.profit:.2f}")
                        print(f"    SL: {pos.sl:.5f}, TP: {pos.tp:.5f}")
                    else:
                        # Check all deals for this position_id to find exit
                        all_pos_deals = mt5.history_deals_get(date_from, date_to, group=f"*{entry['symbol']}*")
                        if all_pos_deals:
                            exit_deals = [d for d in all_pos_deals if d.position_id == pos_id and d.entry == 1]
                            if exit_deals:
                                exit_deal_found = exit_deals[0]
                                exit_deal = {
                                    'time': datetime.fromtimestamp(exit_deal_found.time),
                                    'price': exit_deal_found.price,
                                    'profit': exit_deal_found.profit,
                                    'comment': exit_deal_found.comment
                                }
                                trades['exit'] = exit_deal  # Update the dictionary
                                print(f"    [FOUND] Exit deal found:")
                                print(f"      Time: {exit_deal['time']}")
                                print(f"      Price: {exit_deal['price']:.5f}")
                                print(f"      Profit: {exit_deal['profit']:.2f}")
                                print(f"      Comment: {exit_deal['comment']}")
                            else:
                                print(f"    [WARNING] No exit deal found in MT5 history")
                                print(f"    Position may have been closed outside the system or manually")
                
                print()
    
    # Analyze exit reasons
    print("=" * 70)
    print("Exit Reason Analysis:")
    print("=" * 70)
    print()
    
    for pos_id, trades in positions.items():
        entry = trades['entry']
        exit_deal = trades['exit']
        
        if entry and exit_deal:
            entry_price = entry['price']
            exit_price = exit_deal['price']
            profit = exit_deal['profit']
            exit_comment = exit_deal['comment']
            
            print(f"Position {pos_id}:")
            print(f"  Entry: {entry_price:.5f} at {entry['time']}")
            print(f"  Exit: {exit_price:.5f} at {exit_deal['time']}")
            print(f"  Profit: {profit:.2f}")
            print(f"  Exit Comment: {exit_comment}")
            
            # Determine exit reason
            exit_comment_upper = exit_comment.upper()
            if 'SL' in exit_comment_upper or 'STOP' in exit_comment_upper:
                exit_reason = "Stop Loss (SL)"
                print(f"  Exit Reason: {exit_reason}")
                print(f"  Why: Price hit the stop loss level")
            elif 'TP' in exit_comment_upper or 'TAKE' in exit_comment_upper or 'PROFIT' in exit_comment_upper:
                exit_reason = "Take Profit (TP)"
                print(f"  Exit Reason: {exit_reason}")
                print(f"  Why: Price reached the take profit level")
            elif 'CLOSE' in exit_comment_upper or 'MANUAL' in exit_comment_upper:
                exit_reason = "Manual Close"
                print(f"  Exit Reason: {exit_reason}")
                print(f"  Why: Position was closed manually (either by user or system)")
                print(f"  Note: 'Close position' comment usually indicates manual/system close")
                
                # Check if it might have been closed by system due to SL/TP
                # by checking if price moved in a way that would trigger SL/TP
                if entry['type'] == 'BUY':
                    price_change = exit_price - entry_price
                    if profit < 0:
                        print(f"  Analysis: Trade closed at a loss ({profit:.2f})")
                        print(f"  Price dropped from {entry_price:.5f} to {exit_price:.5f} ({price_change:.5f} points)")
                        print(f"  Possible reasons:")
                        print(f"    - Manual close to limit loss")
                        print(f"    - Stop loss was hit (check if SL was set)")
                        print(f"    - System closed due to risk management")
                    else:
                        print(f"  Analysis: Trade closed at a profit ({profit:.2f})")
                        print(f"  Price rose from {entry_price:.5f} to {exit_price:.5f} ({price_change:.5f} points)")
                        print(f"  Possible reasons:")
                        print(f"    - Manual close to lock profit")
                        print(f"    - Take profit was hit (check if TP was set)")
                        print(f"    - System closed due to profit target")
            else:
                exit_reason = "Unknown"
                print(f"  Exit Reason: {exit_reason}")
                print(f"  Comment: {exit_comment}")
            
            print()
    else:
        print("No BUYEU deals found in history")
        print()
    
    # Try to load BUYEU strategy if it exists
    strategy_file = project_root / "strategies" / "BUYEU.json"
    if strategy_file.exists():
        print("=" * 70)
        print("BUYEU Strategy Configuration:")
        print("=" * 70)
        print()
        
        with open(buyeu_strategy_file, 'r') as f:
            strategy_data = json.load(f)
        
        print(f"Strategy: {strategy_data.get('name', 'N/A')}")
        print(f"Symbol: {strategy_data.get('symbol', 'N/A')}")
        print(f"Timeframe: {strategy_data.get('timeframe', 'N/A')} minutes")
        print(f"Trade Direction: {strategy_data.get('trade_direction', 'N/A')}")
        print(f"SL Type: {strategy_data.get('sl_type', 'N/A')}")
        print(f"SL Value: {strategy_data.get('sl_value', 'N/A')}")
        print(f"SL Enabled: {strategy_data.get('sl_enabled', 'N/A')}")
        print(f"TP Value: {strategy_data.get('tp_value', 'N/A')}")
        print(f"TP Enabled: {strategy_data.get('tp_enabled', 'N/A')}")
        print(f"Trade Monitoring Mode: {strategy_data.get('trade_monitoring_mode', 'N/A')}")
        print()
        
        # Show entry conditions
        buy_filters = strategy_data.get('buy_filters', [])
        if buy_filters:
            print("Entry Conditions:")
            for i, filt in enumerate(buy_filters, 1):
                if filt.get('enabled', True):
                    left = filt.get('left_operand', '')
                    op = filt.get('operator', '')
                    right = filt.get('right_operand', '')
                    print(f"  {i}. {left} {op} {right}")
            print()
    else:
        print("BUYEU strategy file not found")
        print("Checking if strategy exists with different name...")
        print()
    
    mt5.shutdown()
    print()


if __name__ == "__main__":
    check_buyeu_trades()
