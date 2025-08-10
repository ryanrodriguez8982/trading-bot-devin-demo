import json
import sys

import pytest

from trading_bot.utils.config import load_config
from trading_bot.main import parse_args


def test_config_overlays_and_cli_precedence(tmp_path):
    base = {
        "symbol": "BTC/USDT",
        "timeframe": "1m",
        "limit": 500,
        "sma_short": 5,
        "sma_long": 20,
        "trade_size": 1.0,
        "confluence": {"members": ["sma", "rsi"], "required": 1},
    }
    local = {"symbol": "ETH/USDT"}
    config_path = tmp_path / "config.json"
    local_path = tmp_path / "config.local.json"
    config_path.write_text(json.dumps(base))
    local_path.write_text(json.dumps(local))

    config = load_config(config_dir=str(tmp_path))
    assert config["symbol"] == "ETH/USDT"  # local overlay

    original = sys.argv
    try:
        sys.argv = ["main.py", "--symbol", "DOGE/USDT"]
        args = parse_args()
    finally:
        sys.argv = original

    final_symbol = args.symbol or config.get("symbol")
    assert final_symbol == "DOGE/USDT"


def test_env_overrides_secrets(tmp_path, monkeypatch):
    base = {
        "symbol": "BTC/USDT",
        "timeframe": "1m",
        "limit": 500,
        "sma_short": 5,
        "sma_long": 20,
        "trade_size": 1.0,
        "confluence": {"members": ["sma", "rsi"], "required": 1},
        "api_key": "file_key",
        "api_secret": "file_secret",
        "api_passphrase": "file_pass",
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base))

    monkeypatch.setenv("TRADING_BOT_API_KEY", "env_key")
    monkeypatch.setenv("TRADING_BOT_API_SECRET", "env_secret")
    monkeypatch.setenv("TRADING_BOT_API_PASSPHRASE", "env_pass")

    config = load_config(config_dir=str(tmp_path))
    assert config["api_key"] == "env_key"
    assert config["api_secret"] == "env_secret"
    assert config["api_passphrase"] == "env_pass"


def test_missing_confluence_members_raises(tmp_path):
    base = {
        "symbol": "BTC/USDT",
        "timeframe": "1m",
        "limit": 500,
        "sma_short": 5,
        "sma_long": 20,
        "confluence": {"required": 2},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base))
    with pytest.raises(ValueError):
        load_config(config_dir=str(tmp_path))


def test_invalid_confluence_required_raises(tmp_path):
    base = {
        "symbol": "BTC/USDT",
        "timeframe": "1m",
        "limit": 500,
        "sma_short": 5,
        "sma_long": 20,
        "confluence": {"members": ["sma", "rsi"], "required": 3},
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(base))
    with pytest.raises(ValueError):
        load_config(config_dir=str(tmp_path))
