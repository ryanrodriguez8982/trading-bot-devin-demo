"""Dynamic strategy registry with automatic discovery.

Strategies can register themselves via the :func:`register_strategy`
decorator. When this package is imported, all modules inside
``trading_bot.strategies`` are imported so that any decorated strategies are
automatically added to :const:`STRATEGY_REGISTRY`.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List
import importlib
import pkgutil

from .base import StrategyProtocol


@dataclass
class Strategy:
    """Container for a strategy function and its metadata."""

    func: Callable[..., List[dict[str, Any]]]
    metadata: Dict[str, Any] = field(default_factory=dict)


# Global registry populated by the decorator below. When this module is
# reloaded (e.g., during plugin discovery in tests), we reuse the existing
# dictionary object so that external references remain valid.
STRATEGY_REGISTRY: Dict[str, Strategy] = globals().get("STRATEGY_REGISTRY", {})
STRATEGY_REGISTRY.clear()


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
    full_name = f"{__name__}.{module_name}"
    module = importlib.import_module(full_name)
    importlib.reload(module)


def load_strategy_plugins(extra_paths: List[str] | None = None) -> None:
    """Discover and import strategy plugins from external locations.

    Plugins can live in one or more directories specified via the
    ``TRADING_BOT_PLUGIN_PATH`` environment variable (a path-separated list)
    or passed explicitly via ``extra_paths``. Each module found in those
    directories is imported, allowing it to register strategies using the
    :func:`register_strategy` decorator.
    """

    paths: List[str] = []

    env_paths = os.environ.get("TRADING_BOT_PLUGIN_PATH")
    if env_paths:
        paths.extend(env_paths.split(os.pathsep))

    if extra_paths:
        paths.extend(extra_paths)

    default_path = os.path.join(os.getcwd(), "plugins")
    paths.append(default_path)

    for path in paths:
        if not os.path.isdir(path):
            continue
        # Ensure plugin path is importable
        if path not in sys.path:
            sys.path.insert(0, path)
        for _finder, module_name, _ispkg in pkgutil.iter_modules([path]):
            module = importlib.import_module(module_name)
            importlib.reload(module)


# Automatically import all modules in this package so that any decorated
# strategies are registered upon package import.
for _finder, module_name, _ispkg in pkgutil.iter_modules(__path__):
    importlib.import_module(f"{__name__}.{module_name}")

# Load external strategy plugins after built-ins have registered
load_strategy_plugins()


__all__ = [
    "Strategy",
    "STRATEGY_REGISTRY",
    "register_strategy",
    "list_strategies",
    "StrategyProtocol",
    "load_strategy_plugins",
]
