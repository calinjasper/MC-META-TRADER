"""
Python Example - Sending Signals to Trading Platform

This example shows how to send trading signals from Python scripts
to the trading platform's signal server.
"""

import requests
import json
from typing import Optional, Dict


class SignalClient:
    """Client for sending signals to the trading platform"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        """
        Initialize signal client
        
        Args:
            base_url: Base URL of the signal server
        """
        self.base_url = base_url.rstrip('/')
        self.signal_endpoint = f"{self.base_url}/signal"
    
    def send_signal(self, symbol: str, action: str, quantity: float = 0.01,
                   stop_loss: float = 0.0, take_profit: float = 0.0,
                   comment: str = "Python Signal") -> Dict:
        """
        Send a trading signal
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            action: Action ("BUY", "SELL", "EXIT", "CLOSE", "MODIFY")
            quantity: Lot size (default: 0.01)
            stop_loss: Stop loss price (0 to disable)
            take_profit: Take profit price (0 to disable)
            comment: Signal comment
            
        Returns:
            Response dictionary
        """
        # Format 3: POST JSON
        payload = {
            "symbol": symbol,
            "action": action.upper(),
            "quantity": quantity,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "comment": comment
        }
        
        try:
            response = requests.post(
                self.signal_endpoint,
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
    
    def send_signal_get(self, symbol: str, action: str, quantity: float = 0.01,
                       stop_loss: float = 0.0, take_profit: float = 0.0) -> Dict:
        """
        Send signal using GET request (Format 1 or 2)
        
        Args:
            symbol: Trading symbol
            action: Action ("BUY", "SELL", "EXIT", "CLOSE")
            quantity: Lot size
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Response dictionary
        """
        params = {
            "symbol": symbol,
            "action": action.upper(),
            "qty": quantity
        }
        
        if stop_loss > 0:
            params["sl"] = stop_loss
        if take_profit > 0:
            params["tp"] = take_profit
        
        try:
            response = requests.get(
                self.signal_endpoint,
                params=params,
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_health(self) -> Dict:
        """Check signal server health"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_stats(self) -> Dict:
        """Get signal server statistics"""
        try:
            response = requests.get(f"{self.base_url}/stats", timeout=2)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "error": str(e)
            }


# Example usage
if __name__ == "__main__":
    # Create client
    client = SignalClient()
    
    # Check server health
    health = client.check_health()
    print(f"Server Status: {health.get('status')}")
    
    # Example 1: Simple BUY signal
    result = client.send_signal(
        symbol="EURUSD",
        action="BUY",
        quantity=0.01,
        comment="Python Strategy"
    )
    print(f"Signal Result: {result}")
    
    # Example 2: BUY with SL/TP
    result = client.send_signal(
        symbol="GBPUSD",
        action="BUY",
        quantity=0.1,
        stop_loss=1.2500,
        take_profit=1.2600,
        comment="Python Strategy with SL/TP"
    )
    print(f"Signal Result: {result}")
    
    # Example 3: SELL signal
    result = client.send_signal(
        symbol="USDJPY",
        action="SELL",
        quantity=0.05,
        comment="Python SELL Signal"
    )
    print(f"Signal Result: {result}")
    
    # Example 4: Close all positions for symbol
    result = client.send_signal(
        symbol="EURUSD",
        action="EXIT",
        comment="Close all EURUSD positions"
    )
    print(f"Exit Result: {result}")
    
    # Example 5: Using GET request (Format 1)
    result = client.send_signal_get(
        symbol="EURUSD",
        action="BUY",
        quantity=0.01
    )
    print(f"GET Signal Result: {result}")

