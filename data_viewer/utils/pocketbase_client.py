"""
PocketBase API Client
Wrapper for PocketBase REST API with authentication and pagination
"""

import requests
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PocketBaseClient:
    """Client for interacting with PocketBase API"""
    
    def __init__(self, base_url: str, admin_email: str, admin_password: str):
        """
        Initialize PocketBase client
        
        Args:
            base_url: PocketBase server URL
            admin_email: Admin email for authentication
            admin_password: Admin password for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"
        self.admin_email = admin_email
        self.admin_password = admin_password
        self._admin_token = None
        self._token_expiry = 0
    
    def _get_admin_token(self) -> Optional[str]:
        """
        Get admin authentication token (with caching)
        
        Returns:
            Admin token string or None if authentication fails
        """
        # Check if cached token is still valid (cache for 1 hour)
        current_time = time.time()
        if self._admin_token and current_time < self._token_expiry:
            return self._admin_token
        
        try:
            auth_url = f"{self.api_url}/admins/auth-with-password"
            auth_data = {
                "identity": self.admin_email,
                "password": self.admin_password
            }
            
            response = requests.post(auth_url, json=auth_data, timeout=5)
            if response.status_code == 200:
                data = response.json()
                self._admin_token = data.get('token', '')
                # Cache token for 1 hour
                self._token_expiry = current_time + 3600
                return self._admin_token
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error authenticating: {e}")
            return None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        token = self._get_admin_token()
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        return headers
    
    def list_collections(self) -> List[Dict]:
        """
        List all collections in PocketBase
        
        Returns:
            List of collection dictionaries
        """
        try:
            # Get authentication headers
            headers = self._get_headers()
            
            # Check if we have authentication
            if not headers.get('Authorization'):
                logger.error("Cannot list collections: No authentication token available")
                logger.error("Please check admin_email and admin_password in config.json")
                return []
            
            logger.info(f"Fetching collections from PocketBase at {self.api_url}")
            
            response = requests.get(
                f"{self.api_url}/collections",
                headers=headers,
                params={'perPage': 500},
                timeout=15
            )
            
            if response.status_code == 401:
                logger.error("Authentication failed - invalid admin credentials")
                return []
            elif response.status_code == 404:
                logger.error("PocketBase API endpoint not found - check if PocketBase is running")
                return []
            elif response.status_code != 200:
                error_text = response.text[:200] if response.text else "No error message"
                logger.error(f"Failed to list collections: {response.status_code} - {error_text}")
                return []
            
            data = response.json()
            all_items = data.get('items', [])
            
            logger.debug(f"Received {len(all_items)} total collections from PocketBase")
            
            # Filter out system collections and only return base type collections
            collections = [
                item for item in all_items
                if not item.get('system', False) and item.get('type') == 'base'
            ]
            
            logger.info(f"Found {len(collections)} user collections (excluding system collections)")
            
            if len(collections) == 0:
                logger.warning("No user collections found in PocketBase")
                logger.warning("Collections may not exist or all are system collections")
            
            return collections
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to PocketBase at {self.api_url}: {e}")
            logger.error("Please ensure PocketBase is running and accessible")
            # Return a special marker to indicate connection error
            return None  # Use None to indicate connection error vs empty list
        except requests.exceptions.Timeout:
            logger.error("Timeout while fetching collections from PocketBase")
            return None  # Use None to indicate timeout error
        except Exception as e:
            logger.error(f"Error listing collections: {e}", exc_info=True)
            return None  # Use None to indicate general error
    
    def get_collection_info(self, collection_name: str) -> Optional[Dict]:
        """
        Get collection schema and metadata
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection info dictionary or None
        """
        try:
            headers = self._get_headers()
            response = requests.get(
                f"{self.api_url}/collections/{collection_name}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get collection info: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return None
    
    def get_distinct_symbols(self, collection_name: str, max_records: int = 50000) -> List[str]:
        """
        Get distinct symbols from a collection
        Works for any collection that has a 'symbol' field
        
        Args:
            collection_name: Name of the collection
            max_records: Maximum records to scan for symbols
            
        Returns:
            List of distinct symbol strings (sorted)
        """
        try:
            headers = self._get_headers()
            if not headers.get('Authorization'):
                logger.error("No authentication token available for fetching symbols")
                return []
            
            symbols = set()
            page = 1
            per_page = 500  # PocketBase max per page
            total_scanned = 0
            consecutive_empty_pages = 0
            
            logger.info(f"Fetching distinct symbols from '{collection_name}' (max {max_records} records)...")
            
            while total_scanned < max_records:
                params = {
                    'perPage': per_page,
                    'page': page,
                    'fields': 'symbol',
                    'sort': 'symbol'  # Sort by symbol for consistency and better pagination
                }
                
                try:
                    response = requests.get(
                        f"{self.api_url}/collections/{collection_name}/records",
                        headers=headers,
                        params=params,
                        timeout=20  # Increased timeout for large collections
                    )
                    
                    if response.status_code == 404:
                        logger.error(f"Collection '{collection_name}' not found")
                        break
                    elif response.status_code != 200:
                        error_text = response.text[:200]
                        logger.warning(f"Failed to fetch page {page}: {response.status_code} - {error_text}")
                        break
                    
                    data = response.json()
                    items = data.get('items', [])
                    
                    if not items:
                        consecutive_empty_pages += 1
                        if consecutive_empty_pages >= 2:
                            logger.debug(f"No more items after {consecutive_empty_pages} empty pages")
                            break
                    else:
                        consecutive_empty_pages = 0
                    
                    # Extract symbols from this page
                    page_symbols = 0
                    for item in items:
                        symbol = item.get('symbol')
                        if symbol:
                            # Handle both string and other types
                            symbol_str = str(symbol).strip()
                            if symbol_str:  # Only add non-empty symbols
                                symbols.add(symbol_str)
                                page_symbols += 1
                    
                    total_scanned += len(items)
                    
                    # Check if there are more pages
                    total_pages = data.get('totalPages', 1)
                    total_items = data.get('totalItems', 0)
                    
                    logger.debug(f"Page {page}/{total_pages}: Found {page_symbols} new symbols (total unique: {len(symbols)}, scanned {total_scanned}/{total_items} records)")
                    
                    # Stop if we've reached the last page
                    if page >= total_pages:
                        logger.debug(f"Reached last page ({total_pages})")
                        break
                    
                    page += 1
                    
                    # Safety limit - stop if we've found many symbols and scanned enough data
                    # This prevents infinite loops on very large collections
                    if len(symbols) >= 500 and total_scanned >= 10000:
                        logger.info(f"Found {len(symbols)} symbols, stopping scan at {total_scanned} records (safety limit)")
                        break
                    
                except requests.exceptions.Timeout:
                    logger.error(f"Timeout while fetching symbols from page {page}")
                    break
                except requests.exceptions.RequestException as e:
                    logger.error(f"Request error while fetching symbols: {e}")
                    break
            
            result = sorted(list(symbols))
            logger.info(f"Successfully retrieved {len(result)} distinct symbols from '{collection_name}' (scanned {total_scanned} records)")
            
            if len(result) == 0:
                logger.warning(f"No symbols found in collection '{collection_name}' - collection may be empty or have no symbol field data")
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting distinct symbols from '{collection_name}': {e}", exc_info=True)
            return []
    
    def _build_filter(self, symbol: Optional[str] = None, 
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> str:
        """
        Build PocketBase filter string
        
        Args:
            symbol: Symbol filter
            start_date: Start date (ISO format or timestamp)
            end_date: End date (ISO format or timestamp)
            
        Returns:
            Filter string
        """
        filters = []
        
        if symbol:
            filters.append(f'symbol="{symbol}"')
        
        if start_date:
            # Try to parse as timestamp (milliseconds)
            try:
                start_ts = int(start_date)
                filters.append(f'timestamp>={start_ts}')
            except ValueError:
                # Assume ISO date string, convert to timestamp
                try:
                    dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    start_ts = int(dt.timestamp() * 1000)
                    filters.append(f'timestamp>={start_ts}')
                except:
                    pass
        
        if end_date:
            try:
                end_ts = int(end_date)
                filters.append(f'timestamp<={end_ts}')
            except ValueError:
                try:
                    dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    end_ts = int(dt.timestamp() * 1000)
                    filters.append(f'timestamp<={end_ts}')
                except:
                    pass
        
        return ' && '.join(filters) if filters else ''
    
    def fetch_data(self, collection_name: str, 
                   symbol: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   limit: int = 1000,
                   page: int = 1) -> Dict:
        """
        Fetch data from a collection with filters
        
        Args:
            collection_name: Name of the collection
            symbol: Filter by symbol (optional)
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            limit: Maximum records per page
            page: Page number
            
        Returns:
            Dictionary with 'items', 'totalItems', 'page', 'perPage', 'totalPages'
        """
        try:
            headers = self._get_headers()
            params = {
                'perPage': min(limit, 500),  # PocketBase max per page is usually 500
                'page': page,
                'sort': '-timestamp'  # Most recent first
            }
            
            # Build filter
            filter_str = self._build_filter(symbol, start_date, end_date)
            if filter_str:
                params['filter'] = filter_str
            
            response = requests.get(
                f"{self.api_url}/collections/{collection_name}/records",
                headers=headers,
                params=params,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch data: {response.status_code} - {response.text}")
                return {
                    'items': [],
                    'totalItems': 0,
                    'page': 1,
                    'perPage': 0,
                    'totalPages': 0
                }
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return {
                'items': [],
                'totalItems': 0,
                'page': 1,
                'perPage': 0,
                'totalPages': 0
            }
    
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
        per_page = 500
        
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
            
            # Safety limit
            if len(all_items) >= max_records:
                break
        
        return all_items[:max_records]

