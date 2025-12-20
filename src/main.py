"""
Main Application Entry Point
"""

import sys
import os
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.gui.main_window import MainWindow

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
# File handler: INFO level (less verbose, important events only)
file_handler.setLevel(logging.INFO)
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

logging.info(f"Logging initialized. Log file: {log_file}")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("MT5 Trading Platform")
    
    # Set application style
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

