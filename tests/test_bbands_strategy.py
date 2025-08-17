import pandas as pd
from trading_bot.strategies.bbands_strategy import bbands_strategy


def test_bbands_crossings():
    values = [100] * 20 + [80, 100, 120, 100]
    timestamps = pd.date_range("2024-01-01", periods=len(values), freq="1min")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": values,
            "high": values,
            "low": values,
            "close": values,
            "volume": [100] * len(values),
        }
    )
    signals = bbands_strategy(df, window=20, num_std=2)
    actions = [s["action"] for s in signals]
    assert "buy" in actions or "sell" in actions
