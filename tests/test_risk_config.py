import sys

import pytest
from trading_bot.risk.config import get_risk_config
from trading_bot.main import parse_args
from trading_bot.config import load_config
from trading_bot.risk.config import (
    PositionSizingConfig,
    StopLossConfig,
    TakeProfitConfig,
    TrailingConfig,
    MaxDrawdownConfig,
)


def test_default_risk_config():
    rc = get_risk_config({})
    assert rc.slippage_bps == 5
    assert rc.position_sizing.mode == "fixed_fraction"


def test_invalid_risk_config():
    with pytest.raises(ValueError):
        get_risk_config({"slippage_bps": -1})


def test_cli_override():
    original = sys.argv
    try:
        sys.argv = ["main.py", "live", "--risk.slippage_bps", "8"]
        args = parse_args()
        config = load_config()
        rc = get_risk_config(config.get("risk"), args.risk_overrides)
        assert rc.slippage_bps == 8
    finally:
        sys.argv = original


def test_position_sizing_invalid_mode():
    with pytest.raises(ValueError):
        PositionSizingConfig(mode="unknown")


def test_negative_values_raise():
    with pytest.raises(ValueError):
        PositionSizingConfig(fraction_of_equity=-0.1)
    with pytest.raises(ValueError):
        StopLossConfig(value=-0.1)
    with pytest.raises(ValueError):
        TakeProfitConfig(rr=-1)
    with pytest.raises(ValueError):
        TrailingConfig(trail_pct=-0.1)
    with pytest.raises(ValueError):
        MaxDrawdownConfig(monthly_pct=-0.1)


def test_nested_override_non_numeric():
    rc = get_risk_config(overrides={"stops.stop_loss.type": "percent"})
    assert rc.stops.stop_loss.type == "percent"
