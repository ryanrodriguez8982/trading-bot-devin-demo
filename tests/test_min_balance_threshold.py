import logging
from datetime import datetime, timezone

import importlib
import pytest

from trading_bot.broker import PaperBroker


def test_min_balance_threshold_blocks_buys(monkeypatch, tmp_path, caplog):
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

    def stop_sleep(_):
        raise KeyboardInterrupt()

    monkeypatch.setattr(main.time, "sleep", stop_sleep)

    broker = PaperBroker(starting_cash=50, fees_bps=0, slippage_bps=0)

    with caplog.at_level(logging.WARNING):
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
                min_balance_threshold=100,
            )

    assert broker.get_open_positions() == {}
    assert broker.get_balances()["cash"] == pytest.approx(50)
    assert "Balance below minimum $100" in caplog.text
