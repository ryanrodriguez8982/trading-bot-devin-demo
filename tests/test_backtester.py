import pandas as pd
import pytest
from typing import Any

from trading_bot.backtester import (
    load_csv_data,
    run_backtest,
    simulate_equity,
    generate_signals,
)
from trading_bot.strategies import STRATEGY_REGISTRY, Strategy


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


@pytest.mark.parametrize("strategy_name", STRATEGY_REGISTRY.keys())
def test_backtest_different_strategies(tmp_path, strategy_name):
    timestamps = pd.date_range('2024-01-01', periods=30, freq='1min')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100] * 30,
        'high': [105] * 30,
        'low': [95] * 30,
        'close': [100 + i for i in range(30)],
        'volume': [1000] * 30,
    })
    csv_file = write_csv(tmp_path, df)

    result = run_backtest(str(csv_file), strategy=strategy_name)

    assert 'net_pnl' in result


def test_generate_signals_dispatch(tmp_path):
    """Ensure generate_signals calls strategies with only supported params."""
    timestamps = pd.date_range('2024-01-01', periods=5, freq='1min')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100] * 5,
        'high': [105] * 5,
        'low': [95] * 5,
        'close': [100 + i for i in range(5)],
        'volume': [1000] * 5,
    })

    called = {}

    def minimal_strategy(df):  # expects only df
        called['yes'] = True
        return []

    STRATEGY_REGISTRY['minimal'] = Strategy(minimal_strategy)
    try:
        generate_signals(df, strategy='minimal')
    finally:
        del STRATEGY_REGISTRY['minimal']

    assert called.get('yes') is True


def test_run_backtest_accepts_strategy_kwargs(tmp_path):
    """run_backtest should forward kwargs to the chosen strategy."""
    timestamps = pd.date_range('2024-01-01', periods=5, freq='1min')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100] * 5,
        'high': [105] * 5,
        'low': [95] * 5,
        'close': [100 + i for i in range(5)],
        'volume': [1000] * 5,
    })
    csv_file = write_csv(tmp_path, df)

    captured: dict[str, Any] = {}

    def custom_strategy(df, foo=None, **kwargs):
        captured['foo'] = foo
        return []

    STRATEGY_REGISTRY['custom'] = Strategy(custom_strategy)
    try:
        run_backtest(str(csv_file), strategy='custom', foo=42)
    finally:
        del STRATEGY_REGISTRY['custom']

    assert captured.get('foo') == 42


def test_backtest_saves_outputs(tmp_path):
    timestamps = pd.date_range('2024-01-01', periods=10, freq='1min')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100] * 10,
        'high': [105] * 10,
        'low': [95] * 10,
        'close': [100 + i for i in range(10)],
        'volume': [1000] * 10,
    })
    csv_file = write_csv(tmp_path, df)

    equity_out = tmp_path / 'equity_curve.csv'
    stats_out = tmp_path / 'summary_stats.json'
    chart_out = tmp_path / 'equity_chart.png'

    run_backtest(
        str(csv_file),
        strategy='sma',
        plot=True,
        equity_out=str(equity_out),
        stats_out=str(stats_out),
        chart_out=str(chart_out),
    )

    assert equity_out.exists()
    assert stats_out.exists()
    assert chart_out.exists()


def test_fees_slippage_pnl_consistency():
    timestamps = pd.date_range('2024-01-01', periods=2, freq='1min')
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100, 110],
        'high': [100, 110],
        'low': [100, 110],
        'close': [100, 110],
        'volume': [1000, 1000],
    })
    signals = [
        {'timestamp': timestamps[0], 'action': 'buy'},
        {'timestamp': timestamps[1], 'action': 'sell'},
    ]
    _, stats = simulate_equity(
        df,
        signals,
        initial_capital=1000,
        trade_size=1,
        fees_bps=10,
        slippage_bps=25,
    )
    buy_exec = 100 * (1 + 25 / 10_000)
    sell_exec = 110 * (1 - 25 / 10_000)
    fee_buy = buy_exec * 10 / 10_000
    fee_sell = sell_exec * 10 / 10_000
    expected = (sell_exec - buy_exec) - (fee_buy + fee_sell)
    assert stats['net_pnl'] == pytest.approx(expected)
