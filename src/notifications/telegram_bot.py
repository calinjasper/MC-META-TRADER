"""
Telegram Bot Integration
Handles sending trade notifications to Telegram channel
"""

import logging
import requests
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for sending trade notifications"""
    
    API_BASE_URL = "https://api.telegram.org/bot"
    
    def __init__(self, bot_token: str, channel_id: str = None, channel_name: str = "TradingBot_Alerts"):
        """
        Initialize Telegram bot
        
        Args:
            bot_token: Telegram bot token from BotFather
            channel_id: Channel ID or username (e.g., "@channel" or "-1001234567890")
            channel_name: Channel name for auto-creation
        """
        self.bot_token = bot_token
        # Hard override: force known channel id and name regardless of config
        self.channel_id = "-1003453112937"
        self.channel_name = "MC_META_ALERTS_BOT"
        self.api_url = f"{self.API_BASE_URL}{bot_token}"
        self._initialized = False
        
        if bot_token:
            self._initialized = self._test_connection()
            if self._initialized and not channel_id:
                # Try to create or get channel
                self.channel_id = self.create_or_get_channel(channel_name)
    
    def _test_connection(self) -> bool:
        """Test bot connection"""
        try:
            response = requests.get(f"{self.api_url}/getMe", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    logger.info(f"Telegram bot connected: @{data['result']['username']}")
                    return True
            logger.error(f"Telegram bot connection failed: {response.text}")
            return False
        except Exception as e:
            logger.error(f"Error testing Telegram bot connection: {e}")
            return False
    
    def create_or_get_channel(self, channel_name: str) -> Optional[str]:
        """
        Create or get Telegram channel
        
        Args:
            channel_name: Name of the channel to create/get
            
        Returns:
            Channel ID or None if failed
        """
        if not self._initialized:
            logger.error("Telegram bot not initialized")
            return None
        
        # Try to create channel
        try:
            # Note: Creating channels via bot API requires the bot to be a creator
            # For now, we'll use the channel name as identifier
            # User should add bot as admin to channel manually or provide channel ID
            logger.info(f"Channel creation: Use channel name '{channel_name}' or provide channel ID")
            return f"@{channel_name}" if not channel_name.startswith("@") else channel_name
        except Exception as e:
            logger.error(f"Error creating/getting channel: {e}")
            return None
    
    def send_message(self, text: str) -> bool:
        """
        Send message to Telegram channel
        
        Args:
            text: Message text to send
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            logger.warning("Telegram bot not initialized, skipping message")
            return False
        
        if not self.channel_id:
            logger.warning("Telegram channel ID not set, skipping message")
            return False
        
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                "chat_id": self.channel_id,
                "text": text,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    logger.debug("Telegram message sent successfully")
                    return True
                else:
                    logger.error(f"Telegram API error: {data.get('description', 'Unknown error')}")
            else:
                logger.error(f"Telegram HTTP error: {response.status_code} - {response.text}")
            
            return False
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def format_trade_entry(self, ticker: str, volume: float, strategy_name: str,
                          entry_price: float, entry_time: datetime, entry_condition: str) -> str:
        """
        Format trade entry message
        
        Args:
            ticker: Trading symbol
            volume: Trade volume
            strategy_name: Strategy name
            entry_price: Entry price
            entry_time: Entry time
            entry_condition: Entry condition description
            
        Returns:
            Formatted message string
        """
        entry_time_str = entry_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(entry_time, datetime) else str(entry_time)
        
        message = (
            f"<b>📈 TRADE ENTRY</b>\n\n"
            f"<b>Ticker:</b> {ticker}\n"
            f"<b>Volume:</b> {volume}\n"
            f"<b>Strategy:</b> {strategy_name}\n"
            f"<b>Entry Price:</b> {entry_price:.5f}\n"
            f"<b>Entry Time:</b> {entry_time_str}\n"
            f"<b>Entry Condition:</b> {entry_condition}"
        )
        
        return message
    
    def format_trade_exit(self, ticker: str, volume: float, strategy_name: str,
                         entry_price: float, entry_time: datetime, entry_condition: str,
                         exit_price: float, exit_time: datetime, exit_condition: str,
                         profit: float = None) -> str:
        """
        Format trade exit message
        
        Args:
            ticker: Trading symbol
            volume: Trade volume
            strategy_name: Strategy name
            entry_price: Entry price
            entry_time: Entry time
            entry_condition: Entry condition description
            exit_price: Exit price
            exit_time: Exit time
            exit_condition: Exit condition (SL, TP, Manual)
            profit: Actual profit from trade (in account currency). If None, will calculate from prices.
            
        Returns:
            Formatted message string
        """
        entry_time_str = entry_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(entry_time, datetime) else str(entry_time)
        exit_time_str = exit_time.strftime("%Y-%m-%d %H:%M:%S") if isinstance(exit_time, datetime) else str(exit_time)
        
        # Calculate P&L - use actual profit if available, otherwise calculate from prices
        if profit is not None:
            pnl = profit  # Use actual profit from trade history/MT5
        else:
            # Fallback: approximate calculation for forex
            # This is less accurate but better than nothing
            pnl = (exit_price - entry_price) * volume * 100000
        
        pnl_emoji = "✅" if pnl >= 0 else "❌"
        pnl_str = f"{pnl:+.2f}"
        
        message = (
            f"<b>📉 TRADE EXIT {pnl_emoji}</b>\n\n"
            f"<b>Ticker:</b> {ticker}\n"
            f"<b>Volume:</b> {volume}\n"
            f"<b>Strategy:</b> {strategy_name}\n"
            f"<b>Entry Price:</b> {entry_price:.5f}\n"
            f"<b>Entry Time:</b> {entry_time_str}\n"
            f"<b>Entry Condition:</b> {entry_condition}\n"
            f"<b>Exit Price:</b> {exit_price:.5f}\n"
            f"<b>Exit Time:</b> {exit_time_str}\n"
            f"<b>Exit Condition:</b> {exit_condition}\n"
            f"<b>P&L:</b> {pnl_str}"
        )
        
        return message
    
    def send_trade_entry(self, ticker: str, volume: float, strategy_name: str,
                        entry_price: float, entry_time: datetime, entry_condition: str) -> bool:
        """Send trade entry notification"""
        message = self.format_trade_entry(
            ticker, volume, strategy_name, entry_price, entry_time, entry_condition
        )
        return self.send_message(message)
    
    def send_trade_exit(self, ticker: str, volume: float, strategy_name: str,
                       entry_price: float, entry_time: datetime, entry_condition: str,
                       exit_price: float, exit_time: datetime, exit_condition: str,
                       profit: float = None) -> bool:
        """Send trade exit notification"""
        message = self.format_trade_exit(
            ticker, volume, strategy_name, entry_price, entry_time, entry_condition,
            exit_price, exit_time, exit_condition, profit
        )
        return self.send_message(message)

