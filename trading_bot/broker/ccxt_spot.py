"""CCXT spot broker implementation."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

import ccxt

from trading_bot.utils.precision import round_to_increment
from trading_bot.utils.rate_limit import RateLimiter

from .base import Broker

logger = logging.getLogger(__name__)


class CcxtSpotBroker(Broker):
    """Minimal CCXT spot broker.

    Parameters
    ----------
    exchange_name:
        Name of the exchange supported by CCXT (e.g. ``"binance"``).
    api_key, api_secret:
        Credentials for the exchange.  If not provided they will be read from
        the ``TRADING_BOT_API_KEY`` and ``TRADING_BOT_API_SECRET`` environment
        variables.  The exchange name can also be supplied via the
        ``TRADING_BOT_EXCHANGE`` environment variable.
    exchange:
        Optional pre-initialised CCXT exchange instance (useful for tests).
    dry_run:
        When ``True`` no network calls are made and order payloads are printed
        instead of being sent to the exchange.
    retries:
        Number of times to retry failed CCXT calls with exponential backoff.
    """

    def __init__(
        self,
        exchange_name: Optional[str] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        *,
        exchange: Optional[Any] = None,
        fees_bps: float = 0.0,
        dry_run: bool = False,
        retries: int = 3,
        backoff: float = 0.5,
        rate_limit: Optional[float] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ) -> None:
        super().__init__(fees_bps=fees_bps)
        if exchange is not None:
            self.exchange = exchange
        else:
            name = exchange_name or os.getenv("TRADING_BOT_EXCHANGE") or "binance"
            key = api_key or os.getenv("TRADING_BOT_API_KEY")
            secret = api_secret or os.getenv("TRADING_BOT_API_SECRET")
            params: Dict[str, Any] = {}
            if key and secret:
                params = {"apiKey": key, "secret": secret}
            exchange_class = getattr(ccxt, name)
            self.exchange = exchange_class(params)
        self.dry_run = dry_run
        self.retries = retries
        self.backoff = backoff
        self.prices: Dict[str, float] = {}
        self.name = "ccxt"
        self._rate_limiter = rate_limiter or (RateLimiter(rate_limit) if rate_limit else None)

    # ------------------------------------------------------------------
    def set_price(self, symbol: str, price: float) -> None:
        self.prices[symbol] = price

    def get_price(self, symbol: str) -> float:
        price = self.prices.get(symbol)
        if price is not None:
            return price
        self._wait_rate_limit()
        ticker = self.exchange.fetch_ticker(symbol)
        price = ticker.get("last") or ticker.get("close")
        if price is None:
            raise ValueError(f"no price available for {symbol}")
        self.prices[symbol] = float(price)
        return float(price)

    def get_balances(self) -> Dict[str, float]:
        self._wait_rate_limit()
        data = self.exchange.fetch_balance()
        free = data.get("free") or {}
        return {k: float(v) for k, v in free.items() if isinstance(v, (int, float))}

    def get_open_positions(self) -> Dict[str, float]:
        balances = self.get_balances()
        return {k: v for k, v in balances.items() if v}

    # ------------------------------------------------------------------
    def _wait_rate_limit(self) -> None:
        if self._rate_limiter:
            self._rate_limiter.wait()

    def _round_qty(self, symbol: str, qty: float, side: str) -> float:
        market = self.exchange.market(symbol)
        precision = market.get("precision", {}).get("amount")
        limits = market.get("limits", {}).get("amount", {})
        min_amt = limits.get("min")
        original = qty
        if precision is not None:
            step = 10 ** (-precision)
            qty = round_to_increment(qty, step, side)
        if min_amt:
            qty = round_to_increment(qty, float(min_amt), side)
        if qty != original:
            logger.debug(
                "rounded qty",
                extra={"symbol": symbol, "side": side, "from": original, "to": qty},
            )
        return qty

    def create_order(self, side: str, symbol: str, qty: float, type: str = "market") -> Dict[str, Any]:
        if type != "market":
            raise NotImplementedError("CcxtSpotBroker only supports market orders")

        qty = self._round_qty(symbol, float(qty), side)
        if qty <= 0:
            raise ValueError("quantity too small after rounding")

        base, quote = symbol.split("/")
        price = self.get_price(symbol)
        balances = self.get_balances()
        if side == "buy":
            cost = qty * price
            if balances.get(quote, 0.0) < cost:
                raise ValueError("insufficient quote balance")
        else:
            if balances.get(base, 0.0) < qty:
                raise ValueError("insufficient base balance")

        order_payload = {
            "symbol": symbol,
            "type": type,
            "side": side,
            "amount": qty,
        }
        for attempt in range(self.retries):
            try:
                if self.dry_run:
                    logger.info(f"[DRY-RUN] {order_payload}")
                    return order_payload
                self._wait_rate_limit()
                return self.exchange.create_order(symbol, type, side, qty)
            except Exception:  # pragma: no cover - defensive
                logger.exception("ccxt order failed", extra={"payload": order_payload})
                if attempt == self.retries - 1:
                    raise
                time.sleep(self.backoff * (2**attempt))
        raise RuntimeError("unreachable")


__all__ = ["CcxtSpotBroker"]
