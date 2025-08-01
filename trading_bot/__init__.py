"""
Trading Bot - A cryptocurrency trading signal generator using multiple strategies.

This package provides tools for:
- Fetching cryptocurrency price data from Binance
- Generating trading signals using SMA crossover strategy
- Logging signals to database and files
- Interactive dashboard for signal visualization
"""

__version__ = "1.2.0"
__author__ = "Trading Bot Team"
__email__ = "trading-bot@example.com"

from .main import main
from .data_fetch import fetch_btc_usdt_data
from .strategy import sma_crossover_strategy
from .signal_logger import log_signals_to_db, get_signals_from_db
from .performance import compute_equity_curve

__all__ = [
    "main",
    "fetch_btc_usdt_data",
    "sma_crossover_strategy",
    "log_signals_to_db",
    "get_signals_from_db",
    "compute_equity_curve",
]
