"""
Configuration for PocketBase Data Viewer
"""

import json
from pathlib import Path

# Load config from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "config" / "config.json"

def load_config():
    """Load configuration from config.json"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load config.json: {e}")
        return {}

config = load_config()
data_storage = config.get('data_storage', {})
mysql_config = config.get('mysql', {})

# PocketBase Configuration (for trades and signals)
POCKETBASE_URL = data_storage.get('pocketbase_url', 'http://192.168.173.112:8090')
ADMIN_EMAIL = data_storage.get('admin_email', '')
ADMIN_PASSWORD = data_storage.get('admin_password', '')

# MySQL Configuration (for ticks and minute data)
MYSQL_HOST = mysql_config.get('host', '127.0.0.1')
MYSQL_PORT = mysql_config.get('port', 3306)
MYSQL_USERNAME = mysql_config.get('username', 'root')
MYSQL_PASSWORD = mysql_config.get('password', 'lokesh')

# Application Configuration
HOST = "0.0.0.0"
PORT = 8081
DEBUG = True

# Data Limits
MAX_RECORDS_PER_REQUEST = 10000
DEFAULT_LIMIT = 1000

# Static and Template Directories
STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Reference Project Configuration (for loading strategies)
REFERENCE_PROJECT_PATH = Path("D:/DEV__PHASE---2 MC-META-TRADER-----")
REFERENCE_STRATEGY_DIR = REFERENCE_PROJECT_PATH / "src" / "strategy"
REFERENCE_INDICATORS_DIR = REFERENCE_PROJECT_PATH / "indicators"

