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
        cost = price * qty
        fee = cost * fee_bps / 10_000
        total = cost + fee
        if total > self.cash + 1e-12:
            raise ValueError("insufficient cash")
        self.cash -= total
        # Buying incurs a fee which is realized immediately as a loss
        self.realized_pnl -= fee
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
        pos = self.positions.get(symbol)
        if not pos or qty > pos.qty + 1e-12:
            raise ValueError("insufficient position")
        proceeds = price * qty
        fee = proceeds * fee_bps / 10_000
        self.cash += proceeds - fee
        # Realized profit/loss for this sale net of fees
        realized = (price - pos.avg_cost) * qty - fee
        self.realized_pnl += realized
        pos.qty -= qty
        if pos.qty <= 1e-12:
            del self.positions[symbol]

    def equity(self, prices: Dict[str, float]) -> float:
        """Return total equity (cash plus market value of positions)."""
        return self.cash + self.total_position_value(prices)

    def total_position_value(self, prices: Dict[str, float]) -> float:
        """Return market value of all positions given price quotes."""
        value = 0.0
        for symbol, pos in self.positions.items():
            price = prices.get(symbol)
            if price is not None:
                value += pos.market_value(price)
        return value

    def position_qty(self, symbol: str) -> float:
        pos = self.positions.get(symbol)
        return pos.qty if pos else 0.0
