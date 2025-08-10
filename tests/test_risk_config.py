import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from trading_bot.risk_config import get_risk_config
from trading_bot.main import parse_args
from trading_bot.utils.config import load_config


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
        sys.argv = ["main.py", "--risk.slippage_bps", "8"]
        args = parse_args()
        config = load_config()
        rc = get_risk_config(config.get("risk"), args.risk_overrides)
        assert rc.slippage_bps == 8
    finally:
        sys.argv = original
