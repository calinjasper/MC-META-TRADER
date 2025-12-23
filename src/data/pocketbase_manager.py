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

