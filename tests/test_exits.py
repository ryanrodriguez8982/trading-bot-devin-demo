import pytest

from trading_bot.risk.exits import ExitManager


def test_stop_loss_triggers():
    manager = ExitManager(stop_loss_pct=2)
    manager.arm("BTC", entry_price=100)
    assert manager.check("BTC", 99) is None
    assert manager.check("BTC", 97.9) == pytest.approx(98)


def test_take_profit_triggers():
    manager = ExitManager(take_profit_pct=4)
    manager.arm("BTC", 100)
    assert manager.check("BTC", 103.9) is None
    assert manager.check("BTC", 104.1) == pytest.approx(104)


def test_trailing_stop_triggers_after_new_high():
    manager = ExitManager(trailing_stop_pct=2)
    manager.arm("BTC", 100)
    # price rises; record high
    assert manager.check("BTC", 110) is None
    # slight pullback above trail
    assert manager.check("BTC", 108.5) is None
    # drop beyond trailing stop
    assert manager.check("BTC", 107.7) == pytest.approx(107.8)
    # once triggered arm removed
    assert manager.check("BTC", 107) is None
