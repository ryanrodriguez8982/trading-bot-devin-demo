"""Strategy registry with metadata support.

Each strategy resides in a `<key>_strategy.py` module and exposes a
`<key>_strategy` function. The registry maps short, lowercase keys to
these functions and optional metadata to keep naming and structure consistent.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from .sma_strategy import sma_crossover_strategy
from .rsi_strategy import rsi_crossover_strategy
from .macd import macd_strategy
from .bbands import bbands_strategy
from .confluence import confluence_strategy, METADATA as CONFLUENCE_METADATA


@dataclass
class Strategy:
    """Container for a strategy function and its metadata."""
    func: Callable[..., List[dict[str, Any]]]
    metadata: Dict[str, Any] = field(default_factory=dict)


STRATEGY_REGISTRY: Dict[str, Strategy] = {
    "sma": Strategy(sma_crossover_strategy),
    "rsi": Strategy(rsi_crossover_strategy),
    "macd": Strategy(macd_strategy),
    "bbands": Strategy(bbands_strategy),
    "confluence": Strategy(confluence_strategy, CONFLUENCE_METADATA),
}


def list_strategies() -> List[str]:
    """Return the list of available strategy names."""
    return list(STRATEGY_REGISTRY.keys())


__all__ = ["Strategy", "STRATEGY_REGISTRY", "list_strategies"]
