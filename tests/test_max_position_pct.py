import pandas as pd
import pytest

from trading_bot.backtester import simulate_equity


def _basic_df(prices):
    timestamps = pd.date_range("2024-01-01", periods=len(prices), freq="1min")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": [1000] * len(prices),
        }
    )


def test_position_never_exceeds_cap():
    df = _basic_df([400, 400, 400])
    signals = [
        {"timestamp": df.iloc[0]["timestamp"], "action": "buy"},
        {"timestamp": df.iloc[1]["timestamp"], "action": "buy"},
        {"timestamp": df.iloc[2]["timestamp"], "action": "buy"},
    ]
    _, stats = simulate_equity(
        df,
        signals,
        initial_capital=1000,
        trade_size=1.0,
        max_position_pct=0.5,
    )
    assert stats["final_position_qty"] == pytest.approx(1.25)
    assert stats["cash"] == pytest.approx(500)


def test_skips_when_no_equity():
    df = _basic_df([1000])
    signals = [{"timestamp": df.iloc[0]["timestamp"], "action": "buy"}]
    _, stats = simulate_equity(
        df,
        signals,
        initial_capital=0.0,
        trade_size=1.0,
        max_position_pct=0.1,
    )
    assert stats["final_position_qty"] == 0
    assert stats["cash"] == pytest.approx(0.0)
