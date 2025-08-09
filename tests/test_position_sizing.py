import pytest

from trading_bot.risk.position_sizing import calculate_position_size
from trading_bot.risk_config import PositionSizingConfig


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
