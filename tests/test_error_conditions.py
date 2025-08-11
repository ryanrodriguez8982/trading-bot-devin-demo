import json
import logging
import pandas as pd
import pytest
import ccxt

from trading_bot.data_fetch import fetch_btc_usdt_data
from trading_bot.utils.retry import RetryPolicy
from trading_bot.utils.config import load_config
from trading_bot.backtester import run_backtest


class TimeoutExchange:
    id = "timeout"

    def __init__(self):
        self.calls = 0

    def fetch_ohlcv(self, *args, **kwargs):
        self.calls += 1
        raise ccxt.NetworkError("timeout")


def test_fetch_raises_after_retries_logs_error(caplog):
    exch = TimeoutExchange()
    policy = RetryPolicy(retries=2, backoff=0, jitter=0)
    with caplog.at_level(logging.ERROR):
        with pytest.raises(ccxt.NetworkError):
            fetch_btc_usdt_data(exchange=exch, retry_policy=policy)
    assert exch.calls == 3  # retries + initial attempt
    error_messages = [rec.message for rec in caplog.records]
    assert any("network error after 2 retries" in msg for msg in error_messages)


def test_load_config_missing_required_field(tmp_path):
    config_data = {
        "timeframe": "1m",
        "limit": 500,
        "sma_short": 5,
        "sma_long": 20,
        "trade_size": 1.0,
        "rsi_period": 14,
        "rsi_lower": 30,
        "rsi_upper": 70,
        # missing symbol and confluence
    }
    (tmp_path / "config.json").write_text(json.dumps(config_data))
    with pytest.raises(ValueError) as exc:
        load_config(config_dir=str(tmp_path))
    assert "Invalid configuration" in str(exc.value)


def test_run_backtest_unknown_strategy(tmp_path):
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=3, freq="1min"),
        "open": [1, 1, 1],
        "high": [1, 1, 1],
        "low": [1, 1, 1],
        "close": [1, 1, 1],
        "volume": [1, 1, 1],
    })
    csv_path = tmp_path / "data.csv"
    df.to_csv(csv_path, index=False)
    with pytest.raises(ValueError) as exc:
        run_backtest(str(csv_path), strategy="unknown")
    assert "Unknown strategy" in str(exc.value)
