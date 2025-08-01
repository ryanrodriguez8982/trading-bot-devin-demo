import pandas as pd

from trading_bot.performance import compute_equity_curve


def test_compute_equity_curve_basic():
    signals = [
        {
            "timestamp": pd.Timestamp("2024-01-01 00:00:00"),
            "action": "buy",
            "price": 100,
        },
        {
            "timestamp": pd.Timestamp("2024-01-01 01:00:00"),
            "action": "sell",
            "price": 110,
        },
        {
            "timestamp": pd.Timestamp("2024-01-01 02:00:00"),
            "action": "buy",
            "price": 90,
        },
        {
            "timestamp": pd.Timestamp("2024-01-01 03:00:00"),
            "action": "sell",
            "price": 100,
        },
    ]

    df, stats = compute_equity_curve(signals, initial_balance=1000)

    assert not df.empty
    assert stats["num_trades"] == 2
    assert round(stats["win_rate"], 2) == 100.0
    assert round(stats["total_return_abs"], 2) == 222.22
