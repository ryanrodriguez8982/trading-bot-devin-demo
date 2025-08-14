"""Trading Bot - A cryptocurrency trading signal generator using multiple strategies.

This package provides tools for:
- Fetching cryptocurrency price data from Binance
- Generating trading signals using SMA strategy
- Logging signals to database and files
- Interactive dashboard for signal visualization
"""

__version__ = "1.2.0"
__author__ = "Trading Bot Team"
__email__ = "trading-bot@example.com"

from .data_fetch import fetch_market_data
from .main import main as cli_main
from .performance import compute_equity_curve
from .portfolio import Portfolio, Position
from .risk.config import RiskConfig, get_risk_config
from .signal_logger import get_signals_from_db, log_signals_to_db
from .strategy import sma_strategy

__all__ = [
    "cli_main",
    "fetch_market_data",
    "sma_strategy",
    "log_signals_to_db",
    "get_signals_from_db",
    "compute_equity_curve",
    "get_risk_config",
    "RiskConfig",
    "Portfolio",
    "Position",
]
