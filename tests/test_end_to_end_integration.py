import logging
from typing import List

import pandas as pd
import pytest

from trading_bot.broker import PaperBroker
import importlib

main = importlib.import_module("trading_bot.main")


def test_end_to_end_integration(monkeypatch, tmp_path, caplog):
    call = {"i": 0}

    def fake_fetch(symbol: str, timeframe: str, limit: int, exchange=None):
        datasets: List[List[float]] = [
            [1, 1, 1, 2],  # generates a buy signal
            [2, 2, 2, 1],  # generates a sell signal
        ]
        data = datasets[call["i"]]
        start = pd.Timestamp("2023-01-01", tz="UTC") + pd.Timedelta(minutes=call["i"] * 4)
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range(start, periods=len(data), freq="min", tz="UTC"),
                "open": data,
                "high": data,
                "low": data,
                "close": data,
                "volume": [1] * len(data),
            }
        )
        call["i"] += 1
        return df

    monkeypatch.setattr(main, "fetch_market_data", fake_fetch)

    sleep_calls = {"count": 0}

    def fake_sleep(_):
        sleep_calls["count"] += 1
        if sleep_calls["count"] >= 2:
            raise KeyboardInterrupt()

    monkeypatch.setattr(main.time, "sleep", fake_sleep)

    broker = PaperBroker(starting_cash=1000, fees_bps=0, slippage_bps=0)

    with caplog.at_level(logging.INFO):
        with pytest.raises(KeyboardInterrupt):
            main.run_live_mode(
                ["BTC/USDT"],
                "1m",
                2,
                3,
                broker=broker,
                live_trade=False,
                trade_amount=1,
                interval_seconds=1,
                state_dir=str(tmp_path),
            )

    assert caplog.text.count('"status": "executed"') == 2
    assert broker.get_open_positions() == {}
    balances = broker.get_balances()
    assert balances["cash"] == pytest.approx(999)
