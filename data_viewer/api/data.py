"""
Data API endpoints
Fetch data from collections with filtering
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, List
from datetime import datetime
import logging
from data_viewer.utils.pocketbase_client import PocketBaseClient
from data_viewer.utils.mysql_client import MySQLClient
from data_viewer.config import (
    POCKETBASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD, MAX_RECORDS_PER_REQUEST,
    MYSQL_HOST, MYSQL_PORT, MYSQL_USERNAME, MYSQL_PASSWORD
)

logger = logging.getLogger(__name__)

# IST timezone support
try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
    UTC = ZoneInfo("UTC")
except ImportError:
    # Fallback for Python < 3.9
    try:
        import pytz
        IST = pytz.timezone("Asia/Kolkata")
        UTC = pytz.UTC
    except ImportError:
        # If neither available, use UTC offset manually
        from datetime import timedelta, timezone
        IST = timezone(timedelta(hours=5, minutes=30))
        UTC = timezone.utc

router = APIRouter(prefix="/api/data", tags=["data"])

# Initialize clients
pb_client = PocketBaseClient(POCKETBASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD)
mysql_client = MySQLClient(MYSQL_HOST, MYSQL_PORT, MYSQL_USERNAME, MYSQL_PASSWORD)

# Collection routing
MYSQL_COLLECTIONS = ['ticks', 'minute']
POCKETBASE_COLLECTIONS = ['trades', 'signals']


def _to_ist(dt: datetime) -> datetime:
    """Convert datetime to IST timezone"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST)


def _format_ist_timestamp(timestamp_ms: Optional[int], utc_time_str: Optional[str] = None) -> str:
    """
    Convert numeric timestamp (milliseconds) to IST format string
    
    IMPORTANT: If utc_time_str is provided, parse it and display as IST
    by treating the UTC time value as IST (this matches user expectation
    when they query for data where utc_time shows a specific time)
    
    Args:
        timestamp_ms: Timestamp in milliseconds
        utc_time_str: Optional UTC time string from database (e.g., "2025-12-30 17:24:00 UTC")
        
    Returns:
        Formatted string: "YYYY-MM-DD HH:MM:SS IST"
    """
    # If utc_time_str is provided, parse it and display as IST
    if utc_time_str:
        try:
            # Parse the UTC time string (format: "YYYY-MM-DD HH:MM:SS UTC")
            utc_time_clean = utc_time_str.replace(' UTC', '').strip()
            dt_parsed = datetime.strptime(utc_time_clean, "%Y-%m-%d %H:%M:%S")
            # Treat the parsed time as IST (user expects to see the utc_time value as IST)
            return dt_parsed.strftime("%Y-%m-%d %H:%M:%S IST")
        except (ValueError, AttributeError):
            pass
    
    # Fallback to converting timestamp to IST
    if timestamp_ms is None:
        return ""
    
    try:
        # Convert milliseconds to seconds
        timestamp_sec = timestamp_ms / 1000
        # Create UTC datetime from timestamp
        dt_utc = datetime.fromtimestamp(timestamp_sec, tz=UTC)
        # Convert to IST
        dt_ist = _to_ist(dt_utc)
        # Format as IST string
        return dt_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    except (ValueError, TypeError, OSError) as e:
        # If conversion fails, return empty string
        return ""


def _transform_record(record: Dict) -> Dict:
    """
    Transform a record to show only essential fields with formatted timestamp
    
    For OHLC collections (minute): symbol, timeframe, open, high, low, close, timestamp
    For tick collections: symbol, bid, ask, last, timestamp
    For other collections: symbol, timestamp (and other relevant fields if they exist)
    Converts numeric timestamp to IST format string
    
    Args:
        record: Original record dictionary from MySQL or PocketBase
        
    Returns:
        Transformed record with only required fields
    """
    transformed = {}
    
    # Extract symbol if present
    if 'symbol' in record:
        transformed['symbol'] = record['symbol']
    
    # Extract timeframe if present (for minute collection)
    if 'timeframe' in record:
        transformed['timeframe'] = record['timeframe']
    
    # Extract OHLC fields if present (for minute collection)
    for field in ['open', 'high', 'low', 'close']:
        if field in record:
            transformed[field] = record[field]
    
    # Extract tick fields if present (for ticks collection)
    for field in ['bid', 'ask', 'last']:
        if field in record:
            transformed[field] = record[field]
    
    # Convert timestamp from milliseconds to IST format string
    if 'timestamp' in record:
        timestamp_value = record.get('timestamp')
        utc_time_str = record.get('_utc_time_str')  # Get utc_time string if available
        if timestamp_value is not None:
            # Convert to IST format string, using utc_time_str if available
            formatted_timestamp = _format_ist_timestamp(timestamp_value, utc_time_str)
            transformed['timestamp'] = formatted_timestamp
    
    # If no fields were extracted (shouldn't happen, but handle gracefully)
    if not transformed:
        # Return at least the record ID for debugging
        if 'id' in record:
            transformed['id'] = record['id']
    
    return transformed


