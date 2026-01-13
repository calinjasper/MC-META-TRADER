"""
MT5 Alert Listener
Monitors MT5 SMMA indicator alerts and forwards them to strategy manager
"""

import logging
import os
import time
import threading
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

# Import system log service for UI logging
try:
    from ..gui.system_log_service import system_log_service
except ImportError:
    system_log_service = None


class MT5AlertListener(QObject):
    """
    Listens for MT5 alerts from SMMA indicator and forwards to strategy manager
    """
    
    alert_received = pyqtSignal(dict)  # Emitted when alert is received
    
    def __init__(self, alert_file_path: Optional[str] = None, check_interval: float = 0.5):
        """
        Initialize alert listener
        
        Args:
            alert_file_path: Path to alert file (default: auto-detect from MT5)
            check_interval: How often to check for new alerts (seconds)
        """
        super().__init__()
        self.alert_file_path = alert_file_path or self._find_alert_file()
        self.check_interval = check_interval
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_file_position = 0
        self.processed_alerts: set = set()  # Track processed alerts to avoid duplicates
        self.alert_cache_size = 1000  # Keep last 1000 alert hashes
        
        if not self.alert_file_path:
            logger.warning("MT5AlertListener: Could not find alert file, alerts will not be monitored")
        else:
            logger.info(f"MT5AlertListener: Monitoring alert file: {self.alert_file_path}")
    
    def _find_alert_file(self) -> Optional[str]:
        """
        Find the MT5 alert file location
        Looks for smma_alerts.txt in common MT5 locations
        MT5 writes to MQL5/Files/ directory which is accessible via FILE_COMMON flag
        """
        # MT5 Common Files directory (where FILE_COMMON writes to)
        # This is typically: %AppData%\Roaming\MetaQuotes\Terminal\Common\Files\
        common_files_dir = Path(os.path.expanduser("~")) / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "Common" / "Files"
        common_files_path = common_files_dir / "smma_alerts.txt"
        
        # Ensure the directory exists (MT5 should create it, but just in case)
        common_files_dir.mkdir(parents=True, exist_ok=True)
        
        # Always use MT5 Common Files directory (this is where MT5 indicator writes)
        # Create empty file if it doesn't exist (MT5 will append to it)
        if not common_files_path.exists():
            common_files_path.touch()
            logger.info(f"MT5AlertListener: Created alert file at: {common_files_path}")
        else:
            logger.info(f"MT5AlertListener: Found existing alert file at: {common_files_path}")
        
        logger.info(f"MT5AlertListener: Monitoring MT5 Common Files directory: {common_files_path}")
        
        return str(common_files_path)
    
    def start_monitoring(self):
        """Start monitoring for alerts in background thread"""
        if self.running:
            logger.warning("MT5AlertListener: Already monitoring")
            return
        
        if not self.alert_file_path:
            logger.error("MT5AlertListener: Cannot start monitoring - alert file path not set")
            return
        
        # Log file status
        if os.path.exists(self.alert_file_path):
            file_size = os.path.getsize(self.alert_file_path)
            logger.info(f"MT5AlertListener: Alert file exists - {self.alert_file_path} (size: {file_size} bytes)")
        else:
            logger.warning(f"MT5AlertListener: Alert file does not exist yet - {self.alert_file_path}")
            logger.info("MT5AlertListener: Will create file when MT5 indicator writes first alert")
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"MT5AlertListener: Started monitoring for alerts (check interval: {self.check_interval}s)")
        logger.info(f"MT5AlertListener: Monitoring file: {self.alert_file_path}")
    
    def stop_monitoring(self):
        """Stop monitoring for alerts"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("MT5AlertListener: Stopped monitoring")
    
    def _monitor_loop(self):
        """Background thread loop to monitor alert file"""
        while self.running:
            try:
                self._check_for_alerts()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"MT5AlertListener: Error in monitor loop: {e}", exc_info=True)
                time.sleep(self.check_interval)
    
    def _check_for_alerts(self):
        """Check alert file for new alerts"""
        if not self.alert_file_path:
            return
        
        if not os.path.exists(self.alert_file_path):
            # File doesn't exist yet - this is normal when indicator hasn't written any alerts
            return
        
        try:
            with open(self.alert_file_path, 'r', encoding='utf-8') as f:
                # Seek to last known position
                f.seek(self.last_file_position)
                
                # Read new lines
                new_lines = f.readlines()
                
                if new_lines:
                    # Update position
                    self.last_file_position = f.tell()
                    
                    logger.debug(f"MT5AlertListener: Found {len(new_lines)} new alert line(s) in file")
                    
                    # Process each new alert
                    processed_count = 0
                    for line in new_lines:
                        line = line.strip()
                        if line:
                            alert = self.parse_alert(line)
                            if alert:
                                self._process_alert(alert)
                                processed_count += 1
                            else:
                                logger.warning(f"MT5AlertListener: Failed to parse alert line: {line[:100]}")
                    
                    if processed_count > 0:
                        logger.info(f"MT5AlertListener: Processed {processed_count} alert(s) from file")
        except FileNotFoundError:
            # File doesn't exist yet, that's okay
            logger.debug("MT5AlertListener: Alert file not found (will check again)")
        except PermissionError as e:
            logger.error(f"MT5AlertListener: Permission denied reading alert file: {e}")
            logger.error(f"MT5AlertListener: File path: {self.alert_file_path}")
        except Exception as e:
            logger.error(f"MT5AlertListener: Error reading alert file: {e}", exc_info=True)
            logger.error(f"MT5AlertListener: File path: {self.alert_file_path}")
    
    def parse_alert(self, alert_line: str) -> Optional[Dict]:
        """
        Parse alert line from file
        
        Format: timestamp|symbol|action|price|entry_level|indicator|timeframe
        Example: 2026-01-09 15:30:00|XAUUSDm|BUY|4473.919|4473.552|SMMA|15
        
        Returns:
            Dictionary with alert data or None if invalid
        """
        try:
            parts = alert_line.split('|')
            if len(parts) != 7:
                logger.warning(f"MT5AlertListener: Invalid alert format: {alert_line}")
                return None
            
            timestamp_str, symbol, action, price_str, entry_level_str, indicator, timeframe_str = parts
            
            # Parse timestamp (MT5 uses format: "2026.01.09 15:30:00" or "2026-01-09 15:30:00")
            timestamp = datetime.now()  # Default to now
            try:
                # Try MT5 format first: "2026.01.09 15:30:00"
                timestamp = datetime.strptime(timestamp_str, "%Y.%m.%d %H:%M:%S")
            except ValueError:
                try:
                    # Try standard format: "2026-01-09 15:30:00"
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        # Try without seconds: "2026.01.09 15:30"
                        timestamp = datetime.strptime(timestamp_str, "%Y.%m.%d %H:%M")
                    except ValueError:
                        logger.warning(f"MT5AlertListener: Could not parse timestamp '{timestamp_str}', using current time")
                        timestamp = datetime.now()
            
            # Parse numeric values
            price = float(price_str)
            entry_level = float(entry_level_str)
            timeframe = int(timeframe_str)
            
            # Validate action
            action = action.upper()
            if action not in ['BUY', 'SELL']:
                logger.warning(f"MT5AlertListener: Invalid action: {action}")
                return None
            
            # Validate indicator
            if indicator.upper() != 'SMMA':
                logger.debug(f"MT5AlertListener: Ignoring non-SMMA alert: {indicator}")
                return None
            
            alert = {
                'timestamp': timestamp,
                'symbol': symbol,
                'action': action,
                'price': price,
                'entry_level': entry_level,
                'indicator': indicator,
                'timeframe': timeframe,
                'raw_line': alert_line
            }
            
            return alert
            
        except Exception as e:
            logger.error(f"MT5AlertListener: Error parsing alert line '{alert_line}': {e}")
            return None
    
    def _process_alert(self, alert: Dict):
        """
        Process a parsed alert
        
        Args:
            alert: Parsed alert dictionary
        """
        # Create unique hash for duplicate detection
        alert_hash = f"{alert['symbol']}|{alert['action']}|{alert['timestamp'].strftime('%Y%m%d%H%M%S')}"
        
        # Check for duplicates
        if alert_hash in self.processed_alerts:
            logger.debug(f"MT5AlertListener: Duplicate alert ignored: {alert_hash}")
            return
        
        # Add to processed set
        self.processed_alerts.add(alert_hash)
        
        # Limit cache size
        if len(self.processed_alerts) > self.alert_cache_size:
            # Remove oldest entries (simple approach: clear and rebuild)
            self.processed_alerts = set(list(self.processed_alerts)[-self.alert_cache_size:])
        
        # Log alert with full details
        logger.info(f"MT5AlertListener: Alert received - {alert['action']} {alert['symbol']} @ {alert['price']:.5f} (TF: {alert['timeframe']})")
        logger.debug(f"MT5AlertListener: Full alert data: {alert}")
        
        # Log to system logs for UI display
        if system_log_service:
            alert_msg = f"MT5 Alert: {alert['action']} {alert['symbol']} @ {alert['price']:.5f} (TF: {alert['timeframe']})"
            system_log_service.log(
                log_type="ALERTS",
                message=alert_msg,
                strategy=""  # Will be filled by strategy manager if matched
            )
        
        # Emit signal for Qt integration
        self.alert_received.emit(alert)
    
    def get_recent_alerts(self, count: int = 10) -> List[Dict]:
        """
        Get recent alerts from file (for debugging/testing)
        
        Args:
            count: Number of recent alerts to return
            
        Returns:
            List of alert dictionaries
        """
        if not self.alert_file_path or not os.path.exists(self.alert_file_path):
            return []
        
        alerts = []
        try:
            with open(self.alert_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Get last N lines
                for line in lines[-count:]:
                    line = line.strip()
                    if line:
                        alert = self.parse_alert(line)
                        if alert:
                            alerts.append(alert)
        except Exception as e:
            logger.error(f"MT5AlertListener: Error reading recent alerts: {e}")
        
        return alerts
