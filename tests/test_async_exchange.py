import asyncio
import time

from trading_bot.async_exchange import create_async_exchange


class DummyExchange:
    def __init__(self) -> None:
        self.closed = False

    async def fetch_ticker(self, symbol: str):
        await asyncio.sleep(0.1)
        return {"symbol": symbol}

    async def create_market_order(self, symbol: str, side: str, amount: float):
        return {"id": f"{side}:{symbol}:{amount}"}

    async def close(self):
        self.closed = True


def test_fetch_tickers_concurrently(monkeypatch):
    dummy = DummyExchange()
    monkeypatch.setattr("ccxt.async_support.binance", lambda params=None: dummy)

    async def runner():
        exch = create_async_exchange()
        start = time.perf_counter()
        result = await exch.fetch_tickers(["BTC/USDT", "ETH/USDT"])
        duration = time.perf_counter() - start
        assert set(result.keys()) == {"BTC/USDT", "ETH/USDT"}
        assert duration < 0.2

    asyncio.run(runner())


def test_wait_closed_handles_signal(monkeypatch):
    dummy = DummyExchange()
    monkeypatch.setattr("ccxt.async_support.binance", lambda params=None: dummy)

    async def runner():
        exch = create_async_exchange()
        exch._handle_stop_signal()
        await asyncio.wait_for(exch.wait_closed(), 1)
        assert dummy.closed

    asyncio.run(runner())
