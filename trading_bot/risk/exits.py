"""Protective exit utilities for stop-loss, take-profit and trailing stops.

This module provides a lightweight engine-side mechanism for managing
protective exits (a "virtual" OCO).  The :class:`ExitManager` maintains a set
of arms for open positions and, given a stream of prices, decides when an
exit should trigger.  State is kept in-memory; callers may persist the
``arms`` dictionary to durable storage if needed to survive restarts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ExitArm:
    """Tracks state for a single position's protective exits."""

    entry_price: float
    highest_price: float


@dataclass
class ExitManager:
    """Evaluate stop-loss / take-profit / trailing-stop exits."""

    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    arms: Dict[str, ExitArm] = field(default_factory=dict)

    def arm(self, symbol: str, entry_price: float) -> None:
        """Register a new position with its entry price."""
        self.arms[symbol] = ExitArm(entry_price=entry_price, highest_price=entry_price)

    def disarm(self, symbol: str) -> None:
        """Remove tracking for ``symbol`` if present."""
        self.arms.pop(symbol, None)

    def check(self, symbol: str, price: float) -> bool:
        """Return ``True`` if an exit is triggered for ``symbol`` at ``price``.

        The order of evaluation is stop-loss, take-profit then trailing stop.
        Once an exit triggers the arm is removed.
        """
        arm = self.arms.get(symbol)
        if not arm:
            return False
        arm.highest_price = max(arm.highest_price, price)

        if self.stop_loss_pct is not None:
            if price <= arm.entry_price * (1 - self.stop_loss_pct / 100):
                self.disarm(symbol)
                return True
        if self.take_profit_pct is not None:
            if price >= arm.entry_price * (1 + self.take_profit_pct / 100):
                self.disarm(symbol)
                return True
        if self.trailing_stop_pct is not None:
            trail = arm.highest_price * (1 - self.trailing_stop_pct / 100)
            if price <= trail:
                self.disarm(symbol)
                return True
        return False
