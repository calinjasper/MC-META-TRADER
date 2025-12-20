# MetaTrader 5 GUI Trading Platform

A professional PyQt6-based trading platform that integrates with MetaTrader 5, providing live market data visualization, technical indicators, strategy creation and management, and automated trade execution.

## Features

- **MetaTrader 5 Integration**: Seamless connection to MT5 terminal
- **Live Market Data**: Real-time price streaming and visualization
- **Technical Indicators**: Support for common indicators (SMA, EMA, RSI, MACD, Bollinger Bands, Stochastic)
- **Strategy Builder**: Create indicator-based and time-based trading strategies
- **Multiple Strategies**: Run multiple strategies simultaneously
- **Automated Trading**: Execute trades based on strategy signals
- **Risk Management**: Stop loss and take profit management

## Requirements

- Python 3.8 or higher
- MetaTrader 5 terminal installed
- MT5 account credentials

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your MT5 connection in `config/config.json`

4. Run the application:
   ```bash
   python src/main.py
   ```

## Configuration

Edit `config/config.json` to set up your MT5 connection and trading parameters.

## Usage

1. Launch the application
2. Connect to MetaTrader 5
3. Select trading symbols
4. Create or load strategies
5. Start automated trading

## Data Persistence

- **Strategies**: All strategies are automatically saved to the `strategies/` directory when created or modified. They are automatically loaded when you restart the application.
- **Configuration**: Settings are saved in `config/config.json` and persist across sessions.
- **Code Changes**: When you modify the source code, you need to restart the application for changes to take effect. The application does not support hot-reloading.

## Security Note

Never commit sensitive credentials. Use environment variables or secure credential management for production use.

