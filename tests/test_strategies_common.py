import pandas as pd
import pytest


@pytest.mark.parametrize("strategy_name", ["sma", "rsi", "macd", "bbands"])
def test_empty_input_all_strategies(strategy_name):
    from trading_bot.strategies import STRATEGY_REGISTRY
    strategy = STRATEGY_REGISTRY[strategy_name].func
    df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    signals = strategy(df)
    assert signals == []


@pytest.mark.parametrize("strategy_name", ["sma", "rsi", "macd", "bbands"])
def test_flat_series_no_signals(strategy_name, df_constant_factory):
    from trading_bot.strategies import STRATEGY_REGISTRY
    strategy = STRATEGY_REGISTRY[strategy_name].func
    df = df_constant_factory(30)
    signals = strategy(df)
    assert signals == []


@pytest.mark.parametrize("strategy_name", ["sma", "rsi", "macd", "bbands"])
def test_missing_required_column_raises(strategy_name, df_constant_factory):
    from trading_bot.strategies import STRATEGY_REGISTRY
    strategy = STRATEGY_REGISTRY[strategy_name].func
    df = df_constant_factory(20).drop(columns=["close"])
    with pytest.raises(KeyError):
        strategy(df)
