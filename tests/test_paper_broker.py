import pytest
from trading_bot.broker import PaperBroker


def test_buy_and_sell_updates_balances():
    broker = PaperBroker(starting_cash=1000, fees_bps=10, slippage_bps=0)
    broker.set_price('BTC', 100)
    broker.create_order('buy', 'BTC', 1)
    balances = broker.get_balances()
    assert balances['cash'] == pytest.approx(1000 - 100 - 0.1)
    broker.set_price('BTC', 110)
    broker.create_order('sell', 'BTC', 1)
    balances = broker.get_balances()
    assert balances['cash'] == pytest.approx(1000 - 100 - 0.1 + 110 - 0.11)


def test_cannot_sell_without_holdings():
    broker = PaperBroker(starting_cash=1000, fees_bps=0, slippage_bps=0)
    broker.set_price('BTC', 100)
    with pytest.raises(ValueError):
        broker.create_order('sell', 'BTC', 1)


def test_cannot_buy_beyond_cash():
    broker = PaperBroker(starting_cash=50, fees_bps=0, slippage_bps=0)
    broker.set_price('BTC', 100)
    with pytest.raises(ValueError):
        broker.create_order('buy', 'BTC', 1)
