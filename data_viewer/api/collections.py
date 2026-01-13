"""
Collections API endpoints
List collections, get collection info, and fetch distinct symbols
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from data_viewer.utils.pocketbase_client import PocketBaseClient
from data_viewer.utils.mysql_client import MySQLClient
from data_viewer.config import (
    POCKETBASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD,
    MYSQL_HOST, MYSQL_PORT, MYSQL_USERNAME, MYSQL_PASSWORD
)

router = APIRouter(prefix="/api/collections", tags=["collections"])

# Initialize clients
pb_client = PocketBaseClient(POCKETBASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD)
mysql_client = MySQLClient(MYSQL_HOST, MYSQL_PORT, MYSQL_USERNAME, MYSQL_PASSWORD)

# Collection routing
MYSQL_COLLECTIONS = ['ticks', 'minute']
POCKETBASE_COLLECTIONS = ['trades', 'signals']


@router.get("")
async def list_collections() -> List[Dict]:
    """
    List all collections (MySQL and PocketBase)
    
    Returns:
        List of collection dictionaries with name, type, and schema info
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        result = []
        
        # Get MySQL collections (ticks, minute)
        logger.info("Fetching MySQL collections...")
        mysql_collections = mysql_client.list_collections()
        for col in mysql_collections:
            result.append({
                'name': col.get('name'),
                'type': col.get('type', 'base'),
                'system': col.get('system', False),
                'source': 'mysql'
            })
        
        # Get PocketBase collections (trades, signals)
        logger.info("Fetching PocketBase collections...")
        pb_collections = pb_client.list_collections()
        
        # Check if collections is None (connection error) vs empty list (no collections)
        if pb_collections is None:
            logger.warning("PocketBase server not accessible - trades/signals collections unavailable")
            # Don't raise error, just skip PocketBase collections
        elif pb_collections:
            for col in pb_collections:
                collection_name = col.get('name')
                # Only include trades and signals from PocketBase
                if collection_name in POCKETBASE_COLLECTIONS:
                    result.append({
                        'name': collection_name,
                        'type': col.get('type', 'base'),
                        'system': col.get('system', False),
                        'source': 'pocketbase'
                    })
        
        logger.info(f"Returning {len(result)} collections to frontend")
        return result
        
    except Exception as e:
        logger.error(f"Error listing collections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing collections: {str(e)}")


@router.get("/{collection_name}")
async def get_collection_info(collection_name: str) -> Dict:
    """
    Get collection schema and metadata
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Collection info with schema
    """
    try:
        # Route to appropriate client
        if collection_name in MYSQL_COLLECTIONS:
            info = mysql_client.get_collection_info(collection_name)
        elif collection_name in POCKETBASE_COLLECTIONS:
            info = pb_client.get_collection_info(collection_name)
        else:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        
        if not info:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting collection info: {str(e)}")


@router.get("/{collection_name}/symbols")
async def get_collection_symbols(collection_name: str) -> List[str]:
    """
    Get distinct symbols from a collection
    Works for all collections that have a 'symbol' field (ticks, minute, trades, signals, etc.)
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        List of distinct symbol strings
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Route to appropriate client
        if collection_name in MYSQL_COLLECTIONS:
            # Check if collection exists
            info = mysql_client.get_collection_info(collection_name)
            if not info:
                raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
            
            logger.info(f"Fetching distinct symbols from MySQL collection '{collection_name}'...")
            symbols = mysql_client.get_collection_symbols(collection_name)
            
        elif collection_name in POCKETBASE_COLLECTIONS:
            # Check if collection exists
            info = pb_client.get_collection_info(collection_name)
            if not info:
                raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
            
            # Check if collection has symbol field
            schema = info.get('schema', [])
            has_symbol = False
            for field in schema:
                if field.get('name') == 'symbol':
                    has_symbol = True
                    break
            
            if not has_symbol:
                logger.info(f"Collection '{collection_name}' does not have a symbol field")
                return []
            
            logger.info(f"Fetching distinct symbols from PocketBase collection '{collection_name}'...")
            symbols = pb_client.get_distinct_symbols(collection_name, max_records=50000)
        else:
            raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
        
        logger.info(f"Found {len(symbols)} distinct symbols in collection '{collection_name}'")
        
        if len(symbols) == 0:
            logger.warning(f"No symbols found in collection '{collection_name}' - collection may be empty")
        
        return symbols
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting symbols for {collection_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting symbols: {str(e)}")

