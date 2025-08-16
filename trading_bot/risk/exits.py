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
    """Tracks state for a single position's protective exits.

    Attributes
    ----------
    entry_price:
        The price at which the position was opened.
    highest_price:
        Highest price seen since entry, used to compute a trailing stop.
    """

    entry_price: float
    highest_price: float


@dataclass
class ExitManager:
    """Evaluate stop-loss / take-profit / trailing-stop exits.

    Parameters
    ----------
    stop_loss_pct:
        Percentage drop from the entry price that should trigger a stop-loss
        exit. ``5`` for example exits if price falls 5% below entry.
    take_profit_pct:
        Percentage gain from entry at which profits should be taken.
    trailing_stop_pct:
        Distance in percent from the highest price seen since entry used to
        maintain a trailing stop. ``10`` keeps the stop 10% below the peak.
    """

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

    def check_ohlc(self, symbol: str, high: float, low: float) -> Optional[float]:
        """Return exit price if any protective exit triggers for ``symbol``.

        ``high`` and ``low`` are the bar's extreme prices.  The evaluation
        order mirrors exchange priority: stop-loss, then take-profit, then
        trailing stop.  If an exit is triggered the arm is removed and the
        corresponding price level is returned.
        """
        arm = self.arms.get(symbol)
        if not arm:
            return None
        arm.highest_price = max(arm.highest_price, high)

        if self.stop_loss_pct is not None:
            stop_price = arm.entry_price * (1 - self.stop_loss_pct / 100)
            if low <= stop_price:
                self.disarm(symbol)
                return stop_price

        if self.take_profit_pct is not None:
            take_price = arm.entry_price * (1 + self.take_profit_pct / 100)
            if high >= take_price:
                self.disarm(symbol)
                return take_price

        if self.trailing_stop_pct is not None:
            trail_price = arm.highest_price * (1 - self.trailing_stop_pct / 100)
            if low <= trail_price:
                self.disarm(symbol)
                return trail_price

        return None

    def check(self, symbol: str, price: float) -> Optional[float]:
        """Return exit price if an exit triggers at ``price``.

        Convenience wrapper that treats ``price`` as both the high and low for
        the period.  This is suitable for tick-by-tick evaluation in live
        trading where only the latest price is available.
        """
        return self.check_ohlc(symbol, price, price)
