"""
Download API endpoints
CSV download functionality
"""

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import io
from data_viewer.utils.pocketbase_client import PocketBaseClient
from data_viewer.utils.mysql_client import MySQLClient
from data_viewer.utils.csv_exporter import export_to_csv_file
from data_viewer.config import (
    POCKETBASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD, MAX_RECORDS_PER_REQUEST,
    MYSQL_HOST, MYSQL_PORT, MYSQL_USERNAME, MYSQL_PASSWORD
)

router = APIRouter(prefix="/api/download", tags=["download"])

# Initialize clients
pb_client = PocketBaseClient(POCKETBASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD)
mysql_client = MySQLClient(MYSQL_HOST, MYSQL_PORT, MYSQL_USERNAME, MYSQL_PASSWORD)

# Collection routing
MYSQL_COLLECTIONS = ['ticks', 'minute']
POCKETBASE_COLLECTIONS = ['trades', 'signals']


@router.get("/{collection_name}")
async def download_csv(
    collection_name: str,
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format or timestamp in ms)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format or timestamp in ms)")
):
    """
    Download collection data as CSV file
    
    Args:
        collection_name: Name of the collection
        symbol: Filter by symbol (optional)
        start_date: Start date filter (optional)
        end_date: End date filter (optional)
        
    Returns:
        CSV file download
    """
    try:
        # Route to appropriate client
        if collection_name in MYSQL_COLLECTIONS:
            # Verify collection exists
            info = mysql_client.get_collection_info(collection_name)
            if not info:
                raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
            
            # Fetch all data from MySQL
            records = mysql_client.fetch_all_data(
                collection_name=collection_name,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                max_records=MAX_RECORDS_PER_REQUEST
            )
            
        elif collection_name in POCKETBASE_COLLECTIONS:
            # Verify collection exists
            info = pb_client.get_collection_info(collection_name)
            if not info:
                raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
            
            # Fetch all data from PocketBase
            records = pb_client.fetch_all_data(
                collection_name=collection_name,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                max_records=MAX_RECORDS_PER_REQUEST
            )
        else:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        
        if not records:
            raise HTTPException(status_code=404, detail="No data found matching the filters")
        
        # Generate CSV
        csv_bytes = export_to_csv_file(records, collection_name)
        
        # Create filename
        filename = f"{collection_name}"
        if symbol:
            filename += f"_{symbol}"
        filename += ".csv"
        
        # Return as streaming response
        return StreamingResponse(
            io.BytesIO(csv_bytes),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating CSV: {str(e)}")

