"""Interfaces for strategy plugins.

This module defines the minimal callable interface that strategy plugins
must implement. Plugins can provide any callable that accepts a pandas
``DataFrame`` and returns a list of signal dictionaries. Using a protocol
keeps the system flexible while still giving plugin authors a clear
contract to follow.
"""

from __future__ import annotations

from typing import Any, List, Protocol

import pandas as pd


class StrategyProtocol(Protocol):
    """Callable strategy interface.

    Strategy implementations are expected to accept a ``pandas.DataFrame``
    and return a list of signal dictionaries. The exact structure of the
    signal dictionaries is left to the individual strategies, but they are
    typically expected to contain order information such as side, price and
    size.
    """

    def __call__(
        self, df: pd.DataFrame
    ) -> List[dict[str, Any]]:  # pragma: no cover
        ...


__all__ = ["StrategyProtocol"]
