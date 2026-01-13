"""
Device Utilities
Functions for device identification and IP address detection
"""

import socket
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_local_ip_address() -> Optional[str]:
    """
    Get the local IP address of this machine (not localhost)
    
    Returns:
        IP address string (e.g., "192.168.1.100") or None if detection fails
    """
    try:
        # Connect to a remote address to determine local IP
        # This doesn't actually send data, just determines the route
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connect to a public DNS server (doesn't actually connect)
            s.connect(('8.8.8.8', 80))
            ip_address = s.getsockname()[0]
            s.close()
            logger.info(f"Detected local IP address: {ip_address}")
            return ip_address
        except Exception as e:
            logger.warning(f"Failed to get IP via socket connection: {e}")
            s.close()
    except Exception as e:
        logger.error(f"Error getting local IP address: {e}")
    
    # Fallback: Try to get hostname
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        if ip_address and ip_address != '127.0.0.1':
            logger.info(f"Detected IP via hostname: {ip_address}")
            return ip_address
    except Exception as e:
        logger.warning(f"Failed to get IP via hostname: {e}")
    
    logger.warning("Could not detect local IP address, using hostname as fallback")
    try:
        return socket.gethostname()
    except:
        return None


def validate_ip_address(ip: str) -> bool:
    """
    Validate IP address format
    
    Args:
        ip: IP address string to validate
        
    Returns:
        True if valid IP format, False otherwise
    """
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except:
        return False

