"""
PocketBase Manager
Handles storage and retrieval of trading data in PocketBase
"""

import requests
import logging
from datetime import datetime
from typing import List, Dict, Optional
from threading import Thread
import queue
import time

# IST timezone support
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except ImportError:
    # Fallback for Python < 3.9
    try:
        import pytz
        IST = pytz.timezone("Asia/Kolkata")
    except ImportError:
        # If neither available, use UTC offset manually
        from datetime import timedelta, timezone
        IST = timezone(timedelta(hours=5, minutes=30))

logger = logging.getLogger(__name__)


class PocketBaseManager:
    """
    Manager for PocketBase database operations
    Handles storage and retrieval of trading data with async batch writes
    """
    
    def __init__(self, base_url: str = 'http://192.168.173.112:8090'):
        """
        Initialize PocketBase manager
        
        Args:
            base_url: PocketBase server URL
        """
        self.base_url = base_url
        self.api_url = f"{base_url}/api/collections"
        self.auth_token = None
        
        # Async write queue for performance
        self.write_queue = queue.Queue()
        self.batch_size = 100
        self.batch_timeout = 5.0  # seconds
        self._running = True
        
        # Cache for collection existence checks
        self._collection_cache = set()
        
        # Storage attempt counters (for validation)
        self._storage_attempts = {
            'ticks': 0,
            'ohlc': 0,
            'trades': 0,
            'signals': 0,
            'indicators': 0
        }
        self._storage_disabled = True  # Flag to indicate storage is disabled
        
        # Start background writer thread
        self.start_writer_thread()
        
        logger.info(f"PocketBase manager initialized: {base_url} (STORAGE DISABLED)")
    
    def _to_ist(self, dt: datetime) -> datetime:
        """
        Convert datetime to IST timezone
        
        Args:
            dt: Datetime object (assumed to be timezone-aware or naive UTC)
        
        Returns:
            Datetime in IST timezone
        """
        if dt.tzinfo is None:
            # Assume UTC if naive
            try:
                from zoneinfo import ZoneInfo
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            except ImportError:
                import pytz
                dt = pytz.UTC.localize(dt)
        
        # Convert to IST
        if hasattr(IST, 'normalize'):
            # pytz timezone
            return IST.normalize(dt.astimezone(IST))
        else:
            # zoneinfo timezone
            return dt.astimezone(IST)
    
    def _format_ist_timestamp(self, dt: datetime) -> str:
        """
        Format datetime as IST timestamp string
        
        Args:
            dt: Datetime object
        
        Returns:
            Formatted string like "2025-01-15 14:30:00 IST"
        """
        ist_dt = self._to_ist(dt)
        return ist_dt.strftime("%Y-%m-%d %H:%M:%S IST")
    
    def _ensure_collection_exists(self, collection_name: str):
        """
        Ensure a collection exists, create if it doesn't
        
        Args:
            collection_name: Name of the collection
        """
        if collection_name in self._collection_cache:
            return
        
        try:
            response = requests.get(
                f"{self.api_url}/{collection_name}",
                timeout=2
            )
            if response.status_code == 200:
                self._collection_cache.add(collection_name)
                return
        except:
            pass
        
        # Collection doesn't exist, try to create it
        # This will be handled by the batch writer if needed
        # For now, just log a warning
        logger.warning(f"Collection {collection_name} may not exist. It will be created on first write.")
    
    def start_writer_thread(self):
        """Background thread for batch writes"""
        def writer():
            while self._running:
                batch = []
                deadline = time.time() + self.batch_timeout
                
                # Collect items until batch_size or timeout
                while len(batch) < self.batch_size and time.time() < deadline:
                    try:
                        item = self.write_queue.get(timeout=0.1)
                        batch.append(item)
                    except queue.Empty:
                        continue
                
                if batch:
                    self._batch_write(batch)
        
        thread = Thread(target=writer, daemon=True, name="PocketBase-Writer")
        thread.start()
        logger.info("PocketBase batch writer thread started")
    
    def stop(self):
        """Stop the writer thread and flush pending writes"""
        self._running = False
        logger.info("PocketBase manager stopping...")
    
    # === STORE METHODS (Async) ===
    
    def store_tick(self, symbol: str, tick_data: Dict):
        """
        Queue tick for async storage in single ticks collection
        
        Args:
            symbol: Trading symbol
            tick_data: Tick data dictionary with 'time', 'bid', 'ask', etc.
        
        Note: Database storage is disabled - this method returns immediately without storing data.
        """
        # Track storage attempt (for validation)
        self._storage_attempts['ticks'] += 1
        
        # Database storage disabled - return immediately without queuing
        # Verify queue remains empty
        if self.write_queue.qsize() > 0:
            logger.warning(f"[VALIDATION] Unexpected items in queue after store_tick call: {self.write_queue.qsize()}")
        return
    
    def store_ohlc(self, symbol: str, timeframe: str, candle: Dict):
        """
        Queue OHLC candle for async storage
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, M15, H1, H4, D1, etc.)
            candle: Candle data dictionary with 'time', 'open', 'high', 'low', 'close'
        
        Note: Database storage is disabled - this method returns immediately without storing data.
        """
        # Track storage attempt (for validation)
        self._storage_attempts['ohlc'] += 1
        
        # Database storage disabled - return immediately without queuing
        # Verify queue remains empty
        if self.write_queue.qsize() > 0:
            logger.warning(f"[VALIDATION] Unexpected items in queue after store_ohlc call: {self.write_queue.qsize()}")
        return
    
    def store_trade(self, trade_data: Dict):
        """
        Queue trade for async storage
        
        Args:
            trade_data: Trade data dictionary with entry/exit info
        
        Note: Database storage is disabled - this method returns immediately without storing data.
        """
        # Track storage attempt (for validation)
        self._storage_attempts['trades'] += 1
        
        # Database storage disabled - return immediately without queuing
        # Verify queue remains empty
        if self.write_queue.qsize() > 0:
            logger.warning(f"[VALIDATION] Unexpected items in queue after store_trade call: {self.write_queue.qsize()}")
        return
    
    def store_signal(self, signal_data: Dict):
        """
        Queue signal for async storage
        
        Args:
            signal_data: Signal data dictionary
        
        Note: Database storage is disabled - this method returns immediately without storing data.
        """
        # Track storage attempt (for validation)
        self._storage_attempts['signals'] += 1
        
        # Database storage disabled - return immediately without queuing
        # Verify queue remains empty
        if self.write_queue.qsize() > 0:
            logger.warning(f"[VALIDATION] Unexpected items in queue after store_signal call: {self.write_queue.qsize()}")
        return
    
    def store_indicator(self, symbol: str, timeframe: str, timestamp: datetime,
                       indicator_name: str, value: float, metadata: Dict = None):
        """
        Queue indicator value for async storage
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            timestamp: Timestamp of the indicator value
            indicator_name: Name of the indicator (e.g., 'RSI_14', 'EMA_20')
            value: Indicator value
            metadata: Additional metadata dictionary
        
        Note: Database storage is disabled - this method returns immediately without storing data.
        """
        # Track storage attempt (for validation)
        self._storage_attempts['indicators'] += 1
        
        # Database storage disabled - return immediately without queuing
        # Verify queue remains empty
        if self.write_queue.qsize() > 0:
            logger.warning(f"[VALIDATION] Unexpected items in queue after store_indicator call: {self.write_queue.qsize()}")
        return
    
    # === QUERY METHODS (Sync) ===
    
    def get_ohlc(self, symbol: str, timeframe: str, start_time: int, end_time: int) -> List[Dict]:
        """
        Query historical OHLC candles
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, H1, etc.)
            start_time: Start timestamp in milliseconds
            end_time: End timestamp in milliseconds
        
        Returns:
            List of OHLC candle dictionaries
        """
        try:
            params = {
                'filter': f'symbol="{symbol}" && timeframe="{timeframe}" && timestamp>={start_time} && timestamp<={end_time}',
                'sort': 'timestamp',
                'perPage': 5000
            }
            response = requests.get(f"{self.api_url}/ohlc/records", params=params, timeout=10)
            response.raise_for_status()
            return response.json().get('items', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying OHLC from PocketBase: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying OHLC: {e}")
            return []
    
    def get_trades(self, symbol: str = None, start_date: datetime = None,
                   end_date: datetime = None) -> List[Dict]:
        """
        Query trade history
        
        Args:
            symbol: Filter by symbol (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
        
        Returns:
            List of trade dictionaries
        """
        try:
            filters = []
            if symbol:
                filters.append(f'symbol="{symbol}"')
            if start_date:
                filters.append(f'entry_time>="{start_date.isoformat()}"')
            if end_date:
                filters.append(f'entry_time<="{end_date.isoformat()}"')
            
            filter_str = ' && '.join(filters) if filters else ''
            
            params = {
                'filter': filter_str,
                'sort': '-entry_time',
                'perPage': 1000
            }
            response = requests.get(f"{self.api_url}/trades/records", params=params, timeout=10)
            response.raise_for_status()
            return response.json().get('items', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying trades from PocketBase: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying trades: {e}")
            return []
    
    def get_signals(self, symbol: str = None, start_date: datetime = None,
                    end_date: datetime = None) -> List[Dict]:
        """
        Query signal history
        
        Args:
            symbol: Filter by symbol (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
        
        Returns:
            List of signal dictionaries
        """
        try:
            filters = []
            if symbol:
                filters.append(f'symbol="{symbol}"')
            if start_date:
                filters.append(f'timestamp>="{start_date.isoformat()}"')
            if end_date:
                filters.append(f'timestamp<="{end_date.isoformat()}"')
            
            filter_str = ' && '.join(filters) if filters else ''
            
            params = {
                'filter': filter_str,
                'sort': '-timestamp',
                'perPage': 1000
            }
            response = requests.get(f"{self.api_url}/signals/records", params=params, timeout=10)
            response.raise_for_status()
            return response.json().get('items', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying signals from PocketBase: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying signals: {e}")
            return []
    
    def _batch_write(self, batch: List[Dict]):
        """
        Write batch of records to PocketBase
        
        Args:
            batch: List of items to write
        """
        # Group by collection
        grouped = {}
        for item in batch:
            collection = item['collection']
            if collection not in grouped:
                grouped[collection] = []
            grouped[collection].append(item['data'])
        
        # Write each collection
        for collection, records in grouped.items():
            for record in records:
                try:
                    response = requests.post(
                        f"{self.api_url}/{collection}/records",
                        json=record,
                        timeout=5
                    )
                    if response.status_code == 404:
                        # Collection doesn't exist - log warning
                        logger.warning(
                            f"Collection {collection} does not exist. "
                            f"Please run 'python setup_pocketbase_collections.py' to create it."
                        )
                    if response.status_code != 200:
                        logger.error(f"Error writing to {collection}: Status {response.status_code}")
                        logger.error(f"Response body: {response.text}")
                        logger.error(f"Record data: {record}")
                    else:
                        # Mark collection as existing
                        self._collection_cache.add(collection)
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    # Error already logged above if status code was not 200
                    pass
                except Exception as e:
                    logger.error(f"Unexpected error writing to {collection}: {e}")
        
        logger.debug(f"Batch wrote {len(batch)} records to PocketBase")
    
    
    def get_collections(self) -> List[str]:
        """
        Get list of all available collections from PocketBase
        
        Returns:
            List of collection names
        """
        try:
            # Try without authentication first (public collections)
            response = requests.get(f"{self.base_url}/api/collections", timeout=5)
            
            # If 401/403, try with admin auth
            if response.status_code in (401, 403):
                logger.debug("Collections endpoint requires authentication, attempting admin login...")
                # Try to get admin token if we don't have one
                if not self.auth_token:
                    self._get_admin_token()
                
                # Retry with authentication
                if self.auth_token:
                    headers = {"Authorization": f"Bearer {self.auth_token}"}
                    response = requests.get(f"{self.base_url}/api/collections", headers=headers, timeout=5)
                else:
                    logger.error("Could not obtain admin token for collections access")
                    raise requests.exceptions.HTTPError(f"Authentication required but failed: {response.status_code}")
            
            response.raise_for_status()
            collections_data = response.json()
            
            # Handle different response formats
            if isinstance(collections_data, list):
                collections = collections_data
            elif isinstance(collections_data, dict):
                collections = collections_data.get('items', [])
            else:
                logger.warning(f"Unexpected collections response format: {type(collections_data)}")
                collections = []
            
            collection_names = [c.get('name', '') if isinstance(c, dict) else str(c) for c in collections if c]
            # Filter out empty names
            collection_names = [name for name in collection_names if name]
            logger.info(f"Found {len(collection_names)} collections: {collection_names}")
            return collection_names
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching collections from PocketBase: {e}")
            logger.error(f"Response status: {getattr(e.response, 'status_code', 'N/A') if hasattr(e, 'response') else 'N/A'}")
            logger.error(f"Response text: {getattr(e.response, 'text', 'N/A') if hasattr(e, 'response') and e.response else 'N/A'}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching collections: {e}", exc_info=True)
            return []
    
    def _get_admin_token(self) -> Optional[str]:
        """
        Get admin authentication token for PocketBase
        
        Returns:
            Admin token if successful, None otherwise
        """
        try:
            # Use the actual admin credentials from the project
            auth_data = {
                "identity": "nrnnajith@gmail.com",
                "password": "LokeshCalin"
            }
            response = requests.post(
                f"{self.base_url}/api/admins/auth-with-password",
                json=auth_data,
                timeout=5
            )
            if response.status_code == 200:
                token = response.json().get('token')
                self.auth_token = token
                logger.info("Successfully authenticated with PocketBase admin account")
                return token
            else:
                logger.warning(f"Admin authentication failed: {response.status_code} - {response.text}")
        except Exception as e:
            logger.debug(f"Could not get admin token: {e}")
        return None
    
    def get_symbols_from_collection(self, collection_name: str) -> List[str]:
        """
        Get unique symbols from a collection
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            List of unique symbol names
        """
        try:
            symbols = set()
            page = 1
            per_page = 500
            
            # Prepare headers with auth if available
            headers = {}
            if not self.auth_token:
                # Try to get admin token if we don't have one
                self._get_admin_token()
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            while True:
                url = f"{self.api_url}/{collection_name}/records"
                params = {
                    'page': page,
                    'perPage': per_page,
                    'sort': 'symbol'
                }
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                
                # If 401/403, try to authenticate and retry
                if response.status_code in (401, 403):
                    if not self.auth_token:
                        self._get_admin_token()
                    if self.auth_token:
                        headers["Authorization"] = f"Bearer {self.auth_token}"
                        response = requests.get(url, params=params, headers=headers, timeout=10)
                
                response.raise_for_status()
                data = response.json()
                items = data.get('items', [])
                
                if not items:
                    break
                
                # Extract unique symbols
                for item in items:
                    symbol = item.get('symbol', '')
                    if symbol:
                        symbols.add(symbol)
                
                # Check if more pages
                total_items = data.get('totalItems', 0)
                if page * per_page >= total_items:
                    break
                
                page += 1
            
            symbol_list = sorted(list(symbols))
            logger.info(f"Found {len(symbol_list)} unique symbols in collection '{collection_name}': {symbol_list[:10]}{'...' if len(symbol_list) > 10 else ''}")
            return symbol_list
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching symbols from collection {collection_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching symbols: {e}")
            return []
    
    def export_collection_to_csv(self, collection_name: str, symbol: str,
                                 start_date: datetime, end_date: datetime,
                                 file_path: str) -> Dict:
        """
        Export collection data to CSV file with filters
        
        Args:
            collection_name: Name of the collection
            symbol: Symbol to filter by
            start_date: Start date for filtering
            end_date: End date for filtering
            file_path: Path where CSV file should be saved
            
        Returns:
            Dictionary with export statistics
        """
        import csv
        from pathlib import Path
        
        records_exported = 0
        file_size = 0
        
        try:
            # Build filter query
            filters = []
            if symbol:
                filters.append(f'symbol = "{symbol}"')
            
            # Convert dates to timestamps (milliseconds)
            if start_date:
                start_ts = int(start_date.timestamp() * 1000)
                filters.append(f"timestamp >= {start_ts}")
            
            if end_date:
                end_ts = int(end_date.timestamp() * 1000)
                filters.append(f"timestamp <= {end_ts}")
            
            filter_str = ' && '.join(filters) if filters else ''
            
            # Determine CSV headers based on collection type
            # For ticks collection, use standard headers
            # For other collections, we'll try to infer from first record
            headers = None
            first_record = None
            
            # Prepare headers with auth if available
            headers = {}
            if not self.auth_token:
                # Try to get admin token if we don't have one
                self._get_admin_token()
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            # Fetch records with pagination
            page = 1
            per_page = 500
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = None
                
                while True:
                    url = f"{self.api_url}/{collection_name}/records"
                    params = {
                        'page': page,
                        'perPage': per_page,
                        'sort': 'timestamp'
                    }
                    
                    if filter_str:
                        params['filter'] = filter_str
                    
                    response = requests.get(url, params=params, headers=headers, timeout=30)
                    
                    # If 401/403, try to authenticate and retry
                    if response.status_code in (401, 403):
                        logger.debug(f"Export requires authentication for {collection_name}, attempting admin login...")
                        if not self.auth_token:
                            self._get_admin_token()
                        if self.auth_token:
                            headers["Authorization"] = f"Bearer {self.auth_token}"
                            response = requests.get(url, params=params, headers=headers, timeout=30)
                        else:
                            logger.error("Could not obtain admin token for export")
                            raise requests.exceptions.HTTPError(f"Authentication required but failed: {response.status_code}")
                    
                    response.raise_for_status()
                    data = response.json()
                    items = data.get('items', [])
                    
                    if not items:
                        break
                    
                    # Initialize CSV writer on first batch
                    if writer is None:
                        if items:
                            first_record = items[0]
                            logger.debug(f"First record keys for {collection_name}: {list(first_record.keys())}")
                            logger.debug(f"First record sample (first 3 items): {dict(list(first_record.items())[:3])}")
                            
                            # Determine headers from first record
                            if collection_name == 'ticks':
                                headers = ['id', 'symbol', 'timestamp', 'datetime', 
                                          'bid', 'ask', 'last', 'volume', 'spread', 
                                          'created', 'updated']
                            elif collection_name == 'ohlc':
                                # OHLC collection has specific fields - use actual field names from record
                                # Check what fields actually exist
                                actual_fields = [k for k in first_record.keys() if not k.startswith('@')]
                                logger.debug(f"OHLC actual fields: {actual_fields}")
                                
                                # Define expected OHLC fields in order
                                expected_fields = ['id', 'symbol', 'timeframe', 'timestamp', 'timestamp_ist', 'datetime',
                                                  'open', 'high', 'low', 'close', 
                                                  'tick_volume', 'real_volume', 'created', 'updated']
                                
                                # Build headers: include expected fields that exist, plus datetime (calculated)
                                headers = []
                                for field in expected_fields:
                                    if field == 'datetime':
                                        headers.append('datetime')  # Always include, we'll calculate it
                                    elif field in actual_fields:
                                        headers.append(field)
                                
                                # Add any remaining fields that weren't in expected list
                                for field in actual_fields:
                                    if field not in headers and field != 'datetime':
                                        headers.append(field)
                                
                                logger.info(f"OHLC export headers: {headers}")
                            else:
                                # Use all keys from first record, excluding internal fields
                                headers = [k for k in first_record.keys() 
                                          if not k.startswith('@')]
                                # Ensure common fields are first
                                priority_fields = ['id', 'symbol', 'timestamp', 'datetime']
                                headers = ([f for f in priority_fields if f in headers] + 
                                          [f for f in headers if f not in priority_fields])
                            
                            writer = csv.DictWriter(csvfile, fieldnames=headers)
                            writer.writeheader()
                    
                    # Write records
                    for item in items:
                        row = {}
                        for header in headers:
                            if header == 'datetime':
                                # Convert timestamp to readable datetime
                                timestamp = item.get('timestamp', 0)
                                if timestamp:
                                    try:
                                        # Handle both milliseconds and seconds timestamps
                                        if timestamp > 1e10:  # Milliseconds
                                            dt = datetime.fromtimestamp(timestamp / 1000)
                                        else:  # Seconds
                                            dt = datetime.fromtimestamp(timestamp)
                                        row[header] = dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                                    except (ValueError, OSError):
                                        row[header] = ''
                                else:
                                    row[header] = ''
                            else:
                                # Get the actual value from the item
                                value = item.get(header, '')
                                
                                # For OHLC collection, log first record to debug
                                if collection_name == 'ohlc' and records_exported == 0 and header in ['open', 'high', 'low', 'close']:
                                    logger.debug(f"OHLC {header}: {value} (type: {type(value)})")
                                
                                # Ensure numeric fields are properly formatted
                                if header in ['open', 'high', 'low', 'close', 'bid', 'ask', 'last', 
                                            'volume', 'spread', 'tick_volume', 'real_volume', 'timestamp']:
                                    if value != '' and value is not None:
                                        try:
                                            # Convert to float and keep as float (CSV writer will format it)
                                            row[header] = float(value)
                                        except (ValueError, TypeError):
                                            row[header] = value
                                    else:
                                        row[header] = ''
                                else:
                                    row[header] = value
                        
                        # Log first OHLC record for debugging
                        if collection_name == 'ohlc' and records_exported == 0:
                            logger.info(f"First OHLC record exported - open: {row.get('open')}, high: {row.get('high')}, low: {row.get('low')}, close: {row.get('close')}")
                        
                        writer.writerow(row)
                        records_exported += 1
                    
                    # Check if more pages
                    total_items = data.get('totalItems', 0)
                    if page * per_page >= total_items:
                        break
                    
                    page += 1
            
            # Get file size
            file_path_obj = Path(file_path)
            if file_path_obj.exists():
                file_size = file_path_obj.stat().st_size
                file_size_str = f"{file_size / 1024:.2f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.2f} MB"
            else:
                file_size_str = "N/A"
            
            logger.info(f"Exported {records_exported} records from {collection_name} to {file_path}")
            
            return {
                'records_exported': records_exported,
                'file_path': file_path,
                'file_size': file_size_str,
                'collection': collection_name,
                'symbol': symbol,
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error exporting collection {collection_name}: {e}")
            raise Exception(f"Failed to fetch data from PocketBase: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error exporting collection: {e}", exc_info=True)
            raise Exception(f"Export failed: {str(e)}")
    
    def health_check(self) -> bool:
        """
        Check if PocketBase server is reachable
        
        Returns:
            True if server is reachable, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_storage_validation_stats(self) -> Dict:
        """
        Get validation statistics about storage attempts
        
        Returns:
            Dictionary with storage attempt counts and queue status
        """
        return {
            'storage_disabled': self._storage_disabled,
            'storage_attempts': self._storage_attempts.copy(),
            'queue_size': self.write_queue.qsize(),
            'total_attempts': sum(self._storage_attempts.values()),
            'queue_empty': self.write_queue.qsize() == 0
        }
    
    def validate_storage_disabled(self) -> Dict:
        """
        Validate that storage is properly disabled
        
        Returns:
            Dictionary with validation results
        """
        queue_size = self.write_queue.qsize()
        total_attempts = sum(self._storage_attempts.values())
        
        validation_result = {
            'storage_disabled': self._storage_disabled,
            'queue_size': queue_size,
            'queue_empty': queue_size == 0,
            'total_storage_attempts': total_attempts,
            'storage_attempts_by_type': self._storage_attempts.copy(),
            'validation_passed': queue_size == 0 and self._storage_disabled,
            'message': ''
        }
        
        if validation_result['validation_passed']:
            validation_result['message'] = (
                f"[PASS] Storage is DISABLED - {total_attempts} storage attempts blocked, "
                f"queue is empty ({queue_size} items)"
            )
        else:
            validation_result['message'] = (
                f"[FAIL] Validation FAILED - Queue has {queue_size} items, "
                f"storage_disabled={self._storage_disabled}"
            )
        
        return validation_result










