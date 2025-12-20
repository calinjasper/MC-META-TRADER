"""
Signal Parser
Parses different signal formats from external platforms
Supports 4 formats as per STOXXO documentation
"""

import logging
from typing import Dict, Optional, Any
from urllib.parse import parse_qs, urlparse

logger = logging.getLogger(__name__)


class SignalParser:
    """Parse signals from different formats"""
    
    def __init__(self):
        self.supported_formats = ['format1', 'format2', 'format3', 'format4']
    
    def parse_signal(self, request_data: Dict[str, Any], method: str = 'GET') -> Optional[Dict[str, Any]]:
        """
        Parse signal from request data
        
        Args:
            request_data: Request data (query params for GET, JSON body for POST)
            method: HTTP method ('GET' or 'POST')
            
        Returns:
            Parsed signal dictionary or None if parsing fails
        """
        try:
            if method == 'GET':
                return self._parse_get_signal(request_data)
            elif method == 'POST':
                return self._parse_post_signal(request_data)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
        except Exception as e:
            logger.error(f"Error parsing signal: {e}", exc_info=True)
            return None
    
    def _parse_get_signal(self, query_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse GET request signal (Format 1 or Format 2)
        
        Format 1: /signal?symbol=EURUSD&action=BUY&qty=1
        Format 2: /signal?symbol=EURUSD&action=BUY&qty=1&sl=1.0800&tp=1.0900
        """
        # Extract parameters
        symbol = query_params.get('symbol') or query_params.get('Symbol')
        action = query_params.get('action') or query_params.get('Action') or query_params.get('signal')
        qty = query_params.get('qty') or query_params.get('Qty') or query_params.get('quantity') or query_params.get('Quantity')
        sl = query_params.get('sl') or query_params.get('SL') or query_params.get('stop_loss')
        tp = query_params.get('tp') or query_params.get('TP') or query_params.get('take_profit')
        comment = query_params.get('comment') or query_params.get('Comment') or query_params.get('strategy')
        
        if not symbol or not action:
            logger.error("Missing required parameters: symbol and action")
            return None
        
        # Normalize action
        action = action.upper()
        if action not in ['BUY', 'SELL', 'EXIT', 'CLOSE', 'MODIFY']:
            logger.error(f"Invalid action: {action}")
            return None
        
        # Parse quantity
        try:
            quantity = float(qty) if qty else 0.01  # Default lot size
        except (ValueError, TypeError):
            quantity = 0.01
        
        # Parse SL/TP
        stop_loss = float(sl) if sl else 0.0
        take_profit = float(tp) if tp else 0.0
        
        signal = {
            'symbol': symbol.upper(),
            'action': action,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'comment': comment or 'External Signal',
            'format': 'format1' if not sl and not tp else 'format2'
        }
        
        logger.info(f"Parsed GET signal: {signal}")
        return signal
    
    def _parse_post_signal(self, json_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse POST request signal (Format 3 or Format 4)
        
        Format 3: JSON with standard fields
        Format 4: JSON with extended/custom fields
        """
        # Extract standard fields
        symbol = json_data.get('symbol') or json_data.get('Symbol')
        action = json_data.get('action') or json_data.get('Action') or json_data.get('signal') or json_data.get('order_type')
        quantity = json_data.get('quantity') or json_data.get('Qty') or json_data.get('qty') or json_data.get('volume') or json_data.get('lot')
        stop_loss = json_data.get('stop_loss') or json_data.get('SL') or json_data.get('sl')
        take_profit = json_data.get('take_profit') or json_data.get('TP') or json_data.get('tp')
        comment = json_data.get('comment') or json_data.get('Comment') or json_data.get('strategy') or json_data.get('message')
        
        if not symbol or not action:
            logger.error("Missing required parameters: symbol and action")
            return None
        
        # Normalize action
        action = action.upper()
        if action not in ['BUY', 'SELL', 'EXIT', 'CLOSE', 'MODIFY']:
            logger.error(f"Invalid action: {action}")
            return None
        
        # Parse quantity
        try:
            qty = float(quantity) if quantity else 0.01
        except (ValueError, TypeError):
            qty = 0.01
        
        # Parse SL/TP
        sl = float(stop_loss) if stop_loss else 0.0
        tp = float(take_profit) if take_profit else 0.0
        
        # Determine format based on presence of extended fields
        has_extended = any(key in json_data for key in ['price', 'order_type', 'deviation', 'magic', 'expiration'])
        format_type = 'format4' if has_extended else 'format3'
        
        signal = {
            'symbol': symbol.upper(),
            'action': action,
            'quantity': qty,
            'stop_loss': sl,
            'take_profit': tp,
            'comment': comment or 'External Signal',
            'format': format_type
        }
        
        # Add extended fields for format 4
        if format_type == 'format4':
            signal['price'] = json_data.get('price', 0.0)
            signal['order_type'] = json_data.get('order_type', 'MARKET')
            signal['deviation'] = json_data.get('deviation', 20)
            signal['magic'] = json_data.get('magic', 234000)
            signal['expiration'] = json_data.get('expiration')
        
        logger.info(f"Parsed POST signal: {signal}")
        return signal
    
    def validate_signal(self, signal: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate parsed signal
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not signal:
            return False, "Signal is None or empty"
        
        required_fields = ['symbol', 'action', 'quantity']
        for field in required_fields:
            if field not in signal:
                return False, f"Missing required field: {field}"
        
        # Validate action
        if signal['action'] not in ['BUY', 'SELL', 'EXIT', 'CLOSE', 'MODIFY']:
            return False, f"Invalid action: {signal['action']}"
        
        # Validate quantity
        if signal['quantity'] <= 0:
            return False, f"Invalid quantity: {signal['quantity']}"
        
        # Validate SL/TP if provided
        if signal.get('stop_loss', 0) < 0:
            return False, "Stop loss cannot be negative"
        
        if signal.get('take_profit', 0) < 0:
            return False, "Take profit cannot be negative"
        
        return True, None

