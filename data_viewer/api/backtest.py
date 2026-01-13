"""
Backtest API endpoints
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import logging

from data_viewer.backtest.indicator_loader import IndicatorLoader
from data_viewer.backtest.engine import BacktestEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

# Initialize components
indicator_loader = IndicatorLoader()
backtest_engine = BacktestEngine()


class BacktestRequest(BaseModel):
    """Backtest request model"""
    symbol: str
    start_date: str
    end_date: str
    indicator_name: str
    indicator_settings: Dict[str, Any] = {}
    position_sizing_type: str = "fixed"  # "fixed" or "percentage"
    position_size: float = 0.01
    initial_capital: float = 10000.0
    commission: float = 0.0
    slippage: float = 0.0


@router.get("/indicators")
async def list_indicators() -> List[Dict[str, Any]]:
    """
    List all available indicators
    
    Returns:
        List of indicator metadata dictionaries
    """
    try:
        indicators = indicator_loader.discover_indicators()
        return indicators
    except Exception as e:
        logger.error(f"Error listing indicators: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list indicators: {str(e)}")


@router.get("/indicator/{indicator_name}/settings")
async def get_indicator_settings(indicator_name: str) -> Dict[str, Any]:
    """
    Get settings schema for an indicator
    
    Args:
        indicator_name: Name of the indicator
        
    Returns:
        Dictionary with settings schema (parameters and defaults)
    """
    try:
        schema = indicator_loader.get_indicator_settings_schema(indicator_name)
        return schema
    except Exception as e:
        logger.error(f"Error getting indicator settings for {indicator_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get indicator settings: {str(e)}")


@router.post("/run")
async def run_backtest(request: BacktestRequest) -> Dict[str, Any]:
    """
    Run a backtest
    
    Args:
        request: Backtest request with all parameters
        
    Returns:
        Dictionary with backtest results (metrics, trades, equity_curve)
    """
    try:
        logger.info(f"Running backtest: {request.indicator_name} on {request.symbol} from {request.start_date} to {request.end_date}")
        
        results = backtest_engine.run_backtest(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            indicator_name=request.indicator_name,
            indicator_settings=request.indicator_settings,
            position_sizing_type=request.position_sizing_type,
            position_size=request.position_size,
            initial_capital=request.initial_capital,
            commission=request.commission,
            slippage=request.slippage
        )
        
        return results
    except Exception as e:
        logger.error(f"Error running backtest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to run backtest: {str(e)}")

