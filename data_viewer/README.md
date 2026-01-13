# PocketBase Data Viewer Platform

A web-based platform for downloading and visualizing data from PocketBase collections.

## Features

- **Collection Browser**: View all PocketBase collections
- **Data Filtering**: Filter by symbol and date range
- **CSV Download**: Export filtered data as CSV files
- **Interactive Charts**:
  - Candlestick charts for minute OHLC data (using Plotly.js)
  - Line charts for tick data (using Chart.js)
- **Data Tables**: View raw data for all collections

## Installation

All dependencies are already in `requirements.txt`. The platform uses:
- FastAPI
- Jinja2
- requests
- uvicorn

## Running the Platform

### Start the Server

```bash
python scripts/start_data_viewer.py
```

Or directly:

```bash
python -m data_viewer.main
```

The server will start on `http://localhost:8081`

### Access the Dashboard

Open your browser and navigate to:
```
http://localhost:8081
```

## Usage

1. **Select Collection**: Choose a collection from the dropdown (ticks, minute, trades, signals, indicators)

2. **Filter by Symbol** (for ticks/minute collections):
   - The symbol dropdown will automatically populate
   - Select a symbol or leave as "All Symbols"

3. **Set Date Range**:
   - Choose start and end dates using the date pickers
   - Default is last 7 days

4. **Load Data**: Click "Load Data" to fetch and display data

5. **View Charts**:
   - **Minute collection**: Displays candlestick chart (OHLC)
   - **Ticks collection**: Displays line chart (bid/ask/last prices)
   - **Other collections**: Displays data table

6. **Download CSV**: Click "Download CSV" to export filtered data

## API Endpoints

- `GET /` - Main dashboard
- `GET /api/collections` - List all collections
- `GET /api/collections/{name}` - Get collection info
- `GET /api/collections/{name}/symbols` - Get distinct symbols
- `GET /api/data/{collection}` - Fetch data with filters
- `GET /api/download/{collection}` - Download CSV

## Configuration

Configuration is loaded from `config/config.json`:
- PocketBase URL
- Admin credentials
- Server host/port

## Technical Details

- **Backend**: FastAPI (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **Charts**: Plotly.js (candlestick), Chart.js (line charts)
- **Data Source**: PocketBase REST API

