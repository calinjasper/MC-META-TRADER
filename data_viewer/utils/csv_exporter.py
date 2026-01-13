"""
CSV Export Utilities
Convert PocketBase records to CSV format
"""

import csv
import io
from typing import List, Dict, Optional
from datetime import datetime

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


def export_to_csv(records: List[Dict], collection_name: str) -> str:
    """
    Export records to CSV format with filtered fields and formatted timestamps
    
    Args:
        records: List of record dictionaries
        collection_name: Name of the collection (for context)
        
    Returns:
        CSV string with only essential fields (symbol, timeframe, open, high, low, close, timestamp)
    """
    if not records:
        return ""
    
    # Transform records to show only essential fields with formatted timestamps
    transformed_records = [_transform_record(record) for record in records]
    
    # Get all unique field names from transformed records
    fieldnames = set()
    for record in transformed_records:
        fieldnames.update(record.keys())
    
    # Define field order: symbol, timeframe, open, high, low, close, bid, ask, last, timestamp
    preferred_order = ['symbol', 'timeframe', 'open', 'high', 'low', 'close', 'bid', 'ask', 'last', 'timestamp']
    # Sort: preferred fields first, then any remaining fields
    ordered_fieldnames = [f for f in preferred_order if f in fieldnames]
    remaining_fields = sorted([f for f in fieldnames if f not in preferred_order])
    fieldnames = ordered_fieldnames + remaining_fields
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    
    # Write header
    writer.writeheader()
    
    # Write rows
    for record in transformed_records:
        # Convert any nested objects to strings
        cleaned_record = {}
        for key, value in record.items():
            if isinstance(value, (dict, list)):
                cleaned_record[key] = str(value)
            elif value is None:
                cleaned_record[key] = ''
            else:
                cleaned_record[key] = value
        writer.writerow(cleaned_record)
    
    return output.getvalue()


def export_to_csv_file(records: List[Dict], collection_name: str, 
                      filename: Optional[str] = None) -> bytes:
    """
    Export records to CSV file bytes
    
    Args:
        records: List of record dictionaries
        collection_name: Name of the collection
        filename: Optional filename (not used, but kept for compatibility)
        
    Returns:
        CSV file as bytes (UTF-8 encoded)
    """
    csv_string = export_to_csv(records, collection_name)
    return csv_string.encode('utf-8-sig')  # UTF-8 with BOM for Excel compatibility


def _to_ist(dt: datetime) -> datetime:
    """Convert datetime to IST timezone"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST)


def format_timestamp(timestamp: Optional[int], utc_time_str: Optional[str] = None) -> str:
    """
    Format timestamp (milliseconds) to IST format string
    
    IMPORTANT: If utc_time_str is provided, parse it and display as IST
    by treating the UTC time value as IST (this matches user expectation
    when they query for data where utc_time shows a specific time)
    
    Args:
        timestamp: Timestamp in milliseconds
        utc_time_str: Optional UTC time string from database (e.g., "2025-12-30 17:24:00 UTC")
        
    Returns:
        Formatted date string in IST format: "YYYY-MM-DD HH:MM:SS IST"
    """
    # If utc_time_str is provided, parse it and display as IST
    if utc_time_str:
        try:
            # Parse the UTC time string (format: "YYYY-MM-DD HH:MM:SS UTC")
            # Handle both string and timedelta formats
            if isinstance(utc_time_str, str):
                utc_time_clean = utc_time_str.replace(' UTC', '').strip()
            else:
                # If it's a timedelta or other type, convert to string first
                utc_time_clean = str(utc_time_str).replace(' UTC', '').strip()
            dt_parsed = datetime.strptime(utc_time_clean, "%Y-%m-%d %H:%M:%S")
            # Treat the parsed time as IST (user expects to see the utc_time value as IST)
            return dt_parsed.strftime("%Y-%m-%d %H:%M:%S IST")
        except (ValueError, AttributeError, TypeError):
            pass
    
    # Fallback to converting timestamp to IST
    if not timestamp:
        return ""
    
    try:
        # Convert milliseconds to seconds
        timestamp_sec = timestamp / 1000
        # Create UTC datetime from timestamp
        dt_utc = datetime.fromtimestamp(timestamp_sec, tz=UTC)
        # Convert to IST
        dt_ist = _to_ist(dt_utc)
        # Format as IST string
        return dt_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    except (ValueError, TypeError, OSError):
        return str(timestamp)


def _transform_record(record: Dict) -> Dict:
    """
    Transform a record to show only essential fields with formatted timestamp
    
    For OHLC collections (minute): symbol, timeframe, open, high, low, close, timestamp
    For tick collections: symbol, bid, ask, last, timestamp
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
            formatted_timestamp = format_timestamp(timestamp_value, utc_time_str)
            transformed['timestamp'] = formatted_timestamp
    
    return transformed

