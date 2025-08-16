from trading_bot.strategies import (
    STRATEGY_REGISTRY,
    list_strategies,
    register_strategy,
)


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
    expected = ["sma", "rsi", "macd", "bbands", "confluence"]
    assert all(name in strategies for name in expected)


def test_strategy_naming_convention():
    for key, strategy in STRATEGY_REGISTRY.items():
        func = getattr(strategy, "func", None)
        assert callable(func), f"Strategy '{key}' does not have a callable 'func'"

        func_name = getattr(func, "__name__", "<missing>")
        expected_name = f"{key}_strategy"
        assert func_name == expected_name, (
            f"Strategy '{key}' has mismatched function name: expected '{expected_name}', got '{func_name}'"
        )

        module_name = getattr(func, "__module__", "").split(".")[-1]
        assert module_name == expected_name, (
            f"Strategy '{key}' is in incorrect module: expected '{expected_name}.py', got '{module_name}.py'"
        )


def test_register_strategy_decorator():
    @register_strategy("dummy")
    def dummy_strategy(df):
        return []

    try:
        assert "dummy" in STRATEGY_REGISTRY
        assert STRATEGY_REGISTRY["dummy"].func is dummy_strategy
    finally:
        del STRATEGY_REGISTRY["dummy"]


def test_registry_executes_registered_strategies():
    """Ensure strategies retrieved from the registry execute correctly."""
    import numpy as np
    import pandas as pd
    from trading_bot.strategies.sma_strategy import sma_strategy
    from trading_bot.strategies.rsi_strategy import rsi_strategy
    from trading_bot.strategies.macd_strategy import macd_strategy
    from trading_bot.strategies.bbands_strategy import bbands_strategy
    from trading_bot.strategies.confluence_strategy import confluence_strategy

    periods = 60
    timestamps = pd.date_range("2024-01-01", periods=periods, freq="1min")
    prices = np.sin(np.linspace(0, 4 * np.pi, periods)) * 10 + 100
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": prices,
            "high": prices + 1,
            "low": prices - 1,
            "close": prices,
            "volume": 1_000,
        }
    )

    strategy_map = {
        "sma": sma_strategy,
        "rsi": rsi_strategy,
        "macd": macd_strategy,
        "bbands": bbands_strategy,
        "confluence": confluence_strategy,
    }

    for name, func in strategy_map.items():
        registry_func = STRATEGY_REGISTRY[name].func
        assert registry_func is func
        assert registry_func(df) == func(df)
