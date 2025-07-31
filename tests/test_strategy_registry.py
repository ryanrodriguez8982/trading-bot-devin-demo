from strategies import STRATEGY_REGISTRY, list_strategies


def test_registry_contains_expected_strategies():
    assert "sma" in STRATEGY_REGISTRY
    assert "rsi" in STRATEGY_REGISTRY
    assert "macd" in STRATEGY_REGISTRY
    assert callable(STRATEGY_REGISTRY["sma"])


def test_list_strategies_function():
    strategies = list_strategies()
    assert "sma" in strategies and "rsi" in strategies and "macd" in strategies
