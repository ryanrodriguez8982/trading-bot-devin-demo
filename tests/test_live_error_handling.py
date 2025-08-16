import logging
import pytest


def test_live_mode_handles_iteration_errors(monkeypatch, tmp_path, caplog):
    import importlib

    main = importlib.import_module("trading_bot.main")

    def bad_analysis(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(main, "run_single_analysis", bad_analysis)

    monkeypatch.setattr(main, "default_retry", lambda: main.RetryPolicy(retries=0))

    def stop_sleep(_):
        raise KeyboardInterrupt()

    monkeypatch.setattr(main.time, "sleep", stop_sleep)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(KeyboardInterrupt):
            main.run_live_mode(
                ["BTC/USDT"],
                "1m",
                5,
                10,
                interval_seconds=1,
                state_dir=str(tmp_path),
            )
    assert "Error during live trading iteration" in caplog.text
