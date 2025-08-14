import pytest

from trading_bot.risk.position_sizing import calculate_position_size
from trading_bot.risk.config import PositionSizingConfig


def test_fixed_cash_position_size():
    cfg = PositionSizingConfig(mode="fixed_cash", fixed_cash_amount=100)
    qty = calculate_position_size(cfg, price=20000, equity=1000)
    assert qty == pytest.approx(0.005)


def test_fixed_fraction_position_size():
    cfg = PositionSizingConfig(mode="fixed_fraction", fraction_of_equity=0.05)
    qty = calculate_position_size(cfg, price=200, equity=1000)
    assert qty == pytest.approx(0.25)


def test_too_small_capital_returns_zero():
    cfg = PositionSizingConfig(mode="fixed_fraction", fraction_of_equity=0.01)
    qty = calculate_position_size(cfg, price=100, equity=50, lot_size=0.1)
    assert qty == 0


def test_risk_per_trade_mode():
    cfg = PositionSizingConfig(mode="risk_per_trade", risk_pct=0.1)
    qty = calculate_position_size(cfg, price=50, equity=1000)
    assert qty == pytest.approx(2)


def test_precision_flooring():
    cfg = PositionSizingConfig(mode="fixed_fraction", fraction_of_equity=0.5)
    qty = calculate_position_size(
        cfg, price=3, equity=100, lot_size=0.1, precision=2
    )
    assert qty == pytest.approx(16.6)


class _DummyCfg:
    def __init__(self, mode: str):
        self.mode = mode
        self.fixed_cash_amount = 100.0
        self.fraction_of_equity = 0.1
        self.risk_pct = 0.01


def test_unknown_mode_raises():
    cfg = _DummyCfg("other")
    with pytest.raises(ValueError):
        calculate_position_size(cfg, price=1, equity=100)
