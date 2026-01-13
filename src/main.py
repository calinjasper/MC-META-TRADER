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
from src.utils.font_utils import create_font, FontSize, FontWeight

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
    
    # Set default application font with stylish fonts
    default_font = create_font(FontSize.NORMAL, FontWeight.REGULAR)
    app.setFont(default_font)
    logging.info(f"Application font set: {default_font.family()}, size: {default_font.pointSize()}pt")
    
    # Initialize PocketBase Manager (optional - won't fail if server not running)
    pb_manager = None
    try:
        pb_manager = PocketBaseManager('http://192.168.173.112:8090')
        if pb_manager.health_check():
            logging.info("PocketBase connection successful")
        else:
            logging.warning("PocketBase server not reachable - data storage disabled")
            pb_manager = None
    except Exception as e:
        logging.warning(f"PocketBase initialization failed: {e} - continuing without database storage")
        pb_manager = None
    
    # Create and show main window
    window = MainWindow()
    
    # Pass PocketBase manager to components that need it
    if pb_manager:
        try:
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

