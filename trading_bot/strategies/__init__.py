"""Dynamic strategy registry with automatic discovery.

Strategies can register themselves via the :func:`register_strategy`
decorator. When this package is imported, all modules inside
``trading_bot.strategies`` are imported so that any decorated strategies are
automatically added to :const:`STRATEGY_REGISTRY`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List
import importlib
import pkgutil


@dataclass
class Strategy:
    """Container for a strategy function and its metadata."""

    func: Callable[..., List[dict[str, Any]]]
    metadata: Dict[str, Any] = field(default_factory=dict)


# Global registry populated by the decorator below
STRATEGY_REGISTRY: Dict[str, Strategy] = {}


def register_strategy(name: str, metadata: Dict[str, Any] | None = None):
    """Decorator to register a strategy function.

    Parameters
    ----------
    name:
        Key under which the strategy will be registered.
    metadata:
        Optional metadata to associate with the strategy.
    """

    def decorator(func: Callable[..., List[dict[str, Any]]]):
        STRATEGY_REGISTRY[name] = Strategy(func, metadata or {})
        return func

    return decorator


def list_strategies() -> List[str]:
    """Return the list of available strategy names."""

    return list(STRATEGY_REGISTRY.keys())


# Automatically import all modules in this package so that any decorated
# strategies are registered upon package import.
for _finder, module_name, _ispkg in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{module_name}")


__all__ = [
    "Strategy",
    "STRATEGY_REGISTRY",
    "register_strategy",
    "list_strategies",
]
