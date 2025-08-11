import json
import sys

import pytest

from trading_bot.main import parse_args
from trading_bot.utils.config import load_config


def test_negative_trade_size_config(tmp_path):
    base = {
        "symbol": "BTC/USDT",
        "timeframe": "1m",
        "limit": 500,
        "sma_short": 5,
        "sma_long": 20,
        "trade_size": -1.0,
        "rsi_period": 14,
        "rsi_lower": 30,
        "rsi_upper": 70,
        "confluence": {"members": ["sma", "rsi"], "required": 1},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base))
    with pytest.raises(ValueError):
        load_config(config_dir=str(tmp_path))


def test_cli_trade_size_validation():
    original = sys.argv
    try:
        sys.argv = ["main.py", "--trade-size", "-1"]
        with pytest.raises(SystemExit):
            parse_args()
    finally:
        sys.argv = original

