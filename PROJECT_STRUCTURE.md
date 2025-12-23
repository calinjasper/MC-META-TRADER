# Project Structure

This document describes the organized structure of the MC-META-TRADER project.

## Directory Structure

```
MC-META-TRADER/
│
├── src/                          # Main application source code
│   ├── main.py                  # Application entry point
│   ├── config.py                # Configuration management
│   ├── mt5_connector.py         # MetaTrader 5 connector
│   ├── data_feed.py             # Data feed manager
│   │
│   ├── gui/                     # GUI components
│   │   ├── main_window.py       # Main application window
│   │   ├── chart_widget.py      # TradingView chart widget
│   │   └── ...                  # Other GUI panels
│   │
│   ├── trading/                 # Trading logic
│   │   ├── order_manager.py     # Order management
│   │   ├── trade_history.py     # Trade history tracking
│   │   └── ...                  # Risk management, position tracking
│   │
│   ├── strategy/                 # Trading strategies
│   │   ├── base_strategy.py     # Base strategy class
│   │   ├── strategy_manager.py  # Strategy manager
│   │   └── ...                  # Individual strategies
│   │
│   ├── indicators/               # Technical indicators
│   │   ├── base_indicator.py    # Base indicator class
│   │   └── ...                  # RSI, EMA, MACD, etc.
│   │
│   ├── data/                     # Data management
│   │   └── pocketbase_manager.py # PocketBase integration
│   │
│   ├── signal_routing/           # Signal routing system
│   ├── notifications/            # Notification services
│   ├── utils/                    # Utility functions
│   └── tools/                    # Internal tools
│
├── scripts/                      # Utility scripts
│   ├── setup/                    # Setup and configuration scripts
│   │   ├── setup_pocketbase_collections.py
│   │   ├── add_timestamp_ist_field.py
│   │   └── ...
│   │
│   ├── database/                 # Database operations
│   │   ├── migrate_existing_ticks.py
│   │   ├── consolidate_ticks.py
│   │   └── ...
│   │
│   ├── export/                   # Data export scripts
│   │   ├── export_ticks_to_csv.py
│   │   └── view_symbol_ticks.py
│   │
│   └── legacy/                   # Legacy scripts
│
├── tests/                        # Test scripts
│   ├── test_ist_conversion.py
│   ├── test_volume_fix.py
│   ├── test_m1_ohlc_storage.py
│   └── ...
│
├── tools/                        # Diagnostic and verification tools
│   ├── check_ist_timestamps.py
│   ├── verify_ticks_setup.py
│   └── ...
│
├── docs/                         # Documentation
│   ├── README_POCKETBASE.md
│   ├── POCKETBASE_INTEGRATION_COMPLETE.md
│   └── ...
│
├── examples/                     # Example code
│   └── signals/                  # Signal examples
│
├── config/                       # Configuration files
│   └── config.json
│
├── data/                         # Data files
│   ├── trade_history.json
│   └── backups/
│
├── logs/                         # Log files
│   └── trading_platform.log
│
├── pocketbase/                   # PocketBase database
│   ├── pocketbase.exe
│   ├── pb_data/                  # Database files
│   └── pb_migrations/            # Database migrations
│
├── requirements.txt              # Python dependencies
├── start_trading_system.bat     # Windows startup script
├── start_trading_system.sh      # Linux/Mac startup script
└── README.md                     # Main project README
```

## Quick Reference

### Running Scripts

All scripts should be run from the project root directory:

```bash
# Setup PocketBase
python scripts/setup/setup_pocketbase_collections.py

# View ticks
python scripts/export/view_symbol_ticks.py --symbol XAUUSDm

# Run tests
python tests/test_volume_fix.py

# Check data
python tools/check_ist_timestamps.py
```

### Main Application

```bash
# Start the trading system
python src/main.py

# Or use the startup script
./start_trading_system.sh  # Linux/Mac
start_trading_system.bat   # Windows
```

## Directory Purposes

- **src/** - Core application code (production code)
- **scripts/** - Utility scripts for setup, database operations, and exports
- **tests/** - Test scripts for verifying functionality
- **tools/** - Diagnostic tools for checking system status
- **docs/** - Project documentation
- **examples/** - Example code and tutorials
- **config/** - Configuration files
- **data/** - Application data files
- **logs/** - Application log files
- **pocketbase/** - PocketBase database and migrations

## Notes

- All scripts maintain their original functionality
- Import paths remain unchanged (scripts use relative imports or absolute paths from project root)
- Documentation has been organized for easier access
- Legacy code has been moved to `scripts/legacy/` for reference

