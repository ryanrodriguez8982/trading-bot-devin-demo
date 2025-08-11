from trading_bot.risk.exits import ExitManager


def test_stop_loss_triggers():
    manager = ExitManager(stop_loss_pct=2)
    manager.arm("BTC", entry_price=100)
    assert not manager.check("BTC", 99)
    assert manager.check("BTC", 97.9)


def test_take_profit_triggers():
    manager = ExitManager(take_profit_pct=4)
    manager.arm("BTC", 100)
    assert not manager.check("BTC", 103.9)
    assert manager.check("BTC", 104.1)


def test_trailing_stop_triggers_after_new_high():
    manager = ExitManager(trailing_stop_pct=2)
    manager.arm("BTC", 100)
    # price rises; record high
    assert not manager.check("BTC", 110)
    # slight pullback above trail
    assert not manager.check("BTC", 108.5)
    # drop beyond trailing stop
    assert manager.check("BTC", 107.7)
    # once triggered arm removed
    assert not manager.check("BTC", 107)
