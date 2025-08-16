import pytest
import logging

from trading_bot.broker import CcxtSpotBroker


class DummyExchange:
    def __init__(self):
        self.balance = {"free": {"USDT": 1000, "BTC": 1}}
        self.price = 10.0
        self.orders = []
        self.markets = {
            "BTC/USDT": {
                "precision": {"amount": 3},
                "limits": {"amount": {"min": 0.001}},
            }
        }

    def fetch_balance(self):
        return self.balance

    def market(self, symbol):
        return self.markets[symbol]

    def fetch_ticker(self, symbol):
        return {"last": self.price}

    def create_order(self, symbol, type, side, amount):
        payload = {"symbol": symbol, "type": type, "side": side, "amount": amount}
        self.orders.append(payload)
        return payload


class FlakyExchange(DummyExchange):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def create_order(self, symbol, type, side, amount):
        self.calls += 1
        if self.calls == 1:
            raise Exception("temporary failure")
        return super().create_order(symbol, type, side, amount)


class DummyLimiter:
    def __init__(self):
        self.calls = 0

    def wait(self):
        self.calls += 1


def test_buy_respects_precision_and_balance():
    ex = DummyExchange()
    broker = CcxtSpotBroker(exchange=ex)
    order = broker.create_order("buy", "BTC/USDT", 0.123456)
    assert order["amount"] == pytest.approx(0.123)
    assert ex.orders[0]["amount"] == 0.123


def test_sell_raises_on_insufficient_balance():
    ex = DummyExchange()
    broker = CcxtSpotBroker(exchange=ex)
    with pytest.raises(ValueError):
        broker.create_order("sell", "BTC/USDT", 2)


def test_sell_rounds_up():
    ex = DummyExchange()
    broker = CcxtSpotBroker(exchange=ex)
    order = broker.create_order("sell", "BTC/USDT", 0.123456)
    assert order["amount"] == pytest.approx(0.124)


def test_rate_limiter_called():
    ex = DummyExchange()
    limiter = DummyLimiter()
    broker = CcxtSpotBroker(exchange=ex, rate_limiter=limiter)
    broker.create_order("buy", "BTC/USDT", 0.5)
    assert limiter.calls == 3


def test_dry_run_skips_network_call(caplog):
    ex = DummyExchange()
    broker = CcxtSpotBroker(exchange=ex, dry_run=True)
    with caplog.at_level(logging.INFO):
        broker.create_order("buy", "BTC/USDT", 0.5)
    assert not ex.orders
    assert any("DRY-RUN" in r.message for r in caplog.records)


def test_retries_on_failure():
    ex = FlakyExchange()
    broker = CcxtSpotBroker(exchange=ex)
    order = broker.create_order("buy", "BTC/USDT", 0.5)
    assert order["side"] == "buy"
    assert ex.calls == 2
