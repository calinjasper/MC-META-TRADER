"""
Backtest Engine
Executes backtests on historical data using indicator strategies
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from data_viewer.backtest.indicator_loader import IndicatorLoader
from data_viewer.backtest.metrics import MetricsCalculator, Trade
from data_viewer.backtest.sl_tp_calculator import SLTPCalculator
from data_viewer.backtest.advanced_risk_manager import TrailingStopLoss, ProfitManager
from data_viewer.utils.mysql_client import MySQLClient
from data_viewer.config import MYSQL_HOST, MYSQL_PORT, MYSQL_USERNAME, MYSQL_PASSWORD

logger = logging.getLogger(__name__)

# IST timezone support
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
    UTC = ZoneInfo("UTC")
except ImportError:
    try:
        import pytz
        IST = pytz.timezone("Asia/Kolkata")
        UTC = pytz.UTC
    except ImportError:
        from datetime import timedelta, timezone
        IST = timezone(timedelta(hours=5, minutes=30))
        UTC = timezone.utc


class BacktestEngine:
    """Executes backtests on historical data"""
    
    def __init__(self):
        """Initialize backtest engine"""
        self.indicator_loader = IndicatorLoader()
        self.mysql_client = MySQLClient(MYSQL_HOST, MYSQL_PORT, MYSQL_USERNAME, MYSQL_PASSWORD)
        self.sl_tp_calculator = SLTPCalculator()
    
    def run_backtest(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        indicator_name: str,
        indicator_settings: Dict[str, Any] = None,
        position_sizing_type: str = "fixed",
        position_size: float = 0.01,
        initial_capital: float = 10000.0,
        commission: float = 0.0,
        slippage: float = 0.0
    ) -> Dict:
        """
        Run a backtest
        
        Args:
            symbol: Trading symbol
            start_date: Start date (ISO format with timezone)
            end_date: End date (ISO format with timezone)
            indicator_name: Name of indicator strategy
            indicator_settings: Dictionary of indicator-specific settings
            position_sizing_type: "fixed" or "percentage"
            position_size: Lot size (for fixed) or percentage (for percentage)
            initial_capital: Starting capital
            commission: Commission per trade
            slippage: Slippage in points
            
        Returns:
            Dictionary with backtest results:
            - metrics: Performance metrics
            - trades: List of trades
            - equity_curve: Equity over time
        """
        try:
            # Load historical data
            logger.info(f"Loading historical data for {symbol} from {start_date} to {end_date}")
            candles = self._load_historical_data(symbol, start_date, end_date)
            
            if not candles:
                # Provide more helpful error message
                error_msg = (
                    f"No historical data found for symbol '{symbol}' in date range {start_date} to {end_date}. "
                    f"Please check:\n"
                    f"1. Symbol name is correct (tried: {symbol.upper()}, {symbol.lower()})\n"
                    f"2. Date range has data in the database\n"
                    f"3. Table exists: {symbol.lower()}_minute in minute_data schema"
                )
                logger.error(error_msg)
                return {
                    "error": error_msg,
                    "metrics": {},
                    "trades": [],
                    "equity_curve": []
                }
            
            logger.info(f"Loaded {len(candles)} candles")
            
            # Create indicator instance
            logger.info(f"Creating indicator instance: {indicator_name}")
            strategy = self.indicator_loader.create_indicator_instance(
                indicator_name,
                symbol,
                indicator_settings or {}
            )
            
            if not strategy:
                return {
                    "error": f"Failed to create indicator instance: {indicator_name}",
                    "metrics": {},
                    "trades": [],
                    "equity_curve": []
                }
            
            # Mock MT5 connector for strategies that need it
            # Strategies use MT5 connector to fetch historical candles, but we provide them directly
            if hasattr(strategy, 'set_mt5_connector'):
                # Create a mock connector that provides candles from our loaded data
                class MockMT5Connector:
                    def __init__(self, candles_data):
                        self.candles_data = candles_data
                        self._candles_cache = {}
                    
                    def is_connected(self):
                        return True
                    
                    def get_rates(self, symbol, timeframe, count, offset):
                        # Return candles in the format strategies expect
                        if symbol not in self._candles_cache:
                            # Convert our candle format to MT5 format
                            mt5_candles = []
                            for candle in self.candles_data:
                                mt5_candles.append({
                                    'time': candle['time'],
                                    'open': candle['open'],
                                    'high': candle['high'],
                                    'low': candle['low'],
                                    'close': candle['close'],
                                    'tick_volume': candle.get('tick_count', 0),
                                    'volume': candle.get('tick_count', 0),
                                    'spread': 0
                                })
                            self._candles_cache[symbol] = mt5_candles
                        
                        cached = self._candles_cache[symbol]
                        # Return last 'count' candles
                        return cached[-count:] if len(cached) >= count else cached
                
                mock_connector = MockMT5Connector(candles)
                strategy.set_mt5_connector(mock_connector)
            
            # Mock market_data_panel for OHLC strategies
            # OHLC strategies need access to daily OHLC data
            if hasattr(strategy, 'set_market_data_panel') or hasattr(strategy, 'get_ohlc_data'):
                # Create a mock market data panel that provides OHLC from historical candles
                class MockMarketDataPanel:
                    def __init__(self, candles_data, symbol):
                        self.ohlc_data = {}
                        self.symbol = symbol
                        # Calculate daily OHLC from minute candles
                        self._calculate_daily_ohlc(candles_data, symbol)
                    
                    def _calculate_daily_ohlc(self, candles, symbol):
                        """Calculate daily OHLC from minute candles"""
                        if not candles:
                            return
                        
                        # Group candles by date
                        daily_candles = {}
                        for candle in candles:
                            candle_date = candle['time'].date()
                            if candle_date not in daily_candles:
                                daily_candles[candle_date] = {
                                    'open': candle['open'],
                                    'high': candle['high'],
                                    'low': candle['low'],
                                    'close': candle['close'],
                                    'time': candle['time']
                                }
                            else:
                                daily_candles[candle_date]['high'] = max(
                                    daily_candles[candle_date]['high'], 
                                    candle['high']
                                )
                                daily_candles[candle_date]['low'] = min(
                                    daily_candles[candle_date]['low'], 
                                    candle['low']
                                )
                                daily_candles[candle_date]['close'] = candle['close']
                                daily_candles[candle_date]['time'] = candle['time']
                        
                        # Store all daily OHLC data (not just latest)
                        # Strategy will access the most recent one
                        if daily_candles:
                            latest_date = max(daily_candles.keys())
                            self.ohlc_data[symbol.upper()] = daily_candles[latest_date]
                            # Also add lowercase version for case-insensitive matching
                            self.ohlc_data[symbol.lower()] = daily_candles[latest_date]
                            # Store all dates for reference
                            self._daily_candles = daily_candles
                    
                    def update_ohlc_for_date(self, date, ohlc_dict):
                        """Update OHLC for a specific date"""
                        self.ohlc_data[self.symbol.upper()] = ohlc_dict
                        self.ohlc_data[self.symbol.lower()] = ohlc_dict
                
                mock_panel = MockMarketDataPanel(candles, symbol)
                if hasattr(strategy, 'set_market_data_panel'):
                    strategy.set_market_data_panel(mock_panel)
                # Store reference for updating during simulation
                strategy._mock_market_data_panel = mock_panel
            
            # Run simulation
            logger.info("Running backtest simulation...")
            trades, equity_curve = self._simulate_trades(
                candles,
                strategy,
                symbol,
                position_sizing_type,
                position_size,
                initial_capital,
                commission,
                slippage
            )
            
            # Calculate metrics
            logger.info("Calculating metrics...")
            metrics_calc = MetricsCalculator(initial_capital)
            metrics = metrics_calc.calculate_metrics(trades, equity_curve)
            
            # Convert trades to dictionaries for JSON serialization
            trades_dict = [self._trade_to_dict(t) for t in trades]
            
            return {
                "metrics": metrics,
                "trades": trades_dict,
                "equity_curve": equity_curve,
                "summary": {
                    "symbol": symbol,
                    "start_date": start_date,
                    "end_date": end_date,
                    "indicator": indicator_name,
                    "total_candles": len(candles),
                    "total_trades": len(trades)
                }
            }
        except Exception as e:
            logger.error(f"Error running backtest: {e}", exc_info=True)
            return {
                "error": str(e),
                "metrics": {},
                "trades": [],
                "equity_curve": []
            }
    
    def _load_historical_data(self, symbol: str, start_date: str, end_date: str) -> List[Dict]:
        """
        Load historical OHLC data from MySQL
        
        Args:
            symbol: Trading symbol
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            
        Returns:
            List of candle dictionaries with: time, open, high, low, close, tick_count
        """
        try:
            # Parse dates
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            logger.info(f"Loading historical data for {symbol} from {start_dt} to {end_dt}")
            
            # Convert to IST for MySQL query
            if start_dt.tzinfo:
                start_dt = start_dt.astimezone(IST)
            if end_dt.tzinfo:
                end_dt = end_dt.astimezone(IST)
            
            # Format for MySQL query
            start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
            end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
            
            logger.debug(f"Query date range (IST): {start_str} to {end_str}")
            
            # Query MySQL for minute data
            collection_info = self.mysql_client.get_collection_info("minute")
            if not collection_info:
                logger.error("Could not get collection info for 'minute'")
                return []
            
            # Try multiple symbol formats
            symbol_variants = [
                symbol.upper(),
                symbol.lower(),
                symbol.capitalize()
            ]
            
            schema = "minute_data"
            connection = self.mysql_client._get_connection()
            cursor = connection.cursor(dictionary=True)
            
            try:
                # First, check which tables exist
                cursor.execute(f"SHOW TABLES FROM `{schema}` LIKE '%_minute'")
                available_tables = [row[f'Tables_in_{schema}'] for row in cursor.fetchall()]
                logger.debug(f"Available minute tables: {available_tables}")
                
                # Try each symbol variant
                for sym_variant in symbol_variants:
                    table_name = f"{sym_variant.lower()}_minute"
                    
                    if table_name not in available_tables:
                        logger.debug(f"Table {table_name} not found, trying next variant")
                        continue
                    
                    logger.info(f"Trying table: {table_name} for symbol: {symbol}")
                    
                    # Try query with timestamp field first
                    query = f"""
                        SELECT timestamp, utc_time, open, high, low, close, tick_count
                        FROM `{schema}`.`{table_name}`
                        WHERE timestamp >= %s AND timestamp <= %s
                        ORDER BY timestamp ASC
                    """
                    
                    try:
                        cursor.execute(query, (start_str, end_str))
                        rows = cursor.fetchall()
                        logger.info(f"Query returned {len(rows)} rows from {table_name}")
                        
                        if rows:
                            candles = []
                            for row in rows:
                                # Parse timestamp - try multiple formats
                                ts = None
                                
                                # Try timestamp field first
                                if 'timestamp' in row and row['timestamp']:
                                    if isinstance(row['timestamp'], (int, float)):
                                        # Timestamp in milliseconds
                                        ts = datetime.fromtimestamp(row['timestamp'] / 1000, tz=IST)
                                    elif isinstance(row['timestamp'], str):
                                        try:
                                            ts = datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S")
                                            if ts.tzinfo is None:
                                                ts = IST.localize(ts)
                                        except:
                                            # Try other formats
                                            try:
                                                ts = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                                                if ts.tzinfo:
                                                    ts = ts.astimezone(IST)
                                            except:
                                                logger.warning(f"Could not parse timestamp: {row['timestamp']}")
                                                continue
                                    else:
                                        ts = row['timestamp']
                                        if ts.tzinfo is None:
                                            ts = IST.localize(ts)
                                
                                # Fallback to utc_time if timestamp not available
                                if ts is None and 'utc_time' in row and row['utc_time']:
                                    if isinstance(row['utc_time'], str):
                                        try:
                                            ts = datetime.strptime(row['utc_time'], "%Y-%m-%d %H:%M:%S")
                                            if ts.tzinfo is None:
                                                ts = UTC.localize(ts).astimezone(IST)
                                        except:
                                            try:
                                                ts = datetime.fromisoformat(row['utc_time'].replace('Z', '+00:00'))
                                                if ts.tzinfo:
                                                    ts = ts.astimezone(IST)
                                            except:
                                                logger.warning(f"Could not parse utc_time: {row['utc_time']}")
                                                continue
                                    else:
                                        ts = row['utc_time']
                                        if ts and ts.tzinfo is None:
                                            ts = UTC.localize(ts).astimezone(IST)
                                
                                if ts is None:
                                    logger.warning("Could not determine timestamp from row, skipping")
                                    continue
                                
                                candles.append({
                                    "time": ts,
                                    "open": float(row.get('open', 0)),
                                    "high": float(row.get('high', 0)),
                                    "low": float(row.get('low', 0)),
                                    "close": float(row.get('close', 0)),
                                    "tick_count": int(row.get('tick_count', 0))
                                })
                            
                            logger.info(f"Successfully loaded {len(candles)} candles from {table_name}")
                            return candles
                    except Exception as query_error:
                        logger.warning(f"Query failed for {table_name}: {query_error}")
                        # Try alternative query with utc_time
                        try:
                            query_alt = f"""
                                SELECT utc_time as timestamp, open, high, low, close, tick_count
                                FROM `{schema}`.`{table_name}`
                                WHERE utc_time >= %s AND utc_time <= %s
                                ORDER BY utc_time ASC
                            """
                            cursor.execute(query_alt, (start_str, end_str))
                            rows = cursor.fetchall()
                            logger.info(f"Alternative query returned {len(rows)} rows from {table_name}")
                            
                            if rows:
                                candles = []
                                for row in rows:
                                    ts = None
                                    if 'timestamp' in row and row['timestamp']:
                                        if isinstance(row['timestamp'], str):
                                            try:
                                                ts = datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S")
                                                if ts.tzinfo is None:
                                                    ts = UTC.localize(ts).astimezone(IST)
                                            except:
                                                try:
                                                    ts = datetime.fromisoformat(row['timestamp'].replace('Z', '+00:00'))
                                                    if ts.tzinfo:
                                                        ts = ts.astimezone(IST)
                                                except:
                                                    continue
                                        else:
                                            ts = row['timestamp']
                                            if ts.tzinfo is None:
                                                ts = UTC.localize(ts).astimezone(IST)
                                    
                                    if ts is None:
                                        continue
                                    
                                    candles.append({
                                        "time": ts,
                                        "open": float(row.get('open', 0)),
                                        "high": float(row.get('high', 0)),
                                        "low": float(row.get('low', 0)),
                                        "close": float(row.get('close', 0)),
                                        "tick_count": int(row.get('tick_count', 0))
                                    })
                                
                                logger.info(f"Successfully loaded {len(candles)} candles using alternative query")
                                return candles
                        except Exception as alt_error:
                            logger.warning(f"Alternative query also failed: {alt_error}")
                            continue
                
                # If we get here, no data was found
                logger.error(f"No historical data found for symbol '{symbol}' in date range {start_str} to {end_str}")
                logger.error(f"Tried symbol variants: {symbol_variants}")
                logger.error(f"Available tables: {available_tables}")
                return []
                
            finally:
                cursor.close()
        except Exception as e:
            logger.error(f"Error loading historical data: {e}", exc_info=True)
            return []
    
    def _simulate_trades(
        self,
        candles: List[Dict],
        strategy: Any,
        symbol: str,
        position_sizing_type: str,
        position_size: float,
        initial_capital: float,
        commission: float,
        slippage: float
    ) -> tuple[List[Trade], List[Dict]]:
        """
        Simulate trades based on indicator signals
        
        Args:
            candles: List of historical candles
            strategy: Indicator strategy instance
            symbol: Trading symbol
            position_sizing_type: "fixed" or "percentage"
            position_size: Lot size or percentage
            initial_capital: Starting capital
            commission: Commission per trade
            slippage: Slippage in points
            
        Returns:
            Tuple of (trades list, equity_curve list)
        """
        trades = []
        equity_curve = []
        
        current_equity = initial_capital
        current_position = None  # Enhanced position dict with SL/TP and risk management
        previous_signal = None
        
        # Get symbol info for SL/TP calculations (simplified - use defaults)
        symbol_info = self.sl_tp_calculator._get_default_symbol_info(symbol)
        
        # Track indicator state (for strategies that need historical data)
        strategy_candles = []
        
        # For OHLC strategies, calculate and update daily OHLC as we progress
        daily_ohlc_by_date = {}
        if hasattr(strategy, '_mock_market_data_panel'):
            # Pre-calculate all daily OHLC
            for candle in candles:
                candle_date = candle['time'].date()
                if candle_date not in daily_ohlc_by_date:
                    daily_ohlc_by_date[candle_date] = {
                        'open': candle['open'],
                        'high': candle['high'],
                        'low': candle['low'],
                        'close': candle['close'],
                        'time': candle['time']
                    }
                else:
                    daily_ohlc_by_date[candle_date]['high'] = max(
                        daily_ohlc_by_date[candle_date]['high'],
                        candle['high']
                    )
                    daily_ohlc_by_date[candle_date]['low'] = min(
                        daily_ohlc_by_date[candle_date]['low'],
                        candle['low']
                    )
                    daily_ohlc_by_date[candle_date]['close'] = candle['close']
                    daily_ohlc_by_date[candle_date]['time'] = candle['time']
        
        for i, candle in enumerate(candles):
            current_time = candle["time"]
            current_price = candle["close"]
            current_date = current_time.date()
            
            # Update daily OHLC for OHLC strategies
            if hasattr(strategy, '_mock_market_data_panel') and current_date in daily_ohlc_by_date:
                strategy._mock_market_data_panel.update_ohlc_for_date(
                    current_date,
                    daily_ohlc_by_date[current_date]
                )
            
            # Build market_data for strategy
            # Strategy expects tick data, so we'll simulate it from candle
            market_data = {
                "tick": {
                    "bid": current_price - 0.0001,  # Simulate spread
                    "ask": current_price + 0.0001,
                    "last": current_price
                },
                "ohlc": {
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"]
                }
            }
            
            # For strategies that need historical candles, update them
            if hasattr(strategy, '_get_candles'):
                # Some strategies need to fetch candles themselves
                # We'll provide a mock method or update their internal state
                strategy_candles.append(candle)
                # Limit to last 300 candles for performance
                if len(strategy_candles) > 300:
                    strategy_candles = strategy_candles[-300:]
            
            # Generate signal
            try:
                signal = strategy.generate_signal(market_data)
            except Exception as e:
                logger.warning(f"Error generating signal at {current_time}: {e}")
                signal = None
            
            # Get condition description if available (for OHLC strategies)
            condition_description = None
            if signal and hasattr(strategy, 'buy_conditions') and hasattr(strategy, 'sell_conditions'):
                if signal == "BUY" and strategy.buy_conditions:
                    # Create a description of the buy conditions
                    cond_descriptions = []
                    for cond in strategy.buy_conditions:
                        desc = f"{cond.left_field or 'price'} {cond.operator} {cond.right_field or cond.value or 'N/A'}"
                        cond_descriptions.append(desc)
                    condition_description = f"Buy: {' OR '.join(cond_descriptions)}"
                elif signal == "SELL" and strategy.sell_conditions:
                    cond_descriptions = []
                    for cond in strategy.sell_conditions:
                        desc = f"{cond.left_field or 'price'} {cond.operator} {cond.right_field or cond.value or 'N/A'}"
                        cond_descriptions.append(desc)
                    condition_description = f"Sell: {' OR '.join(cond_descriptions)}"
            
            # Check existing position for SL/TP hits and update risk management
            if current_position:
                exit_reason, exit_price = self._check_position_exit(
                    current_position, current_price, candle
                )
                
                if exit_reason:
                    # Close position
                    # Apply slippage
                    if current_position["direction"] == "BUY":
                        exit_price -= slippage * 0.0001
                    else:
                        exit_price += slippage * 0.0001
                    
                    # Calculate P/L
                    if current_position["direction"] == "BUY":
                        pnl = (exit_price - current_position["entry_price"]) * current_position["lot_size"] * 100000
                    else:  # SELL
                        pnl = (current_position["entry_price"] - exit_price) * current_position["lot_size"] * 100000
                    
                    # Apply commission
                    pnl -= commission * 2
                    
                    # Determine hit prices based on exit reason
                    sl_hit_price = None
                    tp_hit_price = None
                    if exit_reason == "SL" or exit_reason == "Trailing SL":
                        sl_hit_price = exit_price
                    elif exit_reason == "TP" or exit_reason == "Profit Lock":
                        tp_hit_price = exit_price
                    
                    # Create trade
                    trade = Trade(
                        entry_time=current_position["entry_time"],
                        exit_time=current_time,
                        entry_price=current_position["entry_price"],
                        exit_price=exit_price,
                        direction=current_position["direction"],
                        lot_size=current_position["lot_size"],
                        pnl=pnl,
                        commission=commission * 2,
                        slippage=slippage,
                        entry_condition=current_position.get("entry_condition"),
                        entry_condition_met_at=current_position.get("entry_condition_met_at"),
                        entry_condition_met_price=current_position.get("entry_condition_met_price"),
                        exit_reason=exit_reason,
                        sl_price=current_position.get("sl_price"),
                        tp_price=current_position.get("tp_price"),
                        sl_hit_price=sl_hit_price,
                        tp_hit_price=tp_hit_price
                    )
                    trades.append(trade)
                    
                    # Update equity
                    current_equity += pnl
                    
                    current_position = None
                else:
                    # Update risk management (trailing SL, profit lock)
                    self._update_position_risk_management(
                        current_position, current_price, candle
                    )
            
            # Handle signal changes
            if signal and signal != previous_signal:
                # Close existing position if any (opposite signal)
                if current_position:
                    exit_price = current_price
                    # Apply slippage
                    if current_position["direction"] == "BUY":
                        exit_price -= slippage * 0.0001
                    else:
                        exit_price += slippage * 0.0001
                    
                    # Calculate P/L
                    if current_position["direction"] == "BUY":
                        pnl = (exit_price - current_position["entry_price"]) * current_position["lot_size"] * 100000
                    else:  # SELL
                        pnl = (current_position["entry_price"] - exit_price) * current_position["lot_size"] * 100000
                    
                    # Apply commission
                    pnl -= commission * 2
                    
                    # Determine exit reason
                    exit_reason = "Signal Reversal"
                    if signal:
                        exit_reason = f"Opposite signal: {signal}"
                    
                    # Create trade
                    trade = Trade(
                        entry_time=current_position["entry_time"],
                        exit_time=current_time,
                        entry_price=current_position["entry_price"],
                        exit_price=exit_price,
                        direction=current_position["direction"],
                        lot_size=current_position["lot_size"],
                        pnl=pnl,
                        commission=commission * 2,
                        slippage=slippage,
                        entry_condition=current_position.get("entry_condition"),
                        entry_condition_met_at=current_position.get("entry_condition_met_at"),
                        entry_condition_met_price=current_position.get("entry_condition_met_price"),
                        exit_reason=exit_reason,
                        sl_price=current_position.get("sl_price"),
                        tp_price=current_position.get("tp_price"),
                        sl_hit_price=None,
                        tp_hit_price=None
                    )
                    trades.append(trade)
                    
                    # Update equity
                    current_equity += pnl
                    
                    current_position = None
                
                # Open new position if signal is opposite
                if signal:
                    entry_price = current_price
                    # Apply slippage
                    if signal == "BUY":
                        entry_price += slippage * 0.0001
                    else:
                        entry_price -= slippage * 0.0001
                    
                    # Calculate lot size
                    if position_sizing_type == "fixed":
                        lot_size = position_size
                    else:  # percentage
                        risk_amount = current_equity * (position_size / 100)
                        lot_size = risk_amount / 100000
                        lot_size = max(0.01, min(lot_size, current_equity / 1000))
                    
                    # Calculate SL/TP
                    sl_price, tp_price = self.sl_tp_calculator.calculate_sl_tp(
                        strategy, symbol, entry_price, signal, symbol_info
                    )
                    
                    # Initialize risk management if enabled
                    trailing_sl = None
                    if getattr(strategy, 'enable_trailing_sl', False):
                        trailing_sl_gap = getattr(strategy, 'trailing_sl_gap', 0.0)
                        if trailing_sl_gap > 0:
                            trailing_sl = TrailingStopLoss(entry_price, trailing_sl_gap, signal)
                    
                    profit_lock = None
                    if getattr(strategy, 'enable_profit_lock', False):
                        profit_lock = ProfitManager(
                            lock_trigger=getattr(strategy, 'profit_lock_trigger', 0.0),
                            lock_value=getattr(strategy, 'profit_lock_value', 0.0),
                            trail_step=getattr(strategy, 'profit_trail_step', 0.0),
                            trail_amount=getattr(strategy, 'profit_trail_amount', 0.0),
                            position_type=signal
                        )
                    
                    current_position = {
                        "direction": signal,
                        "entry_price": entry_price,
                        "entry_time": current_time,
                        "lot_size": lot_size,
                        "entry_condition": condition_description or f"{signal} signal triggered",
                        "entry_condition_met_at": current_time,
                        "entry_condition_met_price": current_price,
                        "sl_price": sl_price,
                        "tp_price": tp_price,
                        "trailing_sl": trailing_sl,
                        "profit_lock": profit_lock,
                        "strategy": strategy
                    }
            
            previous_signal = signal
            
            # Update equity curve
            equity_curve.append({
                "time": current_time.isoformat(),
                "equity": current_equity
            })
        
        # Close any open position at the end
        if current_position and candles:
            last_candle = candles[-1]
            exit_price = last_candle["close"]
            
            if current_position["direction"] == "BUY":
                exit_price -= slippage * 0.0001
                pnl = (exit_price - current_position["entry_price"]) * current_position["lot_size"] * 100000
            else:
                exit_price += slippage * 0.0001
                pnl = (current_position["entry_price"] - exit_price) * current_position["lot_size"] * 100000
            
            pnl -= commission * 2
            
            trade = Trade(
                entry_time=current_position["entry_time"],
                exit_time=last_candle["time"],
                entry_price=current_position["entry_price"],
                exit_price=exit_price,
                direction=current_position["direction"],
                lot_size=current_position["lot_size"],
                pnl=pnl,
                commission=commission * 2,
                slippage=slippage,
                entry_condition=current_position.get("entry_condition"),
                entry_condition_met_at=current_position.get("entry_condition_met_at"),
                entry_condition_met_price=current_position.get("entry_condition_met_price"),
                exit_reason="End of data",
                sl_price=current_position.get("sl_price"),
                tp_price=current_position.get("tp_price")
            )
            trades.append(trade)
            current_equity += pnl
            
            # Update final equity in curve
            if equity_curve:
                equity_curve[-1]["equity"] = current_equity
        
        return trades, equity_curve
    
    def _check_position_exit(
        self, 
        position: Dict, 
        current_price: float, 
        candle: Dict
    ) -> tuple[Optional[str], float]:
        """
        Check if position should be closed due to SL/TP or risk management
        
        Args:
            position: Current position dictionary
            current_price: Current market price
            candle: Current candle data
            
        Returns:
            Tuple of (exit_reason, exit_price) or (None, current_price) if no exit
        """
        direction = position["direction"]
        entry_price = position["entry_price"]
        sl_price = position.get("sl_price")
        tp_price = position.get("tp_price")
        
        # Check regular SL
        if sl_price is not None:
            if direction == "BUY" and current_price <= sl_price:
                return "SL", sl_price
            elif direction == "SELL" and current_price >= sl_price:
                return "SL", sl_price
        
        # Check regular TP
        if tp_price is not None:
            if direction == "BUY" and current_price >= tp_price:
                return "TP", tp_price
            elif direction == "SELL" and current_price <= tp_price:
                return "TP", tp_price
        
        # Check trailing SL
        trailing_sl = position.get("trailing_sl")
        if trailing_sl:
            if trailing_sl.should_trigger_close(current_price):
                return "Trailing SL", trailing_sl.stop_loss
        
        # Check profit lock
        profit_lock = position.get("profit_lock")
        if profit_lock:
            # Calculate current profit
            if direction == "BUY":
                price_diff = current_price - entry_price
            else:  # SELL
                price_diff = entry_price - current_price
            
            profit = price_diff * position["lot_size"] * 100000
            
            # Update profit lock
            locked_profit = profit_lock.update_profit(profit)
            
            # Check if profit dropped below locked profit
            if profit_lock.lock_enabled and profit < locked_profit:
                # Calculate TP price from locked profit
                tp_from_lock = profit_lock.calculate_take_profit_price(
                    entry_price, position["lot_size"]
                )
                if tp_from_lock:
                    if direction == "BUY" and current_price <= tp_from_lock:
                        return "Profit Lock", tp_from_lock
                    elif direction == "SELL" and current_price >= tp_from_lock:
                        return "Profit Lock", tp_from_lock
        
        return None, current_price
    
    def _update_position_risk_management(
        self, 
        position: Dict, 
        current_price: float, 
        candle: Dict
    ):
        """
        Update trailing SL and profit lock for a position
        
        Args:
            position: Current position dictionary
            current_price: Current market price
            candle: Current candle data
        """
        # Update trailing SL
        trailing_sl = position.get("trailing_sl")
        if trailing_sl:
            new_sl = trailing_sl.update_price(current_price)
            # Update position's SL price if trailing SL is active
            if new_sl != position.get("sl_price"):
                position["sl_price"] = new_sl
        
        # Update profit lock
        profit_lock = position.get("profit_lock")
        if profit_lock:
            direction = position["direction"]
            entry_price = position["entry_price"]
            
            # Calculate current profit
            if direction == "BUY":
                price_diff = current_price - entry_price
            else:  # SELL
                price_diff = entry_price - current_price
            
            profit = price_diff * position["lot_size"] * 100000
            
            # Update profit lock
            locked_profit = profit_lock.update_profit(profit)
            
            # Update TP if profit lock is active
            if profit_lock.lock_enabled:
                new_tp = profit_lock.calculate_take_profit_price(
                    entry_price, position["lot_size"]
                )
                if new_tp:
                    position["tp_price"] = new_tp
    
    def _trade_to_dict(self, trade: Trade) -> Dict:
        """Convert Trade object to dictionary"""
        trade_dict = {
            "entry_time": trade.entry_time.isoformat(),
            "exit_time": trade.exit_time.isoformat(),
            "entry_price": round(trade.entry_price, 5),
            "exit_price": round(trade.exit_price, 5),
            "direction": trade.direction,
            "lot_size": round(trade.lot_size, 2),
            "pnl": round(trade.pnl, 2),
            "pnl_percentage": round((trade.pnl / (trade.entry_price * trade.lot_size * 100000)) * 100, 2) if trade.entry_price > 0 else 0,
            "commission": round(trade.commission, 2),
            "slippage": round(trade.slippage, 2),
            "duration_seconds": round(trade.duration, 2),
            "duration_minutes": round(trade.duration / 60, 2),
            "is_win": trade.is_win,
            "is_loss": trade.is_loss
        }
        
        # Add condition details if available
        if trade.entry_condition:
            trade_dict["entry_condition"] = trade.entry_condition
        if trade.entry_condition_met_at:
            trade_dict["entry_condition_met_at"] = trade.entry_condition_met_at.isoformat()
        if trade.entry_condition_met_price:
            trade_dict["entry_condition_met_price"] = round(trade.entry_condition_met_price, 5)
        if trade.exit_reason:
            trade_dict["exit_reason"] = trade.exit_reason
        
        return trade_dict

