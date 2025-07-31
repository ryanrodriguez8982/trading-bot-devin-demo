import pandas as pd
import pytest

from trading_bot.backtester import load_csv_data, run_backtest

REQUIRED_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']

def write_csv(tmp_path, df):
    csv_path = tmp_path / "data.csv"
    df.to_csv(csv_path, index=False)
    return csv_path

def test_missing_columns(tmp_path):
    df = pd.DataFrame({
        'timestamp': [pd.Timestamp('2024-01-01')],
        'open': [1],
        'high': [1],
        'close': [1],
        'volume': [1],
    })  # missing 'low'
    csv_file = write_csv(tmp_path, df)
    with pytest.raises(ValueError):
        load_csv_data(csv_file)

def test_empty_csv(tmp_path):
    df = pd.DataFrame(columns=REQUIRED_COLUMNS)
    csv_file = write_csv(tmp_path, df)
    with pytest.raises(ValueError):
        load_csv_data(csv_file)

def test_inconsistent_timestamps(tmp_path):
    df = pd.DataFrame({
        'timestamp': ['2024-01-02', '2024-01-01'],
        'open': [1, 2],
        'high': [1, 2],
        'low': [1, 2],
        'close': [1, 2],
        'volume': [1, 2],
    })
    csv_file = write_csv(tmp_path, df)
    with pytest.raises(ValueError):
        load_csv_data(csv_file)

def test_backtest_different_strategies(tmp_path):
    timestamps = pd.date_range('2024-01-01', periods=30, freq='1min')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100]*30,
        'high': [105]*30,
        'low': [95]*30,
        'close': [100 + i for i in range(30)],
        'volume': [1000]*30
    })
    csv_file = write_csv(tmp_path, df)

    result_sma = run_backtest(str(csv_file), strategy='sma')
    result_rsi = run_backtest(str(csv_file), strategy='rsi')
    result_macd = run_backtest(str(csv_file), strategy='macd')
    result_boll = run_backtest(str(csv_file), strategy='bollinger')

    assert 'net_pnl' in result_sma
    assert 'net_pnl' in result_rsi
    assert 'net_pnl' in result_macd
    assert 'net_pnl' in result_boll


def test_backtest_saves_outputs(tmp_path):
    timestamps = pd.date_range('2024-01-01', periods=10, freq='1min')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100]*10,
        'high': [105]*10,
        'low': [95]*10,
        'close': [100 + i for i in range(10)],
        'volume': [1000]*10
    })
    csv_file = write_csv(tmp_path, df)

    equity_out = tmp_path / 'equity_curve.csv'
    stats_out = tmp_path / 'summary_stats.json'
    chart_out = tmp_path / 'equity_chart.png'

    run_backtest(str(csv_file), strategy='sma', plot=True,
                equity_out=str(equity_out), stats_out=str(stats_out), chart_out=str(chart_out))

    assert equity_out.exists()
    assert stats_out.exists()
    assert chart_out.exists()

