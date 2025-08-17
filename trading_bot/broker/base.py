"""Abstract broker interface.

Defines the minimal execution API for broker implementations used by the trading bot.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any


class Broker(ABC):
    """Abstract base class for execution brokers.

    Args:
        fees_bps (float): Trading fees in basis points applied to executions.

    """

    def __init__(self, fees_bps: float = 0.0) -> None:
        self.fees_bps = fees_bps

    @abstractmethod
    def get_balances(self) -> Dict[str, float]:
        """Return cash and position balances.

        Returns:
            dict[str, float]: Mapping of currency or symbol to balance quantity.
        """

    @abstractmethod
    def get_price(self, symbol: str) -> float:
        """Return current price for ``symbol``.

        Args:
            symbol (str): Instrument symbol, e.g. "BTC/USDT".

        Returns:
            float: Current price.
        """

    @abstractmethod
    def create_order(self, side: str, symbol: str, qty: float, type: str = "market") -> Dict[str, Any]:
        """Execute an order and return execution details.

        Args:
            side (str): "buy" or "sell".
            symbol (str): Instrument symbol, e.g. "BTC/USDT".
            qty (float): Quantity to trade.
            type (str): Order type, e.g. "market" or "limit".

        Returns:
            dict[str, Any]: Execution details such as order id, filled qty, price, and timestamp.
        """

    @abstractmethod
    def get_open_positions(self) -> Dict[str, float]:
        """Return open positions keyed by symbol.

        Returns:
            dict[str, float]: Mapping from symbol to position size.
        """

    @abstractmethod
    def set_price(self, symbol: str, price: float) -> None:
        """Cache price for ``symbol`` if supported.

        Args:
            symbol (str): Instrument symbol.
            price (float): Price to cache.
        """
