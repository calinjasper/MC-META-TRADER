"""
VWAP Validator and Export Tool
Exports VWAP data for validation and crosschecking with external sources
"""

import json
import csv
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class VWAPValidator:
    """Tool for exporting and validating VWAP data"""
    
    def __init__(self, vwap_strategy=None):
        """
        Initialize VWAP validator
        
        Args:
            vwap_strategy: VWAPStrategy instance (optional)
        """
        self.vwap_strategy = vwap_strategy
    
    def export_vwap_snapshot(self, vwap_data: Dict, current_price: float, 
                            symbol: str, output_path: str, format: str = 'json') -> bool:
        """
        Export current VWAP snapshot to file
        
        Args:
            vwap_data: VWAP data dictionary from strategy
            current_price: Current market price
            symbol: Trading symbol
            output_path: Output file path
            format: 'json' or 'csv'
            
        Returns:
            True if successful, False otherwise
        """
        try:
            vwap_value = vwap_data.get('vwap')
            bands = vwap_data.get('bands', {})
            session_info = vwap_data.get('session_info', {})
            
            timestamp = datetime.now()
            
            if format.lower() == 'json':
                return self._export_json(vwap_value, bands, current_price, symbol, 
                                       session_info, timestamp, output_path)
            elif format.lower() == 'csv':
                return self._export_csv(vwap_value, bands, current_price, symbol, 
                                      session_info, timestamp, output_path)
            else:
                logger.error(f"Unsupported format: {format}")
                return False
        except Exception as e:
            logger.error(f"Error exporting VWAP snapshot: {e}", exc_info=True)
            return False
    
    def _export_json(self, vwap_value: float, bands: Dict, current_price: float,
                    symbol: str, session_info: Dict, timestamp: datetime, output_path: str) -> bool:
        """Export to JSON format"""
        try:
            data = {
                'timestamp': timestamp.isoformat(),
                'symbol': symbol,
                'current_price': current_price,
                'vwap': vwap_value,
                'price_vs_vwap': current_price - vwap_value,
                'price_vs_vwap_pct': ((current_price - vwap_value) / vwap_value * 100) if vwap_value else 0,
                'bands': {},
                'session_info': session_info
            }
            
            # Add band data
            for std_dev, band_data in bands.items():
                upper = band_data.get('upper')
                lower = band_data.get('lower')
                data['bands'][f'std_{std_dev}'] = {
                    'upper': upper,
                    'lower': lower,
                    'upper_distance': current_price - upper if upper else None,
                    'lower_distance': lower - current_price if lower else None
                }
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported VWAP snapshot to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting JSON: {e}", exc_info=True)
            return False
    
    def _export_csv(self, vwap_value: float, bands: Dict, current_price: float,
                   symbol: str, session_info: Dict, timestamp: datetime, output_path: str) -> bool:
        """Export to CSV format"""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow(['Field', 'Value'])
                
                # Basic data
                writer.writerow(['Timestamp', timestamp.isoformat()])
                writer.writerow(['Symbol', symbol])
                writer.writerow(['Current Price', f'{current_price:.5f}'])
                writer.writerow(['VWAP', f'{vwap_value:.5f}'])
                writer.writerow(['Price - VWAP', f'{current_price - vwap_value:.5f}'])
                writer.writerow(['Price vs VWAP %', f'{((current_price - vwap_value) / vwap_value * 100):.2f}%'])
                writer.writerow([])  # Empty row
                
                # Bands
                writer.writerow(['Band Level', 'Upper', 'Lower', 'Price vs Upper', 'Price vs Lower'])
                for std_dev, band_data in bands.items():
                    upper = band_data.get('upper')
                    lower = band_data.get('lower')
                    upper_dist = current_price - upper if upper else 'N/A'
                    lower_dist = lower - current_price if lower else 'N/A'
                    writer.writerow([
                        f'STD {std_dev}',
                        f'{upper:.5f}' if upper else 'N/A',
                        f'{lower:.5f}' if lower else 'N/A',
                        f'{upper_dist:.5f}' if isinstance(upper_dist, float) else upper_dist,
                        f'{lower_dist:.5f}' if isinstance(lower_dist, float) else lower_dist
                    ])
                writer.writerow([])  # Empty row
                
                # Session info
                writer.writerow(['Session Info', 'Value'])
                for key, value in session_info.items():
                    if isinstance(value, datetime):
                        writer.writerow([key, value.isoformat()])
                    else:
                        writer.writerow([key, value])
            
            logger.info(f"Exported VWAP snapshot to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}", exc_info=True)
            return False
    
    def export_historical_vwap(self, vwap_history: List[Dict], output_path: str, 
                               format: str = 'csv') -> bool:
        """
        Export historical VWAP data
        
        Args:
            vwap_history: List of VWAP data dictionaries
            output_path: Output file path
            format: 'json' or 'csv'
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if format.lower() == 'json':
                return self._export_historical_json(vwap_history, output_path)
            elif format.lower() == 'csv':
                return self._export_historical_csv(vwap_history, output_path)
            else:
                logger.error(f"Unsupported format: {format}")
                return False
        except Exception as e:
            logger.error(f"Error exporting historical VWAP: {e}", exc_info=True)
            return False
    
    def _export_historical_json(self, vwap_history: List[Dict], output_path: str) -> bool:
        """Export historical data to JSON"""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(vwap_history, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Exported {len(vwap_history)} historical VWAP records to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting historical JSON: {e}", exc_info=True)
            return False
    
    def _export_historical_csv(self, vwap_history: List[Dict], output_path: str) -> bool:
        """Export historical data to CSV"""
        try:
            if not vwap_history:
                logger.warning("No historical data to export")
                return False
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Get all unique keys for headers
            all_keys = set()
            for record in vwap_history:
                all_keys.update(record.keys())
            
            headers = ['timestamp', 'vwap', 'current_price', 'price_vs_vwap'] + \
                     sorted([k for k in all_keys if k not in ['timestamp', 'vwap', 'current_price', 'price_vs_vwap']])
            
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                
                for record in vwap_history:
                    # Ensure timestamp is string
                    row = record.copy()
                    if 'timestamp' in row and isinstance(row['timestamp'], datetime):
                        row['timestamp'] = row['timestamp'].isoformat()
                    writer.writerow(row)
            
            logger.info(f"Exported {len(vwap_history)} historical VWAP records to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting historical CSV: {e}", exc_info=True)
            return False

