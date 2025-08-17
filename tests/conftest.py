import pandas as pd
import numpy as np
import pytest

from trading_bot.strategies.sma_strategy import sma_strategy
from trading_bot.strategies.rsi_strategy import rsi_strategy
from trading_bot.strategies.macd_strategy import macd_strategy
from trading_bot.strategies.bbands_strategy import bbands_strategy


@pytest.fixture(scope="session")
def strategies():
    return [sma_strategy, rsi_strategy, macd_strategy, bbands_strategy]


@pytest.fixture(scope="session")
def make_timestamps():
    def _make(n, freq="1min"):
        return pd.date_range("2024-01-01", periods=n, freq=freq)
    return _make


@pytest.fixture(scope="session")
def df_constant_factory(make_timestamps):
    def _make(n, price=100.0, volume=1000.0):
        ts = make_timestamps(n)
        data = {
            "timestamp": ts,
            "open": [price] * n,
            "high": [price] * n,
            "low": [price] * n,
            "close": [price] * n,
            "volume": [volume] * n,
        }
        return pd.DataFrame(data)
    return _make


@pytest.fixture(scope="session")
def df_linear_factory(make_timestamps):
    def _make(n, start=100.0, step=1.0, volume=1000.0):
        ts = make_timestamps(n)
        prices = [start + i * step for i in range(n)]
        data = {
            "timestamp": ts,
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": [volume] * n,
        }
        return pd.DataFrame(data)
    return _make


@pytest.fixture(scope="session")
def generate_ohlcv_factory(make_timestamps):
    def _make(length=30, constant=False):
        timestamps = make_timestamps(length)
        if constant:
            base = np.full(length, 100.0)
        else:
            base = 100 + np.cumsum(np.random.uniform(-1, 1, size=length))
        df = pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": base + np.random.uniform(-1, 1, size=length),
                "high": base + np.random.uniform(0, 2, size=length),
                "low": base - np.random.uniform(0, 2, size=length),
                "close": base,
                "volume": np.random.uniform(100, 1000, size=length),
            }
        )
        return df
    return _make


@pytest.fixture(scope="session")
def mutators():
    def inject_nans(df):
        idx = np.random.choice(len(df), size=max(1, len(df) // 5), replace=False)
        for col in ["open", "high", "low", "close", "volume"]:
            df.loc[idx, col] = np.nan
        return df

    def inject_infinite(df):
        if len(df) > 0:
            idx = np.random.choice(len(df))
            df.loc[idx, "close"] = np.inf
        return df

    def apply_price_jump(df):
        if len(df) > 1:
            idx = np.random.randint(1, len(df))
            df.loc[idx:, ["open", "high", "low", "close"]] *= 10
        return df

    return [inject_nans, inject_infinite, apply_price_jump]
