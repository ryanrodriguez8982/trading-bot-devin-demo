import pytest

from trading_bot.live import LiveTrader
from trading_bot.broker.paper import PaperBroker
from trading_bot.risk.exits import ExitManager


def test_live_trader_stop_loss_exit():
    broker = PaperBroker(starting_cash=1000, fees_bps=0, slippage_bps=0)
    exits = ExitManager(stop_loss_pct=10)
    trader = LiveTrader(broker, exits=exits)
    trader.process_signal("BTC/USDT", {"action": "buy", "price": 100}, qty=1)
    trader.update_price("BTC/USDT", 89)
    assert "BTC/USDT" not in broker.get_open_positions()
    balances = broker.get_balances()
    assert balances["cash"] == pytest.approx(990)


def test_live_trader_take_profit_exit():
    broker = PaperBroker(starting_cash=1000, fees_bps=0, slippage_bps=0)
    exits = ExitManager(stop_loss_pct=10, take_profit_pct=20)
    trader = LiveTrader(broker, exits=exits)
    trader.process_signal("BTC/USDT", {"action": "buy", "price": 100}, qty=1)
    trader.update_price("BTC/USDT", 120)
    assert "BTC/USDT" not in broker.get_open_positions()
    balances = broker.get_balances()
    assert balances["cash"] == pytest.approx(1020)
