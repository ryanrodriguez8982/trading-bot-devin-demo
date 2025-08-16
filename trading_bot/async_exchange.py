import asyncio
import logging
import signal
from typing import Any, Dict, Optional, Sequence

import ccxt.async_support as ccxt

logger = logging.getLogger(__name__)


class AsyncExchange:
    """Asynchronous wrapper around a CCXT exchange.

    Creates an exchange client using ``ccxt.async_support`` and installs
    signal handlers for ``SIGINT`` and ``SIGTERM`` to ensure that the
    connection is closed gracefully when the application is interrupted.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        api_passphrase: Optional[str] = None,
        exchange_name: str = "binance",
    ) -> None:
        params: Dict[str, str] = {}
        if api_key and api_secret:
            params.update({"apiKey": api_key, "secret": api_secret})
            if api_passphrase:
                params["password"] = api_passphrase

        exchange_class = getattr(ccxt, exchange_name)
        self.exchange = exchange_class(params)

        self._stop_event = asyncio.Event()
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._handle_stop_signal)

    # ------------------------------------------------------------------
    def _handle_stop_signal(self) -> None:
        """Internal signal handler that triggers graceful shutdown."""
        logger.info("Shutdown signal received; closing exchange")
        self._stop_event.set()

    async def wait_closed(self) -> None:
        """Wait for a termination signal then close the exchange."""
        await self._stop_event.wait()
        await self.exchange.close()

    # ------------------------------------------------------------------
    async def fetch_tickers(self, symbols: Sequence[str]) -> Dict[str, Any]:
        """Fetch multiple tickers concurrently.

        Parameters
        ----------
        symbols : Sequence[str]
            Iterable of market symbols to fetch.
        """
        tasks = [self.exchange.fetch_ticker(sym) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {sym: res for sym, res in zip(symbols, results)}

    async def execute_trade(
        self,
        symbol: str,
        action: str,
        amount: float,
    ) -> Optional[Dict[str, Any]]:
        """Execute a market order asynchronously."""
        side = "buy" if action.lower() == "buy" else "sell"
        try:
            order = await self.exchange.create_market_order(symbol, side, amount)
            logger.info(
                "Executed %s order for %s %s: id=%s",
                side,
                amount,
                symbol,
                order.get("id"),
            )
            return order
        except ccxt.BaseError as e:  # pragma: no cover - ccxt internals
            logger.error("Order execution failed: %s", e)
            return None

    async def close(self) -> None:
        """Close the underlying exchange connection."""
        await self.exchange.close()


def create_async_exchange(
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    api_passphrase: Optional[str] = None,
    exchange_name: str = "binance",
) -> AsyncExchange:
    """Factory for :class:`AsyncExchange`.

    This mirrors the synchronous ``create_exchange`` function but returns an
    :class:`AsyncExchange` that uses ``ccxt.async_support``.
    """
    return AsyncExchange(
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=api_passphrase,
        exchange_name=exchange_name,
    )
