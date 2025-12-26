"""
Custom Indicator Panel - Support/Resistance Based
GUI for Support/Resistance indicator with breakout trading
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QDoubleSpinBox, QSpinBox,
                             QGroupBox, QFormLayout, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QCheckBox, QTextEdit, QSplitter,
                             QTabWidget, QScrollArea, QFrame, QGridLayout, QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QFont
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json
import requests
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import logging
import uuid

from ..utils.symbol_mapper import SymbolMapper

logger = logging.getLogger(__name__)


class PivotPointsCalculator:
    """Calculate Support and Resistance levels using Floor Trader's Pivot Points"""
    
    def __init__(self, pivot_period: str = 'daily', min_touches: int = 2, strength_threshold: float = 0.5):
        """
        Initialize Pivot Points calculator
        
        Args:
            pivot_period: 'daily', 'weekly', or 'monthly'
            min_touches: Minimum number of touches required to confirm a level
            strength_threshold: Minimum strength (0-1) to consider a level significant
        """
        self.pivot_period = pivot_period
        self.min_touches = min_touches
        self.strength_threshold = strength_threshold
    
    def calculate_pivot_levels(self, df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        """
        Calculate pivot point levels (PP, R1-R3, S1-S3) for each period
        
        Returns:
            Tuple of (support_levels, resistance_levels) lists
        """
        if len(df) < 2:
            return [], []
        
        # Determine grouping based on pivot period
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        if self.pivot_period == 'daily':
            df['period'] = df['time'].dt.date
        elif self.pivot_period == 'weekly':
            df['period'] = df['time'].dt.to_period('W').astype(str)
        elif self.pivot_period == 'monthly':
            df['period'] = df['time'].dt.to_period('M').astype(str)
        else:
            df['period'] = df['time'].dt.date  # Default to daily
        
        support_levels = []
        resistance_levels = []
        
        # Group by period and calculate pivots
        for period, group in df.groupby('period'):
            if len(group) < 1:
                continue
            
            high = float(group['high'].max())
            low = float(group['low'].min())
            close = float(group['close'].iloc[-1])
            
            # Calculate Pivot Point
            pp = (high + low + close) / 3.0
            
            # Calculate Resistance levels
            r1 = 2 * pp - low
            r2 = pp + (high - low)
            r3 = high + 2 * (pp - low)
            
            # Calculate Support levels
            s1 = 2 * pp - high
            s2 = pp - (high - low)
            s3 = low - 2 * (high - pp)
            
            # Add resistance levels
            for r_level, r_name in [(r1, 'R1'), (r2, 'R2'), (r3, 'R3')]:
                resistance_levels.append({
                    'price': r_level,
                    'type': 'pivot',
                    'pivot_type': r_name,
                    'period': str(period),
                    'strength': 0.5,  # Base strength, will be updated
                    'touches': 0,
                    'methods': ['pivot'],
                    'confluence_score': 0.0,
                    'timeframe': self.pivot_period
                })
            
            # Add support levels
            for s_level, s_name in [(s1, 'S1'), (s2, 'S2'), (s3, 'S3')]:
                support_levels.append({
                    'price': s_level,
                    'type': 'pivot',
                    'pivot_type': s_name,
                    'period': str(period),
                    'strength': 0.5,  # Base strength, will be updated
                    'touches': 0,
                    'methods': ['pivot'],
                    'confluence_score': 0.0,
                    'timeframe': self.pivot_period
                })
            
            # Also add PP as both support and resistance (neutral level)
            support_levels.append({
                'price': pp,
                'type': 'pivot',
                'pivot_type': 'PP',
                'period': str(period),
                'strength': 0.6,  # PP is typically stronger
                'touches': 0,
                'methods': ['pivot'],
                'confluence_score': 0.0,
                'timeframe': self.pivot_period
            })
        
        return support_levels, resistance_levels
    
    def cluster_levels(self, levels: List[Dict], price_tolerance: float = 0.001) -> List[Dict]:
        """
        Cluster nearby levels together and calculate strength
        
        Args:
            levels: List of level dictionaries
            price_tolerance: Percentage tolerance for clustering (0.001 = 0.1%)
            
        Returns:
            List of clustered level dictionaries
        """
        if not levels:
            return []
        
        # Sort by price
        sorted_levels = sorted(levels, key=lambda x: x['price'])
        
        clusters = []
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # Check if this level is within tolerance of current cluster
            cluster_avg = np.mean([l['price'] for l in current_cluster])
            if abs(level['price'] - cluster_avg) / cluster_avg <= price_tolerance:
                current_cluster.append(level)
            else:
                # Save current cluster and start new one
                if len(current_cluster) >= self.min_touches:
                    cluster_price = np.mean([l['price'] for l in current_cluster])
                    
                    # Aggregate methods from all levels in cluster
                    all_methods = []
                    for l in current_cluster:
                        all_methods.extend(l.get('methods', ['pivot']))
                    unique_methods = list(set(all_methods))
                    
                    # Calculate strength based on touches and confluence
                    base_strength = len(current_cluster) / 10.0  # Normalize
                    confluence_boost = len(unique_methods) * 0.1  # Boost for multiple methods
                    strength = min(base_strength + confluence_boost, 1.0)
                    
                    if strength >= self.strength_threshold:
                        clusters.append({
                            'price': cluster_price,
                            'strength': strength,
                            'touches': len(current_cluster),
                            'methods': unique_methods,
                            'confluence_score': len(unique_methods) / 5.0,  # Max 5 methods
                            'timeframe': current_cluster[0].get('timeframe', self.pivot_period),
                            'type': 'pivot',
                            'pivot_types': [l.get('pivot_type', '') for l in current_cluster]
                        })
                
                current_cluster = [level]
        
        # Don't forget the last cluster
        if len(current_cluster) >= self.min_touches:
            cluster_price = np.mean([l['price'] for l in current_cluster])
            
            all_methods = []
            for l in current_cluster:
                all_methods.extend(l.get('methods', ['pivot']))
            unique_methods = list(set(all_methods))
            
            base_strength = len(current_cluster) / 10.0
            confluence_boost = len(unique_methods) * 0.1
            strength = min(base_strength + confluence_boost, 1.0)
            
            if strength >= self.strength_threshold:
                clusters.append({
                    'price': cluster_price,
                    'strength': strength,
                    'touches': len(current_cluster),
                    'methods': unique_methods,
                    'confluence_score': len(unique_methods) / 5.0,
                    'timeframe': current_cluster[0].get('timeframe', self.pivot_period),
                    'type': 'pivot',
                    'pivot_types': [l.get('pivot_type', '') for l in current_cluster]
                })
        
        return clusters
    
    def calculate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate Support and Resistance levels using Pivot Points
        
        Returns:
            Dictionary with 'support_levels' and 'resistance_levels' lists
        """
        support_levels, resistance_levels = self.calculate_pivot_levels(df)
        
        # Cluster levels to combine nearby pivots
        if support_levels:
            support_levels = self.cluster_levels(support_levels)
        if resistance_levels:
            resistance_levels = self.cluster_levels(resistance_levels)
        
        # Sort by price (descending for resistance, ascending for support)
        resistance_levels.sort(key=lambda x: x['price'], reverse=True)
        support_levels.sort(key=lambda x: x['price'])
        
        return {
            'support_levels': support_levels,
            'resistance_levels': resistance_levels
        }


class SupportResistanceCalculator:
    """Legacy class - kept for backward compatibility, now uses PivotPointsCalculator"""
    
    def __init__(self, lookback_period: int = 50, min_touches: int = 2, strength_threshold: float = 0.5):
        """Initialize - now uses pivot points internally"""
        self.pivot_calculator = PivotPointsCalculator(
            pivot_period='daily',
            min_touches=min_touches,
            strength_threshold=strength_threshold
        )
    
    def calculate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate using pivot points"""
        return self.pivot_calculator.calculate(df)


class RoleReversalTracker:
    """Track when support/resistance levels reverse roles"""
    
    def __init__(self):
        """Initialize role reversal tracker"""
        self.reversal_history = []  # List of (level_price, old_type, new_type, timestamp)
    
    def check_role_reversal(self, level: Dict, current_price: float, previous_close: float) -> Optional[Dict]:
        """
        Check if a level has reversed roles
        
        Args:
            level: Level dictionary with 'price' and 'type' ('support' or 'resistance')
            current_price: Current price
            previous_close: Previous period's close price
            
        Returns:
            Dictionary with reversal info if reversed, None otherwise
        """
        level_price = level['price']
        level_type = level.get('type', 'unknown')
        
        # Check if resistance was broken (price closed above it)
        if level_type == 'resistance' and current_price > level_price and previous_close <= level_price:
            reversal_info = {
                'new_type': 'support',
                'reversed': True,
                'breakout_price': current_price,
                'breakout_time': datetime.now()
            }
            self.reversal_history.append({
                'price': level_price,
                'old_type': 'resistance',
                'new_type': 'support',
                'timestamp': datetime.now()
            })
            return reversal_info
        
        # Check if support was broken (price closed below it)
        elif level_type == 'support' and current_price < level_price and previous_close >= level_price:
            reversal_info = {
                'new_type': 'resistance',
                'reversed': True,
                'breakout_price': current_price,
                'breakout_time': datetime.now()
            }
            self.reversal_history.append({
                'price': level_price,
                'old_type': 'support',
                'new_type': 'resistance',
                'timestamp': datetime.now()
            })
            return reversal_info
        
        return None
    
    def apply_reversal(self, level: Dict, reversal_info: Dict) -> Dict:
        """
        Apply role reversal to a level
        
        Args:
            level: Original level dictionary
            reversal_info: Reversal information from check_role_reversal
            
        Returns:
            Updated level dictionary with reversed role
        """
        updated_level = level.copy()
        updated_level['type'] = reversal_info['new_type']
        updated_level['reversed'] = True
        updated_level['reversal_time'] = reversal_info['breakout_time']
        updated_level['breakout_price'] = reversal_info['breakout_price']
        
        # Add 'reversal' to methods if not already present
        if 'reversal' not in updated_level.get('methods', []):
            updated_level.setdefault('methods', []).append('reversal')
        
        return updated_level


class ReversalDetector:
    """Detect actual price reactions (bounces/reversals) at support/resistance levels"""
    
    def __init__(self, reaction_bars: int = 3):
        """
        Initialize reversal detector
        
        Args:
            reaction_bars: Number of bars to check for reversal after touch
        """
        self.reaction_bars = reaction_bars
    
    def detect_reaction(self, df: pd.DataFrame, level_price: float, level_type: str, touch_index: int) -> Dict:
        """
        Detect if price actually reacted (reversed) at a level
        
        Args:
            df: DataFrame with price data
            level_price: The support/resistance level price
            level_type: 'support' or 'resistance'
            touch_index: Index where price touched the level
            
        Returns:
            Dictionary with reaction information
        """
        if touch_index >= len(df) - self.reaction_bars:
            return {'reaction': False, 'magnitude': 0.0}
        
        touch_price = df.iloc[touch_index]
        reaction_window = df.iloc[touch_index:touch_index + self.reaction_bars + 1]
        
        if level_type == 'support':
            # For support: check if price bounced up after touching
            touch_low = touch_price['low']
            if abs(touch_low - level_price) / level_price <= 0.002:  # Within 0.2% of level
                # Check if subsequent bars moved up
                max_low_after = reaction_window['low'].iloc[1:].min()
                max_high_after = reaction_window['high'].iloc[1:].max()
                
                if max_high_after > level_price * 1.001:  # Price moved up by at least 0.1%
                    magnitude = (max_high_after - level_price) / level_price
                    return {
                        'reaction': True,
                        'magnitude': magnitude,
                        'direction': 'up'
                    }
        
        elif level_type == 'resistance':
            # For resistance: check if price bounced down after touching
            touch_high = touch_price['high']
            if abs(touch_high - level_price) / level_price <= 0.002:  # Within 0.2% of level
                # Check if subsequent bars moved down
                min_high_after = reaction_window['high'].iloc[1:].max()
                min_low_after = reaction_window['low'].iloc[1:].min()
                
                if min_low_after < level_price * 0.999:  # Price moved down by at least 0.1%
                    magnitude = (level_price - min_low_after) / level_price
                    return {
                        'reaction': True,
                        'magnitude': magnitude,
                        'direction': 'down'
                    }
        
        return {'reaction': False, 'magnitude': 0.0}
    
    def count_reactions(self, df: pd.DataFrame, level: Dict) -> int:
        """
        Count how many times price reacted at this level
        
        Args:
            df: DataFrame with price data
            level: Level dictionary
            
        Returns:
            Number of successful reactions
        """
        level_price = level['price']
        level_type = level.get('type', 'support')
        reactions = 0
        
        # Check each bar for touches and reactions
        for i in range(len(df) - self.reaction_bars):
            if level_type == 'support':
                if abs(df.iloc[i]['low'] - level_price) / level_price <= 0.002:
                    reaction = self.detect_reaction(df, level_price, level_type, i)
                    if reaction['reaction']:
                        reactions += 1
            else:  # resistance
                if abs(df.iloc[i]['high'] - level_price) / level_price <= 0.002:
                    reaction = self.detect_reaction(df, level_price, level_type, i)
                    if reaction['reaction']:
                        reactions += 1
        
        return reactions


class ConfluenceCalculator:
    """Calculate confluence when multiple methods identify the same level"""
    
    def __init__(self, price_tolerance: float = 0.001, min_methods: int = 2):
        """
        Initialize confluence calculator
        
        Args:
            price_tolerance: Price tolerance for considering levels as the same (0.001 = 0.1%)
            min_methods: Minimum number of methods needed for confluence
        """
        self.price_tolerance = price_tolerance
        self.min_methods = min_methods
    
    def calculate_confluence(self, all_levels: List[Dict]) -> List[Dict]:
        """
        Identify confluent levels (multiple methods agree)
        
        Args:
            all_levels: List of all levels from different methods
            
        Returns:
            List of levels with confluence scores updated
        """
        if not all_levels:
            return []
        
        # Group levels by price proximity
        sorted_levels = sorted(all_levels, key=lambda x: x['price'])
        confluent_groups = []
        current_group = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            # Check if this level is within tolerance of current group
            group_avg = np.mean([l['price'] for l in current_group])
            if abs(level['price'] - group_avg) / group_avg <= self.price_tolerance:
                current_group.append(level)
            else:
                # Save current group if it has confluence
                if len(current_group) >= self.min_methods:
                    confluent_groups.append(current_group)
                current_group = [level]
        
        # Don't forget the last group
        if len(current_group) >= self.min_methods:
            confluent_groups.append(current_group)
        
        # Update levels with confluence information
        updated_levels = []
        processed_indices = set()
        
        for group in confluent_groups:
            if len(group) < self.min_methods:
                # Not confluent, add as-is
                for level in group:
                    if id(level) not in processed_indices:
                        updated_levels.append(level)
                        processed_indices.add(id(level))
                continue
            
            # Calculate confluence metrics
            group_price = np.mean([l['price'] for l in group])
            all_methods = []
            for l in group:
                all_methods.extend(l.get('methods', []))
            unique_methods = list(set(all_methods))
            
            # Calculate confluence score (0-1)
            confluence_score = min(len(unique_methods) / 5.0, 1.0)  # Max 5 methods
            
            # Boost strength based on confluence
            base_strength = np.mean([l.get('strength', 0.5) for l in group])
            confluence_boost = confluence_score * 0.3  # Up to 30% boost
            boosted_strength = min(base_strength + confluence_boost, 1.0)
            
            # Create confluent level
            confluent_level = {
                'price': group_price,
                'strength': boosted_strength,
                'touches': sum([l.get('touches', 0) for l in group]),
                'methods': unique_methods,
                'confluence_score': confluence_score,
                'timeframe': group[0].get('timeframe', 'daily'),
                'type': group[0].get('type', 'pivot'),
                'confluent': True
            }
            
            updated_levels.append(confluent_level)
            
            # Mark all levels in group as processed
            for level in group:
                processed_indices.add(id(level))
        
        # Add non-confluent levels
        for level in sorted_levels:
            if id(level) not in processed_indices:
                level['confluence_score'] = 0.0
                level['confluent'] = False
                updated_levels.append(level)
        
        return updated_levels


class SignalQueue:
    """Manage multiple pending trade conditions"""
    
    def __init__(self):
        self.conditions: List[Dict[str, Any]] = []
        self.executed_conditions: List[Dict[str, Any]] = []
    
    def add_condition(self, config: Dict[str, Any]) -> str:
        """Add a new condition to the queue - creates separate conditions for BUY and SELL if both enabled"""
        condition_ids = []
        indicator_type = config.get('indicator_type', 'Support/Resistance')
        
        # Support/Resistance conditions
        if indicator_type == 'Support/Resistance':
            # Create BUY condition if enabled
            if config.get('sr_resistance_breakout_buy', False):
                condition_id = str(uuid.uuid4())
                resistance_price = config.get('selected_resistance_price')
                condition = {
                    'id': condition_id,
                    'indicator_type': indicator_type,
                    'symbol': config.get('symbol', config.get('symbols', ['EURUSD'])[0] if config.get('symbols') else 'EURUSD'),
                    'timeframe': config['timeframe'],
                    'entry_type': 'BUY',
                    'level_price': resistance_price,
                    'level_type': 'resistance',
                    'breakout_confirmation': config.get('sr_breakout_confirmation', 0.001),
                    'status': 'Pending',
                    'enabled': True,
                    'exit_conditions': config.get('exit_conditions', {}),
                    'sl_tp_method': config.get('sl_tp_method', 'sr_based'),
                    'sl_tp_params': config.get('sl_tp_params', {}),
                    'quantity': config.get('quantity', 0.01),
                    'risk_reward_ratio': config.get('risk_reward_ratio', 2.0),
                    'created_at': datetime.now(),
                    'current_price': None,
                    'breakout_price': None
                }
                self.conditions.append(condition)
                condition_ids.append(condition_id)
                logger.info(f"Added BUY condition {condition_id} to queue: {condition['symbol']}")
            
            # Create SELL condition if enabled
            if config.get('sr_support_breakdown_sell', False):
                condition_id = str(uuid.uuid4())
                support_price = config.get('selected_support_price')
                condition = {
                    'id': condition_id,
                    'indicator_type': indicator_type,
                    'symbol': config.get('symbol', config.get('symbols', ['EURUSD'])[0] if config.get('symbols') else 'EURUSD'),
                    'timeframe': config['timeframe'],
                    'entry_type': 'SELL',
                    'level_price': support_price,
                    'level_type': 'support',
                    'breakout_confirmation': config.get('sr_breakout_confirmation', 0.001),
                    'status': 'Pending',
                    'enabled': True,
                    'exit_conditions': config.get('exit_conditions', {}),
                    'sl_tp_method': config.get('sl_tp_method', 'sr_based'),
                    'sl_tp_params': config.get('sl_tp_params', {}),
                    'quantity': config.get('quantity', 0.01),
                    'risk_reward_ratio': config.get('risk_reward_ratio', 2.0),
                    'created_at': datetime.now(),
                    'current_price': None,
                    'breakout_price': None
                }
                self.conditions.append(condition)
                condition_ids.append(condition_id)
                logger.info(f"Added SELL condition {condition_id} to queue: {condition['symbol']}")
        
        # OHLC conditions
        elif indicator_type == 'Previous Session OHLC':
            symbol = config.get('symbol', config.get('symbols', ['EURUSD'])[0] if config.get('symbols') else 'EURUSD')
            breakout_conf = config.get('ohlc_breakout_confirmation', 0.001)
            
            # Create BUY conditions for OHLC
            if config.get('ohlc_buy_high', False):
                condition_id = str(uuid.uuid4())
                condition = {
                    'id': condition_id,
                    'indicator_type': indicator_type,
                    'symbol': symbol,
                    'timeframe': config['timeframe'],
                    'entry_type': 'BUY',
                    'level_price': None,  # Will be set to previous high
                    'level_type': 'ohlc_high',
                    'breakout_confirmation': breakout_conf,
                    'status': 'Pending',
                    'enabled': True,
                    'exit_conditions': config.get('exit_conditions', {}),
                    'sl_tp_method': config.get('sl_tp_method', 'sr_based'),
                    'sl_tp_params': config.get('sl_tp_params', {}),
                    'quantity': config.get('quantity', 0.01),
                    'risk_reward_ratio': config.get('risk_reward_ratio', 2.0),
                    'created_at': datetime.now(),
                    'current_price': None,
                    'breakout_price': None
                }
                self.conditions.append(condition)
                condition_ids.append(condition_id)
            
            if config.get('ohlc_buy_close', False):
                condition_id = str(uuid.uuid4())
                condition = {
                    'id': condition_id,
                    'indicator_type': indicator_type,
                    'symbol': symbol,
                    'timeframe': config['timeframe'],
                    'entry_type': 'BUY',
                    'level_price': None,  # Will be set to previous close
                    'level_type': 'ohlc_close',
                    'breakout_confirmation': breakout_conf,
                    'status': 'Pending',
                    'enabled': True,
                    'exit_conditions': config.get('exit_conditions', {}),
                    'sl_tp_method': config.get('sl_tp_method', 'sr_based'),
                    'sl_tp_params': config.get('sl_tp_params', {}),
                    'quantity': config.get('quantity', 0.01),
                    'risk_reward_ratio': config.get('risk_reward_ratio', 2.0),
                    'created_at': datetime.now(),
                    'current_price': None,
                    'breakout_price': None
                }
                self.conditions.append(condition)
                condition_ids.append(condition_id)
            
            if config.get('ohlc_buy_open', False):
                condition_id = str(uuid.uuid4())
                condition = {
                    'id': condition_id,
                    'indicator_type': indicator_type,
                    'symbol': symbol,
                    'timeframe': config['timeframe'],
                    'entry_type': 'BUY',
                    'level_price': None,  # Will be set to previous open
                    'level_type': 'ohlc_open',
                    'breakout_confirmation': breakout_conf,
                    'status': 'Pending',
                    'enabled': True,
                    'exit_conditions': config.get('exit_conditions', {}),
                    'sl_tp_method': config.get('sl_tp_method', 'sr_based'),
                    'sl_tp_params': config.get('sl_tp_params', {}),
                    'quantity': config.get('quantity', 0.01),
                    'risk_reward_ratio': config.get('risk_reward_ratio', 2.0),
                    'created_at': datetime.now(),
                    'current_price': None,
                    'breakout_price': None
                }
                self.conditions.append(condition)
                condition_ids.append(condition_id)
            
            # Create SELL conditions for OHLC
            if config.get('ohlc_sell_low', False):
                condition_id = str(uuid.uuid4())
                condition = {
                    'id': condition_id,
                    'indicator_type': indicator_type,
                    'symbol': symbol,
                    'timeframe': config['timeframe'],
                    'entry_type': 'SELL',
                    'level_price': None,  # Will be set to previous low
                    'level_type': 'ohlc_low',
                    'breakout_confirmation': breakout_conf,
                    'status': 'Pending',
                    'enabled': True,
                    'exit_conditions': config.get('exit_conditions', {}),
                    'sl_tp_method': config.get('sl_tp_method', 'sr_based'),
                    'sl_tp_params': config.get('sl_tp_params', {}),
                    'quantity': config.get('quantity', 0.01),
                    'risk_reward_ratio': config.get('risk_reward_ratio', 2.0),
                    'created_at': datetime.now(),
                    'current_price': None,
                    'breakout_price': None
                }
                self.conditions.append(condition)
                condition_ids.append(condition_id)
            
            if config.get('ohlc_sell_close', False):
                condition_id = str(uuid.uuid4())
                condition = {
                    'id': condition_id,
                    'indicator_type': indicator_type,
                    'symbol': symbol,
                    'timeframe': config['timeframe'],
                    'entry_type': 'SELL',
                    'level_price': None,  # Will be set to previous close
                    'level_type': 'ohlc_close',
                    'breakout_confirmation': breakout_conf,
                    'status': 'Pending',
                    'enabled': True,
                    'exit_conditions': config.get('exit_conditions', {}),
                    'sl_tp_method': config.get('sl_tp_method', 'sr_based'),
                    'sl_tp_params': config.get('sl_tp_params', {}),
                    'quantity': config.get('quantity', 0.01),
                    'risk_reward_ratio': config.get('risk_reward_ratio', 2.0),
                    'created_at': datetime.now(),
                    'current_price': None,
                    'breakout_price': None
                }
                self.conditions.append(condition)
                condition_ids.append(condition_id)
            
            if config.get('ohlc_sell_open', False):
                condition_id = str(uuid.uuid4())
                condition = {
                    'id': condition_id,
                    'indicator_type': indicator_type,
                    'symbol': symbol,
                    'timeframe': config['timeframe'],
                    'entry_type': 'SELL',
                    'level_price': None,  # Will be set to previous open
                    'level_type': 'ohlc_open',
                    'breakout_confirmation': breakout_conf,
                    'status': 'Pending',
                    'enabled': True,
                    'exit_conditions': config.get('exit_conditions', {}),
                    'sl_tp_method': config.get('sl_tp_method', 'sr_based'),
                    'sl_tp_params': config.get('sl_tp_params', {}),
                    'quantity': config.get('quantity', 0.01),
                    'risk_reward_ratio': config.get('risk_reward_ratio', 2.0),
                    'created_at': datetime.now(),
                    'current_price': None,
                    'breakout_price': None
                }
                self.conditions.append(condition)
                condition_ids.append(condition_id)
        
        # Return the first condition ID (or both if needed)
        return condition_ids[0] if condition_ids else ""
    
    def remove_condition(self, condition_id: str) -> bool:
        """Remove a condition from the queue"""
        for i, condition in enumerate(self.conditions):
            if condition['id'] == condition_id:
                self.conditions.pop(i)
                logger.info(f"Removed condition {condition_id} from queue")
                return True
        return False
    
    def toggle_condition(self, condition_id: str) -> bool:
        """Enable/disable a condition"""
        for condition in self.conditions:
            if condition['id'] == condition_id:
                condition['enabled'] = not condition['enabled']
                logger.info(f"Toggled condition {condition_id} to {condition['enabled']}")
                return condition['enabled']
        return False
    
    def get_pending_conditions(self) -> List[Dict[str, Any]]:
        """Get all pending and enabled conditions"""
        return [c for c in self.conditions if c['status'] == 'Pending' and c['enabled']]
    
    def mark_executed(self, condition_id: str):
        """Mark a condition as executed"""
        for condition in self.conditions:
            if condition['id'] == condition_id:
                condition['status'] = 'Executed'
                condition['executed_at'] = datetime.now()
                self.executed_conditions.append(condition.copy())
                logger.info(f"Marked condition {condition_id} as executed")
                break
    
    def update_condition_price(self, condition_id: str, current_price: float, breakout_price: float):
        """Update current price and breakout price for a condition"""
        for condition in self.conditions:
            if condition['id'] == condition_id:
                condition['current_price'] = current_price
                condition['breakout_price'] = breakout_price
                break
    
    def save_to_file(self, file_path: str) -> bool:
        """Save conditions to JSON file"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert datetime objects to strings for JSON serialization
            serializable_conditions = []
            for condition in self.conditions:
                serializable_condition = condition.copy()
                if 'created_at' in serializable_condition and isinstance(serializable_condition['created_at'], datetime):
                    serializable_condition['created_at'] = serializable_condition['created_at'].isoformat()
                if 'executed_at' in serializable_condition and isinstance(serializable_condition['executed_at'], datetime):
                    serializable_condition['executed_at'] = serializable_condition['executed_at'].isoformat()
                serializable_conditions.append(serializable_condition)
            
            data = {
                'conditions': serializable_conditions,
                'executed_conditions': []  # Don't persist executed conditions
            }
            
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(serializable_conditions)} conditions to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving signal queue to {file_path}: {e}", exc_info=True)
            return False
    
    def load_from_file(self, file_path: str) -> bool:
        """Load conditions from JSON file"""
        try:
            path = Path(file_path)
            if not path.exists():
                logger.debug(f"Signal queue file {file_path} does not exist, starting with empty queue")
                return False
            
            with open(path, 'r') as f:
                data = json.load(f)
            
            # Restore datetime objects from strings
            self.conditions = []
            for condition in data.get('conditions', []):
                if 'created_at' in condition and isinstance(condition['created_at'], str):
                    try:
                        condition['created_at'] = datetime.fromisoformat(condition['created_at'])
                    except:
                        condition['created_at'] = datetime.now()
                if 'executed_at' in condition and isinstance(condition['executed_at'], str):
                    try:
                        condition['executed_at'] = datetime.fromisoformat(condition['executed_at'])
                    except:
                        pass
                # Reset status to Pending for loaded conditions
                condition['status'] = 'Pending'
                self.conditions.append(condition)
            
            logger.info(f"Loaded {len(self.conditions)} conditions from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading signal queue from {file_path}: {e}", exc_info=True)
            return False


class PreviousSessionOHLCCalculator:
    """Calculate Previous Trading Session OHLC values"""
    
    def __init__(self, session_type: str = 'daily'):
        """
        Initialize OHLC calculator
        
        Args:
            session_type: 'daily', 'weekly', 'monthly', 'asian', 'european', or 'us'
        """
        self.session_type = session_type.lower()
        self.prev_open = None
        self.prev_high = None
        self.prev_low = None
        self.prev_close = None
        self.session_name = None
        self.session_start = None
        self.session_end = None
        # Initialize symbol mapper for symbol normalization
        self.symbol_mapper = SymbolMapper()
    
    def get_session_times(self, current_time: datetime) -> Tuple[datetime, datetime]:
        """
        Get previous session start and end times based on session type
        
        Returns:
            Tuple of (session_start, session_end) in GMT
        """
        # Convert current time to GMT if needed
        current_gmt = current_time
        
        if self.session_type == 'daily':
            # Previous day's OHLC (00:00-23:59 GMT)
            # Find previous trading day (skip weekends)
            prev_day = current_gmt - timedelta(days=1)
            while prev_day.weekday() >= 5:  # Saturday = 5, Sunday = 6
                prev_day -= timedelta(days=1)
            
            session_start = prev_day.replace(hour=0, minute=0, second=0, microsecond=0)
            session_end = prev_day.replace(hour=23, minute=59, second=59, microsecond=999999)
            self.session_name = f"Daily ({prev_day.strftime('%Y-%m-%d')})"
            
        elif self.session_type == 'asian':
            # Asian session: 00:00-09:00 GMT
            # Get previous Asian session
            if current_gmt.hour < 9:
                # Current session hasn't ended, get session from yesterday
                prev_day = current_gmt - timedelta(days=1)
                while prev_day.weekday() >= 5:
                    prev_day -= timedelta(days=1)
            else:
                prev_day = current_gmt
            
            session_start = prev_day.replace(hour=0, minute=0, second=0, microsecond=0)
            session_end = prev_day.replace(hour=9, minute=0, second=0, microsecond=0)
            self.session_name = f"Asian Session ({prev_day.strftime('%Y-%m-%d')})"
            
        elif self.session_type == 'european':
            # European session: 08:00-17:00 GMT
            if current_gmt.hour < 8:
                # Before European session today, get yesterday's session
                prev_day = current_gmt - timedelta(days=1)
                while prev_day.weekday() >= 5:
                    prev_day -= timedelta(days=1)
                session_start = prev_day.replace(hour=8, minute=0, second=0, microsecond=0)
                session_end = prev_day.replace(hour=17, minute=0, second=0, microsecond=0)
            elif current_gmt.hour < 17:
                # Current European session, get previous day's
                prev_day = current_gmt - timedelta(days=1)
                while prev_day.weekday() >= 5:
                    prev_day -= timedelta(days=1)
                session_start = prev_day.replace(hour=8, minute=0, second=0, microsecond=0)
                session_end = prev_day.replace(hour=17, minute=0, second=0, microsecond=0)
            else:
                # After European session today, get yesterday's session (previous session)
                prev_day = current_gmt - timedelta(days=1)
                while prev_day.weekday() >= 5:
                    prev_day -= timedelta(days=1)
                session_start = prev_day.replace(hour=8, minute=0, second=0, microsecond=0)
                session_end = prev_day.replace(hour=17, minute=0, second=0, microsecond=0)
            
            self.session_name = f"European Session ({prev_day.strftime('%Y-%m-%d')})"
            
        elif self.session_type == 'us':
            # US session: 13:00-22:00 GMT
            if current_gmt.hour < 13:
                # Before US session today, get yesterday's session
                prev_day = current_gmt - timedelta(days=1)
                while prev_day.weekday() >= 5:
                    prev_day -= timedelta(days=1)
                session_start = prev_day.replace(hour=13, minute=0, second=0, microsecond=0)
                session_end = prev_day.replace(hour=22, minute=0, second=0, microsecond=0)
            elif current_gmt.hour < 22:
                # Current US session, get previous day's
                prev_day = current_gmt - timedelta(days=1)
                while prev_day.weekday() >= 5:
                    prev_day -= timedelta(days=1)
                session_start = prev_day.replace(hour=13, minute=0, second=0, microsecond=0)
                session_end = prev_day.replace(hour=22, minute=0, second=0, microsecond=0)
            else:
                # After US session today, get yesterday's session (previous session)
                prev_day = current_gmt - timedelta(days=1)
                while prev_day.weekday() >= 5:
                    prev_day -= timedelta(days=1)
                session_start = prev_day.replace(hour=13, minute=0, second=0, microsecond=0)
                session_end = prev_day.replace(hour=22, minute=0, second=0, microsecond=0)
            
            self.session_name = f"US Session ({prev_day.strftime('%Y-%m-%d')})"
            
        elif self.session_type == 'weekly':
            # Previous week's OHLC (Monday 00:00 to Friday 23:59 GMT)
            # Find the start of current week (Monday)
            days_since_monday = current_gmt.weekday()
            current_week_start = current_gmt - timedelta(days=days_since_monday)
            current_week_start = current_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Previous week is 7 days before current week start
            prev_week_start = current_week_start - timedelta(days=7)
            prev_week_end = prev_week_start + timedelta(days=4, hours=23, minutes=59, seconds=59)  # Friday 23:59
            
            session_start = prev_week_start
            session_end = prev_week_end
            self.session_name = f"Weekly ({prev_week_start.strftime('%Y-%m-%d')} to {prev_week_end.strftime('%Y-%m-%d')})"
            
        elif self.session_type == 'monthly':
            # Previous month's OHLC (1st 00:00 to last day 23:59 GMT)
            # Find first day of current month
            current_month_start = current_gmt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Previous month is one day before current month
            prev_month_end = current_month_start - timedelta(days=1)
            prev_month_start = prev_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            prev_month_end = prev_month_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            session_start = prev_month_start
            session_end = prev_month_end
            self.session_name = f"Monthly ({prev_month_start.strftime('%B %Y')})"
            
        else:
            # Default to daily
            prev_day = current_gmt - timedelta(days=1)
            while prev_day.weekday() >= 5:
                prev_day -= timedelta(days=1)
            session_start = prev_day.replace(hour=0, minute=0, second=0, microsecond=0)
            session_end = prev_day.replace(hour=23, minute=59, second=59, microsecond=999999)
            self.session_name = f"Daily ({prev_day.strftime('%Y-%m-%d')})"
        
        self.session_start = session_start
        self.session_end = session_end
        return session_start, session_end
    
    def calculate_ohlc(self, symbol: str, timeframe=mt5.TIMEFRAME_M1) -> bool:
        """
        Calculate previous session OHLC from MT5 data
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe for data retrieval (ignored for daily, uses D1)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize symbol to ensure correct case (MT5 is case-sensitive)
            # Try to find the correct symbol name using symbol mapper
            normalized_symbol = self.symbol_mapper.find_symbol(symbol)
            if normalized_symbol is None:
                # If mapper can't find it, try case-insensitive search
                all_symbols = self.symbol_mapper._get_all_symbols()
                symbol_upper = symbol.upper()
                for sym in all_symbols:
                    if sym.upper() == symbol_upper:
                        normalized_symbol = sym
                        break
                # If still not found, use original symbol (will fail gracefully)
                if normalized_symbol is None:
                    normalized_symbol = symbol
                    logger.warning(f"Could not normalize symbol {symbol}, using as-is")
            
            # Use normalized symbol for MT5 calls
            symbol = normalized_symbol
            
            # For daily sessions, use D1 timeframe directly to match MT5 exactly
            if self.session_type == 'daily':
                # Get previous day's D1 bar (position 1, since position 0 is today)
                rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_D1, 1, 1)
                
                if rates is None or len(rates) == 0:
                    # Fallback to M1 calculation if D1 not available
                    logger.warning(f"D1 data not available for {symbol}, falling back to M1 calculation")
                    return self._calculate_ohlc_from_m1(symbol)
                
                # Extract OHLC directly from D1 bar (this matches MT5 exactly)
                rate = rates[0]
                self.prev_open = float(rate[1])  # open
                self.prev_high = float(rate[2])  # high
                self.prev_low = float(rate[3])   # low
                self.prev_close = float(rate[4]) # close
                
                # Get the date from the D1 bar for session name
                bar_time = datetime.fromtimestamp(rate[0])
                self.session_name = f"Daily ({bar_time.strftime('%Y-%m-%d')})"
                
                logger.info(f"Calculated {self.session_name} OHLC for {symbol} from D1: "
                           f"O={self.prev_open:.5f}, H={self.prev_high:.5f}, "
                           f"L={self.prev_low:.5f}, C={self.prev_close:.5f}")
                
                return True
            else:
                # For intraday sessions (Asian, European, US), use M1 calculation
                return self._calculate_ohlc_from_m1(symbol)
            
        except Exception as e:
            logger.error(f"Error calculating OHLC for {symbol}: {e}", exc_info=True)
            # Try fallback to M1 if D1 failed
            if self.session_type == 'daily':
                logger.warning(f"Falling back to M1 calculation for {symbol}")
                return self._calculate_ohlc_from_m1(symbol)
            return False
    
    def _calculate_ohlc_from_m1(self, symbol: str) -> bool:
        """
        Calculate OHLC from M1 data (used for intraday sessions and as fallback)
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Normalize symbol to ensure correct case (MT5 is case-sensitive)
            normalized_symbol = self.symbol_mapper.find_symbol(symbol)
            if normalized_symbol is None:
                # If mapper can't find it, try case-insensitive search
                all_symbols = self.symbol_mapper._get_all_symbols()
                symbol_upper = symbol.upper()
                for sym in all_symbols:
                    if sym.upper() == symbol_upper:
                        normalized_symbol = sym
                        break
                # If still not found, use original symbol (will fail gracefully)
                if normalized_symbol is None:
                    normalized_symbol = symbol
                    logger.warning(f"Could not normalize symbol {symbol} in M1 calculation, using as-is")
            
            # Use normalized symbol for MT5 calls
            symbol = normalized_symbol
            
            current_time = datetime.now()
            session_start, session_end = self.get_session_times(current_time)
            
            # Convert to timestamps for MT5
            start_timestamp = int(session_start.timestamp())
            end_timestamp = int(session_end.timestamp())
            
            # Fetch historical data for the session using M1
            rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start_timestamp, end_timestamp)
            if rates is None or len(rates) == 0:
                logger.warning(f"No M1 data found for {symbol} in session {self.session_name}")
                return False
            
            # Convert to DataFrame for easier processing
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Calculate OHLC from M1 bars
            self.prev_open = float(df.iloc[0]['open'])
            self.prev_high = float(df['high'].max())
            self.prev_low = float(df['low'].min())
            self.prev_close = float(df.iloc[-1]['close'])
            
            logger.info(f"Calculated {self.session_name} OHLC for {symbol} from M1: "
                       f"O={self.prev_open:.5f}, H={self.prev_high:.5f}, "
                       f"L={self.prev_low:.5f}, C={self.prev_close:.5f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error calculating OHLC from M1 for {symbol}: {e}", exc_info=True)
            return False
    
    def get_ohlc(self) -> Dict[str, Optional[float]]:
        """Get calculated OHLC values"""
        return {
            'open': self.prev_open,
            'high': self.prev_high,
            'low': self.prev_low,
            'close': self.prev_close,
            'session_name': self.session_name
        }


class TrailingStopLoss:
    """Trailing Stop-Loss System - tracks highest/lowest price and moves SL by gap"""
    
    def __init__(self, entry_price: float, sl_gap: float, position_type: str):
        """
        Args:
            entry_price: Entry price of the position
            sl_gap: Gap for trailing stop (in price points)
            position_type: 'BUY' or 'SELL'
        """
        self.entry_price = entry_price
        self.sl_gap = sl_gap
        self.position_type = position_type.upper()
        
        if self.position_type == 'BUY':
            self.stop_loss = entry_price - sl_gap  # Initial SL below entry
            self.highest_price = entry_price  # Track highest price
        else:  # SELL
            self.stop_loss = entry_price + sl_gap  # Initial SL above entry
            self.lowest_price = entry_price  # Track lowest price
    
    def update_price(self, current_price: float) -> float:
        """
        Update trailing stop-loss based on current price
        Returns: Updated stop-loss price
        """
        if self.position_type == 'BUY':
            # Update highest seen price
            if current_price > self.highest_price:
                self.highest_price = current_price
                # Calculate new SL
                new_sl = self.highest_price - self.sl_gap
                # Trailing SL only moves upward (for BUY)
                if new_sl > self.stop_loss:
                    self.stop_loss = new_sl
        else:  # SELL
            # Update lowest seen price
            if current_price < self.lowest_price:
                self.lowest_price = current_price
                # Calculate new SL
                new_sl = self.lowest_price + self.sl_gap
                # Trailing SL only moves downward (for SELL)
                if new_sl < self.stop_loss:
                    self.stop_loss = new_sl
        
        return self.stop_loss


class ProfitManager:
    """Profit Lock + Trailing Logic - locks minimum profit and trails it"""
    
    def __init__(self, lock_trigger: float, lock_value: float, 
                 trail_step: float, trail_amount: float, position_type: str):
        """
        Args:
            lock_trigger: Profit amount to trigger lock
            lock_value: Minimum profit to lock
            trail_step: Profit increase to trigger trail
            trail_amount: Amount to trail profit by
            position_type: 'BUY' or 'SELL'
        """
        self.lock_trigger = lock_trigger
        self.lock_value = lock_value
        self.trail_step = trail_step
        self.trail_amount = trail_amount
        self.position_type = position_type.upper()
        
        self.lock_enabled = False
        self.current_locked_profit = 0
        self.last_trail_base = lock_trigger  # Will trail only after reaching trigger
    
    def update_profit(self, profit: float) -> float:
        """
        Call this function on every profit change.
        Returns: Updated locked profit (minimum TP to maintain)
        """
        # Enable locking when profit reaches trigger
        if profit >= self.lock_trigger and not self.lock_enabled:
            self.lock_enabled = True
            self.current_locked_profit = self.lock_value
        
        # Apply trailing only after lock trigger is hit
        if self.lock_enabled and self.trail_step > 0:
            # Check if profit increased enough to trail more
            while profit >= self.last_trail_base + self.trail_step:
                self.last_trail_base += self.trail_step
                self.current_locked_profit += self.trail_amount
        
        return self.current_locked_profit
    
    def calculate_take_profit_price(self, entry_price: float, current_price: float) -> float:
        """
        Calculate the take-profit price based on locked profit
        Returns: Take-profit price to maintain locked profit
        """
        if not self.lock_enabled or self.current_locked_profit == 0:
            return 0.0  # No TP adjustment needed
        
        if self.position_type == 'BUY':
            # For BUY: TP = entry + locked_profit
            return entry_price + self.current_locked_profit
        else:  # SELL
            # For SELL: TP = entry - locked_profit
            return entry_price - self.current_locked_profit


class ExitConditionManager:
    """Manage and check exit conditions for open positions"""
    
    def __init__(self):
        self.active_exits: Dict[int, Dict[str, Any]] = {}  # ticket -> exit_config
    
    def register_position(self, ticket: int, entry_data: Dict[str, Any]):
        """Register a position for exit condition monitoring"""
        entry_price = entry_data.get('entry_price')
        entry_type = entry_data.get('entry_type', 'BUY')
        
        # Initialize trailing stop-loss if enabled
        trailing_sl = None
        if entry_data.get('enable_trailing_sl', False):
            sl_gap = entry_data.get('trailing_sl_gap', 0.001)
            trailing_sl = TrailingStopLoss(entry_price, sl_gap, entry_type)
        
        # Initialize profit lock if enabled
        profit_lock = None
        if entry_data.get('enable_profit_lock', False):
            profit_lock = ProfitManager(
                lock_trigger=entry_data.get('profit_lock_trigger', 100.0),
                lock_value=entry_data.get('profit_lock_value', 50.0),
                trail_step=entry_data.get('profit_trail_step', 100.0),
                trail_amount=entry_data.get('profit_trail_amount', 50.0),
                position_type=entry_type
            )
        
        self.active_exits[ticket] = {
            'entry_price': entry_price,
            'entry_time': entry_data.get('entry_time', datetime.now()),
            'entry_type': entry_type,
            'exit_conditions': entry_data.get('exit_conditions', {}),
            'trailing_stop_price': None,
            'highest_price': entry_price if entry_type == 'BUY' else None,
            'lowest_price': entry_price if entry_type == 'SELL' else None,
            'trailing_sl': trailing_sl,  # TrailingStopLoss instance
            'profit_lock': profit_lock,  # ProfitManager instance
            'symbol': entry_data.get('symbol'),
            'volume': entry_data.get('volume', 0.01),
        }
    
    def check_exit_conditions(self, ticket: int, current_price: float, 
                             support_levels: List[Dict], resistance_levels: List[Dict]) -> Optional[str]:
        """Check if any exit condition is met"""
        if ticket not in self.active_exits:
            return None
        
        exit_config = self.active_exits[ticket]
        exit_conditions = exit_config.get('exit_conditions', {})
        entry_type = exit_config['entry_type']
        entry_price = exit_config['entry_price']
        
        # Update trailing stop tracking
        if entry_type == 'BUY':
            if current_price > exit_config['highest_price']:
                exit_config['highest_price'] = current_price
        else:  # SELL
            if current_price < exit_config['lowest_price']:
                exit_config['lowest_price'] = current_price
        
        # Check SR-based exit
        if entry_type == 'BUY' and exit_conditions.get('exit_buy_sr_touch', False):
            # Exit BUY when price touches support
            for support in support_levels:
                if abs(current_price - support['price']) / current_price <= 0.002:  # Within 0.2%
                    return 'SR_Touch'
        elif entry_type == 'SELL' and exit_conditions.get('exit_sell_sr_touch', False):
            # Exit SELL when price touches resistance
            for resistance in resistance_levels:
                if abs(current_price - resistance['price']) / current_price <= 0.002:
                    return 'SR_Touch'
        
        # Check trailing stop
        if entry_type == 'BUY' and exit_conditions.get('exit_buy_trailing_stop', False):
            trailing_pct = exit_conditions.get('exit_buy_trailing_stop_pct', 0.01) / 100.0  # Convert to decimal
            trailing_price = exit_config['highest_price'] * (1 - trailing_pct)
            if exit_config['trailing_stop_price'] is None:
                exit_config['trailing_stop_price'] = trailing_price
            else:
                # Only move up, never down
                exit_config['trailing_stop_price'] = max(exit_config['trailing_stop_price'], trailing_price)
            
            if current_price <= exit_config['trailing_stop_price']:
                return 'TrailingStop'
        elif entry_type == 'SELL' and exit_conditions.get('exit_sell_trailing_stop', False):
            trailing_pct = exit_conditions.get('exit_sell_trailing_stop_pct', 0.01) / 100.0  # Convert to decimal
            trailing_price = exit_config['lowest_price'] * (1 + trailing_pct)
            if exit_config['trailing_stop_price'] is None:
                exit_config['trailing_stop_price'] = trailing_price
            else:
                # Only move down, never up
                exit_config['trailing_stop_price'] = min(exit_config['trailing_stop_price'], trailing_price)
            
            if current_price >= exit_config['trailing_stop_price']:
                return 'TrailingStop'
        
        # Check time limit
        if entry_type == 'BUY' and exit_conditions.get('exit_buy_time_limit', False):
            time_limit_minutes = exit_conditions.get('exit_buy_time_limit_minutes', 60)
            elapsed = (datetime.now() - exit_config['entry_time']).total_seconds() / 60
            if elapsed >= time_limit_minutes:
                return 'TimeLimit'
        elif entry_type == 'SELL' and exit_conditions.get('exit_sell_time_limit', False):
            time_limit_minutes = exit_conditions.get('exit_sell_time_limit_minutes', 60)
            elapsed = (datetime.now() - exit_config['entry_time']).total_seconds() / 60
            if elapsed >= time_limit_minutes:
                return 'TimeLimit'
        
        # Check profit target
        if entry_type == 'BUY' and exit_conditions.get('exit_buy_profit_target', False):
            profit_target_pct = exit_conditions.get('exit_buy_profit_target_pct', 2.0) / 100.0  # Convert to decimal
            profit_pct = (current_price - entry_price) / entry_price
            if profit_pct >= profit_target_pct:
                return 'ProfitTarget'
        elif entry_type == 'SELL' and exit_conditions.get('exit_sell_profit_target', False):
            profit_target_pct = exit_conditions.get('exit_sell_profit_target_pct', 2.0) / 100.0  # Convert to decimal
            profit_pct = (entry_price - current_price) / entry_price
            if profit_pct >= profit_target_pct:
                return 'ProfitTarget'
        
        return None
    
    def update_trailing_and_profit_lock(self, ticket: int, current_price: float, 
                                       current_profit: float, mt5_connector) -> Dict[str, Optional[float]]:
        """
        Update trailing stop-loss and profit lock for a position
        Returns: Dict with 'new_sl' and 'new_tp' if updates needed, None otherwise
        """
        if ticket not in self.active_exits:
            return {'new_sl': None, 'new_tp': None}
        
        exit_config = self.active_exits[ticket]
        entry_price = exit_config['entry_price']
        entry_type = exit_config['entry_type']
        updates = {'new_sl': None, 'new_tp': None}
        
        # Update trailing stop-loss
        trailing_sl = exit_config.get('trailing_sl')
        if trailing_sl:
            new_sl = trailing_sl.update_price(current_price)
            # Check if SL should trigger close
            if entry_type == 'BUY' and current_price <= new_sl:
                return {'new_sl': None, 'new_tp': None, 'should_close': True, 'reason': 'TrailingSL'}
            elif entry_type == 'SELL' and current_price >= new_sl:
                return {'new_sl': None, 'new_tp': None, 'should_close': True, 'reason': 'TrailingSL'}
            
            # Only update if SL has changed significantly (avoid too frequent updates)
            current_sl = exit_config.get('current_sl', 0.0)
            if abs(new_sl - current_sl) > (new_sl * 0.0001):  # 0.01% change threshold
                updates['new_sl'] = new_sl
                exit_config['current_sl'] = new_sl
        
        # Update profit lock
        profit_lock = exit_config.get('profit_lock')
        if profit_lock and current_profit > 0:
            locked_profit = profit_lock.update_profit(current_profit)
            if locked_profit > 0:
                # Calculate new TP price based on locked profit
                # Profit formula: profit = (price_diff) * volume * contract_size / point
                # So: price_diff = profit * point / (volume * contract_size)
                symbol = exit_config.get('symbol', '')
                volume = exit_config.get('volume', 0.01)
                
                # Get symbol info for calculations
                try:
                    symbol_info = mt5.symbol_info(symbol)
                    if symbol_info:
                        point = symbol_info.point
                        contract_size = symbol_info.trade_contract_size
                        
                        if contract_size > 0 and volume > 0:
                            # Calculate price difference needed for locked profit
                            # price_diff = locked_profit * point / (volume * contract_size)
                            price_diff = (locked_profit * point) / (volume * contract_size)
                            
                            if entry_type == 'BUY':
                                # For BUY: TP = entry + price_diff to maintain locked profit
                                new_tp = entry_price + price_diff
                            else:  # SELL
                                # For SELL: TP = entry - price_diff to maintain locked profit
                                new_tp = entry_price - price_diff
                            
                            current_tp = exit_config.get('current_tp', 0.0)
                            # Only update if TP needs to move in favorable direction (up for BUY, down for SELL)
                            if entry_type == 'BUY' and (current_tp == 0 or new_tp > current_tp):
                                updates['new_tp'] = new_tp
                                exit_config['current_tp'] = new_tp
                            elif entry_type == 'SELL' and (current_tp == 0 or new_tp < current_tp):
                                updates['new_tp'] = new_tp
                                exit_config['current_tp'] = new_tp
                except Exception as e:
                    logger.error(f"Error calculating profit lock TP for {symbol}: {e}", exc_info=True)
        
        return updates
    
    def unregister_position(self, ticket: int):
        """Unregister a position when it's closed"""
        if ticket in self.active_exits:
            del self.active_exits[ticket]


