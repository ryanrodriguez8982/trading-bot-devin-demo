"""Utilities for running multi-asset live trading loops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import logging

from trading_bot.broker import Broker
from trading_bot.risk.exits import ExitManager


logger = logging.getLogger(__name__)


@dataclass
class LiveTrader:
    """Simple coordinator for live trading across multiple symbols.

    The trader serialises broker calls to respect API rate limits while
    keeping per-symbol state isolated.  Stop-loss and take-profit levels can
    be attached on buys via the broker's underlying portfolio.  When an
    :class:`~trading_bot.risk.exits.ExitManager` is supplied protective exits
    are automatically evaluated on each price update.
    """

    broker: Broker
    exits: Optional[ExitManager] = None

    def process_signal(
        self,
        symbol: str,
        signal: Dict[str, Union[float, str]],
        qty: float,
        *,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Union[float, str]]:
        """Execute a single trading signal for ``symbol``.

        Parameters
        ----------
        symbol:
            Trading pair symbol (e.g. ``"BTC/USDT"``).
        signal:
            Mapping with at least ``action`` (``"buy"``/``"sell"``) and
            ``price`` keys.
        qty:
            Quantity to trade.
        stop_loss, take_profit:
            Optional levels to attach to the resulting position when buying.
        """
        price = float(signal["price"])
        action = str(signal["action"])

        self.update_price(symbol, price)
        self.broker.set_price(symbol, price)
        order = self.broker.create_order(action, symbol, qty)
        logger.info(
            "Executed order: symbol=%s action=%s price=%.4f qty=%f strategy=%s",
            symbol,
            action,
            price,
            qty,
            signal.get("strategy", ""),
        )
        if action == "buy":
            pos = getattr(self.broker, "portfolio", None)
            if pos and symbol in pos.positions:
                p = pos.positions[symbol]
                if stop_loss is not None:
                    p.stop_loss = stop_loss
                if take_profit is not None:
                    p.take_profit = take_profit
            if self.exits is not None:
                self.exits.arm(symbol, price)
        elif action == "sell" and self.exits is not None:
            self.exits.disarm(symbol)
        return order

    def run_batch(
        self,
        signals_by_symbol: Dict[str, List[Dict[str, Union[float, str]]]],
        qtys: Dict[str, float],
    ) -> None:
        """Process lists of signals for multiple symbols sequentially.

        Each iteration processes at most one signal per symbol, preserving
        order so that broker calls remain serialized.
        """
        max_len = max((len(v) for v in signals_by_symbol.values()), default=0)
        for i in range(max_len):
            for symbol, sigs in signals_by_symbol.items():
                if i >= len(sigs):
                    continue
                self.process_signal(symbol, sigs[i], qtys.get(symbol, 0.0))

    def update_price(self, symbol: str, price: float) -> bool:
        """Update price and trigger protective exits.

        Returns ``True`` if an exit was executed.
        """
        self.broker.set_price(symbol, price)
        if self.exits is None:
            return False
        portfolio = getattr(self.broker, "portfolio", None)
        if not portfolio or symbol not in portfolio.positions:
            return False
        exit_price = self.exits.check(symbol, price)
        if exit_price is None:
            return False
        qty = portfolio.positions[symbol].qty
        self.broker.set_price(symbol, exit_price)
        self.broker.create_order("sell", symbol, qty)
        logger.info(
            "Protective exit triggered: symbol=%s price=%.4f qty=%f",
            symbol,
            exit_price,
            qty,
        )
        return True


__all__ = ["LiveTrader"]
