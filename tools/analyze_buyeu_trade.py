"""
Complete BUYEU Trade Analysis
Analyze why BUYEU strategy entered and exited the trade
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import MetaTrader5 as mt5
from src.config import Config
from src.strategy.strategy_persistence import StrategyPersistence
from src.strategy.smc_utils import extract_ohlc_arrays


def analyze_buyeu_trade():
    """Complete analysis of BUYEU trade entry and exit"""
    print("=" * 70)
    print("  BUYEU Strategy - Complete Trade Analysis")
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
    
    # Find BUYEU strategy file
    strategies_dir = project_root / "strategies"
    buyeu_strategy_file = None
    
    # Try exact match first
    strategy_file = strategies_dir / "BUYEU.json"
    if strategy_file.exists():
        buyeu_strategy_file = strategy_file
    else:
        # Search for any file containing BUYEU
        for file in strategies_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    if data.get('name', '').upper() == 'BUYEU':
                        buyeu_strategy_file = file
                        break
            except:
                continue
    
    if not buyeu_strategy_file or not buyeu_strategy_file.exists():
        print("[WARNING] BUYEU strategy file not found")
        print("Will analyze from trade history only")
        print()
        strategy_data = None
    else:
        with open(buyeu_strategy_file, 'r') as f:
            strategy_data = json.load(f)
        
        print("=" * 70)
        print("BUYEU Strategy Configuration:")
        print("=" * 70)
        print()
        print(f"Strategy: {strategy_data.get('name', 'N/A')}")
        print(f"Symbol: {strategy_data.get('symbol', 'N/A')}")
        print(f"Timeframe: {strategy_data.get('timeframe', 'N/A')} minutes")
        print(f"Trade Direction: {strategy_data.get('trade_direction', 'N/A')}")
        print(f"Strategy Type: {strategy_data.get('strategy_type', 'N/A')}")
        print(f"Trade Monitoring Mode: {strategy_data.get('trade_monitoring_mode', 'N/A')}")
        print()
        
        # Risk management settings
        print("Risk Management Settings:")
        print(f"  SL Type: {strategy_data.get('sl_type', 'N/A')}")
        print(f"  SL Value: {strategy_data.get('sl_value', 'N/A')}")
        print(f"  SL Enabled: {strategy_data.get('sl_enabled', 'N/A')}")
        print(f"  TP Value: {strategy_data.get('tp_value', 'N/A')}")
        print(f"  TP Enabled: {strategy_data.get('tp_enabled', 'N/A')}")
        print(f"  Use Ratio: {strategy_data.get('use_ratio', 'N/A')}")
        print()
        
        # Entry conditions
        if strategy_data.get('strategy_type') == 'smc':
            print(f"SMC Settings:")
            print(f"  Emit On: {strategy_data.get('emit_on', 'NONE')}")
            print(f"  Pivot Settings: Left={strategy_data.get('pivot_left', 2)}, Right={strategy_data.get('pivot_right', 2)}")
            print()
        
        buy_filters = strategy_data.get('buy_filters', [])
        if buy_filters:
            print("Entry Conditions (Buy Filters):")
            for i, filt in enumerate(buy_filters, 1):
                if filt.get('enabled', True):
                    left = filt.get('left_operand', '')
                    op = filt.get('operator', '')
                    right = filt.get('right_operand', '')
                    connector = filt.get('connector', 'AND')
                    print(f"  {i}. {left} {op} {right} ({connector})")
            print()
    
    # Get trade history
    print("=" * 70)
    print("Trade History Analysis:")
    print("=" * 70)
    print()
    
    # Get all deals for BUYEU
    date_from = datetime.now() - timedelta(days=7)
    date_to = datetime.now()
    
    all_deals = mt5.history_deals_get(date_from, date_to)
    if all_deals is None:
        all_deals = []
    
    # First, find all BUYEU entry deals
    buyeu_entry_deals = []
    buyeu_position_ids = set()
    
    for deal in all_deals:
        comment = deal.comment if hasattr(deal, 'comment') else ''
        if 'BUYEU' in comment or 'Strategy: BUYEU' in comment:
            buyeu_entry_deals.append({
                'ticket': deal.ticket,
                'position_id': deal.position_id,
                'symbol': deal.symbol,
                'type': 'BUY' if deal.type == 0 else 'SELL',
                'entry': deal.entry,
                'volume': deal.volume,
                'price': deal.price,
                'profit': deal.profit,
                'time': datetime.fromtimestamp(deal.time),
                'comment': comment,
                'reason': deal.reason if hasattr(deal, 'reason') else -1
            })
            buyeu_position_ids.add(deal.position_id)
    
    # Now find all exit deals for these position IDs (even if comment doesn't contain BUYEU)
    buyeu_deals = buyeu_entry_deals.copy()
    for deal in all_deals:
        if deal.position_id in buyeu_position_ids and deal.entry == 1:  # Exit deal
            comment = deal.comment if hasattr(deal, 'comment') else ''
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
                'comment': comment,
                'reason': deal.reason if hasattr(deal, 'reason') else -1
            })
    
    if not buyeu_deals:
        print("No BUYEU deals found in history")
        mt5.shutdown()
        return
    
    # Group by position_id
    positions = {}
    for deal in buyeu_deals:
        pos_id = deal['position_id']
        if pos_id not in positions:
            positions[pos_id] = {'entry': None, 'exit': None, 'all_deals': []}
        
        positions[pos_id]['all_deals'].append(deal)
        
        if deal['entry'] == 0:  # Entry deal
            positions[pos_id]['entry'] = deal
        elif deal['entry'] == 1:  # Exit deal
            positions[pos_id]['exit'] = deal
    
    # Analyze each position
    for pos_id, trades in positions.items():
        entry = trades['entry']
        exit_deal = trades['exit']
        
        if not entry:
            continue
        
        print(f"Position ID: {pos_id}")
        print("-" * 70)
        
        # ENTRY ANALYSIS
        print("\n[ENTRY ANALYSIS]")
        print(f"Entry Time: {entry['time']}")
        print(f"Entry Price: {entry['price']:.5f}")
        print(f"Symbol: {entry['symbol']}")
        print(f"Type: {entry['type']}")
        print(f"Volume: {entry['volume']}")
        print()
        
        # Analyze why it entered
        if strategy_data and buy_filters:
            symbol = strategy_data.get('symbol', entry['symbol'])
            timeframe = strategy_data.get('timeframe', 15)
            
            # Get candles at entry time
            mt5_timeframe_map = {
                1: mt5.TIMEFRAME_M1, 5: mt5.TIMEFRAME_M5, 15: mt5.TIMEFRAME_M15,
                30: mt5.TIMEFRAME_M30, 60: mt5.TIMEFRAME_H1, 240: mt5.TIMEFRAME_H4, 1440: mt5.TIMEFRAME_D1
            }
            mt5_timeframe = mt5_timeframe_map.get(timeframe, mt5.TIMEFRAME_M15)
            
            # Get candles around entry time
            entry_time_ts = int(entry['time'].timestamp())
            rates = mt5.copy_rates_from(symbol, mt5_timeframe, entry_time_ts - 3600, 100)
            
            if rates is not None and len(rates) > 0:
                # Convert to dict
                rates_dict = []
                for rate in rates:
                    rates_dict.append({
                        'time': rate[0],
                        'open': float(rate[1]),
                        'high': float(rate[2]),
                        'low': float(rate[3]),
                        'close': float(rate[4]),
                    })
                
                # Find the candle that contains entry time
                entry_candle = None
                for i, candle in enumerate(rates_dict):
                    candle_time = datetime.fromtimestamp(candle['time'])
                    if candle_time <= entry['time'] < candle_time + timedelta(minutes=timeframe):
                        entry_candle = candle
                        entry_candle_idx = i
                        break
                
                if entry_candle:
                    print(f"Entry Candle (M{timeframe}):")
                    print(f"  Time: {datetime.fromtimestamp(entry_candle['time'])}")
                    print(f"  OHLC: O={entry_candle['open']:.5f} H={entry_candle['high']:.5f} L={entry_candle['low']:.5f} C={entry_candle['close']:.5f}")
                    
                    # Get previous candle for cross detection
                    if entry_candle_idx > 0:
                        prev_candle = rates_dict[entry_candle_idx - 1]
                        prev_close = prev_candle['close']
                        print(f"  Previous Close: {prev_close:.5f}")
                    
                    # Load strategy and check entry conditions
                    if buyeu_strategy_file:
                        persistence = StrategyPersistence()
                        strategy = persistence.load_strategy(buyeu_strategy_file)
                        
                        if strategy:
                            # Get market data at entry time
                            current_price = entry['price']
                            market_data = {
                                "tick": {"bid": current_price, "ask": current_price, "last": current_price},
                                "rates": rates_dict,
                                "ohlc": {
                                    "open": entry_candle['open'],
                                    "high": entry_candle['high'],
                                    "low": entry_candle['low'],
                                    "close": entry_candle['close'],
                                }
                            }
                            
                            # Update strategy to get SMC data
                            signal = strategy.generate_signal(market_data)
                            
                            # Get SMC prices
                            smc_pivots = market_data.get('smc_pivots', {})
                            choch_price = smc_pivots.get('choch_price') if smc_pivots else (strategy.active_choch_price if hasattr(strategy, 'active_choch_price') else None)
                            pivot_high = smc_pivots.get('pivot_high') if smc_pivots else (strategy.active_pivot_high_price if hasattr(strategy, 'active_pivot_high_price') else None)
                            pivot_low = smc_pivots.get('pivot_low') if smc_pivots else (strategy.active_pivot_low_price if hasattr(strategy, 'active_pivot_low_price') else None)
                            
                            print(f"\nSMC Data at Entry:")
                            if choch_price:
                                print(f"  CHoCH Price: {choch_price:.5f}")
                            if pivot_high:
                                print(f"  Pivot High: {pivot_high:.5f}")
                            if pivot_low:
                                print(f"  Pivot Low: {pivot_low:.5f}")
                            
                            # Evaluate entry conditions
                            print(f"\nEntry Condition Evaluation:")
                            for i, filt in enumerate(buy_filters, 1):
                                if not filt.get('enabled', True):
                                    continue
                                
                                left_op = filt.get('left_operand', '')
                                operator = filt.get('operator', '')
                                right_op = filt.get('right_operand', '')
                                
                                print(f"  Condition {i}: {left_op} {operator} {right_op}")
                                
                                # Get values
                                left_value = current_price if left_op == 'current_price' else None
                                right_value = None
                                if right_op == 'smc_choch_price':
                                    right_value = choch_price
                                elif right_op == 'smc_pivot_high':
                                    right_value = pivot_high
                                elif right_op == 'smc_pivot_low':
                                    right_value = pivot_low
                                
                                if left_value and right_value:
                                    if operator == 'crosses_above':
                                        condition_met = prev_close < right_value <= left_value
                                        print(f"    Check: prev_close ({prev_close:.5f}) < {right_op} ({right_value:.5f}) <= current ({left_value:.5f})")
                                        print(f"    Result: {condition_met} - {'ENTRY TRIGGERED' if condition_met else 'NOT TRIGGERED'}")
                                    elif operator == 'crosses_under':
                                        condition_met = prev_close > right_value >= left_value
                                        print(f"    Check: prev_close ({prev_close:.5f}) > {right_op} ({right_value:.5f}) >= current ({left_value:.5f})")
                                        print(f"    Result: {condition_met} - {'ENTRY TRIGGERED' if condition_met else 'NOT TRIGGERED'}")
        
        # Check if we can get position details from MT5 history
        # Try to find the position that was opened to see SL/TP settings
        print(f"\n[POSITION DETAILS]")
        try:
            # Get position history - check if we can find the position when it was open
            # We'll check the entry deal for any SL/TP information
            entry_deal_obj = None
            for deal in all_deals:
                if deal.position_id == pos_id and deal.entry == 0:
                    entry_deal_obj = deal
                    break
            
            if entry_deal_obj:
                # Check if we can get position info
                # Note: MT5 deals don't directly contain SL/TP, but we can infer from context
                print(f"  Entry Deal Ticket: {entry_deal_obj.ticket}")
                print(f"  Entry Deal Type: {entry_deal_obj.type}")
                print(f"  Entry Deal Volume: {entry_deal_obj.volume}")
        except Exception as e:
            print(f"  [Note] Could not get position details: {e}")
        
        # EXIT ANALYSIS
        print(f"\n[EXIT ANALYSIS]")
        if exit_deal:
            print(f"Exit Time: {exit_deal['time']}")
            print(f"Exit Price: {exit_deal['price']:.5f}")
            print(f"Profit: {exit_deal['profit']:.2f}")
            print(f"Exit Comment: {exit_deal['comment']}")
            print(f"Exit Reason Code: {exit_deal.get('reason', 'N/A')}")
            print()
            
            # Calculate duration
            duration = exit_deal['time'] - entry['time']
            print(f"Trade Duration: {duration}")
            print()
            
            # Determine exit reason
            exit_comment = exit_deal['comment'].upper()
            exit_reason_code = exit_deal.get('reason', -1)
            
            # MT5 reason codes
            reason_codes = {
                3: "Client (manual close)",
                4: "Mobile (manual close)",
                5: "Web (manual close)",
                6: "Expert (EA/script close)",
                7: "SL (Stop Loss)",
                8: "TP (Take Profit)",
                9: "SO (Stop Out - margin call)",
            }
            
            exit_reason = reason_codes.get(exit_reason_code, "Unknown")
            
            print(f"Exit Reason Analysis:")
            print(f"  MT5 Reason Code: {exit_reason_code} = {exit_reason}")
            print(f"  Exit Comment: {exit_deal['comment']}")
            print()
            
            # Try to get SL/TP from trade history or calculate from strategy
            entry_price = entry['price']
            symbol_info = mt5.symbol_info(entry['symbol'])
            point = symbol_info.point if symbol_info else 0.00001
            
            # Check trade history for SL/TP values
            from src.trading.order_manager import OrderManager
            from src.mt5_connector import MT5Connector
            mt5_conn = MT5Connector()
            if mt5_conn.initialize():
                order_mgr = OrderManager(mt5_conn)
                trade = order_mgr.trade_history.get_trade(pos_id) if hasattr(order_mgr, 'trade_history') else None
                
                if trade:
                    sl_from_history = trade.get('sl', 0.0)
                    tp_from_history = trade.get('tp', 0.0)
                    entry_condition = trade.get('entry_condition', '--')
                    
                    print(f"Trade History Data:")
                    print(f"  Entry Condition: {entry_condition}")
                    print(f"  SL from History: {sl_from_history:.5f}" if sl_from_history > 0 else "  SL from History: Not set")
                    print(f"  TP from History: {tp_from_history:.5f}" if tp_from_history > 0 else "  TP from History: Not set")
                    print()
                
                mt5_conn.shutdown()
            
            # Check if SL/TP was set in strategy
            if strategy_data:
                sl_enabled = strategy_data.get('sl_enabled', False)
                tp_enabled = strategy_data.get('tp_enabled', False)
                sl_value = strategy_data.get('sl_value', 0)
                tp_value = strategy_data.get('tp_value', 0)
                sl_type = strategy_data.get('sl_type', '')
                use_ratio = strategy_data.get('use_ratio', False)
                
                print(f"Strategy SL/TP Settings:")
                print(f"  SL Enabled: {sl_enabled}")
                if sl_enabled:
                    print(f"  SL Type: {sl_type}")
                    print(f"  SL Value: {sl_value}")
                print(f"  TP Enabled: {tp_enabled}")
                if tp_enabled:
                    print(f"  TP Value: {tp_value}")
                    print(f"  Use Ratio: {use_ratio}")
                print()
                
                # Calculate expected SL/TP prices
                expected_sl = 0.0
                expected_tp = 0.0
                
                if sl_enabled and sl_type and sl_value > 0:
                    if sl_type == "Price (Points)":
                        if entry['type'] == 'BUY':
                            expected_sl = entry_price - (sl_value * point)
                        else:
                            expected_sl = entry_price + (sl_value * point)
                    elif sl_type == "Price (Pips)":
                        if entry['type'] == 'BUY':
                            expected_sl = entry_price - (sl_value * point * 10)
                        else:
                            expected_sl = entry_price + (sl_value * point * 10)
                    elif sl_type == "Percentage":
                        if entry['type'] == 'BUY':
                            expected_sl = entry_price * (1 - sl_value / 100)
                        else:
                            expected_sl = entry_price * (1 + sl_value / 100)
                
                if tp_enabled and tp_value > 0:
                    if use_ratio and sl_value > 0:
                        # TP = SL * ratio (typically 1:2)
                        ratio = tp_value / sl_value if sl_value > 0 else 2.0
                        if entry['type'] == 'BUY':
                            expected_tp = entry_price + (expected_sl - entry_price) * -ratio if expected_sl > 0 else entry_price + (sl_value * point * ratio)
                        else:
                            expected_tp = entry_price - (entry_price - expected_sl) * ratio if expected_sl > 0 else entry_price - (sl_value * point * ratio)
                    else:
                        if sl_type == "Price (Points)":
                            if entry['type'] == 'BUY':
                                expected_tp = entry_price + (tp_value * point)
                            else:
                                expected_tp = entry_price - (tp_value * point)
                        elif sl_type == "Price (Pips)":
                            if entry['type'] == 'BUY':
                                expected_tp = entry_price + (tp_value * point * 10)
                            else:
                                expected_tp = entry_price - (tp_value * point * 10)
                        elif sl_type == "Percentage":
                            if entry['type'] == 'BUY':
                                expected_tp = entry_price * (1 + tp_value / 100)
                            else:
                                expected_tp = entry_price * (1 - tp_value / 100)
                
                if expected_sl > 0:
                    print(f"  Expected SL Price: {expected_sl:.5f}")
                    print(f"  Actual Exit Price: {exit_deal['price']:.5f}")
                    sl_diff = abs(exit_deal['price'] - expected_sl)
                    if sl_diff < point * 10:  # Within 10 points
                        print(f"  [MATCH] Exit price is close to SL (diff: {sl_diff/point:.1f} points) - Stop Loss likely hit!")
                
                if expected_tp > 0:
                    print(f"  Expected TP Price: {expected_tp:.5f}")
                    print(f"  Actual Exit Price: {exit_deal['price']:.5f}")
                    tp_diff = abs(exit_deal['price'] - expected_tp)
                    if tp_diff < point * 10:  # Within 10 points
                        print(f"  [MATCH] Exit price is close to TP (diff: {tp_diff/point:.1f} points) - Take Profit likely hit!")
                    elif exit_deal['price'] >= expected_tp and entry['type'] == 'BUY':
                        print(f"  [MATCH] Exit price ({exit_deal['price']:.5f}) >= TP ({expected_tp:.5f}) - Take Profit was hit!")
                    elif exit_deal['price'] <= expected_tp and entry['type'] == 'SELL':
                        print(f"  [MATCH] Exit price ({exit_deal['price']:.5f}) <= TP ({expected_tp:.5f}) - Take Profit was hit!")
            
            # Price movement analysis
            symbol_info = mt5.symbol_info(entry['symbol'])
            point = symbol_info.point if symbol_info else 0.00001
            
            price_change = exit_deal['price'] - entry['price'] if entry['type'] == 'BUY' else entry['price'] - exit_deal['price']
            print(f"\nPrice Movement:")
            print(f"  Entry: {entry['price']:.5f}")
            print(f"  Exit: {exit_deal['price']:.5f}")
            print(f"  Change: {price_change:.5f} points ({price_change/point:.1f} pips)")
            print(f"  Profit: {exit_deal['profit']:.2f}")
            print()
            
            # Check log file for exit reason
            log_file = project_root / "logs" / "trading_platform.log"
            log_exit_reason = None
            exit_log_context = []
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                        log_lines = f.readlines()
                    
                    # Search around exit time
                    exit_time_str = exit_deal['time'].strftime('%Y-%m-%d %H:%M')
                    ticket_str = str(pos_id)
                    
                    for i, line in enumerate(log_lines):
                        if exit_time_str[:13] in line and ticket_str in line:
                            if 'Take profit triggered' in line or ('TP' in line.upper() and 'triggered' in line):
                                log_exit_reason = "TP"
                                context_start = max(0, i - 2)
                                context_end = min(len(log_lines), i + 3)
                                exit_log_context = log_lines[context_start:context_end]
                                break
                            elif 'Stop loss triggered' in line or ('SL' in line.upper() and 'triggered' in line):
                                log_exit_reason = "SL"
                                context_start = max(0, i - 2)
                                context_end = min(len(log_lines), i + 3)
                                exit_log_context = log_lines[context_start:context_end]
                                break
                            elif f'Closing position {ticket_str} due to TP' in line:
                                log_exit_reason = "TP"
                                context_start = max(0, i - 2)
                                context_end = min(len(log_lines), i + 3)
                                exit_log_context = log_lines[context_start:context_end]
                                break
                            elif f'Closing position {ticket_str} due to SL' in line:
                                log_exit_reason = "SL"
                                context_start = max(0, i - 2)
                                context_end = min(len(log_lines), i + 3)
                                exit_log_context = log_lines[context_start:context_end]
                                break
                except Exception as e:
                    print(f"  [Note] Could not read log file: {e}")
            
            if exit_log_context:
                print(f"\n  Exit Log Context:")
                for line in exit_log_context:
                    print(f"    {line.strip()}")
                print()
            
            # Final conclusion
            print(f"[CONCLUSION]")
            if exit_reason_code == 8:
                print(f"  Exit Reason: Take Profit (TP) was hit")
                print(f"  The position reached the take profit level and was automatically closed by MT5")
            elif exit_reason_code == 7:
                print(f"  Exit Reason: Stop Loss (SL) was hit")
                print(f"  The position hit the stop loss level and was automatically closed by MT5")
            elif exit_reason_code in [3, 4, 5]:
                print(f"  Exit Reason: Manual/Client Close (Reason Code: {exit_reason_code})")
                print(f"  MT5 reports this as a manual close, but it could be:")
                print(f"    1. System closed when TP/SL was hit (system sends close order)")
                print(f"    2. User manually closed the position")
                print(f"    3. EA or script closed the position")
                
                if log_exit_reason:
                    print(f"\n  [LOG EVIDENCE] Log file shows: {log_exit_reason}")
                    if log_exit_reason == "TP":
                        print(f"  ACTUAL REASON: Take Profit was hit - system closed the position")
                    elif log_exit_reason == "SL":
                        print(f"  ACTUAL REASON: Stop Loss was hit - system closed the position")
                
                if exit_deal['profit'] > 0:
                    print(f"\n  Analysis:")
                    print(f"    - Trade closed at profit ({exit_deal['profit']:.2f})")
                    print(f"    - Price moved favorably: {price_change:.5f} points ({price_change/point:.1f} pips)")
                    print(f"    - Most likely: System closed when Take Profit was hit")
                    print(f"    - Reason code 3 (Client) is used when system sends close order")
                else:
                    print(f"\n  Analysis:")
                    print(f"    - Trade closed at loss ({exit_deal['profit']:.2f})")
                    print(f"    - Price moved unfavorably: {price_change:.5f} points")
                    print(f"    - Most likely: System closed when Stop Loss was hit or manual close to limit loss")
            elif exit_reason_code == 6:
                print(f"  Exit Reason: Expert Advisor/Script Close")
                print(f"  The position was closed by an EA or script")
            else:
                print(f"  Exit Reason: {exit_reason} (Code: {exit_reason_code})")
                print(f"  Check MT5 deal history for more details")
        else:
            print("  Position is still open or exit deal not found")
        
        print()
        print("=" * 70)
        print()
    
    mt5.shutdown()


if __name__ == "__main__":
    analyze_buyeu_trade()
