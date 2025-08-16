import pandas as pd
import pytest

from trading_bot.tuner import walk_forward_optimize
from trading_bot.strategies import STRATEGY_REGISTRY, Strategy


def test_walk_forward_selects_best_params(tmp_path):
    timestamps = pd.date_range("2024-01-01", periods=8, freq="1min")
    prices = [100 + i for i in range(8)]
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": [1000] * 8,
        }
    )
    csv_file = tmp_path / "data.csv"
    df.to_csv(csv_file, index=False)

    def hold_strategy(df, hold=1):
        if len(df) <= hold:
            return []
        buy_ts = df["timestamp"].iloc[0]
        sell_ts = df["timestamp"].iloc[min(hold, len(df) - 1)]
        return [
            {"timestamp": buy_ts, "action": "buy"},
            {"timestamp": sell_ts, "action": "sell"},
        ]

    STRATEGY_REGISTRY["hold"] = Strategy(hold_strategy)
    try:
        results = walk_forward_optimize(
            str(csv_file),
            strategy="hold",
            param_grid={"hold": [1, 2]},
            train_size=5,
            test_size=3,
        )
    finally:
        del STRATEGY_REGISTRY["hold"]

    assert results
    first = results[0]
    assert first["best_params"]["hold"] == 2
    assert first["test_stats"]["net_pnl"] == pytest.approx(2.0)
