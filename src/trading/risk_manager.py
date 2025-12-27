"""
Risk Manager
Handles risk management rules (stop loss, take profit, position sizing)
"""

import logging
from typing import Optional, Dict
from ..mt5_connector import MT5Connector

logger = logging.getLogger(__name__)


class RiskManager:
    """Manages trading risk and position sizing"""
    
    def __init__(self, mt5_connector: MT5Connector):
        self.mt5 = mt5_connector
        self.max_risk_per_trade = 0.02  # 2% of account balance
        self.max_positions = 10
        self.min_lot_size = 0.01
        self.max_lot_size = 1.0
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                                stop_loss: float, risk_amount: float = None) -> float:
        """
        Calculate position size based on risk
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_amount: Risk amount in account currency (None for percentage-based)
            
        Returns:
            Lot size
        """
        if not self.mt5.is_connected():
            return self.min_lot_size
        
        symbol_info = self.mt5.get_symbol_info(symbol)
        if symbol_info is None:
            return self.min_lot_size
        
        account_info = self.mt5.get_account_info()
        if account_info is None:
            return self.min_lot_size
        
        # Calculate risk amount if not provided
        if risk_amount is None:
            risk_amount = account_info['balance'] * self.max_risk_per_trade
        
        # Calculate price difference
        price_diff = abs(entry_price - stop_loss)
        if price_diff == 0:
            return self.min_lot_size
        
        # Calculate lot size
        # Risk = (Price Difference * Lot Size * Contract Size) / Leverage
        contract_size = symbol_info.get('volume_min', 0.01)  # Simplified
        lot_size = (risk_amount * symbol_info.get('leverage', 1)) / (price_diff * contract_size * 100000)
        
        # Round to valid lot size
        lot_size = round(lot_size / symbol_info.get('volume_step', 0.01)) * symbol_info.get('volume_step', 0.01)
        
        # Clamp to valid range
        lot_size = max(self.min_lot_size, min(lot_size, self.max_lot_size))
        
        return lot_size
    
    def calculate_stop_loss(self, symbol: str, entry_price: float, 
                           order_type: str, atr_multiplier: float = 2.0) -> float:
        """
        Calculate stop loss based on ATR or fixed percentage
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            order_type: 'BUY' or 'SELL'
            atr_multiplier: ATR multiplier (if ATR available)
            
        Returns:
            Stop loss price
        """
        # Simple percentage-based stop loss (2%)
        stop_percentage = 0.02
        
        if order_type.upper() == 'BUY':
            stop_loss = entry_price * (1 - stop_percentage)
        else:
            stop_loss = entry_price * (1 + stop_percentage)
        
        return stop_loss
    
    def calculate_take_profit(self, symbol: str, entry_price: float,
                             order_type: str, risk_reward_ratio: float = 2.0,
                             stop_loss: float = None) -> float:
        """
        Calculate take profit based on risk-reward ratio
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            order_type: 'BUY' or 'SELL'
            risk_reward_ratio: Risk-reward ratio (e.g., 2.0 for 1:2)
            stop_loss: Stop loss price (if None, calculated automatically)
            
        Returns:
            Take profit price
        """
        if stop_loss is None:
            stop_loss = self.calculate_stop_loss(symbol, entry_price, order_type)
        
        risk = abs(entry_price - stop_loss)
        reward = risk * risk_reward_ratio
        
        if order_type.upper() == 'BUY':
            take_profit = entry_price + reward
        else:
            take_profit = entry_price - reward
        
        return take_profit
    
    def can_open_position(self, symbol: str = None) -> bool:
        """Check if a new position can be opened"""
        if not self.mt5.is_connected():
            return False
        
        positions = self.mt5.get_positions(symbol)
        return len(positions) < self.max_positions
    
    def validate_order(self, symbol: str, volume: float, 
                      entry_price: float, stop_loss: float, take_profit: float = 0.0) -> Dict[str, any]:
        """
        Validate an order before execution
        
        Args:
            symbol: Trading symbol
            volume: Order volume
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price (optional, defaults to 0.0 to skip TP validation)
        
        Returns:
            Dictionary with 'valid' (bool) and 'message' (str) keys
        """
        if not self.can_open_position():
            return {
                'valid': False,
                'message': f'Maximum positions ({self.max_positions}) reached'
            }
        
        if volume < self.min_lot_size:
            return {
                'valid': False,
                'message': f'Volume too small (minimum: {self.min_lot_size})'
            }
        
        if volume > self.max_lot_size:
            return {
                'valid': False,
                'message': f'Volume too large (maximum: {self.max_lot_size})'
            }
        
        symbol_info = self.mt5.get_symbol_info(symbol)
        if symbol_info is None:
            return {
                'valid': False,
                'message': f'Symbol {symbol} not found'
            }
        
        # Get minimum distance requirement
        trade_stops_level = symbol_info.get('trade_stops_level', 0)
        point = symbol_info.get('point', 0.0001)
        min_diff = trade_stops_level * point if trade_stops_level > 0 else 0
        
        # Check if stop loss is too close
        if stop_loss > 0 and min_diff > 0:
            sl_distance = abs(entry_price - stop_loss)
            if sl_distance < min_diff:
                return {
                    'valid': False,
                    'message': f'Stop loss too close (distance: {sl_distance:.5f}, minimum required: {min_diff:.5f}, trade_stops_level: {trade_stops_level})'
                }
        
        # Check if take profit is too close
        if take_profit > 0 and min_diff > 0:
            tp_distance = abs(take_profit - entry_price)
            if tp_distance < min_diff:
                return {
                    'valid': False,
                    'message': f'Take profit too close (distance: {tp_distance:.5f}, minimum required: {min_diff:.5f}, trade_stops_level: {trade_stops_level})'
                }
        
        return {
            'valid': True,
            'message': 'Order validated'
        }
    
    def calculate_risk_amount(self, symbol: str, entry_price: float, 
                              stop_loss: float, volume: float, 
                              order_type: str) -> Dict[str, float]:
        """
        Calculate risk amount and potential profit/loss
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            volume: Lot size
            order_type: 'BUY' or 'SELL'
            
        Returns:
            Dictionary with 'risk_amount', 'potential_profit', 'potential_loss'
        """
        if not self.mt5.is_connected():
            return {'risk_amount': 0.0, 'potential_profit': 0.0, 'potential_loss': 0.0}
        
        symbol_info = self.mt5.get_symbol_info(symbol)
        if symbol_info is None:
            return {'risk_amount': 0.0, 'potential_profit': 0.0, 'potential_loss': 0.0}
        
        # Calculate price difference
        price_diff = abs(entry_price - stop_loss)
        
        # Calculate contract value
        contract_size = symbol_info.get('trade_contract_size', 100000)
        point = symbol_info.get('point', 0.0001)
        
        # Risk amount = price difference * volume * contract size / point
        risk_amount = (price_diff / point) * volume * (contract_size / 100000)
        
        # Calculate potential profit (assuming 1:2 risk:reward)
        potential_profit = risk_amount * 2.0
        
        # Potential loss = risk amount
        potential_loss = risk_amount
        
        return {
            'risk_amount': risk_amount,
            'potential_profit': potential_profit,
            'potential_loss': potential_loss
        }
    
    def calculate_position_size_from_risk(self, symbol: str, entry_price: float,
                                         stop_loss: float, risk_percentage: float) -> float:
        """
        Calculate position size based on risk percentage
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_percentage: Risk as percentage of account balance (e.g., 0.02 for 2%)
            
        Returns:
            Lot size
        """
        if not self.mt5.is_connected():
            return self.min_lot_size
        
        account_info = self.mt5.get_account_info()
        if account_info is None:
            return self.min_lot_size
        
        risk_amount = account_info['balance'] * risk_percentage
        return self.calculate_position_size(symbol, entry_price, stop_loss, risk_amount)

