"""Utilities for running multi-asset live trading loops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from trading_bot.broker import Broker


@dataclass
class LiveTrader:
    """Simple coordinator for live trading across multiple symbols.

    The trader serialises broker calls to respect API rate limits while
    keeping per-symbol state isolated.  Stop-loss and take-profit levels can
    be attached on buys via the broker's underlying portfolio.
    """

    broker: Broker

    def process_signal(
        self,
        symbol: str,
        signal: Dict[str, float],
        qty: float,
        *,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, float]:
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
        price = signal["price"]
        action = signal["action"]
        self.broker.set_price(symbol, price)
        order = self.broker.create_order(action, symbol, qty)
        if action == "buy" and (stop_loss is not None or take_profit is not None):
            pos = getattr(self.broker, "portfolio", None)
            if pos and symbol in pos.positions:
                p = pos.positions[symbol]
                if stop_loss is not None:
                    p.stop_loss = stop_loss
                if take_profit is not None:
                    p.take_profit = take_profit
        return order

    def run_batch(
        self,
        signals_by_symbol: Dict[str, List[Dict[str, float]]],
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


__all__ = ["LiveTrader"]
