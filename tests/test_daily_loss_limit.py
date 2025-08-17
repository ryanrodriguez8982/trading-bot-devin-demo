import logging
from datetime import datetime, timezone
import importlib

import pytest

from trading_bot.broker import PaperBroker
from trading_bot.risk.config import RiskConfig


def test_daily_loss_limit_halts_and_resets(monkeypatch, tmp_path, caplog):
    main = importlib.import_module("trading_bot.main")

    broker = PaperBroker(starting_cash=100, fees_bps=0, slippage_bps=0)
    risk_cfg = RiskConfig.from_dict({"daily_loss_limit_pct": 0.05, "max_drawdown": {"monthly_pct": 0.0}})

    iteration = {"count": 0}

    class FakeDateTime(datetime):
        current = datetime(2025, 1, 1, tzinfo=timezone.utc)

        @classmethod
        def now(cls, tz=None):  # noqa: D401 - simple stub
            return cls.current

    actions = ["buy", "sell", "buy", "buy"]
    prices = [100, 50, 50, 50]
    days = [0, 0, 0, 1]

    def fake_analysis(*args, **kwargs):
        idx = iteration["count"]
        return [
            {
                "action": actions[idx],
                "price": prices[idx],
                "timestamp": FakeDateTime.now(timezone.utc),
            }
        ]

    def fake_sleep(_):
        iteration["count"] += 1
        if iteration["count"] >= len(actions):
            raise KeyboardInterrupt()
        FakeDateTime.current = datetime(2025, 1, 1 + days[iteration["count"]], tzinfo=timezone.utc)

    monkeypatch.setattr(main, "run_single_analysis", fake_analysis)
    monkeypatch.setattr(main.time, "sleep", fake_sleep)
    monkeypatch.setattr(main, "datetime", FakeDateTime)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(KeyboardInterrupt):
            main.run_live_mode(
                ["BTC/USDT"],
                "1m",
                2,
                3,
                broker=broker,
                trade_amount=1,
                fee_bps=0,
                interval_seconds=1,
                state_dir=str(tmp_path),
                risk_config=risk_cfg,
            )

    assert "Daily max loss exceeded" in caplog.text
    assert broker.get_open_positions()["BTC/USDT"] == pytest.approx(1)
    assert broker.portfolio.realized_pnl == pytest.approx(-50)
