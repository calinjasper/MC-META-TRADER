"""
Python MT5 Indicator Example
Develop custom indicators in Python and send signals to the trading platform

This example shows how to:
1. Connect to MT5 from Python
2. Calculate technical indicators
3. Generate buy/sell signals
4. Send signals via the signal routing system
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import time
import requests
from typing import Optional, Dict
from datetime import datetime


class PythonMT5Indicator:
    """Python-based MT5 indicator that generates trading signals"""
    
    def __init__(self, symbol: str, timeframe: int = mt5.TIMEFRAME_M15, 
                 signal_server_url: str = "http://localhost:8080"):
        """
        Initialize the indicator
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            timeframe: MT5 timeframe (default: M15)
            signal_server_url: URL of the signal server
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.signal_server_url = signal_server_url.rstrip('/')
        self.connected = False
    
    def connect(self, login: int = None, password: str = None, server: str = None) -> bool:
        """Connect to MT5"""
        if not mt5.initialize():
            print(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        
        if login and password and server:
            if not mt5.login(login, password=password, server=server):
                print(f"MT5 login failed: {mt5.last_error()}")
                mt5.shutdown()
                return False
        
        self.connected = True
        print(f"Connected to MT5. Account: {mt5.account_info().login}")
        return True
    
    def disconnect(self):
        """Disconnect from MT5"""
        mt5.shutdown()
        self.connected = False
    
    def get_rates(self, count: int = 100) -> Optional[pd.DataFrame]:
        """Get historical rates from MT5"""
        if not self.connected:
            print("Not connected to MT5")
            return None
        
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, count)
        
        if rates is None or len(rates) == 0:
            print(f"Failed to get rates for {self.symbol}")
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, 
                      signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD indicator"""
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_ema(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return df['close'].ewm(span=period, adjust=False).mean()
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, 
                                 std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        
        return {
            'upper': sma + (std * std_dev),
            'middle': sma,
            'lower': sma - (std * std_dev)
        }
    
    def generate_signal(self, df: pd.DataFrame) -> Optional[str]:
        """
        Generate trading signal based on indicators
        
        This is a custom strategy - modify as needed
        Strategy: RSI + MACD + EMA crossover
        """
        # Calculate indicators
        rsi = self.calculate_rsi(df, period=14)
        macd_data = self.calculate_macd(df)
        ema_fast = self.calculate_ema(df, period=10)
        ema_slow = self.calculate_ema(df, period=20)
        
        if len(df) < 20:
            return None
        
        # Get latest values
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        
        macd_current = macd_data['macd'].iloc[-1]
        signal_current = macd_data['signal'].iloc[-1]
        macd_prev = macd_data['macd'].iloc[-2]
        signal_prev = macd_data['signal'].iloc[-2]
        
        ema_fast_current = ema_fast.iloc[-1]
        ema_slow_current = ema_slow.iloc[-1]
        ema_fast_prev = ema_fast.iloc[-2]
        ema_slow_prev = ema_slow.iloc[-2]
        
        # BUY Signal Conditions:
        # 1. RSI crosses above 30 (oversold recovery)
        # 2. MACD crosses above signal line
        # 3. Fast EMA crosses above slow EMA
        buy_condition_1 = prev_rsi <= 30 and current_rsi > 30
        buy_condition_2 = macd_prev <= signal_prev and macd_current > signal_current
        buy_condition_3 = ema_fast_prev <= ema_slow_prev and ema_fast_current > ema_slow_current
        
        if buy_condition_1 and buy_condition_2 and buy_condition_3:
            return "BUY"
        
        # SELL Signal Conditions:
        # 1. RSI crosses below 70 (overbought decline)
        # 2. MACD crosses below signal line
        # 3. Fast EMA crosses below slow EMA
        sell_condition_1 = prev_rsi >= 70 and current_rsi < 70
        sell_condition_2 = macd_prev >= signal_prev and macd_current < signal_current
        sell_condition_3 = ema_fast_prev >= ema_slow_prev and ema_fast_current < ema_slow_current
        
        if sell_condition_1 and sell_condition_2 and sell_condition_3:
            return "SELL"
        
        return None
    
    def calculate_sl_tp(self, df: pd.DataFrame, signal: str, 
                       risk_reward_ratio: float = 2.0) -> tuple[float, float]:
        """
        Calculate stop loss and take profit based on ATR
        
        Args:
            df: DataFrame with price data
            signal: "BUY" or "SELL"
            risk_reward_ratio: Risk-reward ratio (default: 1:2)
            
        Returns:
            Tuple of (stop_loss, take_profit)
        """
        # Calculate ATR (Average True Range)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14).mean().iloc[-1]
        
        current_price = df['close'].iloc[-1]
        
        if signal == "BUY":
            stop_loss = current_price - (atr * 1.5)
            take_profit = current_price + (atr * 1.5 * risk_reward_ratio)
        else:  # SELL
            stop_loss = current_price + (atr * 1.5)
            take_profit = current_price - (atr * 1.5 * risk_reward_ratio)
        
        return stop_loss, take_profit
    
    def send_signal(self, signal: str, quantity: float = 0.01, 
                   stop_loss: float = 0.0, take_profit: float = 0.0) -> Dict:
        """
        Send signal to the trading platform via signal server
        
        Args:
            signal: "BUY", "SELL", or "EXIT"
            quantity: Lot size
            stop_loss: Stop loss price (0 to disable)
            take_profit: Take profit price (0 to disable)
            
        Returns:
            Response from signal server
        """
        payload = {
            "symbol": self.symbol,
            "action": signal,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "comment": f"Python MT5 Indicator - {datetime.now().strftime('%H:%M:%S')}"
        }
        
        try:
            response = requests.post(
                f"{self.signal_server_url}/signal",
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def run(self, quantity: float = 0.01, check_interval: int = 60):
        """
        Run the indicator in a loop, checking for signals periodically
        
        Args:
            quantity: Lot size for trades
            check_interval: Time in seconds between checks
        """
        if not self.connected:
            print("Not connected to MT5. Please call connect() first.")
            return
        
        print(f"Starting indicator monitoring for {self.symbol}")
        print(f"Checking every {check_interval} seconds")
        print("Press Ctrl+C to stop")
        
        last_signal = None
        
        try:
            while True:
                # Get latest rates
                df = self.get_rates(count=100)
                
                if df is not None and len(df) >= 20:
                    # Generate signal
                    signal = self.generate_signal(df)
                    
                    if signal and signal != last_signal:
                        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Signal detected: {signal}")
                        
                        # Calculate SL/TP
                        sl, tp = self.calculate_sl_tp(df, signal)
                        print(f"Stop Loss: {sl:.5f}, Take Profit: {tp:.5f}")
                        
                        # Send signal
                        result = self.send_signal(signal, quantity, sl, tp)
                        
                        if result.get('success'):
                            print(f"✓ Signal sent successfully: {result.get('message')}")
                        else:
                            print(f"✗ Failed to send signal: {result.get('error')}")
                        
                        last_signal = signal
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] No signal (last: {last_signal})")
                
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\nStopping indicator...")
        finally:
            self.disconnect()


# Example usage
if __name__ == "__main__":
    # Create indicator instance
    indicator = PythonMT5Indicator(
        symbol="EURUSD",
        timeframe=mt5.TIMEFRAME_M15,
        signal_server_url="http://localhost:8080"
    )
    
    # Connect to MT5 (optional - will use default terminal if not provided)
    # indicator.connect(login=123456, password="password", server="Broker-Server")
    indicator.connect()  # Use default MT5 terminal
    
    # Run the indicator (monitors and sends signals automatically)
    indicator.run(quantity=0.01, check_interval=60)  # Check every 60 seconds
    
    # Or manually check for signals:
    # df = indicator.get_rates(count=100)
    # signal = indicator.generate_signal(df)
    # if signal:
    #     sl, tp = indicator.calculate_sl_tp(df, signal)
    #     indicator.send_signal(signal, quantity=0.01, stop_loss=sl, take_profit=tp)

