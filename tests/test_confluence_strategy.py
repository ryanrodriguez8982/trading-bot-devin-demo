import pandas as pd

from trading_bot.strategies.confluence_strategy import confluence_strategy
from trading_bot import strategies as strategies_module


def test_confluence_emits_when_quorum(monkeypatch):
    def strat_a(df):
        ts = df.iloc[2]["timestamp"]
        price = df.iloc[2]["close"]
        return [{"timestamp": ts, "action": "buy", "price": price}]

    def strat_b(df):
        ts = df.iloc[2]["timestamp"]
        price = df.iloc[2]["close"]
        return [{"timestamp": ts, "action": "buy", "price": price}]

    def strat_c(df):
        ts = df.iloc[3]["timestamp"]
        price = df.iloc[3]["close"]
        return [{"timestamp": ts, "action": "sell", "price": price}]

    monkeypatch.setattr(
        strategies_module,
        "STRATEGY_REGISTRY",
        {"a": strat_a, "b": strat_b, "c": strat_c},
    )

    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="T"),
            "open": [1] * 5,
            "high": [1] * 5,
            "low": [1] * 5,
            "close": [1] * 5,
            "volume": [0] * 5,
        }
    )

    signals = confluence_strategy(df, members=["a", "b", "c"], required=2)
    assert len(signals) == 1
    assert signals[0]["action"] == "buy"
