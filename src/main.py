"""
Main Application Entry Point
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

from src.gui.main_window import MainWindow
from src.data.pocketbase_manager import PocketBaseManager
from src.config import Config
from src.utils.device_utils import get_local_ip_address

# Configure logging to both console and file
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "trading_platform.log"

# Use RotatingFileHandler to prevent log files from growing too large
from logging.handlers import RotatingFileHandler

# Create rotating file handler (max 10MB per file, keep 5 backup files)
file_handler = RotatingFileHandler(
    log_file, 
    mode='a', 
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5,  # Keep 5 backup files
    encoding='utf-8'
)
# File handler: DEBUG level (for debugging)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
# Console handler: DEBUG level (verbose for development)
console_handler.setLevel(logging.DEBUG)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Enable DEBUG for chart widget specifically
chart_logger = logging.getLogger('src.gui.chart_widget')
chart_logger.setLevel(logging.DEBUG)

# Enable DEBUG for data feed
data_feed_logger = logging.getLogger('src.data_feed')
data_feed_logger.setLevel(logging.DEBUG)

# Enable DEBUG for MT5 connector
mt5_logger = logging.getLogger('src.mt5_connector')
mt5_logger.setLevel(logging.DEBUG)

# Enable DEBUG for PocketBase manager
pb_logger = logging.getLogger('src.data.pocketbase_manager')
pb_logger.setLevel(logging.DEBUG)

logging.info(f"Logging initialized. Log file: {log_file}")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("MT5 Trading Platform")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Load configuration
    config = Config()
    
    # Check if data storage is enabled
    data_storage_enabled = config.get('data_storage.enabled', True)
    pocketbase_url = config.get('data_storage.pocketbase_url', 'http://192.168.173.112:8090')
    
    # Get or detect device ID
    device_id = config.get('data_storage.device_id')
    if not device_id:
        device_id = get_local_ip_address()
        if device_id:
            config.set('data_storage.device_id', device_id)
            config.save()
            logging.info(f"Auto-detected and saved device_id: {device_id}")
        else:
            logging.warning("Could not detect device ID")
            device_id = 'unknown'
    else:
        logging.info(f"Using configured device_id: {device_id}")
    
    # Create MainWindow first (needed for telegram_bot)
    window = MainWindow()
    
    # Initialize PocketBase Manager (optional - won't fail if server not running)
    pb_manager = None
    if data_storage_enabled:
        try:
            # Get admin credentials for deletion operations
            admin_email = config.get('data_storage.admin_email', '')
            admin_password = config.get('data_storage.admin_password', '')
            
            # Initialize PocketBase with device_id, telegram_bot, and admin credentials
            pb_manager = PocketBaseManager(
                base_url=pocketbase_url,
                device_id=device_id,
                telegram_bot=window.telegram_bot if hasattr(window, 'telegram_bot') else None,
                admin_email=admin_email if admin_email else None,
                admin_password=admin_password if admin_password else None
            )
            
            if pb_manager.health_check():
                logging.info("PocketBase connection successful")
                
                # Check if we need to clear existing data (one-time)
                clear_existing = config.get('data_storage.clear_existing_data', False)
                logging.info(f"Data clearing flag status: clear_existing_data = {clear_existing}")
                if clear_existing:
                    logging.warning("=" * 60)
                    logging.warning("CLEARING ALL EXISTING DATA FROM POCKETBASE (ONE-TIME OPERATION)")
                    logging.warning("=" * 60)
                    collections_to_clear = ['ticks', 'ohlc', 'signals', 'indicators']
                    logging.info(f"Collections to clear: {collections_to_clear}")
                    if pb_manager.clear_all_data(collections_to_clear):
                        logging.info("=" * 60)
                        logging.info("DATA CLEARING COMPLETED SUCCESSFULLY")
                        logging.info("=" * 60)
                    else:
                        logging.error("=" * 60)
                        logging.error("DATA CLEARING FAILED - CHECK LOGS ABOVE FOR DETAILS")
                        logging.error("=" * 60)
                    
                    # Mark as done
                    config.set('data_storage.clear_existing_data', False)
                    config.save()
                    logging.info("Data clearing flag set to False - will not clear again on next run")
                else:
                    logging.info("Data clearing skipped - clear_existing_data flag is False")
                    logging.info("To clear data again, set 'data_storage.clear_existing_data' to true in config.json")
            else:
                logging.warning("PocketBase server not reachable - data storage disabled")
                pb_manager = None
        except Exception as e:
            logging.warning(f"PocketBase initialization failed: {e} - continuing without database storage")
            pb_manager = None
    else:
        logging.info("Data storage disabled in configuration - PocketBase not initialized")
    
    # Pass PocketBase manager to components that need it
    if pb_manager:
        try:
            # Update telegram_bot reference in case it was initialized after PocketBase
            if hasattr(window, 'telegram_bot') and window.telegram_bot:
                pb_manager.telegram_bot = window.telegram_bot
            
            # Pass to data feed (for tick and OHLC storage)
            if hasattr(window, 'data_feed'):
                window.data_feed.pb_manager = pb_manager
                logging.info("PocketBase manager attached to DataFeed")
            
            # Pass to trade history
            if hasattr(window, 'order_manager') and hasattr(window.order_manager, 'trade_history'):
                window.order_manager.trade_history.pb_manager = pb_manager
                logging.info("PocketBase manager attached to TradeHistory")
            
            # Pass to chart widget
            if hasattr(window, 'chart_widget'):
                window.chart_widget.pb_manager = pb_manager
                logging.info("PocketBase manager attached to ChartWidget")
        except Exception as e:
            logging.error(f"Error attaching PocketBase manager: {e}")
    
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

