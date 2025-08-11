from trading_bot.strategies import STRATEGY_REGISTRY, list_strategies


def test_registry_contains_expected_strategies():
    assert "sma" in STRATEGY_REGISTRY
    assert "rsi" in STRATEGY_REGISTRY
    assert "macd" in STRATEGY_REGISTRY
    assert "bbands" in STRATEGY_REGISTRY
    assert "confluence" in STRATEGY_REGISTRY
    assert callable(STRATEGY_REGISTRY["sma"].func)


def test_confluence_metadata():
    meta = STRATEGY_REGISTRY["confluence"].metadata
    assert meta.get("requires") == ["sma", "rsi", "macd"]
    assert meta.get("required_count") == 2


def test_list_strategies_function():
    strategies = list_strategies()
    assert all(name in strategies for name in ["sma", "rsi", "macd", "bbands", "confluence"])


def test_strategy_naming_convention():
    for key, fn in STRATEGY_REGISTRY.items():
    if hasattr(fn, "__name__"):
        assert fn.__name__ == f"{key}_strategy"
        module_name = fn.__module__.split(".")[-1]
        assert module_name == f"{key}_strategy"
    elif hasattr(fn, "func") and hasattr(fn.func, "__name__"):
        assert fn.func.__name__ == f"{key}_strategy"
        module_name = fn.func.__module__.split(".")[-1]
        assert module_name == f"{key}_strategy"
