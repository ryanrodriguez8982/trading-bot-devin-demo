import pandas as pd

from trading_bot.backtest.optimizer import parse_optimize_args, train_valid_split


def test_parse_optimize_args_macd():
    tokens = [
        "strategy=macd",
        "fast=[8,12]",
        "slow=[21,26]",
        "signal=[9,12]",
        "split=70/30",
        "metric=sharpe",
    ]
    opts = parse_optimize_args(tokens)
    assert opts["strategy"] == "macd"
    assert opts["param_grid"]["fast"] == [8, 12]
    assert opts["split"] == (0.7, 0.3)
    assert opts["metric"] == "sharpe"


def test_train_valid_split_sizes():
    df = pd.DataFrame({"a": range(10)})
    train, valid = train_valid_split(df, (0.7, 0.3))
    assert len(train) == 7
    assert len(valid) == 3
