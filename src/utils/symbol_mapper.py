"""
Symbol Mapper
Handles symbol name variations and broker-specific naming conventions
"""

import logging
import MetaTrader5 as mt5
from typing import Optional, Dict, List, Set
import re

logger = logging.getLogger(__name__)


class SymbolMapper:
    """Maps symbol variations to actual MT5 symbols"""
    
    # Common symbol variations mapping
    COMMON_MAPPINGS = {
        # Gold variations
        'XAUUSD': ['XAUUSD', 'GOLD', 'XAUUSDM', 'XAUUSDm', 'GOLDm', 'GOLDM'],
        'XAUUSDM': ['XAUUSDM', 'XAUUSD', 'XAUUSDm', 'GOLD', 'GOLDm', 'GOLDM'],
        'GOLD': ['GOLD', 'XAUUSD', 'XAUUSDM', 'XAUUSDm'],
        
        # EUR pairs
        'EURUSD': ['EURUSD', 'EURUSDM', 'EURUSDm', 'EURUSDm', 'EURUSD_M'],
        'EURUSDM': ['EURUSDM', 'EURUSD', 'EURUSDm', 'EURUSD_M'],
        'EURJPY': ['EURJPY', 'EURJPYM', 'EURJPYm', 'EURJPY_M'],
        'EURJPYM': ['EURJPYM', 'EURJPY', 'EURJPYm', 'EURJPY_M'],
        'EURGBP': ['EURGBP', 'EURGBPM', 'EURGBPm', 'EURGBP_M'],
        'EURAUD': ['EURAUD', 'EURAUDM', 'EURAUDm', 'EURAUD_M'],
        
        # GBP pairs
        'GBPUSD': ['GBPUSD', 'GBPUSDM', 'GBPUSDm', 'GBPUSD_M'],
        'GBPJPY': ['GBPJPY', 'GBPJPYM', 'GBPJPYm', 'GBPJPY_M'],
        
        # USD pairs
        'USDJPY': ['USDJPY', 'USDJPYM', 'USDJPYm', 'USDJPY_M'],
        'USDCHF': ['USDCHF', 'USDCHFM', 'USDCHFm', 'USDCHF_M'],
        'AUDUSD': ['AUDUSD', 'AUDUSDM', 'AUDUSDm', 'AUDUSD_M'],
        'NZDUSD': ['NZDUSD', 'NZDUSDM', 'NZDUSDm', 'NZDUSD_M'],
        'USDCAD': ['USDCAD', 'USDCADM', 'USDCADm', 'USDCAD_M'],
        
        # Crypto (if available)
        'BTCUSD': ['BTCUSD', 'BTCUSDM', 'BTCUSDm', 'BTCUSD_M', 'BTC'],
        'ETHUSD': ['ETHUSD', 'ETHUSDM', 'ETHUSDm', 'ETHUSD_M', 'ETH'],
    }
    
    def __init__(self, mt5_connector=None):
        """
        Initialize symbol mapper
        
        Args:
            mt5_connector: Optional MT5Connector instance for symbol lookups
        """
        self.mt5_connector = mt5_connector
        self.custom_mappings: Dict[str, List[str]] = {}
        self.symbol_cache: Dict[str, Optional[str]] = {}  # Cache successful mappings
    
    def add_custom_mapping(self, requested_symbol: str, actual_symbol: str):
        """
        Add a custom symbol mapping
        
        Args:
            requested_symbol: The symbol name user enters
            actual_symbol: The actual symbol name in MT5
        """
        if requested_symbol not in self.custom_mappings:
            self.custom_mappings[requested_symbol] = []
        if actual_symbol not in self.custom_mappings[requested_symbol]:
            self.custom_mappings[requested_symbol].insert(0, actual_symbol)  # Add to front
        logger.info(f"Added custom mapping: {requested_symbol} -> {actual_symbol}")
    
    def find_symbol(self, requested_symbol: str) -> Optional[str]:
        """
        Find the actual MT5 symbol for a requested symbol name
        
        Args:
            requested_symbol: The symbol name to find
            
        Returns:
            Actual symbol name in MT5, or None if not found
        """
        if not requested_symbol:
            return None
        
        requested_symbol = requested_symbol.upper().strip()
        
        # Check cache first
        if requested_symbol in self.symbol_cache:
            return self.symbol_cache[requested_symbol]
        
        # Try exact match first
        if self._symbol_exists(requested_symbol):
            self.symbol_cache[requested_symbol] = requested_symbol
            return requested_symbol
        
        # Try custom mappings first
        if requested_symbol in self.custom_mappings:
            for variant in self.custom_mappings[requested_symbol]:
                if self._symbol_exists(variant):
                    self.symbol_cache[requested_symbol] = variant
                    logger.info(f"Found symbol via custom mapping: {requested_symbol} -> {variant}")
                    return variant
        
        # Try common mappings
        for base_symbol, variants in self.COMMON_MAPPINGS.items():
            if requested_symbol in variants:
                for variant in variants:
                    if variant != requested_symbol and self._symbol_exists(variant):
                        self.symbol_cache[requested_symbol] = variant
                        logger.info(f"Found symbol via common mapping: {requested_symbol} -> {variant}")
                        return variant
        
        # Try pattern-based variations
        variations = self._generate_variations(requested_symbol)
        for variant in variations:
            if self._symbol_exists(variant):
                self.symbol_cache[requested_symbol] = variant
                logger.info(f"Found symbol via pattern variation: {requested_symbol} -> {variant}")
                return variant
        
        # Try case-insensitive search in all available symbols
        all_symbols = self._get_all_symbols()
        if all_symbols:
            requested_upper = requested_symbol.upper()
            for symbol in all_symbols:
                if symbol.upper() == requested_upper:
                    self.symbol_cache[requested_symbol] = symbol
                    logger.info(f"Found symbol via case-insensitive search: {requested_symbol} -> {symbol}")
                    return symbol
        
        # Try partial matching (e.g., "EURUSD" matches "EURUSDM")
        if all_symbols:
            requested_clean = self._clean_symbol_name(requested_symbol)
            for symbol in all_symbols:
                symbol_clean = self._clean_symbol_name(symbol)
                if requested_clean == symbol_clean:
                    self.symbol_cache[requested_symbol] = symbol
                    logger.info(f"Found symbol via partial match: {requested_symbol} -> {symbol}")
                    return symbol
        
        # Not found
        self.symbol_cache[requested_symbol] = None
        return None
    
    def _symbol_exists(self, symbol: str) -> bool:
        """Check if symbol exists in MT5"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            return symbol_info is not None
        except:
            return False
    
    def _get_all_symbols(self) -> List[str]:
        """Get all available symbols from MT5"""
        try:
            symbols = mt5.symbols_get()
            if symbols:
                return [s.name for s in symbols]
        except:
            pass
        return []
    
    def _generate_variations(self, symbol: str) -> List[str]:
        """Generate common symbol name variations"""
        variations = []
        symbol_upper = symbol.upper()
        
        # Remove common suffixes
        base = re.sub(r'[M_]$', '', symbol_upper)
        if base != symbol_upper:
            variations.append(base)
        
        # Add common suffixes
        suffixes = ['M', 'm', '_M', '_m']
        for suffix in suffixes:
            if not symbol_upper.endswith(suffix):
                variations.append(symbol_upper + suffix)
        
        # Try without last character if it's a letter
        if len(symbol_upper) > 1 and symbol_upper[-1].isalpha():
            variations.append(symbol_upper[:-1])
        
        # Try with/without underscore
        if '_' not in symbol_upper:
            variations.append(symbol_upper + '_M')
        else:
            variations.append(symbol_upper.replace('_', ''))
        
        return variations
    
    def _clean_symbol_name(self, symbol: str) -> str:
        """Clean symbol name for comparison (remove common suffixes)"""
        cleaned = symbol.upper()
        # Remove common suffixes
        cleaned = re.sub(r'[M_]$', '', cleaned)
        cleaned = re.sub(r'_M$', '', cleaned)
        return cleaned
    
    def get_similar_symbols(self, requested_symbol: str, limit: int = 10) -> List[str]:
        """
        Get similar symbols that exist in MT5
        
        Args:
            requested_symbol: The symbol to find similar ones for
            limit: Maximum number of suggestions
            
        Returns:
            List of similar symbol names
        """
        requested_upper = requested_symbol.upper()
        requested_clean = self._clean_symbol_name(requested_symbol)
        
        all_symbols = self._get_all_symbols()
        if not all_symbols:
            return []
        
        similar = []
        
        # Find symbols that start with the same base
        for symbol in all_symbols:
            symbol_clean = self._clean_symbol_name(symbol)
            if symbol_clean == requested_clean:
                similar.append(symbol)
            elif requested_clean in symbol_clean or symbol_clean in requested_clean:
                similar.append(symbol)
            
            if len(similar) >= limit:
                break
        
        # Also check for common patterns (e.g., if looking for EURUSD, suggest EURJPY, EURGBP)
        base_currency = requested_clean[:3] if len(requested_clean) >= 3 else None
        quote_currency = requested_clean[-3:] if len(requested_clean) >= 6 else None
        
        if base_currency:
            for symbol in all_symbols:
                symbol_clean = self._clean_symbol_name(symbol)
                if symbol_clean.startswith(base_currency) and symbol not in similar:
                    similar.append(symbol)
                if len(similar) >= limit * 2:
                    break
        
        return similar[:limit]
    
    def suggest_symbol(self, requested_symbol: str) -> Optional[str]:
        """
        Suggest the most likely symbol name
        
        Args:
            requested_symbol: The symbol name to suggest for
            
        Returns:
            Suggested symbol name or None
        """
        # First try to find exact match
        found = self.find_symbol(requested_symbol)
        if found:
            return found
        
        # Get similar symbols
        similar = self.get_similar_symbols(requested_symbol, limit=5)
        if similar:
            return similar[0]
        
        return None
    
    def clear_cache(self):
        """Clear the symbol cache"""
        self.symbol_cache.clear()
        logger.info("Symbol cache cleared")

