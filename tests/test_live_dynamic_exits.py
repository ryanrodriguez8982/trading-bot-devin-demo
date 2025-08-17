import importlib
import logging
from datetime import datetime, timezone

import pytest

from trading_bot.broker import PaperBroker


@pytest.mark.parametrize(
    "price_path,stop_pct,take_pct,log_msg",
    [
        ([100, 89], 0.1, 0.0, "Stop-loss triggered"),
        ([100, 111], 0.0, 0.1, "Take-profit target hit"),
    ],
)
def test_dynamic_exits(price_path, stop_pct, take_pct, log_msg, monkeypatch, tmp_path, caplog):
    main = importlib.import_module("trading_bot.main")

    prices = iter(price_path)

    class DummyExchange:
        def fetch_ticker(self, _):
            return {"last": next(prices)}

    exchange = DummyExchange()
    broker = PaperBroker(starting_cash=1000, fees_bps=0, slippage_bps=0)

    call = {"n": 0}

    def fake_analysis(*args, **kwargs):
        if call["n"] == 0:
            call["n"] += 1
            return [
                {
                    "action": "buy",
                    "price": 100.0,
                    "timestamp": datetime.now(timezone.utc),
                }
            ]
        return []

    monkeypatch.setattr(main, "run_single_analysis", fake_analysis)
    monkeypatch.setattr(main, "mark_signal_handled", lambda *a, **k: False)

    sleep_calls = {"n": 0}

    def fake_sleep(_):
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 2:
            raise KeyboardInterrupt()

    monkeypatch.setattr(main.time, "sleep", fake_sleep)

    with caplog.at_level(logging.INFO):
        with pytest.raises(KeyboardInterrupt):
            main.run_live_mode(
                ["BTC/USDT"],
                "1m",
                2,
                3,
                exchange=exchange,
                broker=broker,
                live_trade=False,
                trade_amount=1,
                fee_bps=0,
                stop_loss_pct=stop_pct,
                take_profit_pct=take_pct,
                interval_seconds=1,
                state_dir=str(tmp_path),
            )

    assert broker.get_open_positions() == {}
    assert log_msg in caplog.text
