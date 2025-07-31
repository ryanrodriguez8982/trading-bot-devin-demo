import pandas as pd
import numpy as np
import logging
import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from strategies.sma_strategy import sma_crossover_strategy
from strategies.rsi_strategy import rsi_crossover_strategy


def generate_ohlcv(length=30, constant=False):
    timestamps = pd.date_range('2024-01-01', periods=length, freq='1min')
    if constant:
        base = np.full(length, 100.0)
    else:
        base = 100 + np.cumsum(np.random.uniform(-1, 1, size=length))
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': base + np.random.uniform(-1, 1, size=length),
        'high': base + np.random.uniform(0, 2, size=length),
        'low': base - np.random.uniform(0, 2, size=length),
        'close': base,
        'volume': np.random.uniform(100, 1000, size=length)
    })
    return df


def inject_nans(df):
    idx = np.random.choice(len(df), size=max(1, len(df)//5), replace=False)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df.loc[idx, col] = np.nan
    return df


def inject_infinite(df):
    idx = np.random.choice(len(df))
    df.loc[idx, 'close'] = np.inf
    return df


def apply_price_jump(df):
    if len(df) > 1:
        idx = np.random.randint(1, len(df))
        df.loc[idx:, ['open', 'high', 'low', 'close']] *= 10
    return df


@pytest.mark.parametrize("strategy", [sma_crossover_strategy, rsi_crossover_strategy])
def test_random_ohlcv_shapes(strategy):
    for _ in range(5):
        length = np.random.randint(5, 50)
        df = generate_ohlcv(length)
        signals = strategy(df)
        assert isinstance(signals, list)
        for s in signals:
            assert {'timestamp', 'action', 'price'} <= set(s)


@pytest.mark.parametrize("mutator", [inject_nans, inject_infinite, apply_price_jump, lambda df: generate_ohlcv(len(df), constant=True)])
@pytest.mark.parametrize("strategy", [sma_crossover_strategy, rsi_crossover_strategy])
def test_corrupted_inputs_warn_or_raise(strategy, mutator, caplog):
    df = generate_ohlcv(10)  # short to trigger warnings
    df = mutator(df)
    with caplog.at_level(logging.WARNING):
        try:
            signals = strategy(df)
            assert isinstance(signals, list)
        except Exception as e:
            assert isinstance(e, (ValueError, KeyError))
        assert any(rec.levelno == logging.WARNING for rec in caplog.records)


@pytest.mark.parametrize("strategy", [sma_crossover_strategy, rsi_crossover_strategy])
def test_missing_columns_exception(strategy):
    df = generate_ohlcv(20)
    df = df.drop(columns=['close'])
    with pytest.raises(KeyError):
        strategy(df)