class IndicatorRunnerThread(QThread):
    """Thread for running Support/Resistance indicator"""
    
    signal_generated = pyqtSignal(str, float, float, float)  # signal, quantity, sl, tp
    status_update = pyqtSignal(str)
    indicator_values_updated = pyqtSignal(dict)  # indicator values dictionary
    
    def __init__(self, config: Dict):
        super().__init__()
        self.config = config
        self.running = False
        self.mt5_connected = False
    
    def run(self):
        """Run indicator in loop"""
        self.running = True
        
        # Connect to MT5
        if not mt5.initialize():
            error = mt5.last_error()
            self.status_update.emit(f"MT5 initialization failed: {error}")
            return
        
        if self.config.get('mt5_login'):
            if not mt5.login(
                login=self.config['mt5_login'],
                password=self.config['mt5_password'],
                server=self.config['mt5_server']
            ):
                error = mt5.last_error()
                self.status_update.emit(f"MT5 login failed: {error}")
                mt5.shutdown()
                return
        
        self.mt5_connected = True
        self.status_update.emit("Connected to MT5")
        
        # Get symbols to monitor (support multiple symbols)
        symbols = self.config.get('symbols', [])
        if not symbols:
            # Fallback to single symbol for backward compatibility
            symbols = [self.config.get('symbol', 'EURUSD')]
        
        timeframe = self.config['timeframe']
        check_interval = self.config.get('check_interval', 60)
        
        # Get readable timeframe name for error messages
        timeframe_names = {
            mt5.TIMEFRAME_M1: "M1",
            mt5.TIMEFRAME_M5: "M5",
            mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_M30: "M30",
            mt5.TIMEFRAME_H1: "H1",
            mt5.TIMEFRAME_H4: "H4",
            mt5.TIMEFRAME_D1: "D1",
        }
        timeframe_name = timeframe_names.get(timeframe, f"TF{timeframe}")
        
        # Use symbol mapper to find the correct symbol
        symbol_mapper = SymbolMapper()
        actual_symbol = symbol_mapper.find_symbol(symbol)
        
        if actual_symbol is None:
            # Try to suggest similar symbols
            similar = symbol_mapper.get_similar_symbols(symbol, limit=5)
            if similar:
                similar_str = ", ".join(similar[:5])
                self.status_update.emit(f"Symbol {symbol} not found. Similar symbols: {similar_str}")
            else:
                self.status_update.emit(f"Symbol {symbol} not found in MT5. Please check the symbol name.")
            mt5.shutdown()
            return
        
        # Use the actual symbol found by mapper
        symbol = actual_symbol
        symbol_info = mt5.symbol_info(symbol)
        
        if symbol_info is None:
            self.status_update.emit(f"Symbol {symbol} not found in MT5")
            mt5.shutdown()
            return
        
        # Add to Market Watch
        if not mt5.symbol_select(symbol, True):
            self.status_update.emit(f"Warning: Could not add {symbol} to Market Watch, but will try to use it")
        else:
            self.status_update.emit(f"Added {symbol} to Market Watch")
        
        # If the requested symbol was different, log the mapping
        if actual_symbol.upper() != self.config['symbol'].upper():
            self.status_update.emit(f"Symbol mapped: {self.config['symbol']} -> {actual_symbol}")
        
        self.status_update.emit(f"Symbol {symbol} verified and ready")
        
        last_signal = None
        last_breakout_level = None
        first_check = True
        
        # Check indicator type
        indicator_type = self.config.get('indicator_type', 'Support/Resistance')
        
        # Initialize OHLC calculator if needed
        ohlc_calculator = None
        if indicator_type == 'Previous Session OHLC':
            session_type = self.config.get('ohlc_session_type', 'daily')
            ohlc_calculator = PreviousSessionOHLCCalculator(session_type)
            if ohlc_calculator.calculate_ohlc(symbol):
                ohlc_values = ohlc_calculator.get_ohlc()
                self.status_update.emit(f"Previous Session OHLC: O={ohlc_values['open']:.5f}, "
                                       f"H={ohlc_values['high']:.5f}, L={ohlc_values['low']:.5f}, "
                                       f"C={ohlc_values['close']:.5f}")
            else:
                self.status_update.emit(f"Failed to calculate OHLC for {symbol}")
                mt5.shutdown()
                return
        
        # Initialize Support/Resistance calculator with Pivot Points (if SR indicator)
        pivot_period = self.config.get('pivot_period', 'daily')  # 'daily', 'weekly', 'monthly'
        min_touches = self.config.get('sr_min_touches', 2)
        strength_threshold = self.config.get('sr_strength', 0.5)
        pivot_calculator = PivotPointsCalculator(pivot_period, min_touches, strength_threshold)
        
        # Initialize role reversal tracker
        enable_role_reversal = self.config.get('enable_role_reversal', True)
        role_reversal_tracker = RoleReversalTracker() if enable_role_reversal else None
        
        # Initialize reversal detector
        reversal_detector = ReversalDetector(reaction_bars=3)
        
        # Initialize confluence calculator
        confluence_tolerance = self.config.get('confluence_tolerance', 0.001)
        min_confluence_methods = self.config.get('min_confluence_methods', 2)
        confluence_calculator = ConfluenceCalculator(confluence_tolerance, min_confluence_methods)
        
        try:
            while self.running:
                # Check MT5 connection
                if not mt5.terminal_info():
                    self.status_update.emit(f"MT5 disconnected. Attempting to reconnect...")
                    if mt5.initialize():
                        self.status_update.emit(f"Reconnected to MT5")
                        for sym in verified_symbols:
                            symbol_info = mt5.symbol_info(sym)
                            if symbol_info:
                                mt5.symbol_select(sym, True)
                    else:
                        self.status_update.emit(f"Failed to reconnect to MT5. Check MT5 terminal.")
                        self.msleep(check_interval * 1000)
                        continue
                
                # Process each symbol
                for symbol in verified_symbols:
                    if not self.running:
                        break
                    
                    # Get rates - fetch more historical data for better SR calculation
                # Calculate how many bars we need based on timeframe
                from datetime import datetime, timedelta
                
                # Determine days to fetch based on timeframe
                timeframe_days = {
                    mt5.TIMEFRAME_M1: 30,   # 30 days for M1 = ~43,200 bars
                    mt5.TIMEFRAME_M5: 60,   # 60 days for M5 = ~17,280 bars
                    mt5.TIMEFRAME_M15: 90,  # 90 days for M15 = ~8,640 bars
                    mt5.TIMEFRAME_M30: 120, # 120 days for M30 = ~5,760 bars
                    mt5.TIMEFRAME_H1: 180,  # 180 days for H1 = ~4,320 bars
                    mt5.TIMEFRAME_H4: 365,  # 365 days for H4 = ~2,190 bars
                    mt5.TIMEFRAME_D1: 730,  # 730 days for D1 = ~730 bars
                }
                days_to_fetch = timeframe_days.get(timeframe, 90)
                bars_needed = max(500, 200)  # At least 500 bars for pivot calculation
                
                self.status_update.emit(f"Fetching historical data for {symbol} ({bars_needed} bars)...")
                
                # Try to get rates from current position first
                rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars_needed)
                
                if rates is None or len(rates) == 0 or len(rates) < bars_needed:
                    # Fallback: fetch from date range
                    start_date = datetime.now() - timedelta(days=days_to_fetch)
                    rates = mt5.copy_rates_from(symbol, timeframe, start_date, bars_needed)
                    
                    if rates is None or len(rates) == 0:
                        # Try symbol mapper to find correct symbol
                        symbol_mapper = SymbolMapper()
                        mapped_symbol = symbol_mapper.find_symbol(symbol)
                        
                        if mapped_symbol and mapped_symbol != symbol:
                            self.status_update.emit(f"Trying mapped symbol: {mapped_symbol}")
                            symbol = mapped_symbol
                            mt5.symbol_select(symbol, True)
                            # Retry getting rates with mapped symbol
                            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars_needed)
                            if rates is not None and len(rates) > 0:
                                continue  # Success, continue with the loop
                        
                        symbol_info = mt5.symbol_info(symbol)
                        if symbol_info is None:
                            # Get similar symbols for suggestion
                            similar = symbol_mapper.get_similar_symbols(symbol, limit=5)
                            if similar:
                                similar_str = ", ".join(similar)
                                self.status_update.emit(f"Symbol {symbol} not found. Try: {similar_str}")
                            else:
                                self.status_update.emit(f"Symbol {symbol} not found. Please check symbol name.")
                        else:
                            self.status_update.emit(f"No data for {symbol} on {timeframe_name}. Symbol exists but no historical data available.")
                        self.msleep(check_interval * 1000)
                        continue
                
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                
                if len(df) < 50:
                    self.status_update.emit(f"Insufficient data for {symbol} (got {len(df)} bars, need at least 50)")
                    self.msleep(check_interval * 1000)
                    continue
                
                # Get current price first (needed for role reversal detection)
                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    current_price = float(df['close'].iloc[-1])
                else:
                    # Use last price if available, otherwise use bid/ask average
                    if tick.last > 0:
                        current_price = tick.last
                    elif tick.bid > 0 and tick.ask > 0:
                        current_price = (tick.bid + tick.ask) / 2.0
                    elif tick.bid > 0:
                        current_price = tick.bid
                    elif tick.ask > 0:
                        current_price = tick.ask
                    else:
                        current_price = float(df['close'].iloc[-1])
                
                # Validate current price
                if current_price <= 0:
                    self.status_update.emit(f"Warning: Invalid current price ({current_price}). Using last close price.")
                    current_price = float(df['close'].iloc[-1])
                    if current_price <= 0:
                        self.status_update.emit(f"Error: Cannot get valid price for {symbol}")
                        self.msleep(check_interval * 1000)
                        continue
                
                previous_close = float(df['close'].iloc[-2]) if len(df) > 1 else current_price
                
                # Calculate Support/Resistance levels using Pivot Points
                self.status_update.emit(f"Calculating Pivot Point levels from {len(df)} historical bars...")
                try:
                    sr_data = pivot_calculator.calculate(df)
                    support_levels = sr_data['support_levels']
                    resistance_levels = sr_data['resistance_levels']
                    
                    # Mark levels with type for role reversal detection
                    for level in support_levels:
                        level['type'] = 'support'
                    for level in resistance_levels:
                        level['type'] = 'resistance'
                    
                    # Detect reactions and update touches
                    for level in support_levels + resistance_levels:
                        reactions = reversal_detector.count_reactions(df, level)
                        level['touches'] = reactions
                        # Boost strength based on reactions
                        if reactions > 0:
                            level['strength'] = min(level.get('strength', 0.5) + (reactions * 0.1), 1.0)
                    
                    # Check for role reversals
                    if role_reversal_tracker:
                        reversed_supports = []
                        reversed_resistances = []
                        
                        for level in resistance_levels[:]:  # Copy list to iterate
                            reversal = role_reversal_tracker.check_role_reversal(level, current_price, previous_close)
                            if reversal:
                                reversed_level = role_reversal_tracker.apply_reversal(level, reversal)
                                reversed_supports.append(reversed_level)
                                resistance_levels.remove(level)
                                self.status_update.emit(f"Resistance {level['price']:.5f} reversed to Support")
                        
                        for level in support_levels[:]:  # Copy list to iterate
                            reversal = role_reversal_tracker.check_role_reversal(level, current_price, previous_close)
                            if reversal:
                                reversed_level = role_reversal_tracker.apply_reversal(level, reversal)
                                reversed_resistances.append(reversed_level)
                                support_levels.remove(level)
                                self.status_update.emit(f"Support {level['price']:.5f} reversed to Resistance")
                        
                        # Add reversed levels to appropriate lists
                        support_levels.extend(reversed_supports)
                        resistance_levels.extend(reversed_resistances)
                    
                    # Calculate confluence
                    all_levels = support_levels + resistance_levels
                    confluent_levels = confluence_calculator.calculate_confluence(all_levels)
                    
                    # Separate back into supports and resistances
                    support_levels = [l for l in confluent_levels if l.get('type') == 'support' or (l.get('price', 0) < current_price and 'support' in str(l.get('type', '')))]
                    resistance_levels = [l for l in confluent_levels if l.get('type') == 'resistance' or (l.get('price', 0) > current_price and 'resistance' in str(l.get('type', '')))]
                    
                    # Ensure type is set correctly
                    for level in support_levels:
                        if 'type' not in level or level.get('type') != 'support':
                            level['type'] = 'support'
                    for level in resistance_levels:
                        if 'type' not in level or level.get('type') != 'resistance':
                            level['type'] = 'resistance'
                    
                    self.status_update.emit(f"Found {len(support_levels)} support levels and {len(resistance_levels)} resistance levels")
                except Exception as e:
                    logger.error(f"Error calculating SR levels: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    self.status_update.emit(f"Error calculating SR levels: {str(e)}")
                    self.msleep(check_interval * 1000)
                    continue
                
                # Process ALL support levels (calculate distance from current price)
                all_supports = []
                for support in support_levels:
                    distance = abs(current_price - support['price'])
                    distance_pct = (distance / current_price) * 100 if current_price > 0 else 0
                    support_data = {
                        'price': support['price'],
                        'strength': support.get('strength', 0.5),
                        'touches': support.get('touches', 0),
                        'distance': distance,
                        'distance_pct': distance_pct,
                        'is_below': support['price'] < current_price,
                        'methods': support.get('methods', ['pivot']),
                        'confluence_score': support.get('confluence_score', 0.0),
                        'timeframe': support.get('timeframe', pivot_period),
                        'reversed': support.get('reversed', False)
                    }
                    all_supports.append(support_data)
                
                # Process ALL resistance levels (calculate distance from current price)
                all_resistances = []
                for resistance in resistance_levels:
                    distance = abs(resistance['price'] - current_price)
                    distance_pct = (distance / current_price) * 100 if current_price > 0 else 0
                    resistance_data = {
                        'price': resistance['price'],
                        'strength': resistance.get('strength', 0.5),
                        'touches': resistance.get('touches', 0),
                        'distance': distance,
                        'distance_pct': distance_pct,
                        'is_above': resistance['price'] > current_price,
                        'methods': resistance.get('methods', ['pivot']),
                        'confluence_score': resistance.get('confluence_score', 0.0),
                        'timeframe': resistance.get('timeframe', pivot_period),
                        'reversed': resistance.get('reversed', False)
                    }
                    all_resistances.append(resistance_data)
                
                # Sort supports by price (ascending - lowest first)
                all_supports.sort(key=lambda x: x['price'])
                
                # Sort resistances by price (descending - highest first)
                all_resistances.sort(key=lambda x: x['price'], reverse=True)
                
                # Find nearest support and resistance for backward compatibility
                nearest_support = None
                nearest_resistance = None
                
                # Find nearest support (below current price)
                supports_below = [s for s in all_supports if s['is_below']]
                if supports_below:
                    nearest_support = max(supports_below, key=lambda x: x['price'])  # Highest support below price
                
                # Find nearest resistance (above current price)
                resistances_above = [r for r in all_resistances if r['is_above']]
                if resistances_above:
                    nearest_resistance = min(resistances_above, key=lambda x: x['price'])  # Lowest resistance above price
                
                # Prepare indicator values for display
                indicator_values = {
                    'Current Price': round(current_price, 5)
                }
                
                # Nearest support (for backward compatibility)
                if nearest_support:
                    indicator_values['Nearest Support'] = round(nearest_support['price'], 5)
                    indicator_values['Support Strength'] = round(nearest_support['strength'], 2)
                    indicator_values['Support Touches'] = nearest_support['touches']
                else:
                    indicator_values['Nearest Support'] = "--"
                    indicator_values['Support Strength'] = "--"
                    indicator_values['Support Touches'] = "--"
                
                # Nearest resistance (for backward compatibility)
                if nearest_resistance:
                    indicator_values['Nearest Resistance'] = round(nearest_resistance['price'], 5)
                    indicator_values['Resistance Strength'] = round(nearest_resistance['strength'], 2)
                    indicator_values['Resistance Touches'] = nearest_resistance['touches']
                else:
                    indicator_values['Nearest Resistance'] = "--"
                    indicator_values['Resistance Strength'] = "--"
                    indicator_values['Resistance Touches'] = "--"
                
                # Add ALL levels (not just nearby)
                indicator_values['All Supports'] = all_supports
                indicator_values['All Resistances'] = all_resistances
                
                # Add all levels count
                indicator_values['Total Support Levels'] = len(support_levels)
                indicator_values['Total Resistance Levels'] = len(resistance_levels)
                
                # Add OHLC values if OHLC indicator is active
                if indicator_type == 'Previous Session OHLC' and ohlc_calculator:
                    ohlc_vals = ohlc_calculator.get_ohlc()
                    indicator_values['OHLC Session'] = ohlc_vals.get('session_name', '--')
                    indicator_values['Previous Open'] = ohlc_vals.get('open', 0)
                    indicator_values['Previous High'] = ohlc_vals.get('high', 0)
                    indicator_values['Previous Low'] = ohlc_vals.get('low', 0)
                    indicator_values['Previous Close'] = ohlc_vals.get('close', 0)
                
                # Debug logging
                logger.debug(f"Indicator values: price={current_price:.5f}, supports={len(support_levels)}, resistances={len(resistance_levels)}")
                
                # Emit indicator values
                self.indicator_values_updated.emit(indicator_values)
                
                # Status update for monitoring
                if self.config.get('monitoring_only', False):
                    if indicator_type == 'Previous Session OHLC' and ohlc_calculator:
                        ohlc_vals = ohlc_calculator.get_ohlc()
                        status_msg = f"Monitoring {symbol} - Price: {current_price:.5f}, OHLC: O={ohlc_vals.get('open', 0):.5f}, H={ohlc_vals.get('high', 0):.5f}, L={ohlc_vals.get('low', 0):.5f}, C={ohlc_vals.get('close', 0):.5f}"
                    else:
                        status_msg = f"Monitoring {symbol} - Price: {current_price:.5f}, Supports: {len(support_levels)}, Resistances: {len(resistance_levels)}"
                    self.status_update.emit(status_msg)
                
                # Check for OHLC breakouts (only if trading is enabled and OHLC indicator)
                if not self.config.get('monitoring_only', False) and indicator_type == 'Previous Session OHLC' and ohlc_calculator:
                    ohlc_values = ohlc_calculator.get_ohlc()
                    breakout_conf = self.config.get('ohlc_breakout_confirmation', 0.001)
                    signal = None
                    
                    # Check BUY breakouts
                    if self.config.get('ohlc_buy_high', False) and ohlc_values.get('high'):
                        breakout_price = ohlc_values['high'] * (1 + breakout_conf)
                        if current_price >= breakout_price:
                            signal = "BUY"
                            last_breakout_level = ohlc_values['high']
                            self.status_update.emit(f"BUY signal: Price broke above Previous High {ohlc_values['high']:.5f}")
                    
                    if not signal and self.config.get('ohlc_buy_close', False) and ohlc_values.get('close'):
                        breakout_price = ohlc_values['close'] * (1 + breakout_conf)
                        if current_price >= breakout_price:
                            signal = "BUY"
                            last_breakout_level = ohlc_values['close']
                            self.status_update.emit(f"BUY signal: Price broke above Previous Close {ohlc_values['close']:.5f}")
                    
                    if not signal and self.config.get('ohlc_buy_open', False) and ohlc_values.get('open'):
                        breakout_price = ohlc_values['open'] * (1 + breakout_conf)
                        if current_price >= breakout_price:
                            signal = "BUY"
                            last_breakout_level = ohlc_values['open']
                            self.status_update.emit(f"BUY signal: Price broke above Previous Open {ohlc_values['open']:.5f}")
                    
                    # Check SELL breakouts
                    if not signal and self.config.get('ohlc_sell_low', False) and ohlc_values.get('low'):
                        breakout_price = ohlc_values['low'] * (1 - breakout_conf)
                        if current_price <= breakout_price:
                            signal = "SELL"
                            last_breakout_level = ohlc_values['low']
                            self.status_update.emit(f"SELL signal: Price broke below Previous Low {ohlc_values['low']:.5f}")
                    
                    if not signal and self.config.get('ohlc_sell_close', False) and ohlc_values.get('close'):
                        breakout_price = ohlc_values['close'] * (1 - breakout_conf)
                        if current_price <= breakout_price:
                            signal = "SELL"
                            last_breakout_level = ohlc_values['close']
                            self.status_update.emit(f"SELL signal: Price broke below Previous Close {ohlc_values['close']:.5f}")
                    
                    if not signal and self.config.get('ohlc_sell_open', False) and ohlc_values.get('open'):
                        breakout_price = ohlc_values['open'] * (1 - breakout_conf)
                        if current_price <= breakout_price:
                            signal = "SELL"
                            last_breakout_level = ohlc_values['open']
                            self.status_update.emit(f"SELL signal: Price broke below Previous Open {ohlc_values['open']:.5f}")
                    
                    # Generate signal if breakout detected
                    if signal and signal != last_signal:
                        # Calculate SL/TP for OHLC
                        sl, tp = self._calculate_ohlc_sl_tp(signal, ohlc_values, current_price)
                        quantity = self.config.get('quantity', 0.01)
                        self.signal_generated.emit(signal, quantity, sl, tp)
                        last_signal = signal
                
                # Monitor positions for trailing SL and profit lock (if trading enabled)
                if not self.config.get('monitoring_only', False):
                    exit_manager = self.config.get('exit_manager')
                    if exit_manager:
                        try:
                            # Get open positions for this symbol
                            positions = mt5.positions_get(symbol=symbol)
                            if positions:
                                for pos in positions:
                                    ticket = pos.ticket
                                    pos_type_str = 'BUY' if pos.type == 0 else 'SELL'
                                    pos_profit = pos.profit
                                    
                                    # Register position if not already registered
                                    if ticket not in exit_manager.active_exits:
                                        # Register new position with trailing SL/profit lock settings
                                        entry_data = {
                                            'entry_price': pos.price_open,
                                            'entry_time': datetime.fromtimestamp(pos.time),
                                            'entry_type': pos_type_str,
                                            'symbol': symbol,
                                            'volume': pos.volume,
                                            'enable_trailing_sl': self.config.get('enable_trailing_sl', False),
                                            'trailing_sl_gap': self.config.get('trailing_sl_gap', 0.001),
                                            'enable_profit_lock': self.config.get('enable_profit_lock', False),
                                            'profit_lock_trigger': self.config.get('profit_lock_trigger', 100.0),
                                            'profit_lock_value': self.config.get('profit_lock_value', 50.0),
                                            'profit_trail_step': self.config.get('profit_trail_step', 100.0),
                                            'profit_trail_amount': self.config.get('profit_trail_amount', 50.0),
                                            'exit_conditions': {},
                                        }
                                        exit_manager.register_position(ticket, entry_data)
                                        logger.info(f"Registered position {ticket} for trailing SL/profit lock monitoring")
                                    
                                    # Update trailing SL and profit lock
                                    updates = exit_manager.update_trailing_and_profit_lock(
                                        ticket, current_price, pos_profit, mt5
                                    )
                                    
                                    # Check if position should be closed
                                    if updates.get('should_close'):
                                        logger.info(f"Position {ticket} should be closed: {updates.get('reason')}")
                                        # The position will be closed by MT5's SL/TP mechanism
                                        continue
                                    
                                    # Update position SL/TP if needed
                                    new_sl = updates.get('new_sl')
                                    new_tp = updates.get('new_tp')
                                    current_sl = pos.sl
                                    current_tp = pos.tp
                                    
                                    # Modify position if SL or TP needs updating
                                    if new_sl is not None and abs(new_sl - current_sl) > (new_sl * 0.0001):
                                        # Update SL
                                        sl_to_use = new_sl
                                        tp_to_use = current_tp if current_tp > 0 else new_tp if new_tp else 0.0
                                        if mt5.order_modify(ticket, sl_to_use, tp_to_use):
                                            logger.info(f"Updated trailing SL for position {ticket}: {current_sl:.5f} -> {new_sl:.5f}")
                                            self.status_update.emit(f"Updated trailing SL for {ticket}: {new_sl:.5f}")
                                        else:
                                            error = mt5.last_error()
                                            logger.warning(f"Failed to update SL for position {ticket}: {error}")
                                    
                                    if new_tp is not None and new_tp > 0:
                                        # Update TP
                                        sl_to_use = current_sl if current_sl > 0 else new_sl if new_sl else 0.0
                                        tp_to_use = new_tp
                                        if abs(tp_to_use - current_tp) > (tp_to_use * 0.0001):
                                            if mt5.order_modify(ticket, sl_to_use, tp_to_use):
                                                logger.info(f"Updated profit lock TP for position {ticket}: {current_tp:.5f} -> {new_tp:.5f}")
                                                self.status_update.emit(f"Updated profit lock TP for {ticket}: {new_tp:.5f}")
                                            else:
                                                error = mt5.last_error()
                                                logger.warning(f"Failed to update TP for position {ticket}: {error}")
                        except Exception as e:
                            logger.error(f"Error monitoring positions: {e}", exc_info=True)
                
                # Check for breakouts (only if trading is enabled)
                if not self.config.get('monitoring_only', False):
                    signal = None
                    target_resistance = None
                    target_support = None
                    
                    # Check signal queue first
                    signal_queue = self.config.get('signal_queue')
                    queue_executed = False
                    
                    if signal_queue:
                        pending_conditions = signal_queue.get_pending_conditions()
                        for condition in pending_conditions:
                            if condition['symbol'] != symbol:
                                continue  # Check only conditions for current symbol
                            
                            if not condition.get('enabled', True):
                                continue  # Skip disabled conditions
                            
                            # Check if breakout is met for this condition
                            condition_level_price = condition.get('level_price')
                            condition_entry_type = condition['entry_type']
                            breakout_conf = condition['breakout_confirmation']
                            
                            breakout_met = False
                            target_level = None
                            
                            if condition_entry_type == 'BUY':
                                if condition_level_price is None:
                                    # "Any" - use nearest resistance
                                    target_level = nearest_resistance
                                else:
                                    # Find specific resistance level
                                    for res in all_resistances:
                                        if abs(res['price'] - condition_level_price) < (condition_level_price * 0.001):
                                            target_level = res
                                            break
                                
                                if target_level:
                                    breakout_price = target_level['price'] * (1 + breakout_conf)
                                    if current_price >= breakout_price:
                                        breakout_met = True
                                        signal = "BUY"
                                        target_resistance = target_level
                            
                            else:  # SELL
                                if condition_level_price is None:
                                    # "Any" - use nearest support
                                    target_level = nearest_support
                                else:
                                    # Find specific support level
                                    for sup in all_supports:
                                        if abs(sup['price'] - condition_level_price) < (condition_level_price * 0.001):
                                            target_level = sup
                                            break
                                
                                if target_level:
                                    breakdown_price = target_level['price'] * (1 - breakout_conf)
                                    if current_price <= breakdown_price:
                                        breakout_met = True
                                        signal = "SELL"
                                        target_support = target_level
                            
                            if breakout_met:
                                # Execute this condition
                                # Use condition's SL/TP method if specified
                                condition_config = condition.copy()
                                condition_config['sl_tp_method'] = condition.get('sl_tp_method', self.config.get('sl_tp_method', 'Support/Resistance Based'))
                                condition_config['sl_tp_params'] = condition.get('sl_tp_params', self.config.get('sl_tp_params', {}))
                                
                                # Temporarily update config for SL/TP calculation
                                original_method = self.config.get('sl_tp_method')
                                original_params = self.config.get('sl_tp_params')
                                self.config['sl_tp_method'] = condition_config['sl_tp_method']
                                self.config['sl_tp_params'] = condition_config['sl_tp_params']
                                
                                sl, tp = self._calculate_sl_tp(df, signal, nearest_support, nearest_resistance, current_price)
                                quantity = condition.get('quantity', 0.01)
                                
                                # Restore original config
                                self.config['sl_tp_method'] = original_method
                                self.config['sl_tp_params'] = original_params
                                
                                self.signal_generated.emit(signal, quantity, sl, tp)
                                signal_queue.mark_executed(condition['id'])
                                self.status_update.emit(f"Condition {condition['id'][:8]} executed: {signal} at {target_level['price']:.5f}")
                                queue_executed = True
                                break  # Execute one condition per check
                    
                    # Also check direct config (backward compatibility) - only if queue didn't execute
                    if not queue_executed and (not signal_queue or len(signal_queue.get_pending_conditions()) == 0):
                        breakout_confirmation = self.config.get('sr_breakout_confirmation', 0.001)
                        signal = None
                        target_resistance = None
                        target_support = None
                        
                        selected_resistance_price = self.config.get('selected_resistance_price')
                        selected_support_price = self.config.get('selected_support_price')
                        
                        if self.config.get('sr_resistance_breakout_buy', True):
                            if selected_resistance_price is not None:
                                for res in all_resistances:
                                    if abs(res['price'] - selected_resistance_price) < (selected_resistance_price * 0.001):
                                        target_resistance = res
                                        break
                            else:
                                target_resistance = nearest_resistance
                            
                            if target_resistance:
                                breakout_price = target_resistance['price'] * (1 + breakout_confirmation)
                                if current_price >= breakout_price and last_breakout_level != target_resistance['price']:
                                    signal = "BUY"
                                    last_breakout_level = target_resistance['price']
                                    self.status_update.emit(f"Resistance breakout detected at {target_resistance['price']:.5f}")
                        
                        if self.config.get('sr_support_breakdown_sell', True):
                            if selected_support_price is not None:
                                for sup in all_supports:
                                    if abs(sup['price'] - selected_support_price) < (selected_support_price * 0.001):
                                        target_support = sup
                                        break
                            else:
                                target_support = nearest_support
                            
                            if target_support:
                                breakdown_price = target_support['price'] * (1 - breakout_confirmation)
                                if current_price <= breakdown_price and last_breakout_level != target_support['price']:
                                    signal = "SELL"
                                    last_breakout_level = target_support['price']
                                    self.status_update.emit(f"Support breakdown detected at {target_support['price']:.5f}")
                    
                    # On first check, just log (but values are already emitted above)
                    if first_check:
                        if signal:
                            self.status_update.emit(f"Current condition: {signal} signal detected. Waiting for signal change to execute...")
                        else:
                            self.status_update.emit(f"Monitoring {symbol} for Support/Resistance breakouts...")
                        first_check = False
                        last_signal = signal
                        # Don't continue here - let it sleep and continue to next iteration
                    
                    # Only send signal if it's different from the last signal
                    # Track signals per level to prevent duplicates
                    signal_level_key = None
                    if signal == "BUY" and target_resistance:
                        signal_level_key = ('BUY', target_resistance['price'])
                    elif signal == "SELL" and target_support:
                        signal_level_key = ('SELL', target_support['price'])
                    
                    if signal and signal != last_signal:
                        # Check if we've already sent a signal for this level
                        if signal_level_key:
                            last_signal_for_level = self.config.get('_last_signal_per_level', {}).get(signal_level_key)
                            if last_signal_for_level == signal:
                                # Already sent this signal for this level, skip
                                self.status_update.emit(f"Signal already sent for {signal} at level {signal_level_key[1]:.5f}")
                            else:
                                # New signal for this level
                                # Calculate SL/TP
                                sl, tp = self._calculate_sl_tp(df, signal, nearest_support, nearest_resistance, current_price)
                                quantity = self.config.get('quantity', 0.01)
                                
                                self.signal_generated.emit(signal, quantity, sl, tp)
                                last_signal = signal
                                
                                # Track this signal
                                if '_last_signal_per_level' not in self.config:
                                    self.config['_last_signal_per_level'] = {}
                                self.config['_last_signal_per_level'][signal_level_key] = signal
                                
                                self.status_update.emit(f"Signal change detected: {signal} for {symbol} at level {signal_level_key[1]:.5f}")
                        else:
                            # Fallback: no level key (shouldn't happen, but handle gracefully)
                            sl, tp = self._calculate_sl_tp(df, signal, nearest_support, nearest_resistance, current_price)
                            quantity = self.config.get('quantity', 0.01)
                            self.signal_generated.emit(signal, quantity, sl, tp)
                            last_signal = signal
                            self.status_update.emit(f"Signal change detected: {signal} for {symbol}")
                    elif signal == last_signal and signal:
                        self.status_update.emit(f"Breakout condition still met: {signal} (no new signal - waiting for change)")
                    elif not signal:
                        if last_signal:
                            self.status_update.emit(f"Breakout condition no longer met. Last signal was: {last_signal}")
                            last_signal = None
                            last_breakout_level = None
                else:
                    # Monitoring-only mode
                    if first_check:
                        self.status_update.emit(f"Monitoring {symbol} - Support/Resistance levels updating...")
                        first_check = False
                
                self.msleep(check_interval * 1000)
                
        except KeyboardInterrupt:
            self.status_update.emit("Indicator stopped by user")
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.status_update.emit(error_msg)
            logger.error(f"Indicator runner error: {e}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            pass  # Don't shutdown MT5 - main app manages it
    
    def _calculate_sl_tp(self, df: pd.DataFrame, signal: str, 
                         nearest_support: Optional[Dict], nearest_resistance: Optional[Dict],
                         current_price: float) -> Tuple[float, float]:
        """Calculate Stop Loss and Take Profit based on selected method"""
        method = self.config.get('sl_tp_method', 'Support/Resistance Based')
        params = self.config.get('sl_tp_params', {})
        
        if method == "Support/Resistance Based":
            return self._calculate_sr_based_sl_tp(signal, nearest_support, nearest_resistance, current_price)
        elif method == "Fixed Percentage":
            return self._calculate_fixed_pct_sl_tp(signal, current_price, params)
        elif method == "ATR Based":
            return self._calculate_atr_based_sl_tp(df, signal, current_price, params)
        elif method == "Risk:Reward Ratio":
            return self._calculate_rr_ratio_sl_tp(signal, current_price, params)
        elif method == "Custom":
            return self._calculate_custom_sl_tp(signal, current_price, params)
        else:
            # Fallback to SR based
            return self._calculate_sr_based_sl_tp(signal, nearest_support, nearest_resistance, current_price)
    
    def _calculate_sr_based_sl_tp(self, signal: str, nearest_support: Optional[Dict], 
                                   nearest_resistance: Optional[Dict], current_price: float) -> Tuple[float, float]:
        """Calculate SL/TP based on Support/Resistance levels"""
        risk_reward = self.config.get('risk_reward_ratio', 2.0)
        
        if signal == "BUY":
            if nearest_support:
                sl = nearest_support['price'] * 0.999
            else:
                sl = current_price * 0.995
            
            risk = current_price - sl
            tp = current_price + (risk * risk_reward)
            
            if nearest_resistance and tp > nearest_resistance['price']:
                tp = nearest_resistance['price'] * 0.999
        else:  # SELL
            if nearest_resistance:
                sl = nearest_resistance['price'] * 1.001
            else:
                sl = current_price * 1.005
            
            risk = sl - current_price
            tp = current_price - (risk * risk_reward)
            
            if nearest_support and tp < nearest_support['price']:
                tp = nearest_support['price'] * 1.001
        
        return sl, tp
    
    def _calculate_fixed_pct_sl_tp(self, signal: str, current_price: float, params: Dict) -> Tuple[float, float]:
        """Calculate SL/TP using fixed percentages"""
        sl_pct = params.get('sl_fixed_pct', 1.0) / 100.0
        tp_pct = params.get('tp_fixed_pct', 2.0) / 100.0
        
        if signal == "BUY":
            sl = current_price * (1 - sl_pct)
            tp = current_price * (1 + tp_pct)
        else:  # SELL
            sl = current_price * (1 + sl_pct)
            tp = current_price * (1 - tp_pct)
        
        return sl, tp
    
    def _calculate_atr_based_sl_tp(self, df: pd.DataFrame, signal: str, current_price: float, params: Dict) -> Tuple[float, float]:
        """Calculate SL/TP using ATR (Average True Range)"""
        period = params.get('atr_period', 14)
        sl_multiplier = params.get('sl_atr_multiplier', 2.0)
        tp_multiplier = params.get('tp_atr_multiplier', 4.0)
        
        # Calculate ATR
        if len(df) < period + 1:
            # Fallback to fixed percentage if not enough data
            return self._calculate_fixed_pct_sl_tp(signal, current_price, {'sl_fixed_pct': 1.0, 'tp_fixed_pct': 2.0})
        
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # Calculate True Range
        tr_list = []
        for i in range(1, len(df)):
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            tr_list.append(max(tr1, tr2, tr3))
        
        # Calculate ATR as SMA of TR
        atr = np.mean(tr_list[-period:]) if len(tr_list) >= period else tr_list[-1] if tr_list else current_price * 0.01
        
        if signal == "BUY":
            sl = current_price - (atr * sl_multiplier)
            tp = current_price + (atr * tp_multiplier)
        else:  # SELL
            sl = current_price + (atr * sl_multiplier)
            tp = current_price - (atr * tp_multiplier)
        
        return sl, tp
    
    def _calculate_rr_ratio_sl_tp(self, signal: str, current_price: float, params: Dict) -> Tuple[float, float]:
        """Calculate SL/TP using Risk:Reward ratio"""
        rr_ratio = params.get('risk_reward_ratio', 2.0)
        
        # Use a default risk percentage (1%)
        risk_pct = 0.01
        
        if signal == "BUY":
            sl = current_price * (1 - risk_pct)
            risk = current_price - sl
            tp = current_price + (risk * rr_ratio)
        else:  # SELL
            sl = current_price * (1 + risk_pct)
            risk = sl - current_price
            tp = current_price - (risk * rr_ratio)
        
        return sl, tp
    
    def _calculate_custom_sl_tp(self, signal: str, current_price: float, params: Dict) -> Tuple[float, float]:
        """Use custom SL/TP values"""
        sl = params.get('sl_custom', current_price * 0.99)
        tp = params.get('tp_custom', current_price * 1.02)
        
        # Validate: for BUY, SL should be below price, TP above
        # For SELL, SL should be above price, TP below
        if signal == "BUY":
            if sl >= current_price:
                sl = current_price * 0.99
            if tp <= current_price:
                tp = current_price * 1.02
        else:  # SELL
            if sl <= current_price:
                sl = current_price * 1.01
            if tp >= current_price:
                tp = current_price * 0.98
        
        return sl, tp
    
    def _calculate_ohlc_sl_tp(self, signal: str, ohlc_values: Dict, current_price: float) -> Tuple[float, float]:
        """Calculate SL/TP for OHLC-based signals"""
        # Use OHLC levels for SL/TP
        if signal == "BUY":
            # SL below the breakout level (or previous low)
            sl = ohlc_values.get('low', current_price * 0.995) * 0.999  # Slightly below low
            # TP above previous high or based on risk:reward
            risk = current_price - sl
            tp = current_price + (risk * 2.0)  # 1:2 risk:reward
        else:  # SELL
            # SL above the breakout level (or previous high)
            sl = ohlc_values.get('high', current_price * 1.005) * 1.001  # Slightly above high
            # TP below previous low or based on risk:reward
            risk = sl - current_price
            tp = current_price - (risk * 2.0)  # 1:2 risk:reward
        
        return sl, tp
    
    def stop(self):
        """Stop the indicator"""
        self.running = False


class CustomIndicatorPanel(QWidget):
    """Custom Indicator Panel - Support/Resistance Based"""
    
    def __init__(self, mt5_connector, signal_server_url: str = "http://localhost:8080"):
        super().__init__()
        self.mt5 = mt5_connector
        self.signal_server_url = signal_server_url
        self.monitoring_thread: Optional[IndicatorRunnerThread] = None
        self.trading_thread: Optional[IndicatorRunnerThread] = None
        self.indicator_values_labels: Dict[str, QLabel] = {}
        self.symbol_mapper = SymbolMapper(mt5_connector)
        
        # Signal Queue and Exit Manager
        self.signal_queue = SignalQueue()
        self.exit_manager = ExitConditionManager()
        
        # Performance optimization: debounced updates
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._perform_table_update)
        self.pending_values = None
        
        # Queue update timer
        self.queue_update_timer = QTimer()
        self.queue_update_timer.timeout.connect(self.update_queue_table)
        self.queue_update_timer.start(1000)  # Update every second
        
        # Signal deduplication tracking
        self.last_signal_per_level: Dict[Tuple[str, float], str] = {}  # (signal_type, level_price) -> last_signal
        
        # State persistence
        project_root = Path(__file__).parent.parent.parent
        self.state_file = project_root / "config" / "custom_indicator_state.json"
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.setup_ui()
        self.setup_timers()
        # Load saved state after UI is set up
        self.load_state()
    
    def setup_ui(self):
        """Setup the UI with tabbed interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Create tab widget with styling
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #1e1e1e;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #2b2b2b;
                color: #aaa;
                padding: 10px 25px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #3d5afe;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #424242;
            }
        """)
        
        # Create tabs
        self._create_configuration_tab()
        self._create_monitoring_tab()
        self._create_queue_tab()
        
        main_layout.addWidget(self.tab_widget)
    
    def _create_configuration_tab(self):
        """Create Configuration tab with all settings"""
        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        config_layout.setContentsMargins(15, 15, 15, 15)
        config_layout.setSpacing(12)
        
        # Scroll area for configuration
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        config_content = QWidget()
        config_content_layout = QVBoxLayout(config_content)
        config_content_layout.setContentsMargins(10, 10, 10, 10)
        config_content_layout.setSpacing(12)
        
        # Indicator Type Selector
        indicator_type_group = QGroupBox("Indicator Type")
        indicator_type_group.setStyleSheet(self._get_group_style())
        indicator_type_layout = QFormLayout()
        
        self.indicator_type_combo = QComboBox()
        self.indicator_type_combo.addItems([
            "Support/Resistance",
            "Previous Session OHLC"
        ])
        self.indicator_type_combo.setCurrentText("Support/Resistance")
        self.indicator_type_combo.currentTextChanged.connect(self.on_indicator_type_changed)
        indicator_type_layout.addRow("Indicator Type:", self.indicator_type_combo)
        
        indicator_type_group.setLayout(indicator_type_layout)
        config_content_layout.addWidget(indicator_type_group)
        
        # Symbol & Timeframe
        symbol_group = QGroupBox("Symbol & Timeframe")
        symbol_layout = QFormLayout()
        
        # Multi-symbol support
        symbol_input_layout = QHBoxLayout()
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.setPlaceholderText("Select or enter symbol (e.g., EURUSD, XAUUSD)")
        self.symbol_combo.lineEdit().setPlaceholderText("Enter symbol - auto-mapping enabled")
        self.symbol_combo.currentTextChanged.connect(self.on_symbol_changed)
        symbol_input_layout.addWidget(self.symbol_combo)
        
        add_symbol_btn = QPushButton("+")
        add_symbol_btn.setToolTip("Add symbol to monitoring list")
        add_symbol_btn.setMaximumWidth(40)
        add_symbol_btn.clicked.connect(self.add_symbol_to_list)
        symbol_input_layout.addWidget(add_symbol_btn)
        symbol_layout.addRow("Symbol:", symbol_input_layout)
        
        # Active symbols list
        self.active_symbols_list = QComboBox()
        self.active_symbols_list.setEditable(False)
        self.active_symbols_list.setToolTip("Currently monitored symbols - select to remove")
        remove_symbol_btn = QPushButton("Remove Selected")
        remove_symbol_btn.clicked.connect(self.remove_selected_symbol)
        symbols_manage_layout = QHBoxLayout()
        symbols_manage_layout.addWidget(QLabel("Active Symbols:"))
        symbols_manage_layout.addWidget(self.active_symbols_list)
        symbols_manage_layout.addWidget(remove_symbol_btn)
        symbol_layout.addRow("", symbols_manage_layout)
        
        symbol_buttons_layout = QHBoxLayout()
        refresh_symbols_btn = QPushButton("Refresh Symbols")
        refresh_symbols_btn.clicked.connect(self.load_available_symbols)
        symbol_buttons_layout.addWidget(refresh_symbols_btn)
        
        map_symbol_btn = QPushButton("Map Symbol")
        map_symbol_btn.setToolTip("Manually map the entered symbol to an actual MT5 symbol")
        map_symbol_btn.clicked.connect(self.map_symbol)
        symbol_buttons_layout.addWidget(map_symbol_btn)
        
        symbol_buttons_layout.addStretch()
        symbol_layout.addRow("", symbol_buttons_layout)
        
        # Initialize active symbols list
        self.active_symbols = []  # List of symbols being monitored
        
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["M1", "M5", "M15", "M30", "H1", "H4", "D1"])
        self.timeframe_combo.setCurrentText("M15")
        symbol_layout.addRow("Timeframe:", self.timeframe_combo)
        
        symbol_group.setLayout(symbol_layout)
        symbol_group.setStyleSheet(self._get_group_style())
        config_content_layout.addWidget(symbol_group)
        
        # Support/Resistance Settings Container
        self.sr_settings_container = QWidget()
        sr_container_layout = QVBoxLayout(self.sr_settings_container)
        sr_container_layout.setContentsMargins(0, 0, 0, 0)
        sr_container_layout.setSpacing(12)
        
        # Support/Resistance Settings
        sr_group = QGroupBox("Support/Resistance Settings")
        sr_group.setStyleSheet(self._get_group_style())
        sr_layout = QFormLayout()
        
        self.pivot_period_combo = QComboBox()
        self.pivot_period_combo.addItems(["daily", "weekly", "monthly"])
        self.pivot_period_combo.setCurrentText("daily")
        self.pivot_period_combo.setToolTip("Pivot point calculation period (daily, weekly, or monthly)")
        sr_layout.addRow("Pivot Period:", self.pivot_period_combo)
        
        self.sr_min_touches = QSpinBox()
        self.sr_min_touches.setRange(1, 10)
        self.sr_min_touches.setValue(2)
        self.sr_min_touches.setToolTip("Minimum number of touches required to confirm a level")
        sr_layout.addRow("Min Touches:", self.sr_min_touches)
        
        self.sr_strength = QDoubleSpinBox()
        self.sr_strength.setRange(0.1, 1.0)
        self.sr_strength.setSingleStep(0.1)
        self.sr_strength.setValue(0.5)
        self.sr_strength.setToolTip("Minimum strength (0-1) to consider a level significant")
        sr_layout.addRow("Strength Threshold:", self.sr_strength)
        
        self.sr_breakout_confirmation = QDoubleSpinBox()
        self.sr_breakout_confirmation.setRange(0.0001, 0.01)
        self.sr_breakout_confirmation.setSingleStep(0.0001)
        self.sr_breakout_confirmation.setValue(0.001)
        self.sr_breakout_confirmation.setDecimals(4)
        self.sr_breakout_confirmation.setToolTip("Breakout confirmation percentage (0.001 = 0.1%)")
        sr_layout.addRow("Breakout Confirmation:", self.sr_breakout_confirmation)
        
        self.enable_role_reversal = QCheckBox("Enable Role Reversal")
        self.enable_role_reversal.setChecked(True)
        self.enable_role_reversal.setToolTip("Detect when broken resistance becomes support and vice versa")
        sr_layout.addRow("", self.enable_role_reversal)
        
        self.confluence_tolerance = QDoubleSpinBox()
        self.confluence_tolerance.setRange(0.0001, 0.01)
        self.confluence_tolerance.setSingleStep(0.0001)
        self.confluence_tolerance.setValue(0.001)
        self.confluence_tolerance.setDecimals(4)
        self.confluence_tolerance.setToolTip("Price tolerance for confluence detection (0.001 = 0.1%)")
        sr_layout.addRow("Confluence Tolerance:", self.confluence_tolerance)
        
        self.min_confluence_methods = QSpinBox()
        self.min_confluence_methods.setRange(2, 5)
        self.min_confluence_methods.setValue(2)
        self.min_confluence_methods.setToolTip("Minimum methods needed for confluence")
        sr_layout.addRow("Min Confluence Methods:", self.min_confluence_methods)
        
        sr_group.setLayout(sr_layout)
        sr_container_layout.addWidget(sr_group)
        
        # Entry Conditions
        entry_group = QGroupBox("Entry Conditions")
        entry_group.setStyleSheet(self._get_group_style())
        entry_layout = QFormLayout()
        
        # BUY Condition
        buy_layout = QHBoxLayout()
        self.sr_resistance_breakout_buy = QCheckBox("BUY on Resistance Breakout")
        self.sr_resistance_breakout_buy.setChecked(True)
        self.sr_resistance_breakout_buy.setToolTip("Enter BUY when price breaks above resistance")
        self.resistance_dropdown = QComboBox()
        self.resistance_dropdown.setToolTip("Select specific resistance level, or 'Any' for all levels")
        self.resistance_dropdown.setMinimumWidth(200)
        buy_layout.addWidget(self.sr_resistance_breakout_buy)
        buy_layout.addWidget(self.resistance_dropdown)
        buy_layout.addStretch()
        entry_layout.addRow("", buy_layout)
        
        # SELL Condition
        sell_layout = QHBoxLayout()
        self.sr_support_breakdown_sell = QCheckBox("SELL on Support Breakdown")
        self.sr_support_breakdown_sell.setChecked(True)
        self.sr_support_breakdown_sell.setToolTip("Enter SELL when price breaks below support")
        self.support_dropdown = QComboBox()
        self.support_dropdown.setToolTip("Select specific support level, or 'Any' for all levels")
        self.support_dropdown.setMinimumWidth(200)
        sell_layout.addWidget(self.sr_support_breakdown_sell)
        sell_layout.addWidget(self.support_dropdown)
        sell_layout.addStretch()
        entry_layout.addRow("", sell_layout)
        
        entry_group.setLayout(entry_layout)
        sr_container_layout.addWidget(entry_group)
        
        # Add SR container to main layout
        config_content_layout.addWidget(self.sr_settings_container)
        
        # Previous Session OHLC Settings Container
        self.ohlc_settings_container = QWidget()
        ohlc_container_layout = QVBoxLayout(self.ohlc_settings_container)
        ohlc_container_layout.setContentsMargins(0, 0, 0, 0)
        ohlc_container_layout.setSpacing(12)
        
        # Previous Session OHLC Settings
        ohlc_group = QGroupBox("Previous Session OHLC Settings")
        ohlc_group.setStyleSheet(self._get_group_style())
        ohlc_layout = QFormLayout()
        
        # Trading Session Selector
        self.ohlc_session_combo = QComboBox()
        self.ohlc_session_combo.addItems([
            "Daily",
            "Asian Session",
            "European Session",
            "US Session"
        ])
        self.ohlc_session_combo.setCurrentText("Daily")
        self.ohlc_session_combo.setToolTip("Select which trading session to use for OHLC calculation")
        ohlc_layout.addRow("Trading Session:", self.ohlc_session_combo)
        
        # Breakout Confirmation
        self.ohlc_breakout_confirmation = QDoubleSpinBox()
        self.ohlc_breakout_confirmation.setRange(0.0001, 0.01)
        self.ohlc_breakout_confirmation.setSingleStep(0.0001)
        self.ohlc_breakout_confirmation.setValue(0.001)
        self.ohlc_breakout_confirmation.setDecimals(4)
        self.ohlc_breakout_confirmation.setToolTip("Breakout confirmation percentage (0.001 = 0.1%)")
        ohlc_layout.addRow("Breakout Confirmation:", self.ohlc_breakout_confirmation)
        
        # Separator
        separator_ohlc = QFrame()
        separator_ohlc.setFrameShape(QFrame.Shape.HLine)
        separator_ohlc.setFrameShadow(QFrame.Shadow.Sunken)
        separator_ohlc.setStyleSheet("background-color: #555; max-height: 1px; margin: 5px 0;")
        ohlc_layout.addRow("", separator_ohlc)
        
        # OHLC Values Display (Read-only)
        ohlc_values_group = QGroupBox("Previous Session OHLC Values")
        ohlc_values_group.setStyleSheet(self._get_group_style())
        ohlc_values_layout = QFormLayout()
        
        self.ohlc_session_label = QLabel("--")
        self.ohlc_session_label.setStyleSheet("color: #aaa; font-weight: bold;")
        ohlc_values_layout.addRow("Session:", self.ohlc_session_label)
        
        self.ohlc_open_label = QLabel("--")
        self.ohlc_open_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        ohlc_values_layout.addRow("Previous Open:", self.ohlc_open_label)
        
        self.ohlc_high_label = QLabel("--")
        self.ohlc_high_label.setStyleSheet("color: #FF9800; font-weight: bold;")
        ohlc_values_layout.addRow("Previous High:", self.ohlc_high_label)
        
        self.ohlc_low_label = QLabel("--")
        self.ohlc_low_label.setStyleSheet("color: #f44336; font-weight: bold;")
        ohlc_values_layout.addRow("Previous Low:", self.ohlc_low_label)
        
        self.ohlc_close_label = QLabel("--")
        self.ohlc_close_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        ohlc_values_layout.addRow("Previous Close:", self.ohlc_close_label)
        
        ohlc_values_group.setLayout(ohlc_values_layout)
        ohlc_layout.addRow("", ohlc_values_group)
        
        ohlc_group.setLayout(ohlc_layout)
        ohlc_container_layout.addWidget(ohlc_group)
        
        # OHLC Entry Conditions
        ohlc_entry_group = QGroupBox("OHLC Entry Conditions")
        ohlc_entry_group.setStyleSheet(self._get_group_style())
        ohlc_entry_layout = QFormLayout()
        
        # BUY Triggers
        self.ohlc_buy_high = QCheckBox("BUY on break above Previous High")
        self.ohlc_buy_high.setToolTip("Enter BUY when price breaks above previous session High")
        ohlc_entry_layout.addRow("", self.ohlc_buy_high)
        
        self.ohlc_buy_close = QCheckBox("BUY on break above Previous Close")
        self.ohlc_buy_close.setToolTip("Enter BUY when price breaks above previous session Close")
        ohlc_entry_layout.addRow("", self.ohlc_buy_close)
        
        self.ohlc_buy_open = QCheckBox("BUY on break above Previous Open")
        self.ohlc_buy_open.setToolTip("Enter BUY when price breaks above previous session Open")
        ohlc_entry_layout.addRow("", self.ohlc_buy_open)
        
        # Separator
        separator_ohlc_entry = QFrame()
        separator_ohlc_entry.setFrameShape(QFrame.Shape.HLine)
        separator_ohlc_entry.setFrameShadow(QFrame.Shadow.Sunken)
        separator_ohlc_entry.setStyleSheet("background-color: #555; max-height: 1px; margin: 5px 0;")
        ohlc_entry_layout.addRow("", separator_ohlc_entry)
        
        # SELL Triggers
        self.ohlc_sell_low = QCheckBox("SELL on break below Previous Low")
        self.ohlc_sell_low.setToolTip("Enter SELL when price breaks below previous session Low")
        ohlc_entry_layout.addRow("", self.ohlc_sell_low)
        
        self.ohlc_sell_close = QCheckBox("SELL on break below Previous Close")
        self.ohlc_sell_close.setToolTip("Enter SELL when price breaks below previous session Close")
        ohlc_entry_layout.addRow("", self.ohlc_sell_close)
        
        self.ohlc_sell_open = QCheckBox("SELL on break below Previous Open")
        self.ohlc_sell_open.setToolTip("Enter SELL when price breaks below previous session Open")
        ohlc_entry_layout.addRow("", self.ohlc_sell_open)
        
        ohlc_entry_group.setLayout(ohlc_entry_layout)
        ohlc_container_layout.addWidget(ohlc_entry_group)
        
        # Add OHLC container to main layout (initially hidden)
        config_content_layout.addWidget(self.ohlc_settings_container)
        self.ohlc_settings_container.setVisible(False)
        
        # Trading Settings
        trading_group = QGroupBox("Trading Settings")
        trading_group.setStyleSheet(self._get_group_style())
        trading_layout = QFormLayout()
        
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.01, 100.0)
        self.quantity_spin.setSingleStep(0.01)
        self.quantity_spin.setValue(0.01)
        trading_layout.addRow("Lot Size:", self.quantity_spin)
        
        # SL/TP Method Selection
        self.sl_tp_method_combo = QComboBox()
        self.sl_tp_method_combo.addItems([
            "Support/Resistance Based",
            "Fixed Percentage",
            "ATR Based",
            "Risk:Reward Ratio",
            "Custom"
        ])
        self.sl_tp_method_combo.setCurrentText("Support/Resistance Based")
        self.sl_tp_method_combo.currentTextChanged.connect(self.on_sl_tp_method_changed)
        trading_layout.addRow("SL/TP Method:", self.sl_tp_method_combo)
        
        # SL/TP Parameters Container
        self.sl_tp_params_widget = QWidget()
        self.sl_tp_params_layout = QFormLayout(self.sl_tp_params_widget)
        self.sl_tp_params_layout.setContentsMargins(0, 0, 0, 0)
        
        # Fixed Percentage inputs
        self.sl_fixed_pct = QDoubleSpinBox()
        self.sl_fixed_pct.setRange(0.1, 10.0)
        self.sl_fixed_pct.setSingleStep(0.1)
        self.sl_fixed_pct.setValue(1.0)
        self.sl_fixed_pct.setSuffix("%")
        self.sl_fixed_pct.setToolTip("Stop Loss percentage")
        self.sl_tp_params_layout.addRow("SL %:", self.sl_fixed_pct)
        
        self.tp_fixed_pct = QDoubleSpinBox()
        self.tp_fixed_pct.setRange(0.1, 50.0)
        self.tp_fixed_pct.setSingleStep(0.1)
        self.tp_fixed_pct.setValue(2.0)
        self.tp_fixed_pct.setSuffix("%")
        self.tp_fixed_pct.setToolTip("Take Profit percentage")
        self.sl_tp_params_layout.addRow("TP %:", self.tp_fixed_pct)
        
        # ATR Based inputs
        self.atr_period = QSpinBox()
        self.atr_period.setRange(5, 50)
        self.atr_period.setValue(14)
        self.atr_period.setToolTip("ATR period")
        self.sl_tp_params_layout.addRow("ATR Period:", self.atr_period)
        
        self.sl_atr_multiplier = QDoubleSpinBox()
        self.sl_atr_multiplier.setRange(0.5, 5.0)
        self.sl_atr_multiplier.setSingleStep(0.1)
        self.sl_atr_multiplier.setValue(2.0)
        self.sl_atr_multiplier.setToolTip("SL = ATR * multiplier")
        self.sl_tp_params_layout.addRow("SL ATR Multiplier:", self.sl_atr_multiplier)
        
        self.tp_atr_multiplier = QDoubleSpinBox()
        self.tp_atr_multiplier.setRange(0.5, 10.0)
        self.tp_atr_multiplier.setSingleStep(0.1)
        self.tp_atr_multiplier.setValue(4.0)
        self.tp_atr_multiplier.setToolTip("TP = ATR * multiplier")
        self.sl_tp_params_layout.addRow("TP ATR Multiplier:", self.tp_atr_multiplier)
        
        # Risk:Reward Ratio input
        self.risk_reward = QDoubleSpinBox()
        self.risk_reward.setRange(0.5, 10.0)
        self.risk_reward.setSingleStep(0.5)
        self.risk_reward.setValue(2.0)
        self.risk_reward.setToolTip("Risk:Reward ratio (e.g., 2.0 = 1:2)")
        self.sl_tp_params_layout.addRow("Risk:Reward Ratio:", self.risk_reward)
        
        # Custom SL/TP inputs
        self.sl_custom = QDoubleSpinBox()
        self.sl_custom.setRange(0.00001, 999999.0)
        self.sl_custom.setDecimals(5)
        self.sl_custom.setToolTip("Custom Stop Loss price")
        self.sl_tp_params_layout.addRow("Custom SL:", self.sl_custom)
        
        self.tp_custom = QDoubleSpinBox()
        self.tp_custom.setRange(0.00001, 999999.0)
        self.tp_custom.setDecimals(5)
        self.tp_custom.setToolTip("Custom Take Profit price")
        self.sl_tp_params_layout.addRow("Custom TP:", self.tp_custom)
        
        trading_layout.addRow("", self.sl_tp_params_widget)
        
        # Initially hide all SL/TP params (will show based on method)
        self._update_sl_tp_params_visibility()
        
        self.check_interval = QSpinBox()
        self.check_interval.setRange(10, 3600)
        self.check_interval.setValue(60)
        self.check_interval.setSuffix(" seconds")
        trading_layout.addRow("Check Interval:", self.check_interval)
        
        trading_group.setLayout(trading_layout)
        config_content_layout.addWidget(trading_group)
        
        # Trailing Stop-Loss & Profit Lock Settings
        trailing_group = QGroupBox("Trailing Stop-Loss & Profit Lock")
        trailing_group.setStyleSheet(self._get_group_style())
        trailing_layout = QFormLayout()
        
        # Trailing Stop-Loss Section
        self.enable_trailing_sl = QCheckBox("Enable Trailing Stop-Loss")
        self.enable_trailing_sl.setToolTip("Automatically move stop-loss as price moves in your favor")
        trailing_layout.addRow("", self.enable_trailing_sl)
        
        self.trailing_sl_gap = QDoubleSpinBox()
        self.trailing_sl_gap.setRange(0.00001, 1000.0)
        self.trailing_sl_gap.setDecimals(5)
        self.trailing_sl_gap.setValue(0.001)
        self.trailing_sl_gap.setToolTip("Gap between highest price and stop-loss (in price points)")
        self.trailing_sl_gap.setEnabled(False)
        self.enable_trailing_sl.toggled.connect(self.trailing_sl_gap.setEnabled)
        trailing_layout.addRow("  SL Gap (points):", self.trailing_sl_gap)
        
        # Separator
        separator_trailing = QFrame()
        separator_trailing.setFrameShape(QFrame.Shape.HLine)
        separator_trailing.setFrameShadow(QFrame.Shadow.Sunken)
        separator_trailing.setStyleSheet("background-color: #555; max-height: 1px; margin: 5px 0;")
        trailing_layout.addRow("", separator_trailing)
        
        # Profit Lock Section
        self.enable_profit_lock = QCheckBox("Enable Profit Lock")
        self.enable_profit_lock.setToolTip("Lock minimum profit and trail it as profit increases")
        trailing_layout.addRow("", self.enable_profit_lock)
        
        self.profit_lock_trigger = QDoubleSpinBox()
        self.profit_lock_trigger.setRange(0.01, 100000.0)
        self.profit_lock_trigger.setDecimals(2)
        self.profit_lock_trigger.setValue(100.0)
        self.profit_lock_trigger.setToolTip("Profit amount that triggers the lock (in account currency)")
        self.profit_lock_trigger.setEnabled(False)
        self.enable_profit_lock.toggled.connect(self.profit_lock_trigger.setEnabled)
        trailing_layout.addRow("  Lock Trigger:", self.profit_lock_trigger)
        
        self.profit_lock_value = QDoubleSpinBox()
        self.profit_lock_value.setRange(0.01, 100000.0)
        self.profit_lock_value.setDecimals(2)
        self.profit_lock_value.setValue(50.0)
        self.profit_lock_value.setToolTip("Minimum profit to lock when trigger is reached")
        self.profit_lock_value.setEnabled(False)
        self.enable_profit_lock.toggled.connect(self.profit_lock_value.setEnabled)
        trailing_layout.addRow("  Lock Value:", self.profit_lock_value)
        
        self.profit_trail_step = QDoubleSpinBox()
        self.profit_trail_step.setRange(0.01, 100000.0)
        self.profit_trail_step.setDecimals(2)
        self.profit_trail_step.setValue(100.0)
        self.profit_trail_step.setToolTip("Profit increase amount that triggers trailing")
        self.profit_trail_step.setEnabled(False)
        self.enable_profit_lock.toggled.connect(self.profit_trail_step.setEnabled)
        trailing_layout.addRow("  Trail Step:", self.profit_trail_step)
        
        self.profit_trail_amount = QDoubleSpinBox()
        self.profit_trail_amount.setRange(0.01, 100000.0)
        self.profit_trail_amount.setDecimals(2)
        self.profit_trail_amount.setValue(50.0)
        self.profit_trail_amount.setToolTip("Amount to increase locked profit when trail step is reached")
        self.profit_trail_amount.setEnabled(False)
        self.enable_profit_lock.toggled.connect(self.profit_trail_amount.setEnabled)
        trailing_layout.addRow("  Trail Amount:", self.profit_trail_amount)
        
        trailing_group.setLayout(trailing_layout)
        config_content_layout.addWidget(trailing_group)
        
        # Control Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.monitor_btn = QPushButton("Monitor Indicators")
        self.monitor_btn.setStyleSheet(self._get_button_style("#2196F3"))
        self.monitor_btn.clicked.connect(self.toggle_monitoring)
        self.monitor_btn.setToolTip("Start/Stop monitoring indicator values without trading")
        button_layout.addWidget(self.monitor_btn)
        
        self.add_condition_btn = QPushButton("Add Condition")
        self.add_condition_btn.setStyleSheet(self._get_button_style("#FF9800"))
        self.add_condition_btn.clicked.connect(self.add_condition_to_queue)
        self.add_condition_btn.setToolTip("Add trade condition to queue without stopping")
        button_layout.addWidget(self.add_condition_btn)
        
        self.start_btn = QPushButton("Start Trading")
        self.start_btn.setStyleSheet(self._get_button_style("#4CAF50"))
        self.start_btn.clicked.connect(self.toggle_trading)
        self.start_btn.setToolTip("Start/Stop trading with the configured conditions")
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("Stop All")
        self.stop_btn.setStyleSheet(self._get_button_style("#f44336"))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_indicator)
        self.stop_btn.setToolTip("Stop both monitoring and trading")
        button_layout.addWidget(self.stop_btn)
        
        config_content_layout.addLayout(button_layout)
        config_content_layout.addStretch()
        
        scroll.setWidget(config_content)
        config_layout.addWidget(scroll)
        
        self.tab_widget.addTab(config_tab, "⚙️ Configuration")
        
        # Initialize indicator type visibility
        self.on_indicator_type_changed("Support/Resistance")
    
    def on_indicator_type_changed(self, indicator_type: str):
        """Show/hide indicator-specific settings based on selected type"""
        if indicator_type == "Support/Resistance":
            self.sr_settings_container.setVisible(True)
            self.ohlc_settings_container.setVisible(False)
            # Update monitoring tab
            if hasattr(self, 'sr_monitoring_container'):
                self.sr_monitoring_container.setVisible(True)
            if hasattr(self, 'ohlc_monitoring_container'):
                self.ohlc_monitoring_container.setVisible(False)
        elif indicator_type == "Previous Session OHLC":
            self.sr_settings_container.setVisible(False)
            self.ohlc_settings_container.setVisible(True)
            # Update monitoring tab
            if hasattr(self, 'sr_monitoring_container'):
                self.sr_monitoring_container.setVisible(False)
            if hasattr(self, 'ohlc_monitoring_container'):
                self.ohlc_monitoring_container.setVisible(True)
    
    def _create_monitoring_tab(self):
        """Create Monitoring tab with live values and tables"""
        monitoring_tab = QWidget()
        monitoring_layout = QVBoxLayout(monitoring_tab)
        monitoring_layout.setContentsMargins(20, 20, 20, 20)
        monitoring_layout.setSpacing(20)
        
        # Main horizontal splitter: Live Values on left, Tables on right
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Live Indicator Values Section (more prominent)
        values_container = QWidget()
        values_container_layout = QVBoxLayout(values_container)
        values_container_layout.setContentsMargins(10, 10, 10, 10)
        
        values_group = QGroupBox("Live Indicator Values")
        values_group.setStyleSheet(self._get_group_style())
        values_group.setMinimumWidth(350)
        values_group.setMaximumWidth(500)
        
        # Use GridLayout for better organization
        values_layout = QGridLayout()
        values_layout.setSpacing(12)
        values_layout.setContentsMargins(15, 15, 15, 15)
        # Set column stretch factors: column 0 (labels) = 1, column 1 (values) = 2
        values_layout.setColumnStretch(0, 1)
        values_layout.setColumnStretch(1, 2)
        # Set minimum column widths
        values_layout.setColumnMinimumWidth(0, 100)
        values_layout.setColumnMinimumWidth(1, 150)
        
        # Current Price - Large and prominent
        price_label_text = QLabel("Current Price:")
        price_label_text.setStyleSheet("font-weight: bold; font-size: 12px; color: #aaa;")
        price_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.price_label = QLabel("--")
        self.price_label.setMinimumHeight(40)
        self.price_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.price_label.setStyleSheet("""
            font-weight: bold; 
            font-size: 20px; 
            color: #FFFFFF; 
            background-color: #2b2b2b; 
            border: 2px solid #4CAF50; 
            border-radius: 5px; 
            padding: 10px;
        """)
        self.price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        values_layout.addWidget(price_label_text, 0, 0)
        values_layout.addWidget(self.price_label, 0, 1)
        self.indicator_values_labels['Current Price'] = self.price_label
        
        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        separator1.setStyleSheet("background-color: #555; max-height: 1px;")
        values_layout.addWidget(separator1, 1, 0, 1, 2)
        
        # Support/Resistance Section Container
        self.sr_monitoring_container = QWidget()
        sr_monitoring_layout = QGridLayout(self.sr_monitoring_container)
        sr_monitoring_layout.setContentsMargins(0, 0, 0, 0)
        sr_monitoring_layout.setSpacing(12)
        sr_monitoring_layout.setColumnStretch(0, 1)
        sr_monitoring_layout.setColumnStretch(1, 2)
        sr_monitoring_layout.setColumnMinimumWidth(0, 100)
        sr_monitoring_layout.setColumnMinimumWidth(1, 150)
        sr_row = 0
        
        # Support Section
        support_header = QLabel("Support Levels")
        support_header.setStyleSheet("font-weight: bold; font-size: 13px; color: #4CAF50; margin-top: 5px;")
        values_layout.addWidget(support_header, 2, 0, 1, 2)
        
        support_price_label_text = QLabel("Nearest:")
        support_price_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        support_price_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.support_label = QLabel("--")
        self.support_label.setMinimumHeight(30)
        self.support_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.support_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 14px; background-color: #1e2e1e; border: 1px solid #4CAF50; border-radius: 3px; padding: 5px;")
        self.support_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sr_monitoring_layout.addWidget(support_price_label_text, sr_row, 0)
        sr_monitoring_layout.addWidget(self.support_label, sr_row, 1)
        sr_row += 1
        self.indicator_values_labels['Nearest Support'] = self.support_label
        
        support_strength_label_text = QLabel("Strength:")
        support_strength_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        support_strength_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.support_strength_label = QLabel("--")
        self.support_strength_label.setMinimumHeight(25)
        self.support_strength_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.support_strength_label.setStyleSheet("color: #66BB6A; font-size: 12px; background-color: #1e2e1e; padding: 5px;")
        self.support_strength_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sr_monitoring_layout.addWidget(support_strength_label_text, sr_row, 0)
        sr_monitoring_layout.addWidget(self.support_strength_label, sr_row, 1)
        sr_row += 1
        self.indicator_values_labels['Support Strength'] = self.support_strength_label
        
        support_touches_label_text = QLabel("Touches:")
        support_touches_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        support_touches_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.support_touches_label = QLabel("--")
        self.support_touches_label.setMinimumHeight(25)
        self.support_touches_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.support_touches_label.setStyleSheet("color: #66BB6A; font-size: 12px; background-color: #1e2e1e; padding: 5px;")
        self.support_touches_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sr_monitoring_layout.addWidget(support_touches_label_text, sr_row, 0)
        sr_monitoring_layout.addWidget(self.support_touches_label, sr_row, 1)
        sr_row += 1
        self.indicator_values_labels['Support Touches'] = self.support_touches_label
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        separator2.setStyleSheet("background-color: #555; max-height: 1px;")
        sr_monitoring_layout.addWidget(separator2, sr_row, 0, 1, 2)
        sr_row += 1
        
        # Resistance Section
        resistance_header = QLabel("Resistance Levels")
        resistance_header.setStyleSheet("font-weight: bold; font-size: 13px; color: #f44336; margin-top: 5px;")
        sr_monitoring_layout.addWidget(resistance_header, sr_row, 0, 1, 2)
        sr_row += 1
        
        resistance_price_label_text = QLabel("Nearest:")
        resistance_price_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        resistance_price_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.resistance_label = QLabel("--")
        self.resistance_label.setMinimumHeight(30)
        self.resistance_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.resistance_label.setStyleSheet("color: #f44336; font-weight: bold; font-size: 14px; background-color: #2e1e1e; border: 1px solid #f44336; border-radius: 3px; padding: 5px;")
        self.resistance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sr_monitoring_layout.addWidget(resistance_price_label_text, sr_row, 0)
        sr_monitoring_layout.addWidget(self.resistance_label, sr_row, 1)
        sr_row += 1
        self.indicator_values_labels['Nearest Resistance'] = self.resistance_label
        
        resistance_strength_label_text = QLabel("Strength:")
        resistance_strength_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        resistance_strength_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.resistance_strength_label = QLabel("--")
        self.resistance_strength_label.setMinimumHeight(25)
        self.resistance_strength_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.resistance_strength_label.setStyleSheet("color: #e57373; font-size: 12px; background-color: #2e1e1e; padding: 5px;")
        self.resistance_strength_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sr_monitoring_layout.addWidget(resistance_strength_label_text, sr_row, 0)
        sr_monitoring_layout.addWidget(self.resistance_strength_label, sr_row, 1)
        sr_row += 1
        self.indicator_values_labels['Resistance Strength'] = self.resistance_strength_label
        
        resistance_touches_label_text = QLabel("Touches:")
        resistance_touches_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        resistance_touches_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.resistance_touches_label = QLabel("--")
        self.resistance_touches_label.setMinimumHeight(25)
        self.resistance_touches_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.resistance_touches_label.setStyleSheet("color: #e57373; font-size: 12px; background-color: #2e1e1e; padding: 5px;")
        self.resistance_touches_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sr_monitoring_layout.addWidget(resistance_touches_label_text, sr_row, 0)
        sr_monitoring_layout.addWidget(self.resistance_touches_label, sr_row, 1)
        sr_row += 1
        self.indicator_values_labels['Resistance Touches'] = self.resistance_touches_label
        
        # Separator
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.HLine)
        separator3.setFrameShadow(QFrame.Shadow.Sunken)
        separator3.setStyleSheet("background-color: #555; max-height: 1px;")
        sr_monitoring_layout.addWidget(separator3, sr_row, 0, 1, 2)
        sr_row += 1
        
        # Summary Section
        summary_header = QLabel("Summary")
        summary_header.setStyleSheet("font-weight: bold; font-size: 13px; color: #888; margin-top: 5px;")
        sr_monitoring_layout.addWidget(summary_header, sr_row, 0, 1, 2)
        sr_row += 1
        
        total_support_label_text = QLabel("Total Supports:")
        total_support_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        total_support_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.total_support_label = QLabel("--")
        self.total_support_label.setMinimumHeight(25)
        self.total_support_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.total_support_label.setStyleSheet("color: #888; font-size: 12px; padding: 5px;")
        self.total_support_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sr_monitoring_layout.addWidget(total_support_label_text, sr_row, 0)
        sr_monitoring_layout.addWidget(self.total_support_label, sr_row, 1)
        sr_row += 1
        self.indicator_values_labels['Total Support Levels'] = self.total_support_label
        
        total_resistance_label_text = QLabel("Total Resistances:")
        total_resistance_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        total_resistance_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.total_resistance_label = QLabel("--")
        self.total_resistance_label.setMinimumHeight(25)
        self.total_resistance_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.total_resistance_label.setStyleSheet("color: #888; font-size: 12px; padding: 5px;")
        self.total_resistance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sr_monitoring_layout.addWidget(total_resistance_label_text, sr_row, 0)
        sr_monitoring_layout.addWidget(self.total_resistance_label, sr_row, 1)
        self.indicator_values_labels['Total Resistance Levels'] = self.total_resistance_label
        
        # Add SR container to main values layout
        values_layout.addWidget(self.sr_monitoring_container, 2, 0, 1, 2)
        
        # OHLC Monitoring Container
        self.ohlc_monitoring_container = QWidget()
        ohlc_monitoring_layout = QGridLayout(self.ohlc_monitoring_container)
        ohlc_monitoring_layout.setContentsMargins(0, 0, 0, 0)
        ohlc_monitoring_layout.setSpacing(12)
        ohlc_monitoring_layout.setColumnStretch(0, 1)
        ohlc_monitoring_layout.setColumnStretch(1, 2)
        ohlc_monitoring_layout.setColumnMinimumWidth(0, 100)
        ohlc_monitoring_layout.setColumnMinimumWidth(1, 150)
        ohlc_row = 0
        
        # OHLC Section (for Previous Session OHLC indicator)
        separator_ohlc = QFrame()
        separator_ohlc.setFrameShape(QFrame.Shape.HLine)
        separator_ohlc.setFrameShadow(QFrame.Shadow.Sunken)
        separator_ohlc.setStyleSheet("background-color: #555; max-height: 1px; margin: 5px 0;")
        ohlc_monitoring_layout.addWidget(separator_ohlc, ohlc_row, 0, 1, 2)
        ohlc_row += 1
        
        ohlc_header = QLabel("Previous Session OHLC")
        ohlc_header.setStyleSheet("font-weight: bold; font-size: 13px; color: #FF9800; margin-top: 5px;")
        ohlc_monitoring_layout.addWidget(ohlc_header, ohlc_row, 0, 1, 2)
        ohlc_row += 1
        
        ohlc_session_label_text = QLabel("Session:")
        ohlc_session_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        ohlc_session_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.ohlc_session_label = QLabel("--")
        self.ohlc_session_label.setMinimumHeight(25)
        self.ohlc_session_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ohlc_session_label.setStyleSheet("color: #FF9800; font-size: 12px; background-color: #1e1e1e; padding: 5px;")
        self.ohlc_session_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ohlc_monitoring_layout.addWidget(ohlc_session_label_text, ohlc_row, 0)
        ohlc_monitoring_layout.addWidget(self.ohlc_session_label, ohlc_row, 1)
        ohlc_row += 1
        self.indicator_values_labels['OHLC Session'] = self.ohlc_session_label
        
        ohlc_open_label_text = QLabel("Previous Open:")
        ohlc_open_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        ohlc_open_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.ohlc_open_label = QLabel("--")
        self.ohlc_open_label.setMinimumHeight(25)
        self.ohlc_open_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ohlc_open_label.setStyleSheet("color: #4CAF50; font-size: 12px; background-color: #1e1e1e; padding: 5px;")
        self.ohlc_open_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ohlc_monitoring_layout.addWidget(ohlc_open_label_text, ohlc_row, 0)
        ohlc_monitoring_layout.addWidget(self.ohlc_open_label, ohlc_row, 1)
        ohlc_row += 1
        self.indicator_values_labels['Previous Open'] = self.ohlc_open_label
        
        ohlc_high_label_text = QLabel("Previous High:")
        ohlc_high_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        ohlc_high_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.ohlc_high_label = QLabel("--")
        self.ohlc_high_label.setMinimumHeight(25)
        self.ohlc_high_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ohlc_high_label.setStyleSheet("color: #FF9800; font-size: 12px; background-color: #1e1e1e; padding: 5px;")
        self.ohlc_high_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ohlc_monitoring_layout.addWidget(ohlc_high_label_text, ohlc_row, 0)
        ohlc_monitoring_layout.addWidget(self.ohlc_high_label, ohlc_row, 1)
        ohlc_row += 1
        self.indicator_values_labels['Previous High'] = self.ohlc_high_label
        
        ohlc_low_label_text = QLabel("Previous Low:")
        ohlc_low_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        ohlc_low_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.ohlc_low_label = QLabel("--")
        self.ohlc_low_label.setMinimumHeight(25)
        self.ohlc_low_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ohlc_low_label.setStyleSheet("color: #f44336; font-size: 12px; background-color: #1e1e1e; padding: 5px;")
        self.ohlc_low_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ohlc_monitoring_layout.addWidget(ohlc_low_label_text, ohlc_row, 0)
        ohlc_monitoring_layout.addWidget(self.ohlc_low_label, ohlc_row, 1)
        ohlc_row += 1
        self.indicator_values_labels['Previous Low'] = self.ohlc_low_label
        
        ohlc_close_label_text = QLabel("Previous Close:")
        ohlc_close_label_text.setStyleSheet("color: #aaa; font-size: 11px;")
        ohlc_close_label_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.ohlc_close_label = QLabel("--")
        self.ohlc_close_label.setMinimumHeight(25)
        self.ohlc_close_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.ohlc_close_label.setStyleSheet("color: #2196F3; font-size: 12px; background-color: #1e1e1e; padding: 5px;")
        self.ohlc_close_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ohlc_monitoring_layout.addWidget(ohlc_close_label_text, ohlc_row, 0)
        ohlc_monitoring_layout.addWidget(self.ohlc_close_label, ohlc_row, 1)
        self.indicator_values_labels['Previous Close'] = self.ohlc_close_label
        
        # Add OHLC container to main values layout (initially hidden)
        values_layout.addWidget(self.ohlc_monitoring_container, 2, 0, 1, 2)
        self.ohlc_monitoring_container.setVisible(False)
        
        values_group.setLayout(values_layout)
        values_container_layout.addWidget(values_group)
        values_container_layout.addStretch()
        main_splitter.addWidget(values_container)
        
        # Right side: Tables in vertical splitter
        tables_container = QWidget()
        tables_container_layout = QVBoxLayout(tables_container)
        tables_container_layout.setContentsMargins(10, 10, 10, 10)
        tables_container_layout.setSpacing(15)
        
        # Splitter for tables
        tables_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # All Support/Resistance Levels Table
        all_levels_group = QGroupBox("All Support & Resistance Levels")
        all_levels_group.setStyleSheet(self._get_group_style())
        all_levels_layout = QVBoxLayout()
        all_levels_layout.setContentsMargins(5, 5, 5, 5)
        
        self.all_levels_table = QTableWidget()
        self.all_levels_table.setColumnCount(9)
        self.all_levels_table.setHorizontalHeaderLabels(["Type", "Price", "Strength", "Touches", "Distance %", "Method", "Confluence", "Timeframe", "Reversed"])
        self.all_levels_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Set minimum column widths for better readability
        self.all_levels_table.setColumnWidth(0, 90)   # Type
        self.all_levels_table.setColumnWidth(1, 100)  # Price
        self.all_levels_table.setColumnWidth(2, 80)   # Strength
        self.all_levels_table.setColumnWidth(3, 70)   # Touches
        self.all_levels_table.setColumnWidth(4, 90)   # Distance %
        self.all_levels_table.setColumnWidth(5, 100)  # Method
        self.all_levels_table.setColumnWidth(6, 90)   # Confluence
        self.all_levels_table.setColumnWidth(7, 90)   # Timeframe
        self.all_levels_table.setColumnWidth(8, 80)   # Reversed
        self.all_levels_table.setAlternatingRowColors(True)
        self.all_levels_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.all_levels_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.all_levels_table.setSortingEnabled(True)
        self.all_levels_table.setStyleSheet(self._get_table_style())
        all_levels_layout.addWidget(self.all_levels_table)
        all_levels_group.setLayout(all_levels_layout)
        tables_splitter.addWidget(all_levels_group)
        
        # Nearby Support/Resistance Levels Table
        nearby_group = QGroupBox("Nearby Support & Resistance Levels")
        nearby_group.setStyleSheet(self._get_group_style())
        nearby_layout = QVBoxLayout()
        nearby_layout.setContentsMargins(5, 5, 5, 5)
        
        self.nearby_levels_table = QTableWidget()
        self.nearby_levels_table.setColumnCount(5)
        self.nearby_levels_table.setHorizontalHeaderLabels(["Type", "Price", "Strength", "Touches", "Distance %"])
        self.nearby_levels_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        # Set minimum column widths for better readability
        self.nearby_levels_table.setColumnWidth(0, 100)  # Type
        self.nearby_levels_table.setColumnWidth(1, 120)  # Price
        self.nearby_levels_table.setColumnWidth(2, 100)  # Strength
        self.nearby_levels_table.setColumnWidth(3, 90)   # Touches
        self.nearby_levels_table.setColumnWidth(4, 110)   # Distance %
        self.nearby_levels_table.setAlternatingRowColors(True)
        self.nearby_levels_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.nearby_levels_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.nearby_levels_table.setSortingEnabled(True)
        self.nearby_levels_table.setStyleSheet(self._get_table_style())
        nearby_layout.addWidget(self.nearby_levels_table)
        nearby_group.setLayout(nearby_layout)
        tables_splitter.addWidget(nearby_group)
        
        tables_splitter.setStretchFactor(0, 2)
        tables_splitter.setStretchFactor(1, 1)
        tables_container_layout.addWidget(tables_splitter)
        main_splitter.addWidget(tables_container)
        
        # Set splitter proportions (30% for values, 70% for tables)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)
        main_splitter.setSizes([350, 1050])
        
        monitoring_layout.addWidget(main_splitter)
        
        # Status Log - at the bottom with better spacing
        status_group = QGroupBox("Status Log")
        status_group.setStyleSheet(self._get_group_style())
        status_group.setMaximumHeight(200)
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(5, 5, 5, 5)
        status_layout.setSpacing(5)
        
        status_buttons = QHBoxLayout()
        clear_status_btn = QPushButton("Clear")
        clear_status_btn.setStyleSheet(self._get_button_style("#666", small=True))
        clear_status_btn.clicked.connect(lambda: self.status_text.clear())
        status_buttons.addWidget(clear_status_btn)
        status_buttons.addStretch()
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #aaa;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 10px;
            }
        """)
        status_layout.addLayout(status_buttons)
        status_layout.addWidget(self.status_text)
        status_group.setLayout(status_layout)
        monitoring_layout.addWidget(status_group)
        
        self.tab_widget.addTab(monitoring_tab, "📊 Monitoring")
    
    def _create_queue_tab(self):
        """Create Signal Queue tab"""
        queue_tab = QWidget()
        queue_layout = QVBoxLayout(queue_tab)
        queue_layout.setContentsMargins(15, 15, 15, 15)
        queue_layout.setSpacing(12)
        
        # Signal Queue Table
        queue_group = QGroupBox("Signal Queue")
        queue_group.setStyleSheet(self._get_group_style())
        queue_group_layout = QVBoxLayout()
        
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(11)
        self.queue_table.setHorizontalHeaderLabels([
            "Symbol", "Entry Type", "Level Price", "Current Price", "BUY Breakout", "SELL Breakout", "Distance %", "Status", "Actions", "Enable"
        ])
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.queue_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.queue_table.setSortingEnabled(True)
        self.queue_table.setStyleSheet(self._get_table_style())
        queue_group_layout.addWidget(self.queue_table)
        queue_group.setLayout(queue_group_layout)
        queue_layout.addWidget(queue_group)
        
        # Signal History Table
        history_group = QGroupBox("Signal History")
        history_group.setStyleSheet(self._get_group_style())
        history_group_layout = QVBoxLayout()
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Time", "Symbol", "Action", "Quantity", "SL", "TP"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.history_table.setSortingEnabled(True)
        self.history_table.setStyleSheet(self._get_table_style())
        history_group_layout.addWidget(self.history_table)
        history_group.setLayout(history_group_layout)
        queue_layout.addWidget(history_group)
        
        self.tab_widget.addTab(queue_tab, "📋 Signal Queue")
    
    def _get_group_style(self) -> str:
        """Get consistent group box styling"""
        return """
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: #252525;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #fff;
            }
        """
    
    def _get_table_style(self) -> str:
        """Get consistent table styling"""
        return """
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #2b2b2b;
                color: white;
                gridline-color: #555;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 6px;
            }
            QTableWidget::item:selected {
                background-color: #3d5afe;
                color: white;
            }
            QHeaderView::section {
                background-color: #2b2b2b;
                color: white;
                padding: 8px;
                border: 1px solid #555;
                font-weight: bold;
                font-size: 11px;
            }
        """
    
    def _get_button_style(self, color: str, small: bool = False) -> str:
        """Get consistent button styling"""
        padding = "5px 15px" if small else "8px 20px"
        font_size = "11px" if small else "12px"
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                font-weight: bold;
                font-size: {font_size};
                padding: {padding};
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color, 0.8)};
            }}
            QPushButton:disabled {{
                background-color: #666;
                color: #999;
            }}
        """
    
    def _darken_color(self, color: str, factor: float = 0.9) -> str:
        """Darken a hex color"""
        # Simple darkening - convert hex to RGB, darken, convert back
        color = color.lstrip('#')
        
        # Handle both 3-digit and 6-digit hex colors
        if len(color) == 3:
            # Expand 3-digit to 6-digit (e.g., "666" -> "666666")
            r = int(color[0], 16) * 17
            g = int(color[1], 16) * 17
            b = int(color[2], 16) * 17
        else:
            # 6-digit hex color
            r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def setup_timers(self):
        """Setup update timers"""
        # Timer is already set up in __init__
        pass
    
    def get_timeframe_mt5(self) -> int:
        """Convert timeframe string to MT5 constant"""
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
        }
        return tf_map.get(self.timeframe_combo.currentText(), mt5.TIMEFRAME_M15)
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        indicator_type = self.indicator_type_combo.currentText()
        
        config = {
            'symbol': self.symbol_combo.currentText().upper(),
            'timeframe': self.get_timeframe_mt5(),
            'quantity': self.quantity_spin.value(),
            'risk_reward_ratio': self.risk_reward.value(),
            'check_interval': self.check_interval.value(),
            'indicator_type': indicator_type,
            
            # Support/Resistance settings
            'pivot_period': self.pivot_period_combo.currentText(),
            'sr_min_touches': self.sr_min_touches.value(),
            'sr_strength': self.sr_strength.value(),
            'sr_breakout_confirmation': self.sr_breakout_confirmation.value(),
            'sr_resistance_breakout_buy': self.sr_resistance_breakout_buy.isChecked(),
            'sr_support_breakdown_sell': self.sr_support_breakdown_sell.isChecked(),
            'enable_role_reversal': self.enable_role_reversal.isChecked(),
            'confluence_tolerance': self.confluence_tolerance.value(),
            'min_confluence_methods': self.min_confluence_methods.value(),
            
            # Selected levels for entry conditions
            'selected_resistance_price': self._get_selected_resistance_price(),
            'selected_support_price': self._get_selected_support_price(),
            
            # Exit conditions (empty - exit conditions UI removed)
            'exit_conditions': {},
            
            # SL/TP method and parameters
            'sl_tp_method': self.sl_tp_method_combo.currentText(),
            'sl_tp_params': {
                'sl_fixed_pct': self.sl_fixed_pct.value(),
                'tp_fixed_pct': self.tp_fixed_pct.value(),
                'atr_period': self.atr_period.value(),
                'sl_atr_multiplier': self.sl_atr_multiplier.value(),
                'tp_atr_multiplier': self.tp_atr_multiplier.value(),
                'risk_reward_ratio': self.risk_reward.value(),
                'sl_custom': self.sl_custom.value(),
                'tp_custom': self.tp_custom.value(),
            },
            
            # Trailing Stop-Loss settings
            'enable_trailing_sl': self.enable_trailing_sl.isChecked(),
            'trailing_sl_gap': self.trailing_sl_gap.value() if self.enable_trailing_sl.isChecked() else None,
            
            # Profit Lock settings
            'enable_profit_lock': self.enable_profit_lock.isChecked(),
            'profit_lock_trigger': self.profit_lock_trigger.value() if self.enable_profit_lock.isChecked() else None,
            'profit_lock_value': self.profit_lock_value.value() if self.enable_profit_lock.isChecked() else None,
            'profit_trail_step': self.profit_trail_step.value() if self.enable_profit_lock.isChecked() else None,
            'profit_trail_amount': self.profit_trail_amount.value() if self.enable_profit_lock.isChecked() else None,
            
            # Previous Session OHLC settings
            'ohlc_session_type': self.ohlc_session_combo.currentText().lower().replace(' session', ''),
            'ohlc_breakout_confirmation': self.ohlc_breakout_confirmation.value(),
            'ohlc_buy_high': self.ohlc_buy_high.isChecked(),
            'ohlc_buy_close': self.ohlc_buy_close.isChecked(),
            'ohlc_buy_open': self.ohlc_buy_open.isChecked(),
            'ohlc_sell_low': self.ohlc_sell_low.isChecked(),
            'ohlc_sell_close': self.ohlc_sell_close.isChecked(),
            'ohlc_sell_open': self.ohlc_sell_open.isChecked(),
            
            # Active symbols list
            'symbols': self.active_symbols if hasattr(self, 'active_symbols') else [],
        }
        
        return config
    
    def _get_selected_resistance_price(self) -> Optional[float]:
        """Get selected resistance level price from dropdown"""
        current_data = self.resistance_dropdown.currentData()
        if current_data is not None and isinstance(current_data, (int, float)):
            return float(current_data)
        return None
    
    def _get_selected_support_price(self) -> Optional[float]:
        """Get selected support level price from dropdown"""
        current_data = self.support_dropdown.currentData()
        if current_data is not None and isinstance(current_data, (int, float)):
            return float(current_data)
        return None
    
    def on_sl_tp_method_changed(self, method: str):
        """Handle SL/TP method selection change"""
        self._update_sl_tp_params_visibility()
    
    def _update_sl_tp_params_visibility(self):
        """Show/hide SL/TP parameter inputs based on selected method"""
        method = self.sl_tp_method_combo.currentText()
        
        # Hide all first
        for i in range(self.sl_tp_params_layout.rowCount()):
            item = self.sl_tp_params_layout.itemAt(i, QFormLayout.ItemRole.FieldRole)
            if item:
                item.widget().setVisible(False)
            label_item = self.sl_tp_params_layout.itemAt(i, QFormLayout.ItemRole.LabelRole)
            if label_item:
                label_item.widget().setVisible(False)
        
        # Show relevant inputs based on method
        if method == "Fixed Percentage":
            self.sl_fixed_pct.setVisible(True)
            self.sl_tp_params_layout.labelForField(self.sl_fixed_pct).setVisible(True)
            self.tp_fixed_pct.setVisible(True)
            self.sl_tp_params_layout.labelForField(self.tp_fixed_pct).setVisible(True)
        elif method == "ATR Based":
            self.atr_period.setVisible(True)
            self.sl_tp_params_layout.labelForField(self.atr_period).setVisible(True)
            self.sl_atr_multiplier.setVisible(True)
            self.sl_tp_params_layout.labelForField(self.sl_atr_multiplier).setVisible(True)
            self.tp_atr_multiplier.setVisible(True)
            self.sl_tp_params_layout.labelForField(self.tp_atr_multiplier).setVisible(True)
        elif method == "Risk:Reward Ratio":
            self.risk_reward.setVisible(True)
            self.sl_tp_params_layout.labelForField(self.risk_reward).setVisible(True)
        elif method == "Custom":
            self.sl_custom.setVisible(True)
            self.sl_tp_params_layout.labelForField(self.sl_custom).setVisible(True)
            self.tp_custom.setVisible(True)
            self.sl_tp_params_layout.labelForField(self.tp_custom).setVisible(True)
        # "Support/Resistance Based" shows nothing (uses SR levels)
    
    def add_condition_to_queue(self):
        """Add current configuration as a condition to the signal queue"""
        config = self.get_config()
        
        if not config['symbol']:
            QMessageBox.warning(self, "Error", "Please select a symbol")
            return
        
        if not (config.get('sr_resistance_breakout_buy') or config.get('sr_support_breakdown_sell')):
            QMessageBox.warning(self, "Error", "Please enable at least one entry condition")
            return
        
        condition_id = self.signal_queue.add_condition(config)
        self.add_status(f"Added condition {condition_id[:8]} to queue")
        self.update_queue_table()
        self.save_state()  # Auto-save when condition is added
        
        # Start trading thread if not already running (to check queue)
        if not self.trading_thread:
            self.start_indicator()
    
    def update_queue_table(self):
        """Update the signal queue table with current conditions"""
        self.queue_table.setRowCount(0)
        
        # Get current prices for all symbols in queue
        current_prices = {}
        for condition in self.signal_queue.conditions:
            symbol = condition['symbol']
            if symbol not in current_prices:
                try:
                    tick = mt5.symbol_info_tick(symbol)
                    if tick and tick.last > 0:
                        current_prices[symbol] = tick.last
                    elif tick and tick.bid > 0:
                        current_prices[symbol] = tick.bid
                except:
                    current_prices[symbol] = None
        
        for condition in self.signal_queue.conditions:
            row = self.queue_table.rowCount()
            self.queue_table.insertRow(row)
            
            # Symbol
            symbol_item = QTableWidgetItem(condition['symbol'])
            self.queue_table.setItem(row, 0, symbol_item)
            
            # Entry Type - Show which action will be triggered
            entry_type = condition['entry_type']
            level_type = condition.get('level_type', 'resistance' if entry_type == 'BUY' else 'support')
            entry_text = f"{entry_type} on {level_type.title()}"
            entry_item = QTableWidgetItem(entry_text)
            if entry_type == 'BUY':
                entry_item.setForeground(QColor("#4CAF50"))
            else:
                entry_item.setForeground(QColor("#f44336"))
            entry_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            entry_item.setToolTip(f"Will {entry_type} when {level_type} level breaks")
            self.queue_table.setItem(row, 1, entry_item)
            
            # Level Price - The support/resistance level
            level_price = condition.get('level_price')
            level_text = f"{level_price:.5f}" if level_price else "Any Level"
            level_item = QTableWidgetItem(level_text)
            if level_price:
                level_item.setToolTip(f"{level_type.title()} level at {level_price:.5f}")
            else:
                level_item.setToolTip(f"Will trigger on any {level_type} level")
            self.queue_table.setItem(row, 2, level_item)
            
            # Current Price
            current_price = current_prices.get(condition['symbol'])
            if current_price:
                condition['current_price'] = current_price
                price_item = QTableWidgetItem(f"{current_price:.5f}")
            else:
                price_item = QTableWidgetItem("--")
            self.queue_table.setItem(row, 3, price_item)
            
            # BUY Breakout Price - Calculate based on resistance level or OHLC
            breakout_confirmation = condition.get('breakout_confirmation', 0.001)
            buy_breakout_item = QTableWidgetItem("--")
            
            if indicator_type == 'Previous Session OHLC':
                # For OHLC, we need to get the OHLC values dynamically
                # This will be updated when OHLC is calculated
                if entry_type == 'BUY' and level_type in ['ohlc_high', 'ohlc_close', 'ohlc_open']:
                    buy_breakout_item = QTableWidgetItem("Calculating...")
                    buy_breakout_item.setForeground(QColor("#4CAF50"))
            elif level_price and entry_type == 'BUY' and level_type == 'resistance':
                buy_breakout_price = level_price * (1 + breakout_confirmation)
                buy_breakout_item = QTableWidgetItem(f"{buy_breakout_price:.5f}")
                buy_breakout_item.setForeground(QColor("#4CAF50"))
                buy_breakout_item.setToolTip(f"BUY when price breaks above {buy_breakout_price:.5f} (resistance {level_price:.5f} + {breakout_confirmation*100:.2f}%)")
            elif level_price and level_type == 'resistance':
                # Show BUY breakout even if this condition is for SELL (for reference)
                buy_breakout_price = level_price * (1 + breakout_confirmation)
                buy_breakout_item = QTableWidgetItem(f"{buy_breakout_price:.5f}")
                buy_breakout_item.setForeground(QColor("#888"))
                buy_breakout_item.setToolTip(f"BUY breakout would be at {buy_breakout_price:.5f} (not active for this condition)")
            self.queue_table.setItem(row, 4, buy_breakout_item)
            
            # SELL Breakout Price - Calculate based on support level or OHLC
            sell_breakout_item = QTableWidgetItem("--")
            
            if indicator_type == 'Previous Session OHLC':
                # For OHLC, we need to get the OHLC values dynamically
                if entry_type == 'SELL' and level_type in ['ohlc_low', 'ohlc_close', 'ohlc_open']:
                    sell_breakout_item = QTableWidgetItem("Calculating...")
                    sell_breakout_item.setForeground(QColor("#f44336"))
            elif level_price and entry_type == 'SELL' and level_type == 'support':
                sell_breakout_price = level_price * (1 - breakout_confirmation)
                sell_breakout_item = QTableWidgetItem(f"{sell_breakout_price:.5f}")
                sell_breakout_item.setForeground(QColor("#f44336"))
                sell_breakout_item.setToolTip(f"SELL when price breaks below {sell_breakout_price:.5f} (support {level_price:.5f} - {breakout_confirmation*100:.2f}%)")
            elif level_price and level_type == 'support':
                # Show SELL breakout even if this condition is for BUY (for reference)
                sell_breakout_price = level_price * (1 - breakout_confirmation)
                sell_breakout_item = QTableWidgetItem(f"{sell_breakout_price:.5f}")
                sell_breakout_item.setForeground(QColor("#888"))
                sell_breakout_item.setToolTip(f"SELL breakout would be at {sell_breakout_price:.5f} (not active for this condition)")
            self.queue_table.setItem(row, 5, sell_breakout_item)
            
            # Distance % - Distance from current price to level
            if current_price and level_price:
                distance = abs(current_price - level_price)
                distance_pct = (distance / current_price) * 100
                distance_item = QTableWidgetItem(f"{distance_pct:.2f}%")
                if distance_pct < 0.5:
                    distance_item.setForeground(QColor("#FFD700"))  # Gold for very close
                    distance_item.setToolTip("Very close to breakout level!")
                else:
                    distance_item.setToolTip(f"Current price is {distance_pct:.2f}% away from {level_type} level")
            else:
                distance_item = QTableWidgetItem("--")
            self.queue_table.setItem(row, 6, distance_item)
            
            # Status
            status_item = QTableWidgetItem(condition['status'])
            if condition['status'] == 'Pending':
                status_item.setForeground(QColor("#FFA500"))  # Orange
            elif condition['status'] == 'Executed':
                status_item.setForeground(QColor("#4CAF50"))  # Green
            self.queue_table.setItem(row, 7, status_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(2, 2, 2, 2)
            
            remove_btn = QPushButton("Remove")
            remove_btn.setStyleSheet("background-color: #f44336; color: white; font-size: 10px;")
            remove_btn.clicked.connect(lambda checked, cid=condition['id']: self.remove_condition_from_queue(cid))
            actions_layout.addWidget(remove_btn)
            
            self.queue_table.setCellWidget(row, 8, actions_widget)
            
            # Enable/Disable checkbox
            enable_checkbox = QCheckBox()
            enable_checkbox.setChecked(condition.get('enabled', True))
            enable_checkbox.stateChanged.connect(lambda state, cid=condition['id']: self.toggle_condition_in_queue(cid))
            self.queue_table.setCellWidget(row, 9, enable_checkbox)
        
        self.queue_table.resizeColumnsToContents()
    
    def remove_condition_from_queue(self, condition_id: str):
        """Remove a condition from the queue"""
        if self.signal_queue.remove_condition(condition_id):
            self.add_status(f"Removed condition {condition_id[:8]} from queue")
            self.update_queue_table()
            self.save_state()  # Auto-save when condition is removed
    
    def toggle_condition_in_queue(self, condition_id: str):
        """Toggle enable/disable a condition in the queue"""
        self.signal_queue.toggle_condition(condition_id)
        self.update_queue_table()
        self.save_state()  # Auto-save when condition is toggled
    
    def toggle_monitoring(self):
        """Toggle monitoring on/off"""
        if self.monitoring_thread:
            # Stop monitoring
            self.monitoring_thread.stop()
            self.monitoring_thread.wait(5000)
            self.monitoring_thread = None
            
            self.monitor_btn.setText("Monitor Indicators")
            self.monitor_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
            self.add_status("Monitoring stopped")
            
            # Update stop button
            if not self.trading_thread:
                self.stop_btn.setEnabled(False)
        else:
            # Start monitoring
            self.start_monitoring()
    
    def start_monitoring(self):
        """Start monitoring indicators only (no trading)"""
        config = self.get_config()
        
        if not config['symbol']:
            QMessageBox.warning(self, "Error", "Please select a symbol")
            return
        
        config['monitoring_only'] = True
        self.monitoring_thread = IndicatorRunnerThread(config)
        self.monitoring_thread.status_update.connect(self.on_status_update)
        self.monitoring_thread.indicator_values_updated.connect(self.on_indicator_values_updated)
        self.monitoring_thread.start()
        
        # Update button states
        self.monitor_btn.setText("Stop Monitoring")
        self.monitor_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        # Trading button remains enabled if trading not running
        if not self.trading_thread:
            self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        self.add_status("Monitoring Support/Resistance started (no trading)")
    
    def toggle_trading(self):
        """Toggle trading on/off"""
        if self.trading_thread:
            # Stop trading
            self.trading_thread.stop()
            self.trading_thread.wait(5000)
            self.trading_thread = None
            
            self.start_btn.setText("Start Trading")
            self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            self.add_status("Trading stopped")
            
            # Update stop button
            if not self.monitoring_thread:
                self.stop_btn.setEnabled(False)
        else:
            # Start trading
            self.start_indicator()
    
    def start_indicator(self):
        """Start the indicator with trading enabled - checks signal queue"""
        # Check if queue has conditions, if not, add current config
        if len(self.signal_queue.get_pending_conditions()) == 0:
            config = self.get_config()
            
            if not config['symbol']:
                QMessageBox.warning(self, "Error", "Please select a symbol")
                return
            
            if not (config.get('sr_resistance_breakout_buy') or config.get('sr_support_breakdown_sell')):
                QMessageBox.warning(self, "Error", "Please enable at least one entry condition")
                return
            
            # Add current config to queue
            self.signal_queue.add_condition(config)
            self.update_queue_table()
        
        # Create config for thread (will check queue)
        base_config = self.get_config()
        base_config['monitoring_only'] = False
        base_config['signal_queue'] = self.signal_queue  # Pass queue reference
        base_config['exit_manager'] = self.exit_manager  # Pass exit manager reference
        
        self.trading_thread = IndicatorRunnerThread(base_config)
        self.trading_thread.signal_generated.connect(self.on_signal_generated)
        self.trading_thread.status_update.connect(self.on_status_update)
        self.trading_thread.indicator_values_updated.connect(self.on_indicator_values_updated)
        self.trading_thread.start()
        
        # Update button states
        self.start_btn.setText("Stop Trading")
        self.start_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        # Monitoring button remains enabled if monitoring not running
        if not self.monitoring_thread:
            self.monitor_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        self.add_status("Support/Resistance trading started - checking signal queue")
        self.save_state()  # Auto-save when trading starts
    
    def stop_indicator(self):
        """Stop both monitoring and trading threads"""
        stopped_anything = False
        
        if self.monitoring_thread:
            self.monitoring_thread.stop()
            self.monitoring_thread.wait(5000)
            self.monitoring_thread = None
            stopped_anything = True
            self.add_status("Monitoring stopped")
        
        if self.trading_thread:
            self.trading_thread.stop()
            self.trading_thread.wait(5000)
            self.trading_thread = None
            stopped_anything = True
            self.add_status("Trading stopped")
        
        # Reset button states
        self.monitor_btn.setText("Monitor Indicators")
        self.monitor_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.monitor_btn.setEnabled(True)
        
        self.save_state()  # Auto-save when trading stops
        
        self.start_btn.setText("Start Trading")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.start_btn.setEnabled(True)
        
        if not stopped_anything:
            self.add_status("Nothing to stop")
    
    def save_state(self):
        """Save current configuration, signal queue, and trading state"""
        try:
            config = self.get_config()
            state = {
                'config': config,
                'signal_queue_conditions': [c for c in self.signal_queue.conditions if c['status'] == 'Pending'],
                'trading_active': self.trading_thread is not None,
                'monitoring_active': self.monitoring_thread is not None,
                'saved_at': datetime.now().isoformat()
            }
            
            # Save signal queue separately
            queue_file = self.state_file.parent / "signal_queue.json"
            self.signal_queue.save_to_file(str(queue_file))
            
            # Save state
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            
            logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Error saving state: {e}", exc_info=True)
    
    def load_state(self):
        """Load and restore saved configuration and signal queue"""
        try:
            # Load signal queue first
            queue_file = self.state_file.parent / "signal_queue.json"
            if queue_file.exists():
                self.signal_queue.load_from_file(str(queue_file))
                self.update_queue_table()
                logger.info(f"Loaded {len(self.signal_queue.conditions)} conditions from queue file")
            
            # Load state
            if not self.state_file.exists():
                logger.debug(f"State file {self.state_file} does not exist, starting fresh")
                return
            
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Restore configuration
            if 'config' in state:
                config = state['config']
                # Restore UI values from config
                if config.get('symbol'):
                    index = self.symbol_combo.findText(config['symbol'], Qt.MatchFlag.MatchFixedString)
                    if index >= 0:
                        self.symbol_combo.setCurrentIndex(index)
                    else:
                        self.symbol_combo.setCurrentText(config['symbol'])
                
                # Restore timeframe
                timeframe_map = {
                    mt5.TIMEFRAME_M1: "M1",
                    mt5.TIMEFRAME_M5: "M5",
                    mt5.TIMEFRAME_M15: "M15",
                    mt5.TIMEFRAME_M30: "M30",
                    mt5.TIMEFRAME_H1: "H1",
                    mt5.TIMEFRAME_H4: "H4",
                    mt5.TIMEFRAME_D1: "D1",
                }
                if 'timeframe' in config:
                    tf_str = timeframe_map.get(config['timeframe'], "M15")
                    index = self.timeframe_combo.findText(tf_str)
                    if index >= 0:
                        self.timeframe_combo.setCurrentIndex(index)
                
                # Restore other settings
                if 'quantity' in config:
                    self.quantity_spin.setValue(config['quantity'])
                if 'check_interval' in config:
                    self.check_interval.setValue(config['check_interval'])
                if 'sr_min_touches' in config:
                    self.sr_min_touches.setValue(config['sr_min_touches'])
                if 'sr_strength' in config:
                    self.sr_strength.setValue(config['sr_strength'])
                if 'sr_breakout_confirmation' in config:
                    self.sr_breakout_confirmation.setValue(config['sr_breakout_confirmation'])
                if 'sr_resistance_breakout_buy' in config:
                    self.sr_resistance_breakout_buy.setChecked(config['sr_resistance_breakout_buy'])
                if 'sr_support_breakdown_sell' in config:
                    self.sr_support_breakdown_sell.setChecked(config['sr_support_breakdown_sell'])
                if 'sl_tp_method' in config:
                    index = self.sl_tp_method_combo.findText(config['sl_tp_method'])
                    if index >= 0:
                        self.sl_tp_method_combo.setCurrentIndex(index)
                
                # Restore trailing SL settings
                if 'enable_trailing_sl' in config:
                    self.enable_trailing_sl.setChecked(config['enable_trailing_sl'])
                if 'trailing_sl_gap' in config and config['trailing_sl_gap']:
                    self.trailing_sl_gap.setValue(config['trailing_sl_gap'])
                
                # Restore profit lock settings
                if 'enable_profit_lock' in config:
                    self.enable_profit_lock.setChecked(config['enable_profit_lock'])
                if 'profit_lock_trigger' in config and config['profit_lock_trigger']:
                    self.profit_lock_trigger.setValue(config['profit_lock_trigger'])
                if 'profit_lock_value' in config and config['profit_lock_value']:
                    self.profit_lock_value.setValue(config['profit_lock_value'])
                if 'profit_trail_step' in config and config['profit_trail_step']:
                    self.profit_trail_step.setValue(config['profit_trail_step'])
                if 'profit_trail_amount' in config and config['profit_trail_amount']:
                    self.profit_trail_amount.setValue(config['profit_trail_amount'])
                
                logger.info("Configuration restored from saved state")
            
            # Note: We don't auto-start trading/monitoring on load to avoid unwanted trades
            # User must manually start if they want to resume
            
        except Exception as e:
            logger.error(f"Error loading state: {e}", exc_info=True)
    
    def on_signal_generated(self, signal: str, quantity: float, sl: float, tp: float):
        """Handle signal generation with deduplication"""
        config = self.get_config()
        symbol = config['symbol']
        
        # Create a unique key for this signal (signal type + level price approximation)
        # We'll use SL/TP to approximate the level
        if signal == "BUY":
            level_price = sl * 1.01  # Approximate resistance level
        else:
            level_price = sl * 0.99  # Approximate support level
        
        signal_key = (signal, round(level_price, 5))
        
        # Check if we've already processed this signal recently
        if signal_key in self.last_signal_per_level:
            # Check if enough time has passed (e.g., 60 seconds)
            # For now, we'll just skip duplicates
            logger.debug(f"Skipping duplicate signal: {signal} at level {level_price:.5f}")
            return
        
        # Track this signal
        self.last_signal_per_level[signal_key] = datetime.now()
        
        # Clean up old signals (older than 5 minutes)
        current_time = datetime.now()
        keys_to_remove = []
        for key, timestamp in self.last_signal_per_level.items():
            if (current_time - timestamp).total_seconds() > 300:  # 5 minutes
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self.last_signal_per_level[key]
        
        # Direct trade execution via MT5
        try:
            # Get current price for the symbol
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                self.add_status(f"✗ Failed to get price for {symbol}")
                return
            
            # Determine entry price based on signal type
            if signal == "BUY":
                entry_price = tick.ask
                order_type = mt5.ORDER_TYPE_BUY
            else:  # SELL
                entry_price = tick.bid
                order_type = mt5.ORDER_TYPE_SELL
            
            # Place order directly via MT5
            result = self.mt5.place_order(
                symbol=symbol,
                order_type=order_type,
                volume=quantity,
                price=0.0,  # Market order
                sl=sl,
                tp=tp,
                comment=f"Custom Indicator {signal} - {datetime.now().strftime('%H:%M:%S')}"
            )
            
            if result and result.get('success'):
                order_ticket = result.get('order', 0)
                self.add_status(f"✓ {signal} order placed successfully - Ticket: {order_ticket}")
                
                # Register position for trailing SL/profit lock if enabled
                if order_ticket and (config.get('enable_trailing_sl', False) or config.get('enable_profit_lock', False)):
                    entry_data = {
                        'entry_price': entry_price,
                        'entry_time': datetime.now(),
                        'entry_type': signal,
                        'symbol': symbol,
                        'volume': quantity,
                        'enable_trailing_sl': config.get('enable_trailing_sl', False),
                        'trailing_sl_gap': config.get('trailing_sl_gap', 0.001),
                        'enable_profit_lock': config.get('enable_profit_lock', False),
                        'profit_lock_trigger': config.get('profit_lock_trigger', 100.0),
                        'profit_lock_value': config.get('profit_lock_value', 50.0),
                        'profit_trail_step': config.get('profit_trail_step', 100.0),
                        'profit_trail_amount': config.get('profit_trail_amount', 50.0),
                        'exit_conditions': {},
                    }
                    self.exit_manager.register_position(order_ticket, entry_data)
                    logger.info(f"Registered position {order_ticket} for trailing SL/profit lock")
            else:
                error_msg = result.get('comment', 'Unknown error') if result else 'Order placement failed'
                retcode = result.get('retcode', 0) if result else 0
                self.add_status(f"✗ Failed to place {signal} order: {error_msg} (Code: {retcode})")
                QMessageBox.warning(
                    self,
                    "Order Execution Failed",
                    f"Order execution failed:\n\n{error_msg}\n\nReturn Code: {retcode}"
                )
        except Exception as e:
            error_msg = f"Error placing order: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.add_status(f"✗ {error_msg}")
            QMessageBox.critical(self, "Error", error_msg)
        
        # Add to history table
        row = self.history_table.rowCount()
        self.history_table.insertRow(row)
        
        self.history_table.setItem(row, 0, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
        self.history_table.setItem(row, 1, QTableWidgetItem(symbol))
        
        action_item = QTableWidgetItem(signal)
        if signal == "BUY":
            action_item.setForeground(QColor("#4CAF50"))
        else:
            action_item.setForeground(QColor("#f44336"))
        self.history_table.setItem(row, 2, action_item)
        
        self.history_table.setItem(row, 3, QTableWidgetItem(f"{quantity:.2f}"))
        self.history_table.setItem(row, 4, QTableWidgetItem(f"{sl:.5f}"))
        self.history_table.setItem(row, 5, QTableWidgetItem(f"{tp:.5f}"))
    
    def on_status_update(self, message: str):
        """Handle status update"""
        self.add_status(message)
    
    def on_indicator_values_updated(self, values: Dict[str, float]):
        """Handle indicator values update - debounced"""
        logger.debug(f"Received indicator values update: {values}")
        
        # Update labels immediately (lightweight) with proper formatting
        for key, label in self.indicator_values_labels.items():
            if key in values:
                value = values[key]
                # Handle string values like "--"
                if isinstance(value, str):
                    formatted_value = value
                elif isinstance(value, (int, float)):
                    # Format based on the type of value
                    if key in ['Current Price', 'Nearest Support', 'Nearest Resistance', 'Previous Open', 'Previous High', 'Previous Low', 'Previous Close']:
                        # Prices: 5 decimal places
                        formatted_value = f"{value:.5f}"
                    elif key in ['Support Strength', 'Resistance Strength', 'Distance %']:
                        # Percentages/strength: 2 decimal places
                        formatted_value = f"{value:.2f}"
                    elif key in ['Support Touches', 'Resistance Touches', 'Total Support Levels', 'Total Resistance Levels']:
                        # Integers: no decimals
                        formatted_value = f"{int(value)}"
                    else:
                        # Default: 2 decimal places
                        formatted_value = f"{value:.2f}"
                else:
                    formatted_value = str(value)
                label.setText(formatted_value)
            else:
                label.setText("--")
            label.setVisible(True)
        
        # Update OHLC labels in configuration tab if they exist
        if 'Previous Open' in values and hasattr(self, 'ohlc_open_label'):
            self.ohlc_open_label.setText(f"{values['Previous Open']:.5f}")
        if 'Previous High' in values and hasattr(self, 'ohlc_high_label'):
            self.ohlc_high_label.setText(f"{values['Previous High']:.5f}")
        if 'Previous Low' in values and hasattr(self, 'ohlc_low_label'):
            self.ohlc_low_label.setText(f"{values['Previous Low']:.5f}")
        if 'Previous Close' in values and hasattr(self, 'ohlc_close_label'):
            self.ohlc_close_label.setText(f"{values['Previous Close']:.5f}")
        if 'OHLC Session' in values and hasattr(self, 'ohlc_session_label'):
            self.ohlc_session_label.setText(str(values['OHLC Session']))
        
        # Store values and start debounce timer for heavy operations
        self.pending_values = values
        self.update_timer.start(500)  # 500ms debounce
    
    def _perform_table_update(self):
        """Perform actual table updates (called after debounce)"""
        if self.pending_values:
            # Update tables
            self.update_all_levels_table(self.pending_values)
            self.update_nearby_levels_table(self.pending_values)
            # Update dropdowns
            self.update_entry_level_dropdowns(self.pending_values)
            self.pending_values = None
    
    def update_entry_level_dropdowns(self, values: Dict[str, Any]):
        """Populate entry condition dropdowns from calculated levels"""
        all_supports = values.get('All Supports', [])
        all_resistances = values.get('All Resistances', [])
        current_price = values.get('Current Price', 0)
        
        # Store current selections
        current_resistance_price = self._get_selected_resistance_price()
        current_support_price = self._get_selected_support_price()
        
        # Populate resistance dropdown
        self.resistance_dropdown.blockSignals(True)
        self.resistance_dropdown.clear()
        self.resistance_dropdown.addItem("Any", None)
        
        # Sort resistances by distance (nearest first)
        resistances_sorted = sorted(all_resistances, key=lambda x: x.get('distance_pct', 999))
        for resistance in resistances_sorted:
            price = resistance['price']
            strength = resistance.get('strength', 0)
            touches = resistance.get('touches', 0)
            distance_pct = resistance.get('distance_pct', 0)
            display_text = f"{price:.5f} (Str: {strength:.2f}, Touch: {touches}, Dist: {distance_pct:.2f}%)"
            self.resistance_dropdown.addItem(display_text, price)
        
        # Restore selection if it still exists
        if current_resistance_price is not None:
            for i in range(self.resistance_dropdown.count()):
                if self.resistance_dropdown.itemData(i) == current_resistance_price:
                    self.resistance_dropdown.setCurrentIndex(i)
                    break
        
        self.resistance_dropdown.blockSignals(False)
        
        # Populate support dropdown
        self.support_dropdown.blockSignals(True)
        self.support_dropdown.clear()
        self.support_dropdown.addItem("Any", None)
        
        # Sort supports by distance (nearest first)
        supports_sorted = sorted(all_supports, key=lambda x: x.get('distance_pct', 999))
        for support in supports_sorted:
            price = support['price']
            strength = support.get('strength', 0)
            touches = support.get('touches', 0)
            distance_pct = support.get('distance_pct', 0)
            display_text = f"{price:.5f} (Str: {strength:.2f}, Touch: {touches}, Dist: {distance_pct:.2f}%)"
            self.support_dropdown.addItem(display_text, price)
        
        # Restore selection if it still exists
        if current_support_price is not None:
            for i in range(self.support_dropdown.count()):
                if self.support_dropdown.itemData(i) == current_support_price:
                    self.support_dropdown.setCurrentIndex(i)
                    break
        
        self.support_dropdown.blockSignals(False)
    
    def update_all_levels_table(self, values: Dict[str, Any]):
        """Update the all support/resistance levels table"""
        self.all_levels_table.setSortingEnabled(False)
        self.all_levels_table.setRowCount(0)
        
        # Get all supports and resistances
        all_supports = values.get('All Supports', [])
        all_resistances = values.get('All Resistances', [])
        current_price = values.get('Current Price', 0)
        
        # Combine and sort by distance
        all_levels = []
        for resistance in all_resistances:
            all_levels.append(('RESISTANCE', resistance))
        for support in all_supports:
            all_levels.append(('SUPPORT', support))
        
        # Sort by distance percentage (nearest first)
        all_levels.sort(key=lambda x: x[1].get('distance_pct', 999))
        
        # Add to table
        for level_type, level in all_levels:
            row = self.all_levels_table.rowCount()
            self.all_levels_table.insertRow(row)
            
            # Type
            type_item = QTableWidgetItem(level_type)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            if level_type == 'RESISTANCE':
                type_item.setForeground(QColor("#f44336"))
            else:
                type_item.setForeground(QColor("#4CAF50"))
            type_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            self.all_levels_table.setItem(row, 0, type_item)
            
            # Price
            price = level['price']
            price_item = QTableWidgetItem(f"{price:.5f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if level_type == 'RESISTANCE':
                price_item.setForeground(QColor("#f44336"))
            else:
                price_item.setForeground(QColor("#4CAF50"))
            self.all_levels_table.setItem(row, 1, price_item)
            
            # Strength
            strength_item = QTableWidgetItem(f"{level.get('strength', 0):.2f}")
            strength_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.all_levels_table.setItem(row, 2, strength_item)
            
            # Touches
            touches_item = QTableWidgetItem(str(level.get('touches', 0)))
            touches_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.all_levels_table.setItem(row, 3, touches_item)
            
            # Distance %
            distance_pct = level.get('distance_pct', 0)
            distance_item = QTableWidgetItem(f"{distance_pct:.2f}%")
            distance_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.all_levels_table.setItem(row, 4, distance_item)
            
            # Method
            methods = level.get('methods', ['pivot'])
            method_str = ', '.join(methods) if isinstance(methods, list) else str(methods)
            method_item = QTableWidgetItem(method_str)
            method_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            self.all_levels_table.setItem(row, 5, method_item)
            
            # Confluence
            confluence = level.get('confluence_score', 0.0)
            confluence_item = QTableWidgetItem(f"{confluence:.2f}")
            confluence_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if confluence > 0.5:
                confluence_item.setForeground(QColor("#FFD700"))
                confluence_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            self.all_levels_table.setItem(row, 6, confluence_item)
            
            # Timeframe
            timeframe = level.get('timeframe', 'daily')
            timeframe_item = QTableWidgetItem(str(timeframe))
            timeframe_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.all_levels_table.setItem(row, 7, timeframe_item)
            
            # Reversed
            reversed_status = "Yes" if level.get('reversed', False) else "No"
            reversed_item = QTableWidgetItem(reversed_status)
            reversed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            if level.get('reversed', False):
                reversed_item.setForeground(QColor("#FF9800"))
                reversed_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            self.all_levels_table.setItem(row, 8, reversed_item)
        
        self.all_levels_table.setSortingEnabled(True)
        # Ensure minimum column widths are maintained
        self.all_levels_table.setColumnWidth(0, max(90, self.all_levels_table.columnWidth(0)))
        self.all_levels_table.setColumnWidth(1, max(100, self.all_levels_table.columnWidth(1)))
        self.all_levels_table.setColumnWidth(2, max(80, self.all_levels_table.columnWidth(2)))
        self.all_levels_table.setColumnWidth(3, max(70, self.all_levels_table.columnWidth(3)))
        self.all_levels_table.setColumnWidth(4, max(90, self.all_levels_table.columnWidth(4)))
        self.all_levels_table.setColumnWidth(5, max(100, self.all_levels_table.columnWidth(5)))
        self.all_levels_table.setColumnWidth(6, max(90, self.all_levels_table.columnWidth(6)))
        self.all_levels_table.setColumnWidth(7, max(90, self.all_levels_table.columnWidth(7)))
        self.all_levels_table.setColumnWidth(8, max(80, self.all_levels_table.columnWidth(8)))
    
    def update_nearby_levels_table(self, values: Dict[str, Any]):
        """Update the nearby support/resistance levels table (sorted by distance)"""
        self.nearby_levels_table.setSortingEnabled(False)
        self.nearby_levels_table.setRowCount(0)
        
        # Get all supports and resistances
        all_supports = values.get('All Supports', [])
        all_resistances = values.get('All Resistances', [])
        current_price = values.get('Current Price', 0)
        
        # Combine and sort by distance (nearest first, limit to top 10)
        nearby_levels = []
        for resistance in all_resistances:
            nearby_levels.append(('RESISTANCE', resistance))
        for support in all_supports:
            nearby_levels.append(('SUPPORT', support))
        
        # Sort by distance and take top 10
        nearby_levels.sort(key=lambda x: x[1].get('distance_pct', 999))
        nearby_levels = nearby_levels[:10]
        
        # Add to table
        for level_type, level in nearby_levels:
            row = self.nearby_levels_table.rowCount()
            self.nearby_levels_table.insertRow(row)
            
            # Type
            type_item = QTableWidgetItem(level_type)
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            if level_type == 'RESISTANCE':
                type_item.setForeground(QColor("#f44336"))
            else:
                type_item.setForeground(QColor("#4CAF50"))
            type_item.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            self.nearby_levels_table.setItem(row, 0, type_item)
            
            # Price
            price = level['price']
            price_item = QTableWidgetItem(f"{price:.5f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if level_type == 'RESISTANCE':
                price_item.setForeground(QColor("#f44336"))
            else:
                price_item.setForeground(QColor("#4CAF50"))
            self.nearby_levels_table.setItem(row, 1, price_item)
            
            # Strength
            strength_item = QTableWidgetItem(f"{level.get('strength', 0):.2f}")
            strength_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.nearby_levels_table.setItem(row, 2, strength_item)
            
            # Touches
            touches_item = QTableWidgetItem(str(level.get('touches', 0)))
            touches_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            self.nearby_levels_table.setItem(row, 3, touches_item)
            
            # Distance %
            distance_pct = level.get('distance_pct', 0)
            distance_item = QTableWidgetItem(f"{distance_pct:.2f}%")
            distance_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.nearby_levels_table.setItem(row, 4, distance_item)
        
        self.nearby_levels_table.setSortingEnabled(True)
        # Ensure minimum column widths are maintained
        self.nearby_levels_table.setColumnWidth(0, max(100, self.nearby_levels_table.columnWidth(0)))
        self.nearby_levels_table.setColumnWidth(1, max(120, self.nearby_levels_table.columnWidth(1)))
        self.nearby_levels_table.setColumnWidth(2, max(100, self.nearby_levels_table.columnWidth(2)))
        self.nearby_levels_table.setColumnWidth(3, max(90, self.nearby_levels_table.columnWidth(3)))
        self.nearby_levels_table.setColumnWidth(4, max(110, self.nearby_levels_table.columnWidth(4)))
    
    def add_status(self, message: str):
        """Add status message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")
    
    def on_symbol_changed(self, text: str):
        """Handle symbol text change - auto-map if possible"""
        if not text or len(text) < 3:
            return
        
        # Try to find the symbol automatically
        actual_symbol = self.symbol_mapper.find_symbol(text)
        if actual_symbol and actual_symbol.upper() != text.upper():
            # Show a tooltip or status message about the mapping
            self.add_status(f"Symbol '{text}' will be mapped to '{actual_symbol}'")
    
    def map_symbol(self):
        """Manually map a symbol"""
        requested_symbol = self.symbol_combo.currentText().strip().upper()
        if not requested_symbol:
            QMessageBox.warning(self, "No Symbol", "Please enter a symbol name")
            return
        
        # Try to find the symbol
        actual_symbol = self.symbol_mapper.find_symbol(requested_symbol)
        
        if actual_symbol:
            if actual_symbol.upper() != requested_symbol:
                # Ask user to confirm mapping
                reply = QMessageBox.question(
                    self,
                    "Symbol Mapping",
                    f"Symbol '{requested_symbol}' will be mapped to '{actual_symbol}'.\n\n"
                    f"Save this mapping for future use?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.symbol_mapper.add_custom_mapping(requested_symbol, actual_symbol)
                    self.add_status(f"Saved mapping: {requested_symbol} -> {actual_symbol}")
                
                # Update combo box to show actual symbol
                self.symbol_combo.setCurrentText(actual_symbol)
            else:
                QMessageBox.information(self, "Symbol Found", f"Symbol '{requested_symbol}' exists in MT5")
        else:
            # Show similar symbols
            similar = self.symbol_mapper.get_similar_symbols(requested_symbol, limit=10)
            if similar:
                similar_str = "\n".join(similar[:10])
                QMessageBox.warning(
                    self,
                    "Symbol Not Found",
                    f"Symbol '{requested_symbol}' not found in MT5.\n\n"
                    f"Similar symbols available:\n{similar_str}\n\n"
                    f"Please select one from the list or add it manually."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Symbol Not Found",
                    f"Symbol '{requested_symbol}' not found in MT5.\n\n"
                    f"Please check:\n"
                    f"1. Symbol name is correct\n"
                    f"2. Symbol is available in your broker\n"
                    f"3. Symbol is added to Market Watch in MT5"
                )
    
    def add_symbol_to_list(self):
        """Add current symbol to active symbols list"""
        symbol = self.symbol_combo.currentText().strip().upper()
        if not symbol:
            QMessageBox.warning(self, "No Symbol", "Please enter a symbol name")
            return
        
        # Map symbol if needed
        actual_symbol = self.symbol_mapper.find_symbol(symbol)
        if not actual_symbol:
            QMessageBox.warning(self, "Symbol Not Found", f"Symbol '{symbol}' not found in MT5")
            return
        
        # Use mapped symbol
        symbol = actual_symbol
        
        # Check if already in list
        if symbol in self.active_symbols:
            QMessageBox.information(self, "Already Added", f"Symbol '{symbol}' is already in the monitoring list")
            return
        
        # Add to list
        self.active_symbols.append(symbol)
        self.active_symbols_list.addItem(symbol)
        self.add_status(f"Added {symbol} to monitoring list")
        self.save_state()  # Save state when symbols change
    
    def remove_selected_symbol(self):
        """Remove selected symbol from active symbols list"""
        current_text = self.active_symbols_list.currentText()
        if not current_text:
            QMessageBox.warning(self, "No Selection", "Please select a symbol to remove")
            return
        
        if current_text in self.active_symbols:
            self.active_symbols.remove(current_text)
            index = self.active_symbols_list.findText(current_text)
            if index >= 0:
                self.active_symbols_list.removeItem(index)
            self.add_status(f"Removed {current_text} from monitoring list")
            self.save_state()  # Save state when symbols change
    
    def load_available_symbols(self):
        """Load available symbols from MT5"""
        try:
            if not self.mt5 or not self.mt5.is_connected():
                QMessageBox.warning(self, "Not Connected", "Please connect to MT5 first")
                return
            
            symbols = self.mt5.get_available_symbols()
            if symbols:
                self.symbol_combo.clear()
                # Add common symbols first
                common_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'XAUUSDM', 
                                 'EURJPY', 'AUDUSD', 'USDCAD', 'EURGBP', 'NZDUSD']
                for symbol in common_symbols:
                    if symbol in symbols:
                        self.symbol_combo.addItem(symbol)
                
                # Add separator if we have common symbols
                if common_symbols:
                    self.symbol_combo.insertSeparator(len(common_symbols))
                
                # Add all other symbols
                for symbol in symbols:
                    if symbol not in common_symbols:
                        self.symbol_combo.addItem(symbol)
                
                self.add_status(f"Loaded {len(symbols)} available symbols")
            else:
                QMessageBox.warning(self, "No Symbols", "No symbols found. Please check your MT5 connection and broker account.")
        except Exception as e:
            error_msg = f"Error loading symbols: {str(e)}"
            self.add_status(error_msg)
            logger.error(f"Error loading symbols: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", error_msg)

