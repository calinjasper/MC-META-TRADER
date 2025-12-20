"""
Python MT5 Custom Strategy Example
Create your own custom trading strategy in Python

This example shows how to create a custom strategy class
that can be easily extended with your own logic.
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import requests
from typing import Optional, Dict, List
from datetime import datetime
from abc import ABC, abstractmethod


class BaseStrategy(ABC):
    """Base class for custom trading strategies"""
    
    def __init__(self, symbol: str, timeframe: int = mt5.TIMEFRAME_M15):
        self.symbol = symbol
        self.timeframe = timeframe
    
    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate all indicators needed for the strategy"""
        pass
    
    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, indicators: Dict) -> Optional[str]:
        """Generate trading signal based on indicators"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, df: pd.DataFrame) -> float:
        """Calculate position size based on risk management"""
        pass
    
    @abstractmethod
    def calculate_sl_tp(self, df: pd.DataFrame, signal: str) -> tuple[float, float]:
        """Calculate stop loss and take profit"""
        pass


class MovingAverageCrossoverStrategy(BaseStrategy):
    """Simple Moving Average Crossover Strategy"""
    
    def __init__(self, symbol: str, fast_period: int = 10, slow_period: int = 20,
                 timeframe: int = mt5.TIMEFRAME_M15):
        super().__init__(symbol, timeframe)
        self.fast_period = fast_period
        self.slow_period = slow_period
    
    def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate moving averages"""
        return {
            'sma_fast': df['close'].rolling(window=self.fast_period).mean(),
            'sma_slow': df['close'].rolling(window=self.slow_period).mean()
        }
    
    def generate_signal(self, df: pd.DataFrame, indicators: Dict) -> Optional[str]:
        """Generate signal on MA crossover"""
        sma_fast = indicators['sma_fast']
        sma_slow = indicators['sma_slow']
        
        if len(df) < self.slow_period + 1:
            return None
        
        # Check for crossover
        current_fast = sma_fast.iloc[-1]
        current_slow = sma_slow.iloc[-1]
        prev_fast = sma_fast.iloc[-2]
        prev_slow = sma_slow.iloc[-2]
        
        # Golden cross (BUY)
        if prev_fast <= prev_slow and current_fast > current_slow:
            return "BUY"
        
        # Death cross (SELL)
        if prev_fast >= prev_slow and current_fast < current_slow:
            return "SELL"
        
        return None
    
    def calculate_position_size(self, df: pd.DataFrame) -> float:
        """Fixed position size"""
        return 0.01
    
    def calculate_sl_tp(self, df: pd.DataFrame, signal: str) -> tuple[float, float]:
        """Calculate SL/TP based on ATR"""
        # Calculate ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = true_range.rolling(window=14).mean().iloc[-1]
        
        current_price = df['close'].iloc[-1]
        
        if signal == "BUY":
            sl = current_price - (atr * 2)
            tp = current_price + (atr * 4)  # 1:2 risk-reward
        else:
            sl = current_price + (atr * 2)
            tp = current_price - (atr * 4)
        
        return sl, tp


class RSIStrategy(BaseStrategy):
    """RSI-based mean reversion strategy"""
    
    def __init__(self, symbol: str, rsi_period: int = 14, oversold: float = 30,
                 overbought: float = 70, timeframe: int = mt5.TIMEFRAME_M15):
        super().__init__(symbol, timeframe)
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
    
    def calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate RSI"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return {'rsi': rsi}
    
    def generate_signal(self, df: pd.DataFrame, indicators: Dict) -> Optional[str]:
        """Generate signal based on RSI levels"""
        rsi = indicators['rsi']
        
        if len(rsi) < 2:
            return None
        
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        
        # Buy when RSI crosses above oversold
        if prev_rsi <= self.oversold and current_rsi > self.oversold:
            return "BUY"
        
        # Sell when RSI crosses below overbought
        if prev_rsi >= self.overbought and current_rsi < self.overbought:
            return "SELL"
        
        return None
    
    def calculate_position_size(self, df: pd.DataFrame) -> float:
        """Fixed position size"""
        return 0.01
    
    def calculate_sl_tp(self, df: pd.DataFrame, signal: str) -> tuple[float, float]:
        """Calculate SL/TP based on recent price range"""
        recent_range = df['high'].tail(20).max() - df['low'].tail(20).min()
        current_price = df['close'].iloc[-1]
        
        if signal == "BUY":
            sl = current_price - (recent_range * 0.3)
            tp = current_price + (recent_range * 0.6)
        else:
            sl = current_price + (recent_range * 0.3)
            tp = current_price - (recent_range * 0.6)
        
        return sl, tp


class StrategyRunner:
    """Runs a strategy and sends signals to the trading platform"""
    
    def __init__(self, strategy: BaseStrategy, signal_server_url: str = "http://localhost:8080"):
        self.strategy = strategy
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
        return True
    
    def get_rates(self, count: int = 100) -> Optional[pd.DataFrame]:
        """Get historical rates"""
        if not self.connected:
            return None
        
        rates = mt5.copy_rates_from_pos(
            self.strategy.symbol, 
            self.strategy.timeframe, 
            0, 
            count
        )
        
        if rates is None:
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    
    def send_signal(self, signal: str, quantity: float, sl: float, tp: float) -> Dict:
        """Send signal to platform"""
        payload = {
            "symbol": self.strategy.symbol,
            "action": signal,
            "quantity": quantity,
            "stop_loss": sl,
            "take_profit": tp,
            "comment": f"{self.strategy.__class__.__name__} - {datetime.now().strftime('%H:%M:%S')}"
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
            return {"success": False, "error": str(e)}
    
    def run_once(self) -> Optional[Dict]:
        """Run strategy once and return result"""
        df = self.get_rates(count=100)
        if df is None or len(df) < 20:
            return None
        
        indicators = self.strategy.calculate_indicators(df)
        signal = self.strategy.generate_signal(df, indicators)
        
        if signal:
            quantity = self.strategy.calculate_position_size(df)
            sl, tp = self.strategy.calculate_sl_tp(df, signal)
            result = self.send_signal(signal, quantity, sl, tp)
            return {
                "signal": signal,
                "quantity": quantity,
                "sl": sl,
                "tp": tp,
                "result": result
            }
        
        return None


# Example usage
if __name__ == "__main__":
    # Create a strategy
    strategy = MovingAverageCrossoverStrategy(
        symbol="EURUSD",
        fast_period=10,
        slow_period=20
    )
    
    # Or use RSI strategy:
    # strategy = RSIStrategy(symbol="EURUSD", oversold=30, overbought=70)
    
    # Create runner
    runner = StrategyRunner(strategy, signal_server_url="http://localhost:8080")
    
    # Connect to MT5
    runner.connect()  # Or provide credentials: runner.connect(login=123, password="pass", server="server")
    
    # Run strategy once
    result = runner.run_once()
    if result:
        print(f"Signal: {result['signal']}")
        print(f"Result: {result['result']}")
    
    # Or run in a loop:
    # import time
    # while True:
    #     runner.run_once()
    #     time.sleep(60)  # Check every minute

