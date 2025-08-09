"""Abstract broker interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any


class Broker(ABC):
    """Abstract base class for execution brokers."""

    def __init__(self, fees_bps: float = 0.0) -> None:
        self.fees_bps = fees_bps

    @abstractmethod
    def get_balances(self) -> Dict[str, float]:
        """Return cash and position balances."""

    @abstractmethod
    def get_price(self, symbol: str) -> float:
        """Return current price for ``symbol``."""

    @abstractmethod
    def create_order(self, side: str, symbol: str, qty: float, type: str = "market") -> Dict[str, Any]:
        """Execute an order and return execution details."""

    @abstractmethod
    def get_open_positions(self) -> Dict[str, float]:
        """Return open positions keyed by symbol."""
