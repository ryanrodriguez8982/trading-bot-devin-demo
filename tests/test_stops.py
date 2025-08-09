import pandas as pd
import pytest

from trading_bot.backtester import simulate_equity


def make_df(prices):
    ts = pd.date_range('2024-01-01', periods=len(prices), freq='1min')
    rows = []
    for i, p in enumerate(prices):
        rows.append({
            'timestamp': ts[i],
            'open': p['open'],
            'high': p['high'],
            'low': p['low'],
            'close': p['close'],
            'volume': 1_000,
        })
    return pd.DataFrame(rows)


def run_scenario(bars):
    df = make_df(bars)
    signals = [{'timestamp': df['timestamp'].iloc[0], 'action': 'buy'}]
    _, stats = simulate_equity(
        df,
        signals,
        initial_capital=100,
        trade_size=1,
        fee_bps=0,
        slippage_bps=0,
        stop_loss_pct=0.10,
        take_profit_rr=2.0,
    )
    return stats['net_pnl']


def run_trailing(bars):
    df = make_df(bars)
    signals = [{'timestamp': df['timestamp'].iloc[0], 'action': 'buy'}]
    _, stats = simulate_equity(
        df,
        signals,
        initial_capital=100,
        trade_size=1,
        fee_bps=0,
        slippage_bps=0,
        trailing_stop_pct=0.05,
    )
    return stats['net_pnl']


def test_stop_loss_hit():
    net = run_scenario([
        {'open': 100, 'high': 100, 'low': 100, 'close': 100},
        {'open': 100, 'high': 105, 'low': 89, 'close': 95},
        {'open': 95, 'high': 95, 'low': 95, 'close': 95},
    ])
    assert net == pytest.approx(-10)


def test_take_profit_hit():
    net = run_scenario([
        {'open': 100, 'high': 100, 'low': 100, 'close': 100},
        {'open': 100, 'high': 125, 'low': 95, 'close': 110},
        {'open': 110, 'high': 110, 'low': 110, 'close': 110},
    ])
    assert net == pytest.approx(20)


def test_both_hit_stop_first():
    net = run_scenario([
        {'open': 100, 'high': 100, 'low': 100, 'close': 100},
        {'open': 100, 'high': 125, 'low': 85, 'close': 110},
        {'open': 110, 'high': 110, 'low': 110, 'close': 110},
    ])
    assert net == pytest.approx(-10)


def test_neither_hit():
    net = run_scenario([
        {'open': 100, 'high': 100, 'low': 100, 'close': 100},
        {'open': 100, 'high': 110, 'low': 95, 'close': 105},
        {'open': 105, 'high': 105, 'low': 105, 'close': 105},
    ])
    assert net == pytest.approx(5)


def test_trailing_stop_hit():
    net = run_trailing([
        {'open': 100, 'high': 100, 'low': 100, 'close': 100},
        {'open': 115, 'high': 120, 'low': 115, 'close': 119},
        {'open': 119, 'high': 119, 'low': 113, 'close': 115},
    ])
    assert net == pytest.approx(14)

