"""Portfolio and Position models for spot-only trading."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Position:
    """Represents a spot position for a single trading symbol."""

    symbol: str
    qty: float = 0.0
    avg_cost: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    def market_value(self, price: float) -> float:
        return self.qty * price


@dataclass
class Portfolio:
    """Simple portfolio tracking cash, positions and PnL."""

    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0
    # Last known prices for symbols to allow equity calculation without
    # always passing in a price dictionary.
    last_prices: Dict[str, float] = field(default_factory=dict)

    def buy(
        self,
        symbol: str,
        qty: float,
        price: float,
        fee_bps: float = 0.0,
        *,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> None:
        """Buy ``qty`` of ``symbol`` at ``price`` and deduct fees from cash.

        The purchase increases the position's average cost and quantity and
        immediately realises the trading fee as a loss.  A ``ValueError`` is
        raised if there is insufficient cash or non‑positive inputs are
        provided.
        """
        if qty <= 0 or price <= 0:
            raise ValueError("qty and price must be positive")
        cost = price * qty
        fee = cost * fee_bps / 10_000
        total = cost + fee
        if total > self.cash + 1e-12:
            raise ValueError("insufficient cash")
        self.cash -= total
        # Buying incurs a fee which is realized immediately as a loss
        self.realized_pnl -= fee
        # track last trade price
        self.last_prices[symbol] = price
        pos = self.positions.get(symbol)
        if pos:
            new_qty = pos.qty + qty
            if new_qty <= 0:
                raise ValueError("resulting position would be non-positive")
            pos.avg_cost = (pos.avg_cost * pos.qty + cost) / new_qty
            pos.qty = new_qty
            if stop_loss is not None:
                pos.stop_loss = stop_loss
            if take_profit is not None:
                pos.take_profit = take_profit
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                qty=qty,
                avg_cost=cost / qty,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )

    def sell(self, symbol: str, qty: float, price: float, fee_bps: float = 0.0) -> None:
        """Sell ``qty`` of ``symbol`` at ``price`` and update cash and PnL.

        Fees are deducted from the proceeds and the position quantity is
        reduced.  Selling more than is held raises ``ValueError`` and the
        portfolio state remains unchanged.
        """
        if qty <= 0 or price <= 0:
            raise ValueError("qty and price must be positive")
        pos = self.positions.get(symbol)
        if not pos or qty > pos.qty + 1e-12:
            raise ValueError("insufficient position")
        proceeds = price * qty
        fee = proceeds * fee_bps / 10_000
        self.cash += proceeds - fee
        # Realized profit/loss for this sale net of fees
        realized = (price - pos.avg_cost) * qty - fee
        self.realized_pnl += realized
        # update last traded price
        self.last_prices[symbol] = price
        pos.qty -= qty
        if pos.qty <= 1e-12:
            del self.positions[symbol]
            self.last_prices.pop(symbol, None)

    def equity(self, prices: Optional[Dict[str, float]] = None) -> float:
        """Return total equity (cash plus market value of positions).

        If ``prices`` is provided the internal price cache is updated and
        used for the valuation.  This allows callers to fetch equity once
        with prices and subsequently without needing to supply them again.
        """
        if prices:
            self.last_prices.update(prices)
        return self.cash + self.total_position_value()

    def total_position_value(self, prices: Optional[Dict[str, float]] = None) -> float:
        """Return market value of all positions.

        If ``prices`` is given they will update the cached last prices.
        """
        if prices:
            self.last_prices.update(prices)
        value = 0.0
        for symbol, pos in self.positions.items():
            price = self.last_prices.get(symbol)
            if price is not None:
                value += pos.market_value(price)
        return value

    def position_qty(self, symbol: str) -> float:
        pos = self.positions.get(symbol)
        return pos.qty if pos else 0.0
