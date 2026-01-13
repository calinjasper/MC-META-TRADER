"""
Metrics Calculator
Calculates comprehensive performance metrics from trade history
"""

from typing import List, Dict, Optional
import math
from datetime import datetime, timedelta


class Trade:
    """Represents a single trade"""
    
    def __init__(
        self,
        entry_time: datetime,
        exit_time: datetime,
        entry_price: float,
        exit_price: float,
        direction: str,  # "BUY" or "SELL"
        lot_size: float,
        pnl: float,
        commission: float = 0.0,
        slippage: float = 0.0,
        entry_condition: Optional[str] = None,
        entry_condition_met_at: Optional[datetime] = None,
        entry_condition_met_price: Optional[float] = None,
        exit_reason: Optional[str] = None,
        sl_price: Optional[float] = None,
        tp_price: Optional[float] = None,
        sl_hit_price: Optional[float] = None,
        tp_hit_price: Optional[float] = None
    ):
        self.entry_time = entry_time
        self.exit_time = exit_time
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.direction = direction
        self.lot_size = lot_size
        self.pnl = pnl
        self.commission = commission
        self.slippage = slippage
        self.duration = (exit_time - entry_time).total_seconds()
        self.is_win = pnl > 0
        self.is_loss = pnl < 0
        self.entry_condition = entry_condition  # Description of condition that triggered entry
        self.entry_condition_met_at = entry_condition_met_at or entry_time
        self.entry_condition_met_price = entry_condition_met_price or entry_price
        self.exit_reason = exit_reason or "Signal Reversal"
        self.sl_price = sl_price  # Stop loss price
        self.tp_price = tp_price  # Take profit price
        self.sl_hit_price = sl_hit_price  # Actual price when SL was hit
        self.tp_hit_price = tp_hit_price  # Actual price when TP was hit


