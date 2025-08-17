import pandas as pd
from trading_bot.strategies.rsi_strategy import rsi_strategy


def test_rsi_boundary_crossings():
    data = [29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 71, 70, 69, 68, 67, 66, 65, 64, 63, 62]
    timestamps = pd.date_range("2024-01-01", periods=len(data), freq="1min")
    df = pd.DataFrame(
        {"timestamp": timestamps, "open": data, "high": data, "low": data, "close": data, "volume": [100] * len(data)}
    )
    signals = rsi_strategy(df, period=2, lower_thresh=30, upper_thresh=70)
    actions = [s["action"] for s in signals]
    assert "buy" in actions or "sell" in actions
