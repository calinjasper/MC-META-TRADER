"""
MySQL API Client
Wrapper for MySQL database queries with collection-like interface
Maps virtual collections to MySQL schemas and tables
"""

import mysql.connector
from mysql.connector import Error
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# IST timezone support
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
    UTC = ZoneInfo("UTC")
except ImportError:
    try:
        import pytz
        IST = pytz.timezone("Asia/Kolkata")
        UTC = pytz.UTC
    except ImportError:
        from datetime import timedelta, timezone
        IST = timezone(timedelta(hours=5, minutes=30))
        UTC = timezone.utc

logger = logging.getLogger(__name__)

ALLOWED_SYMBOLS = ['XAUUSD', 'EURUSD', 'EURJPY', 'USDJPY', 'BTCUSD']

# Collection mapping
MYSQL_COLLECTIONS = {
    'ticks': {
        'schema': 'forex',
        'table_prefix': '_tick_level',
        'fields': ['timestamp', 'utc_time', 'bid', 'ask', 'last']
    },
    'minute': {
        'schema': 'minute_data',
        'table_prefix': '_minute',
        'fields': ['timestamp', 'utc_time', 'open', 'high', 'low', 'close', 'tick_count']
    }
}


class MySQLClient:
    """Client for interacting with MySQL database with collection-like interface"""
    
    def __init__(self, host: str, port: int, username: str, password: str):
        """
        Initialize MySQL client
        
        Args:
            host: MySQL server host
            port: MySQL server port
            username: MySQL username
            password: MySQL password
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._connection = None
    
    def _get_connection(self):
        """Get or create database connection"""
        if self._connection is None or not self._connection.is_connected():
            try:
                self._connection = mysql.connector.connect(
                    host=self.host,
                    port=self.port,
                    user=self.username,
                    password=self.password,
                    charset='utf8mb4',
                    collation='utf8mb4_unicode_ci'
                )
            except Error as e:
                logger.error(f"Failed to connect to MySQL: {e}")
                raise
        return self._connection
    
    def _format_ist_timestamp(self, timestamp_ms: Optional[int]) -> str:
        """
        Convert numeric timestamp (milliseconds) to IST format string
        
        Args:
            timestamp_ms: Timestamp in milliseconds
            
        Returns:
            Formatted string: "YYYY-MM-DD HH:MM:SS IST"
        """
        if timestamp_ms is None:
            return ""
        
        try:
            timestamp_sec = timestamp_ms / 1000
            dt_utc = datetime.fromtimestamp(timestamp_sec, tz=UTC)
            dt_ist = dt_utc.astimezone(IST)
            return dt_ist.strftime("%Y-%m-%d %H:%M:%S IST")
        except (ValueError, TypeError, OSError) as e:
            logger.warning(f"Failed to format timestamp {timestamp_ms}: {e}")
            return ""
    
    def list_collections(self) -> List[Dict]:
        """
        List available collections (virtual collections mapped to MySQL)
        
        Returns:
            List of collection dictionaries
        """
        collections = []
        
        # Add MySQL-based collections
        for collection_name, config in MYSQL_COLLECTIONS.items():
            collections.append({
                'name': collection_name,
                'type': 'base',
                'system': False,
                'source': 'mysql'
            })
        
        return collections
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """
        Get collection schema and metadata
        
        Args:
            collection_name: Name of the collection (ticks or minute)
            
        Returns:
            Collection info dictionary or None
        """
        if collection_name not in MYSQL_COLLECTIONS:
            return None
        
        config = MYSQL_COLLECTIONS[collection_name]
        
        # Build schema based on collection type
        schema = []
        
        if collection_name == 'ticks':
            schema = [
                {'name': 'symbol', 'type': 'text', 'required': True},
                {'name': 'timestamp', 'type': 'number', 'required': True},
                {'name': 'bid', 'type': 'number', 'required': True},
                {'name': 'ask', 'type': 'number', 'required': True},
                {'name': 'last', 'type': 'number', 'required': False}
            ]
        elif collection_name == 'minute':
            schema = [
                {'name': 'symbol', 'type': 'text', 'required': True},
                {'name': 'timeframe', 'type': 'text', 'required': True},
                {'name': 'timestamp', 'type': 'number', 'required': True},
                {'name': 'open', 'type': 'number', 'required': True},
                {'name': 'high', 'type': 'number', 'required': True},
                {'name': 'low', 'type': 'number', 'required': True},
                {'name': 'close', 'type': 'number', 'required': True},
                {'name': 'tick_count', 'type': 'number', 'required': False}
            ]
        
        return {
            'name': collection_name,
            'type': 'base',
            'system': False,
            'schema': schema,
            'source': 'mysql'
        }
    
    def get_collection_symbols(self, collection_name: str) -> List[str]:
        """
        Get distinct symbols from a MySQL collection
        
        Args:
            collection_name: Name of the collection (ticks or minute)
            
        Returns:
            List of distinct symbol strings
        """
        if collection_name not in MYSQL_COLLECTIONS:
            return []
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            config = MYSQL_COLLECTIONS[collection_name]
            schema = config['schema']
            
            # Get all tables in the schema that match the pattern
            cursor.execute(f"SHOW TABLES FROM `{schema}`")
            tables = [row[0] for row in cursor.fetchall()]
            
            symbols = []
            for symbol in ALLOWED_SYMBOLS:
                table_name = f"{symbol.lower()}{config['table_prefix']}"
                if table_name in tables:
                    symbols.append(symbol)
            
            cursor.close()
            
            logger.info(f"Found {len(symbols)} symbols in MySQL collection '{collection_name}'")
            return sorted(symbols)
            
        except Error as e:
            logger.error(f"Error getting symbols from MySQL collection '{collection_name}': {e}")
            return []
    
    def _get_table_name(self, collection_name: str, symbol: str) -> Optional[str]:
        """
        Get MySQL table name for a collection and symbol
        
        Args:
            collection_name: Name of the collection
            symbol: Trading symbol
            
        Returns:
            Table name or None if invalid
        """
        if collection_name not in MYSQL_COLLECTIONS:
            return None
        
        # Normalize symbol (remove 'm' suffix, uppercase)
        normalized_symbol = symbol.upper().replace('M', '')
        
        if normalized_symbol not in ALLOWED_SYMBOLS:
            return None
        
        config = MYSQL_COLLECTIONS[collection_name]
        return f"{normalized_symbol.lower()}{config['table_prefix']}"
    
    def _parse_date_filter(self, date_str: Optional[str]) -> Optional[int]:
        """
        Parse date filter to timestamp in milliseconds
        
        IMPORTANT: The user enters time in datetime-local input, which we treat as IST.
        However, the database has data where utc_time shows UTC times directly.
        So when user enters 17:24, they want to see data where utc_time shows 17:24 UTC,
        not data where IST time is 17:24 (which would be 11:54 UTC).
        
        Args:
            date_str: Date string (ISO format with timezone or timestamp in ms)
            
        Returns:
            Timestamp in milliseconds (UTC) or None
        """
        if not date_str:
            return None
        
        try:
            # Try as timestamp (milliseconds) - if it's a pure number
            if date_str.isdigit():
                ts = int(date_str)
                logger.debug(f"Parsed as timestamp: {date_str} -> {ts}")
                return ts
        except (ValueError, AttributeError):
            pass
        
        try:
            # Try as ISO date string (e.g., "2025-12-30T17:24:00+05:30")
            # CRITICAL FIX: If the string has +05:30 (IST), we need to treat the input time
            # as the UTC time the user wants to see, not as IST time to convert to UTC.
            # This is because the database stores utc_time as UTC directly.
            logger.debug(f"Parsing date string: '{date_str}'")
            
            if 'Z' in date_str:
                # UTC timezone indicator
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            elif '+' in date_str and '+05:30' in date_str:
                # Has IST timezone indicator - treat the time as UTC (what user wants to see in utc_time column)
                # Extract the date-time part without timezone
                dt_str = date_str.split('+')[0]  # Remove timezone part
                dt = datetime.fromisoformat(dt_str)
                dt = dt.replace(tzinfo=UTC)  # Treat as UTC directly
            elif '+' in date_str or (date_str.count('-') > 2 and ':' in date_str):
                # Has other timezone indicator
                dt = datetime.fromisoformat(date_str)
            else:
                # No timezone - assume UTC
                dt = datetime.fromisoformat(date_str)
                dt = dt.replace(tzinfo=UTC)
            
            # Ensure timezone-aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            
            # Convert to UTC timestamp (milliseconds)
            # Since we're treating the input as UTC directly, no conversion needed
            utc_dt = dt.astimezone(UTC) if dt.tzinfo != UTC else dt
            ts_ms = int(utc_dt.timestamp() * 1000)
            
            logger.debug(f"Parsed date '{date_str}' -> UTC: {utc_dt}, timestamp: {ts_ms}, IST: {utc_dt.astimezone(IST)}")
            return ts_ms
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse date filter '{date_str}': {e}")
            return None
    
    def fetch_data(self, collection_name: str,
                   symbol: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   limit: int = 1000,
                   page: int = 1) -> Dict:
        """
        Fetch data from a MySQL collection with filters
        
        Args:
            collection_name: Name of the collection (ticks or minute)
            symbol: Filter by symbol (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            limit: Maximum records per page
            page: Page number
            
        Returns:
            Dictionary with 'items', 'totalItems', 'page', 'perPage', 'totalPages'
        """
        if collection_name not in MYSQL_COLLECTIONS:
            return {
                'items': [],
                'totalItems': 0,
                'page': 1,
                'perPage': 0,
                'totalPages': 0
            }
        
        cursor = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            
            config = MYSQL_COLLECTIONS[collection_name]
            schema = config['schema']
            
            # If symbol specified, query single table
            if symbol:
                table_name = self._get_table_name(collection_name, symbol)
                if not table_name:
                    return {
                        'items': [],
                        'totalItems': 0,
                        'page': 1,
                        'perPage': 0,
                        'totalPages': 0
                    }
                
                items = self._fetch_from_table(
                    cursor, schema, table_name, symbol, start_date, end_date, limit, page
                )
                
                # Get total count
                total_count = self._count_from_table(
                    cursor, schema, table_name, symbol, start_date, end_date
                )
                
                total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
                
                return {
                    'items': items,
                    'totalItems': total_count,
                    'page': page,
                    'perPage': limit,
                    'totalPages': total_pages
                }
            else:
                # No symbol specified - query all tables and combine
                all_items = []
                total_count = 0
                
                for sym in ALLOWED_SYMBOLS:
                    table_name = self._get_table_name(collection_name, sym)
                    if not table_name:
                        continue
                    
                    # Check if table exists
                    cursor.execute(f"SHOW TABLES FROM `{schema}` LIKE '{table_name}'")
                    if not cursor.fetchone():
                        continue
                    
                    table_items = self._fetch_from_table(
                        cursor, schema, table_name, sym, start_date, end_date, limit=None, page=1
                    )
                    table_count = self._count_from_table(
                        cursor, schema, table_name, sym, start_date, end_date
                    )
                    
                    all_items.extend(table_items)
                    total_count += table_count
                
                # Sort by timestamp descending
                all_items.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
                
                # Apply pagination
                start_idx = (page - 1) * limit
                end_idx = start_idx + limit
                paginated_items = all_items[start_idx:end_idx]
                
                total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
                
                return {
                    'items': paginated_items,
                    'totalItems': total_count,
                    'page': page,
                    'perPage': limit,
                    'totalPages': total_pages
                }
                
        except Error as e:
            logger.error(f"Error fetching data from MySQL collection '{collection_name}': {e}")
            return {
                'items': [],
                'totalItems': 0,
                'page': 1,
                'perPage': 0,
                'totalPages': 0
            }
        finally:
            if cursor:
                cursor.close()
    
    def _fetch_from_table(self, cursor, schema: str, table_name: str, symbol: str,
                         start_date: Optional[str], end_date: Optional[str],
                         limit: Optional[int], page: int) -> List[Dict]:
        """Fetch data from a specific table"""
        # Determine collection type from table name
        if 'tick_level' in table_name:
            config = MYSQL_COLLECTIONS['ticks']
        else:
            config = MYSQL_COLLECTIONS['minute']
        fields = config['fields']
        
        # Build query - ensure utc_time is included for timestamp formatting
        query_fields = list(fields)
        if 'utc_time' not in query_fields:
            query_fields.append('utc_time')
        query = f"SELECT {', '.join(f'`{f}`' for f in query_fields)} FROM `{schema}`.`{table_name}`"
        conditions = []
        params = []
        
        # Date filters
        start_ts = self._parse_date_filter(start_date)
        end_ts = self._parse_date_filter(end_date)
        
        if start_ts:
            conditions.append("`timestamp` >= %s")
            params.append(start_ts)
            logger.debug(f"[_fetch_from_table] Applied start_date filter: '{start_date}' -> timestamp {start_ts}")
        
        if end_ts:
            conditions.append("`timestamp` <= %s")
            params.append(end_ts)
            logger.debug(f"[_fetch_from_table] Applied end_date filter: '{end_date}' -> timestamp {end_ts}")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY `timestamp` ASC"
        
        # Apply limit and offset
        if limit:
            offset = (page - 1) * limit
            query += f" LIMIT {limit} OFFSET {offset}"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Transform rows to match expected format
        items = []
        for idx, row in enumerate(rows):
            item = {
                'symbol': symbol,
                'timestamp': row.get('timestamp', 0)
            }
            
            # Add collection-specific fields
            if 'tick_level' in table_name:
                # Tick data
                item['bid'] = float(row.get('bid', 0))
                item['ask'] = float(row.get('ask', 0))
                if row.get('last'):
                    item['last'] = float(row.get('last', 0))
            else:
                # Minute OHLC data
                item['timeframe'] = 'M1'
                item['open'] = float(row.get('open', 0))
                item['high'] = float(row.get('high', 0))
                item['low'] = float(row.get('low', 0))
                item['close'] = float(row.get('close', 0))
                if row.get('tick_count'):
                    item['tick_count'] = int(row.get('tick_count', 0))
            
            # Store utc_time for timestamp formatting
            # The utc_time column shows the UTC time, but we want to display it as IST
            # by parsing the UTC time string and treating the hour as IST
            if row.get('utc_time'):
                utc_time_val = row.get('utc_time')
                # Handle timedelta objects (convert to string format)
                if isinstance(utc_time_val, timedelta):
                    # If it's a timedelta, convert timestamp to UTC string format
                    ts = row.get('timestamp', 0)
                    if ts:
                        dt_utc = datetime.fromtimestamp(ts / 1000, UTC)
                        item['_utc_time_str'] = dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
                    else:
                        item['_utc_time_str'] = None
                else:
                    item['_utc_time_str'] = str(utc_time_val)
            
            items.append(item)
        
        return items
    
    def _count_from_table(self, cursor, schema: str, table_name: str, symbol: str,
                         start_date: Optional[str], end_date: Optional[str]) -> int:
        """Count records in a specific table"""
        query = f"SELECT COUNT(*) as count FROM `{schema}`.`{table_name}`"
        conditions = []
        params = []
        
        start_ts = self._parse_date_filter(start_date)
        end_ts = self._parse_date_filter(end_date)
        
        if start_ts:
            conditions.append("`timestamp` >= %s")
            params.append(start_ts)
            logger.debug(f"[_count_from_table] Applied start_date filter: '{start_date}' -> timestamp {start_ts}")
        
        if end_ts:
            conditions.append("`timestamp` <= %s")
            params.append(end_ts)
            logger.debug(f"[_count_from_table] Applied end_date filter: '{end_date}' -> timestamp {end_ts}")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        return result.get('count', 0) if result else 0
    
    def fetch_all_data(self, collection_name: str,
                      symbol: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      max_records: int = 10000) -> List[Dict]:
        """
        Fetch all data from a collection (with pagination)
        
        Args:
            collection_name: Name of the collection
            symbol: Filter by symbol (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            max_records: Maximum total records to fetch
            
        Returns:
            List of all records
        """
        all_items = []
        page = 1
        per_page = 1000
        
        while len(all_items) < max_records:
            result = self.fetch_data(
                collection_name=collection_name,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                limit=per_page,
                page=page
            )
            
            items = result.get('items', [])
            if not items:
                break
            
            all_items.extend(items)
            
            total_pages = result.get('totalPages', 1)
            if page >= total_pages:
                break
            
            page += 1
            
            if len(all_items) >= max_records:
                break
        
        return all_items[:max_records]
    
    def close(self):
        """Close database connection"""
        if self._connection and self._connection.is_connected():
            self._connection.close()
            self._connection = None

