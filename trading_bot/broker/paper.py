"""Paper trading broker implementation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

from .base import Broker
from trading_bot.portfolio import Portfolio


@dataclass
class PaperBroker(Broker):
    """Simple in-memory paper trading broker."""

    starting_cash: float = 0.0
    fees_bps: float = 0.0
    slippage_bps: float = 0.0

    def __post_init__(self) -> None:
        super().__init__(fees_bps=self.fees_bps)
        self.portfolio = Portfolio(cash=self.starting_cash)
        self.prices: Dict[str, float] = {}
        self.name = "paper"

    def set_price(self, symbol: str, price: float) -> None:
        self.prices[symbol] = price

    def get_price(self, symbol: str) -> float:
        price = self.prices.get(symbol)
        if price is None:
            raise ValueError(f"price for {symbol} not set")
        return price

    # Broker interface -------------------------------------------------
    def get_balances(self) -> Dict[str, float]:
        balances = {sym: pos.qty for sym, pos in self.portfolio.positions.items()}
        balances["cash"] = self.portfolio.cash
        return balances

    def get_open_positions(self) -> Dict[str, float]:
        return {sym: pos.qty for sym, pos in self.portfolio.positions.items()}

    def create_order(self, side: str, symbol: str, qty: float, type: str = "market") -> Dict[str, Any]:
        if type != "market":
            raise NotImplementedError("only market orders supported in PaperBroker")
        price = self.get_price(symbol)
        slip = self.slippage_bps / 10_000
        exec_price = price * (1 + slip) if side == "buy" else price * (1 - slip)
        fee = exec_price * qty * self.fees_bps / 10_000
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        if side == "buy":
            self.portfolio.buy(symbol, qty, exec_price, fee_bps=self.fees_bps)
        else:
            self.portfolio.sell(symbol, qty, exec_price, fee_bps=self.fees_bps)
        return {
            "timestamp": ts,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": exec_price,
            "fee": fee,
            "broker": self.name,
        }
