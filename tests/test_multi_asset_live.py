import pytest

from trading_bot.broker import PaperBroker
from trading_bot.live import LiveTrader


def test_multi_symbol_balances_and_positions():
    broker = PaperBroker(starting_cash=1000, fees_bps=0, slippage_bps=0)
    trader = LiveTrader(broker)

    # Open positions on two symbols
    trader.process_signal("BTC/USDT", {"action": "buy", "price": 100}, qty=1)
    trader.process_signal("ETH/USDT", {"action": "buy", "price": 50}, qty=1)

    balances = broker.get_balances()
    assert balances["BTC/USDT"] == pytest.approx(1)
    assert balances["ETH/USDT"] == pytest.approx(1)
    assert balances["cash"] == pytest.approx(850)

    # Close both positions
    trader.process_signal("BTC/USDT", {"action": "sell", "price": 110}, qty=1)
    trader.process_signal("ETH/USDT", {"action": "sell", "price": 55}, qty=1)

    balances = broker.get_balances()
    assert balances["cash"] == pytest.approx(1015)
    assert broker.get_open_positions() == {}
