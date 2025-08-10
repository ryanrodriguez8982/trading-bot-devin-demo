import ccxt
import pytest

from trading_bot import data_fetch
from trading_bot.data_fetch import fetch_btc_usdt_data


class DummyExchange:
    id = "dummy"

    def __init__(self):
        self.called = False

    def fetch_ohlcv(self, symbol, timeframe, limit=500):
        self.called = True
        return [[0, 1, 2, 0, 1, 100]]


class FailingExchange:
    id = "fail"

    def fetch_ohlcv(self, *args, **kwargs):
        raise ccxt.BaseError("boom")


def test_fetch_uses_provided_exchange():
    exch = DummyExchange()
    df = fetch_btc_usdt_data(exchange=exch)
    assert exch.called
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]


def test_fetch_with_exchange_name(monkeypatch):
    exch = DummyExchange()
    monkeypatch.setattr(data_fetch, "create_exchange", lambda **kwargs: exch)
    df = fetch_btc_usdt_data(exchange_name="dummy")
    assert not df.empty


def test_fetch_raises_on_error():
    with pytest.raises(ccxt.BaseError):
        fetch_btc_usdt_data(exchange=FailingExchange())
