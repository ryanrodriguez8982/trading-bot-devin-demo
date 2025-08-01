import pandas as pd
from trading_bot.tuner import tune


def test_tune_returns_sorted_results(tmp_path):
    timestamps = pd.date_range('2024-01-01', periods=10, freq='1min')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100]*10,
        'high': [101]*10,
        'low': [99]*10,
        'close': [100 + i for i in range(10)],
        'volume': [1000]*10,
    })
    csv_file = tmp_path / 'data.csv'
    df.to_csv(csv_file, index=False)

    grid = {'sma_short': [2, 3], 'sma_long': [5, 6]}
    results = tune(str(csv_file), strategy='sma', param_grid=grid)

    assert isinstance(results, list) and results
    net_pnls = [r['net_pnl'] for r in results]
    assert net_pnls == sorted(net_pnls, reverse=True)

