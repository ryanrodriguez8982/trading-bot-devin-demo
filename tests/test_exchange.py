import os
import sys
from unittest import mock

import ccxt
import pytest

project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(project_root, 'trading_bot'))

from exchange import create_exchange, execute_trade


def test_create_exchange_with_keys():
    with mock.patch('ccxt.binance') as mock_binance:
        create_exchange('key', 'secret', 'pass')
        mock_binance.assert_called_once()
        args, kwargs = mock_binance.call_args
        params = args[0]
        assert params['apiKey'] == 'key'
        assert params['secret'] == 'secret'
        assert params['password'] == 'pass'


def test_create_exchange_invalid_name():
    with pytest.raises(AttributeError):
        create_exchange(exchange_name='notreal')


class DummyEx:
    def __init__(self):
        self.called = False

    def create_market_order(self, symbol, side, amount):
        self.called = True
        return {"id": "1", "symbol": symbol, "side": side, "amount": amount}


class FailingEx:
    def create_market_order(self, symbol, side, amount):
        raise ccxt.BaseError('oops')


def test_execute_trade_success():
    ex = DummyEx()
    order = execute_trade(ex, 'BTC/USDT', 'buy', 1)
    assert ex.called
    assert order['side'] == 'buy'


def test_execute_trade_failure():
    order = execute_trade(FailingEx(), 'BTC/USDT', 'buy', 1)
    assert order is None

