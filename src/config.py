"""
Configuration Management
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Configuration manager for the trading platform"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Default to config/config.json relative to project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "config.json"
        
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> None:
        """Load configuration from JSON file"""
        default_config = self._get_default_config()
        
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                loaded_config = json.load(f)
                # Merge with defaults to ensure all keys exist
                self._config = self._merge_config(default_config, loaded_config)
        else:
            # Create default config
            self._config = default_config
            self.save()
    
    def _merge_config(self, default: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        """Merge loaded config with defaults"""
        merged = default.copy()
        for key, value in loaded.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                merged[key] = self._merge_config(merged[key], value)
            else:
                merged[key] = value
        return merged
    
    def save(self) -> None:
        """Save configuration to JSON file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value by key (supports dot notation)"""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "mt5": {
                "path": "",  # Will be auto-detected if empty
                "login": 277285010,
                "password": "Ecj@200131",
                "server": "Exness-MT5Trial5",
                "timeout": 10000
            },
            "trading": {
                "default_symbol": "EURUSD",
                "default_lot_size": 0.01,
                "default_slippage": 3,
                "max_positions": None
            },
            "ui": {
                "theme": "dark",
                "update_interval_ms": 1000
            },
            "data_feed": {
                "update_interval_seconds": 0.05,  # 20 updates per second for maximum real-time accuracy
                "real_time_updates": True,
                "symbols": []  # Saved symbols for persistence
            },
            "indicators": {
                "default_period": 14
            },
            "signal_server": {
                "enabled": True,
                "port": 8080,
                "host": "0.0.0.0",
                "cancel_previous": True,
                "stop_reverse": False,
                "allowed_ips": []  # Empty list means allow all
            },
            "telegram": {
                "enabled": True,
                "bot_token": "8132953143:AAGOV_S8Cp6gg6hgM3auMY34Q-Mv0OKTTVk",
                "channel_id": "-1003453112937",
                "channel_name": "MC_META_ALERTS_BOT",
                "auto_create_channel": False
            }
        }

