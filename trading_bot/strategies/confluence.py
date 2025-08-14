"""Confluence strategy (Python 3.9–3.12 compatible).

Provides:
- confluence_strategy: function that may combine multiple member strategies.
- METADATA: dictionary with basic descriptive fields.

This minimal implementation returns no signals by default to avoid runtime errors.
It can be expanded later to aggregate signals across member strategies.
"""

from typing import Any, Dict, List, Optional

import logging
import pandas as pd

logger = logging.getLogger(__name__)

METADATA: Dict[str, Any] = {
    "name": "Confluence Strategy",
    "description": "Combines multiple member strategies and requires a quorum to act.",
    "requires": ["sma", "rsi", "macd"],
    "required_count": 2,
}


def confluence_strategy(
    df: pd.DataFrame,
    members: Optional[List[str]] = None,
    required: int = 2,
) -> List[Dict[str, Any]]:
    """Return consensus signals when multiple strategies agree.

    Minimal placeholder: returns an empty list to satisfy imports/tests.
    Compatible with Python 3.9–3.12 (uses Optional[...] instead of X | None).
    """
    # Placeholder to keep runtime safe. Real logic can be added later.
    # For example implementation, import STRATEGY_REGISTRY lazily to avoid cycles:
    # from trading_bot.strategies import STRATEGY_REGISTRY
    # ... gather/merge signals ...
    return []
