import importlib
import logging
from datetime import datetime, timezone

import pytest

from trading_bot.broker import PaperBroker


def test_min_trade_interval_blocks_consecutive_trades(monkeypatch, tmp_path, caplog):
    main = importlib.import_module("trading_bot.main")

    def fake_analysis(*args, **kwargs):
        return [
            {
                "action": "buy",
                "price": 10.0,
                "timestamp": datetime.now(timezone.utc),
            }
        ]

    monkeypatch.setattr(main, "run_single_analysis", fake_analysis)
    monkeypatch.setattr(main, "mark_signal_handled", lambda *a, **k: False)

    broker = PaperBroker(starting_cash=100, fees_bps=0, slippage_bps=0)

    sleep_calls = {"count": 0}

    def fake_sleep(_):
        sleep_calls["count"] += 1
        if sleep_calls["count"] >= 2:
            raise KeyboardInterrupt()

    monkeypatch.setattr(main.time, "sleep", fake_sleep)

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
                min_trade_interval_sec=5,
            )

    assert broker.get_open_positions() == {"BTC/USDT": pytest.approx(1)}
    assert "skipped" in caplog.text and "last trade" in caplog.text
