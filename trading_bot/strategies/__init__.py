"""Strategy registry and naming conventions.

Each strategy resides in a ``<key>_strategy.py`` module and exposes a
``<key>_strategy`` function.  The registry maps short, lowercase keys to
these functions to keep the naming consistent across the codebase.
"""

from .sma_strategy import sma_strategy
from .rsi_strategy import rsi_strategy
from .macd_strategy import macd_strategy
from .bbands_strategy import bbands_strategy
from .confluence_strategy import confluence_strategy

STRATEGY_REGISTRY = {
    "sma": sma_strategy,
    "rsi": rsi_strategy,
    "macd": macd_strategy,
    "bbands": bbands_strategy,
    "confluence": confluence_strategy,
}


def list_strategies():
    return list(STRATEGY_REGISTRY.keys())
