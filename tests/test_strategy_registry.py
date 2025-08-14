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
    for key, strategy in STRATEGY_REGISTRY.items():
        func = getattr(strategy, "func", None)
        assert callable(func), f"Strategy '{key}' does not have a callable 'func'"
        
        func_name = getattr(func, "__name__", "<missing>")
        expected = f"{key}_strategy"
        assert func_name == expected, (
            f"Strategy '{key}' has mismatched function name: expected '{expected}', got '{func_name}'"
        )

        module_name = getattr(func, "__module__", "").split(".")[-1]
        assert module_name == expected, (
            f"Strategy '{key}' is in incorrect module: expected '{expected}.py', got '{module_name}.py'"
        )