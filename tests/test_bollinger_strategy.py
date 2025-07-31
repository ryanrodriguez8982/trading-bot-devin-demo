import pandas as pd
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from strategies.bollinger_strategy import bollinger_bands_strategy


def test_empty_input():
    df = pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    signals = bollinger_bands_strategy(df)
    assert signals == []


def test_flat_price_series():
    timestamps = pd.date_range('2024-01-01', periods=20, freq='1min')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100]*20,
        'high': [100]*20,
        'low': [100]*20,
        'close': [100]*20,
        'volume': [1000]*20
    })
    signals = bollinger_bands_strategy(df, window=5)
    assert signals == []


def test_bollinger_crossings():
    values = [100]*20 + [80, 100, 120, 100]
    timestamps = pd.date_range('2024-01-01', periods=len(values), freq='1min')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': values,
        'high': values,
        'low': values,
        'close': values,
        'volume': [100]*len(values)
    })
    signals = bollinger_bands_strategy(df, window=20, num_std=2)
    actions = [s['action'] for s in signals]
    assert 'buy' in actions or 'sell' in actions