class MetricsCalculator:
    """Calculates comprehensive backtest metrics"""
    
    def __init__(self, initial_capital: float = 10000.0):
        """
        Initialize metrics calculator
        
        Args:
            initial_capital: Starting capital for the backtest
        """
        self.initial_capital = initial_capital
    
    def calculate_metrics(self, trades: List[Trade], equity_curve: List[Dict] = None) -> Dict:
        """
        Calculate comprehensive performance metrics
        
        Args:
            trades: List of Trade objects
            equity_curve: List of {time, equity} dictionaries for drawdown calculation
            
        Returns:
            Dictionary with all calculated metrics
        """
        if not trades:
            return self._empty_metrics()
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.is_win]
        losing_trades = [t for t in trades if t.is_loss]
        
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        win_rate = (num_wins / total_trades * 100) if total_trades > 0 else 0
        
        # P/L metrics
        total_pnl = sum(t.pnl for t in trades)
        gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
        
        avg_win = gross_profit / num_wins if num_wins > 0 else 0
        avg_loss = gross_loss / num_losses if num_losses > 0 else 0
        avg_trade = total_pnl / total_trades if total_trades > 0 else 0
        
        # Profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0)
        
        # Largest win/loss
        largest_win = max((t.pnl for t in winning_trades), default=0)
        largest_loss = min((t.pnl for t in losing_trades), default=0)
        
        # Win/Loss streaks
        win_streak, loss_streak = self._calculate_streaks(trades)
        
        # Average trade duration
        avg_duration = sum(t.duration for t in trades) / total_trades if total_trades > 0 else 0
        
        # ROI
        final_equity = self.initial_capital + total_pnl
        roi = ((final_equity - self.initial_capital) / self.initial_capital * 100) if self.initial_capital > 0 else 0
        
        # Drawdown metrics
        max_drawdown, max_drawdown_percent = self._calculate_drawdown(equity_curve or [])
        
        # Sharpe ratio (simplified - using returns)
        sharpe_ratio = self._calculate_sharpe_ratio(trades)
        
        # Expectancy
        expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * avg_loss)
        
        return {
            # Basic metrics
            "total_trades": total_trades,
            "winning_trades": num_wins,
            "losing_trades": num_losses,
            "win_rate": round(win_rate, 2),
            
            # P/L metrics
            "total_pnl": round(total_pnl, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "net_profit": round(total_pnl, 2),
            
            # Average metrics
            "average_win": round(avg_win, 2),
            "average_loss": round(avg_loss, 2),
            "average_trade": round(avg_trade, 2),
            
            # Advanced metrics
            "profit_factor": round(profit_factor, 2),
            "largest_win": round(largest_win, 2),
            "largest_loss": round(largest_loss, 2),
            "win_streak": win_streak,
            "loss_streak": loss_streak,
            "average_duration_seconds": round(avg_duration, 2),
            "average_duration_hours": round(avg_duration / 3600, 2),
            
            # Capital metrics
            "initial_capital": round(self.initial_capital, 2),
            "final_equity": round(final_equity, 2),
            "roi": round(roi, 2),
            
            # Risk metrics
            "max_drawdown": round(max_drawdown, 2),
            "max_drawdown_percent": round(max_drawdown_percent, 2),
            "sharpe_ratio": round(sharpe_ratio, 3),
            "expectancy": round(expectancy, 2),
        }
    
    def _calculate_streaks(self, trades: List[Trade]) -> tuple[int, int]:
        """Calculate maximum win and loss streaks"""
        if not trades:
            return 0, 0
        
        max_win_streak = 0
        max_loss_streak = 0
        current_win_streak = 0
        current_loss_streak = 0
        
        for trade in trades:
            if trade.is_win:
                current_win_streak += 1
                current_loss_streak = 0
                max_win_streak = max(max_win_streak, current_win_streak)
            elif trade.is_loss:
                current_loss_streak += 1
                current_win_streak = 0
                max_loss_streak = max(max_loss_streak, current_loss_streak)
        
        return max_win_streak, max_loss_streak
    
    def _calculate_drawdown(self, equity_curve: List[Dict]) -> tuple[float, float]:
        """
        Calculate maximum drawdown
        
        Args:
            equity_curve: List of {time, equity} dictionaries
            
        Returns:
            Tuple of (max_drawdown_amount, max_drawdown_percent)
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0.0, 0.0
        
        max_equity = self.initial_capital
        max_drawdown = 0.0
        max_drawdown_percent = 0.0
        
        for point in equity_curve:
            equity = point.get("equity", self.initial_capital)
            if equity > max_equity:
                max_equity = equity
            
            drawdown = max_equity - equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                if max_equity > 0:
                    max_drawdown_percent = (drawdown / max_equity) * 100
        
        return max_drawdown, max_drawdown_percent
    
    def _calculate_sharpe_ratio(self, trades: List[Trade], risk_free_rate: float = 0.0) -> float:
        """
        Calculate Sharpe ratio (simplified version)
        
        Args:
            trades: List of trades
            risk_free_rate: Risk-free rate (default: 0)
            
        Returns:
            Sharpe ratio
        """
        if not trades or len(trades) < 2:
            return 0.0
        
        # Calculate returns
        returns = [t.pnl / self.initial_capital for t in trades]
        
        if not returns:
            return 0.0
        
        # Calculate mean return
        mean_return = sum(returns) / len(returns)
        
        # Calculate standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return 0.0
        
        # Sharpe ratio = (mean return - risk free rate) / std dev
        sharpe = (mean_return - risk_free_rate) / std_dev
        
        # Annualize (assuming daily returns, multiply by sqrt(252))
        # For simplicity, we'll use the raw Sharpe ratio
        return sharpe
    
    def _empty_metrics(self) -> Dict:
        """Return empty metrics structure"""
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "net_profit": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "average_trade": 0.0,
            "profit_factor": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "win_streak": 0,
            "loss_streak": 0,
            "average_duration_seconds": 0.0,
            "average_duration_hours": 0.0,
            "initial_capital": round(self.initial_capital, 2),
            "final_equity": round(self.initial_capital, 2),
            "roi": 0.0,
            "max_drawdown": 0.0,
            "max_drawdown_percent": 0.0,
            "sharpe_ratio": 0.0,
            "expectancy": 0.0,
        }

