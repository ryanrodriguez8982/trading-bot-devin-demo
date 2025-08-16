import pandas as pd
from trading_bot.strategies.macd_strategy import macd_strategy


def test_empty_input():
    df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    signals = macd_strategy(df)
    assert signals == []


def test_constant_price_series():
    timestamps = pd.date_range("2024-01-01", periods=30, freq="1min")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [100] * 30,
            "high": [100] * 30,
            "low": [100] * 30,
            "close": [100] * 30,
            "volume": [1000] * 30,
        }
    )
    signals = macd_strategy(df)
    assert signals == []


def test_macd_crossovers():
    data = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    timestamps = pd.date_range("2024-01-01", periods=len(data), freq="1min")
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": data,
            "high": data,
            "low": data,
            "close": data,
            "volume": [100] * len(data),
        }
    )
    signals = macd_strategy(df, fast_period=3, slow_period=6, signal_period=3)
    actions = [s["action"] for s in signals]
    assert "buy" in actions or "sell" in actions
