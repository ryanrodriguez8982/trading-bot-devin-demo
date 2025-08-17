from unittest import mock

import ccxt
import pytest

from trading_bot.exchange import create_exchange, execute_trade


def test_create_exchange_with_keys():
    with mock.patch("ccxt.binance") as mock_binance:
        create_exchange("key", "secret", "pass")
        mock_binance.assert_called_once()
        args, kwargs = mock_binance.call_args
        params = args[0]
        assert params["apiKey"] == "key"
        assert params["secret"] == "secret"
        assert params["password"] == "pass"


def test_create_exchange_invalid_name():
    with pytest.raises(AttributeError):
        create_exchange(exchange_name="notreal")


class DummyEx:
    def __init__(self, balances, price=1.0, fee_rate=0.0):
        self.called = False
        self._balances = balances
        self._price = price
        self.fees = {"trading": {"taker": fee_rate}}

    def fetch_balance(self):
        return {"free": self._balances}

    def fetch_ticker(self, symbol):
        return {"last": self._price}

    def create_market_order(self, symbol, side, amount):
        self.called = True
        return {"id": "1", "symbol": symbol, "side": side, "amount": amount}


class FailingEx(DummyEx):
    def __init__(self):
        super().__init__({"USDT": 1000, "BTC": 1}, price=1.0)

    def create_market_order(self, symbol, side, amount):
        raise ccxt.BaseError("oops")


def test_execute_trade_success():
    ex = DummyEx({"USDT": 1000}, price=100)
    order = execute_trade(ex, "BTC/USDT", "buy", 1)
    assert ex.called
    assert order["side"] == "buy"


def test_execute_trade_failure():
    order = execute_trade(FailingEx(), "BTC/USDT", "buy", 1)
    assert order is None


def test_execute_trade_buy_insufficient_balance():
    ex = DummyEx({"USDT": 50}, price=100)
    order = execute_trade(ex, "BTC/USDT", "buy", 1)
    assert order is None
    assert not ex.called


def test_execute_trade_sell_insufficient_balance():
    ex = DummyEx({"BTC": 0.5}, price=100)
    order = execute_trade(ex, "BTC/USDT", "sell", 1)
    assert order is None
    assert not ex.called
