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


def test_process_signal_sets_stops():
    broker = PaperBroker(starting_cash=1000, fees_bps=0, slippage_bps=0)
    trader = LiveTrader(broker)
    trader.process_signal(
        "BTC/USDT",
        {"action": "buy", "price": 100},
        qty=1,
        stop_loss=90,
        take_profit=110,
    )
    pos = broker.portfolio.positions["BTC/USDT"]
    assert pos.stop_loss == 90
    assert pos.take_profit == 110


def test_run_batch_executes_all():
    broker = PaperBroker(starting_cash=1000, fees_bps=0, slippage_bps=0)
    trader = LiveTrader(broker)
    signals = {
        "BTC/USDT": [
            {"action": "buy", "price": 100},
            {"action": "sell", "price": 110},
        ],
        "ETH/USDT": [{"action": "buy", "price": 50}],
    }
    qtys = {"BTC/USDT": 1, "ETH/USDT": 2}
    trader.run_batch(signals, qtys)
    balances = broker.get_balances()
    assert balances["ETH/USDT"] == pytest.approx(2)
    assert "BTC/USDT" not in broker.get_open_positions()
