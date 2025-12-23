"""
Chart Renderer Classes
Separated indicator rendering logic for better maintainability
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pyqtgraph as pg
from PyQt6.QtCore import Qt

from ..indicators.ema import EMA
from ..strategy.supertrend_strategy import compute_supertrend
from ..strategy.smc_strategy import _fractal_pivot_high, _fractal_pivot_low

logger = logging.getLogger(__name__)


class IndicatorRenderer:
    """Base class for indicator renderers"""
    
    def __init__(self, chart_widget):
        self.chart_widget = chart_widget
        self.chart = chart_widget.chart
        self.items = []
        self.payload = []

    def clear(self):
        for item in self.items:
            try:
                self.chart.removeItem(item)
            except Exception:
                pass
        self.items.clear()
        self.payload.clear()

    def _normalize_time(self, value):
        if isinstance(value, datetime):
            return float(value.timestamp())
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return float(value)
        except Exception:
            return None

    def _build_points(self, times, values):
        points = []
        min_len = min(len(times), len(values))
        for i in range(min_len):
            ts = self._normalize_time(times[i])
            val = values[i]
            if ts is None or val is None:
                continue
            try:
                points.append({'time': ts, 'value': float(val)})
            except Exception:
                continue
        return points

    def _record_payload(self, name, color, times, values, width=2.0):
        points = self._build_points(times, values)
        if points:
            self.payload.append({
                'name': name,
                'color': color,
                'type': 'line',
                'width': width,
                'points': points,
            })

    def get_payload(self):
        return list(self.payload)


class VWAPRenderer(IndicatorRenderer):
    """Renders VWAP indicator and bands"""
    
    def render(self, times: List[datetime], rates: List[Dict], 
               vwap_values: List[float], bands_dict: Dict,
               show_bands: bool, std_levels: List[float]):
        """
        Render VWAP line and bands
        
        Args:
            times: List of datetime objects
            rates: List of rate dictionaries
            vwap_values: List of VWAP values
            bands_dict: Dictionary mapping std_dev to (upper_bands, lower_bands)
            show_bands: Whether to show bands
            std_levels: List of standard deviation levels
        """
        self.clear()
        
        if not vwap_values or not times:
            return
        
        times_ts = self._to_timestamps(times)
        min_len = min(len(times_ts), len(vwap_values))
        
        # Filter valid values
        valid_times = []
        valid_vwap = []
        for i in range(min_len):
            if vwap_values[i] is not None and times_ts[i] is not None:
                valid_times.append(times_ts[i])
                valid_vwap.append(vwap_values[i])
        
        if not valid_times:
            return
        
        # Plot VWAP line
        vwap_line = self.chart.plot(
            valid_times, valid_vwap,
            pen=pg.mkPen(color='#00FFFF', width=2.5),
            name="VWAP",
            antialias=True
        )
        self.items.append(vwap_line)
        self._record_payload("VWAP", "#00FFFF", valid_times, valid_vwap, width=2.5)
        
        # Store metadata for tooltip detection
        if hasattr(self.chart_widget, 'plot_items_metadata'):
            self.chart_widget.plot_items_metadata[vwap_line] = {
                'name': 'VWAP',
                'type': 'vwap',
                'values': valid_vwap,
                'times': valid_times
            }
        
        # Plot bands if enabled
        if show_bands and bands_dict:
            upper_colors = {1.0: '#FF6B6B', 1.5: '#FF5252', 2.0: '#F44336'}
            lower_colors = {1.0: '#66BB6A', 1.5: '#4CAF50', 2.0: '#388E3C'}
            
            for std_dev in sorted(bands_dict.keys()):
                upper_bands, lower_bands = bands_dict[std_dev]
                
                # Filter valid band values
                valid_upper = []
                valid_lower = []
                valid_band_times = []
                
                min_band_len = min(len(times_ts), len(upper_bands), len(lower_bands))
                for i in range(min_band_len):
                    if (upper_bands[i] is not None and lower_bands[i] is not None and
                        times_ts[i] is not None):
                        valid_band_times.append(times_ts[i])
                        valid_upper.append(upper_bands[i])
                        valid_lower.append(lower_bands[i])
                
                if not valid_band_times:
                    continue
                
                # Calculate label offset
                if valid_upper and valid_lower:
                    price_range = max(max(valid_upper), max(valid_lower)) - min(min(valid_upper), min(valid_lower))
                    label_offset = max(price_range * 0.015, 1.0)
                else:
                    label_offset = 1.0
                
                # Upper band
                upper_line = self.chart.plot(
                    valid_band_times, valid_upper,
                    pen=pg.mkPen(color=upper_colors.get(std_dev, '#FF6B6B'), 
                               width=1.5, style=Qt.PenStyle.DashLine),
                    name=f"VWAP Upper {std_dev}STD",
                    antialias=True
                )
                self.items.append(upper_line)
                self._record_payload(f"VWAP Upper {std_dev}STD", upper_colors.get(std_dev, '#FF6B6B'),
                                     valid_band_times, valid_upper, width=1.2)
                
                # Store metadata
                if hasattr(self.chart_widget, 'plot_items_metadata'):
                    self.chart_widget.plot_items_metadata[upper_line] = {
                        'name': f'VWAP Upper {std_dev}STD',
                        'type': 'band_upper',
                        'values': valid_upper,
                        'times': valid_band_times,
                        'std_dev': std_dev
                    }
                
                # Add text label for upper band
                if valid_band_times and valid_upper:
                    from pyqtgraph import TextItem
                    last_time = valid_band_times[-1]
                    last_upper = valid_upper[-1]
                    
                    upper_label = TextItem(
                        text=f"Upper ({std_dev} STD)",
                        color=upper_colors.get(std_dev, '#FF6B6B'),
                        anchor=(1, 0)
                    )
                    upper_label.setPos(last_time, last_upper + label_offset)
                    self.chart.addItem(upper_label)
                    self.items.append(upper_label)
                
                # Lower band
                lower_line = self.chart.plot(
                    valid_band_times, valid_lower,
                    pen=pg.mkPen(color=lower_colors.get(std_dev, '#66BB6A'), 
                               width=1.5, style=Qt.PenStyle.DashLine),
                    name=f"VWAP Lower {std_dev}STD",
                    antialias=True
                )
                self.items.append(lower_line)
                self._record_payload(f"VWAP Lower {std_dev}STD", lower_colors.get(std_dev, '#66BB6A'),
                                     valid_band_times, valid_lower, width=1.2)
                
                # Store metadata
                if hasattr(self.chart_widget, 'plot_items_metadata'):
                    self.chart_widget.plot_items_metadata[lower_line] = {
                        'name': f'VWAP Lower {std_dev}STD',
                        'type': 'band_lower',
                        'values': valid_lower,
                        'times': valid_band_times,
                        'std_dev': std_dev
                    }
                
                # Add text label for lower band
                if valid_band_times and valid_lower:
                    from pyqtgraph import TextItem
                    last_time = valid_band_times[-1]
                    last_lower = valid_lower[-1]
                    
                    lower_label = TextItem(
                        text=f"Lower ({std_dev} STD)",
                        color=lower_colors.get(std_dev, '#66BB6A'),
                        anchor=(1, 1)
                    )
                    lower_label.setPos(last_time, last_lower - label_offset)
                    self.chart.addItem(lower_label)
                    self.items.append(lower_label)


class EMARenderer(IndicatorRenderer):
    """Renders EMA indicators"""
    
    def render(self, times: List[datetime], rates: List[Dict], 
               periods: List[int], colors: List[str]):
        """
        Render multiple EMA lines
        
        Args:
            times: List of datetime objects
            rates: List of rate dictionaries
            periods: List of EMA periods
            colors: List of colors for each EMA
        """
        self.clear()
        
        if not times or not rates:
            return
        
        times_ts = self._to_timestamps(times)
        
        for period, color in zip(periods, colors):
            try:
                ema_series = EMA(int(period)).calculate(rates)
                if not ema_series:
                    continue
                
                # Align and filter
                min_len = min(len(times_ts), len(ema_series))
                x_vals = []
                y_vals = []
                
                for i in range(min_len):
                    if times_ts[i] is not None and ema_series[i] is not None:
                        x_vals.append(times_ts[i])
                        y_vals.append(float(ema_series[i]))
                
                if x_vals:
                    line = self.chart.plot(
                        x_vals, y_vals,
                        pen=pg.mkPen(color=color, width=2.0),
                        name=f"EMA({period})",
                        antialias=True
                    )
                    self.items.append(line)
                    self._record_payload(f"EMA({period})", color, x_vals, y_vals, width=2.0)
            except Exception as e:
                logger.debug(f"Error rendering EMA({period}): {e}")


class SuperTrendRenderer(IndicatorRenderer):
    """Renders SuperTrend indicator"""
    
    def render(self, times: List[datetime], rates: List[Dict],
               period: int, multiplier: float, use_wilder: bool):
        """
        Render SuperTrend bands and active line
        
        Args:
            times: List of datetime objects
            rates: List of rate dictionaries
            period: ATR period
            multiplier: ATR multiplier
            use_wilder: Whether to use Wilder's ATR method
        """
        self.clear()
        
        if not times or not rates:
            return
        
        times_ts = self._to_timestamps(times)
        
        try:
            # Prepare candles
            candles = [{
                "time": r.get("time"),
                "open": float(r.get("open")),
                "high": float(r.get("high")),
                "low": float(r.get("low")),
                "close": float(r.get("close")),
            } for r in rates]
            
            trend, atr, up_final, dn_final = compute_supertrend(
                candles=candles,
                period=period,
                multiplier=multiplier,
                use_wilder_atr=use_wilder,
            )
            
            if not trend:
                return
            
            series_len = min(len(times_ts), len(trend), len(up_final), len(dn_final))
            
            def _plot_series(name: str, series: List[Optional[float]], 
                           color: str, width: float, dash: bool = False):
                x_vals = []
                y_vals = []
                for i in range(series_len):
                    if times_ts[i] is not None and series[i] is not None:
                        x_vals.append(times_ts[i])
                        y_vals.append(float(series[i]))
                
                if x_vals:
                    pen = pg.mkPen(color=color, width=width,
                                  style=Qt.PenStyle.DashLine if dash else Qt.PenStyle.SolidLine)
                    item = self.chart.plot(x_vals, y_vals, pen=pen, name=name, antialias=True)
                    self.items.append(item)
                    self._record_payload(name, color, x_vals, y_vals, width=width)
            
            # Bands (dashed)
            _plot_series("SuperTrend Upper", up_final, "#EF5350", 1.3, dash=True)
            _plot_series("SuperTrend Lower", dn_final, "#66BB6A", 1.3, dash=True)
            
            # Active line
            st_up = [None] * series_len
            st_dn = [None] * series_len
            for i in range(series_len):
                if int(trend[i]) == 1:
                    st_up[i] = dn_final[i]
                else:
                    st_dn[i] = up_final[i]
            
            _plot_series("SuperTrend UP", st_up, "#00E676", 2.4, dash=False)
            _plot_series("SuperTrend DOWN", st_dn, "#FF1744", 2.4, dash=False)
            
        except Exception as e:
            logger.debug(f"Error rendering SuperTrend: {e}")


class SMCRenderer(IndicatorRenderer):
    """Renders SMC (Smart Money Concepts) indicators"""
    
    def render(self, times: List[datetime], rates: List[Dict],
               pivot_left: int, pivot_right: int, emit_on: str):
        """
        Render SMC pivots and BOS/CHoCH markers
        
        Args:
            times: List of datetime objects
            rates: List of rate dictionaries
            pivot_left: Number of bars to left of pivot
            pivot_right: Number of bars to right of pivot
            emit_on: When to emit signals ('CHoCH', 'BOS', or 'BOTH')
        """
        self.clear()
        
        if not times or not rates:
            return
        
        times_ts = self._to_timestamps(times)
        highs = [float(r.get("high")) for r in rates]
        lows = [float(r.get("low")) for r in rates]
        closes = [float(r.get("close")) for r in rates]
        
        # Find pivots
        pivot_high_idx = []
        pivot_low_idx = []
        for i in range(pivot_left, max(pivot_left, len(highs) - pivot_right)):
            if _fractal_pivot_high(highs, i, pivot_left, pivot_right):
                pivot_high_idx.append(i)
            if _fractal_pivot_low(lows, i, pivot_left, pivot_right):
                pivot_low_idx.append(i)
        
        # Plot pivot points
        if pivot_high_idx:
            ph_times = [times_ts[i] for i in pivot_high_idx if times_ts[i] is not None]
            ph_vals = [highs[i] for i in pivot_high_idx if times_ts[i] is not None]
            if ph_times:
                ph_scatter = pg.ScatterPlotItem(
                    x=ph_times, y=ph_vals,
                    pen=pg.mkPen(color="#FFCA28", width=1),
                    brush=pg.mkBrush(color="#FFCA28"),
                    symbol="o", size=7,
                    name="SMC Pivot Highs",
                )
                self.chart.addItem(ph_scatter)
                self.items.append(ph_scatter)
        
        if pivot_low_idx:
            pl_times = [times_ts[i] for i in pivot_low_idx if times_ts[i] is not None]
            pl_vals = [lows[i] for i in pivot_low_idx if times_ts[i] is not None]
            if pl_times:
                pl_scatter = pg.ScatterPlotItem(
                    x=pl_times, y=pl_vals,
                    pen=pg.mkPen(color="#29B6F6", width=1),
                    brush=pg.mkBrush(color="#29B6F6"),
                    symbol="o", size=7,
                    name="SMC Pivot Lows",
                )
                self.chart.addItem(pl_scatter)
                self.items.append(pl_scatter)
        
        # Calculate BOS/CHoCH markers
        self._render_bos_choch(times_ts, closes, pivot_high_idx, pivot_low_idx, 
                              highs, lows, emit_on)
    
    def _render_bos_choch(self, times_ts: List[float], closes: List[float],
                         pivot_high_idx: List[int], pivot_low_idx: List[int],
                         highs: List[float], lows: List[float], emit_on: str):
        """Render BOS/CHoCH markers"""
        last_ph = None
        last_pl = None
        bias = None
        bos_up_t, bos_up_p = [], []
        bos_dn_t, bos_dn_p = [], []
        choch_up_t, choch_up_p = [], []
        choch_dn_t, choch_dn_p = [], []
        
        ph_map = {i: highs[i] for i in pivot_high_idx}
        pl_map = {i: lows[i] for i in pivot_low_idx}
        
        for i in range(len(closes)):
            if i in ph_map:
                last_ph = ph_map[i]
            if i in pl_map:
                last_pl = pl_map[i]
            
            close = closes[i]
            event = None
            direction = None
            
            if last_ph is not None and close > last_ph:
                direction = "UP"
                event = "CHoCH" if bias == "BEARISH" else ("BOS" if bias == "BULLISH" else "BOS")
            elif last_pl is not None and close < last_pl:
                direction = "DOWN"
                event = "CHoCH" if bias == "BULLISH" else ("BOS" if bias == "BEARISH" else "BOS")
            
            if event == "CHoCH":
                bias = "BULLISH" if direction == "UP" else "BEARISH"
            elif bias is None and event == "BOS":
                bias = "BULLISH" if direction == "UP" else "BEARISH"
            
            if not event or times_ts[i] is None:
                continue
            
            # Filter by emit_on setting
            if emit_on == "CHoCH" and event != "CHoCH":
                continue
            if emit_on == "BOS" and event != "BOS":
                continue
            
            # Collect markers
            if event == "BOS" and direction == "UP":
                bos_up_t.append(times_ts[i])
                bos_up_p.append(close)
            elif event == "BOS" and direction == "DOWN":
                bos_dn_t.append(times_ts[i])
                bos_dn_p.append(close)
            elif event == "CHoCH" and direction == "UP":
                choch_up_t.append(times_ts[i])
                choch_up_p.append(close)
            elif event == "CHoCH" and direction == "DOWN":
                choch_dn_t.append(times_ts[i])
                choch_dn_p.append(close)
        
        # Plot markers
        markers = [
            (bos_up_t, bos_up_p, "#B0BEC5", "t", 11, "SMC BOS UP"),
            (bos_dn_t, bos_dn_p, "#B0BEC5", "t3", 11, "SMC BOS DOWN"),
            (choch_up_t, choch_up_p, "#CE93D8", "t", 14, "SMC CHoCH UP"),
            (choch_dn_t, choch_dn_p, "#CE93D8", "t3", 14, "SMC CHoCH DOWN"),
        ]
        
        for times_list, prices_list, color, symbol, size, name in markers:
            if times_list:
                scatter = pg.ScatterPlotItem(
                    x=times_list, y=prices_list,
                    pen=pg.mkPen(color=color, width=2),
                    brush=pg.mkBrush(color=color),
                    symbol=symbol, size=size,
                    name=name,
                )
                self.chart.addItem(scatter)
                self.items.append(scatter)