@router.get("/{collection_name}")
async def fetch_data(
    collection_name: str,
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format or timestamp in ms)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format or timestamp in ms)"),
    limit: int = Query(1000, ge=1, le=MAX_RECORDS_PER_REQUEST, description="Max records per page"),
    page: int = Query(1, ge=1, description="Page number")
) -> Dict:
    """
    Fetch data from a collection with optional filters
    
    Args:
        collection_name: Name of the collection
        symbol: Filter by symbol (optional)
        start_date: Start date filter (optional, ISO format or timestamp)
        end_date: End date filter (optional, ISO format or timestamp)
        limit: Maximum records to fetch (if > 500, automatically paginates)
        page: Page number (only used if limit <= 500)
        
    Returns:
        Dictionary with items, totalItems, page, perPage, totalPages, dateRange
    """
    logger.debug(f"fetch_data called: collection={collection_name}, symbol={symbol}, start_date={start_date}, end_date={end_date}")
    try:
        # Route to appropriate client
        if collection_name in MYSQL_COLLECTIONS:
            # Verify collection exists
            info = mysql_client.get_collection_info(collection_name)
            if not info:
                raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
            
            # Fetch data from MySQL
            if limit > 1000:  # Use fetch_all_data for large requests
                all_items = mysql_client.fetch_all_data(
                    collection_name=collection_name,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    max_records=limit
                )
                
                # Transform records
                transformed_items = [_transform_record(record) for record in all_items]
                
                # Calculate date range
                earliest_timestamp = None
                latest_timestamp = None
                for record in all_items:
                    if 'timestamp' in record and record['timestamp'] is not None:
                        ts = record['timestamp']
                        if earliest_timestamp is None or ts < earliest_timestamp:
                            earliest_timestamp = ts
                        if latest_timestamp is None or ts > latest_timestamp:
                            latest_timestamp = ts
                
                date_range = {}
                if earliest_timestamp:
                    date_range['earliest'] = _format_ist_timestamp(earliest_timestamp)
                if latest_timestamp:
                    date_range['latest'] = _format_ist_timestamp(latest_timestamp)
                
                return {
                    'items': transformed_items,
                    'totalItems': len(transformed_items),
                    'page': 1,
                    'perPage': len(transformed_items),
                    'totalPages': 1,
                    'dateRange': date_range
                }
            else:
                result = mysql_client.fetch_data(
                    collection_name=collection_name,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    page=page
                )
                
                # Transform records
                if 'items' in result and isinstance(result['items'], list):
                    result['items'] = [_transform_record(record) for record in result['items']]
                
                return result
                
        elif collection_name in POCKETBASE_COLLECTIONS:
            # Verify collection exists
            info = pb_client.get_collection_info(collection_name)
            if not info:
                raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
            
            # If limit > 500, use fetch_all_data() to automatically paginate through all pages
            if limit > 500:
                all_items = pb_client.fetch_all_data(
                    collection_name=collection_name,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    max_records=limit
                )
                
                transformed_items = [_transform_record(record) for record in all_items]
                
                earliest_timestamp = None
                latest_timestamp = None
                for record in all_items:
                    if 'timestamp' in record and record['timestamp'] is not None:
                        ts = record['timestamp']
                        if earliest_timestamp is None or ts < earliest_timestamp:
                            earliest_timestamp = ts
                        if latest_timestamp is None or ts > latest_timestamp:
                            latest_timestamp = ts
                
                date_range = {}
                if earliest_timestamp:
                    date_range['earliest'] = _format_ist_timestamp(earliest_timestamp)
                if latest_timestamp:
                    date_range['latest'] = _format_ist_timestamp(latest_timestamp)
                
                return {
                    'items': transformed_items,
                    'totalItems': len(transformed_items),
                    'page': 1,
                    'perPage': len(transformed_items),
                    'totalPages': 1,
                    'dateRange': date_range
                }
            else:
                result = pb_client.fetch_data(
                    collection_name=collection_name,
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                    page=page
                )
                
                if 'items' in result and isinstance(result['items'], list):
                    result['items'] = [_transform_record(record) for record in result['items']]
                
                return result
        else:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {str(e)}")

