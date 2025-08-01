import pandas as pd
import logging
import os
import json
from datetime import datetime

# ? Absolute import for package compatibility
from trading_bot.signal_logger import log_signals_to_db
from trading_bot.strategies import STRATEGY_REGISTRY

REQUIRED_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']


def load_csv_data(csv_path):
    """Load historical OHLCV data from CSV."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    if df.empty:
        raise ValueError("CSV file contains no rows")

    df['timestamp'] = pd.to_datetime(df['timestamp'])
    if not df['timestamp'].is_monotonic_increasing:
        raise ValueError("Timestamps must be strictly increasing")

    return df


def compute_drawdown(equity_curve):
    max_drawdown = 0.0
    peak = equity_curve[0]
    for value in equity_curve:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak if peak != 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    return max_drawdown * 100


def simulate_equity(df, signals, initial_capital=10000):
    cash = initial_capital
    position = 0
    equity_history = []
    open_price = None
    trade_profits = []

    signal_iter = iter(sorted(signals, key=lambda x: x['timestamp']))
    current_signal = next(signal_iter, None)

    for _, row in df.iterrows():
        ts = row['timestamp']
        price = row['close']

        while current_signal is not None and current_signal['timestamp'] <= ts:
            action = current_signal['action']
            if action == 'buy' and cash >= price:
                cash -= price
                position += 1
                open_price = price
            elif action == 'sell' and position > 0:
                cash += price
                position -= 1
                if open_price is not None:
                    trade_profits.append(price - open_price)
                    open_price = None
            current_signal = next(signal_iter, None)

        equity = cash + position * price
        equity_history.append(equity)

    final_equity = cash + position * df.iloc[-1]['close']
    net_pnl = final_equity - initial_capital
    win_rate = 0.0
    if trade_profits:
        wins = len([p for p in trade_profits if p > 0])
        win_rate = wins / len(trade_profits) * 100

    max_drawdown = compute_drawdown(equity_history)
    return equity_history, {
        'net_pnl': float(net_pnl),
        'win_rate': float(win_rate),
        'max_drawdown': float(max_drawdown),
    }


def run_backtest(csv_path, strategy='sma', sma_short=5, sma_long=20,
                 rsi_period=14, macd_fast=12, macd_slow=26, macd_signal=9,
                 bollinger_window=20, bollinger_std=2, plot=False,
                 equity_out=None, stats_out=None, chart_out=None):
    """Run backtest on CSV data using specified strategy."""
    df = load_csv_data(csv_path)

    if strategy not in STRATEGY_REGISTRY:
        raise ValueError("Unknown strategy")

    strategy_fn = STRATEGY_REGISTRY[strategy]
    if strategy == 'rsi':
        signals = strategy_fn(df, period=rsi_period)
    elif strategy == 'macd':
        signals = strategy_fn(df, fast_period=macd_fast,
                              slow_period=macd_slow,
                              signal_period=macd_signal)
    elif strategy == 'bollinger':
        signals = strategy_fn(df, window=bollinger_window,
                              num_std=bollinger_std)
    else:
        signals = strategy_fn(df, sma_short, sma_long)

    equity_curve, stats = simulate_equity(df, signals)

    eq_df = pd.DataFrame({
        'timestamp': df['timestamp'],
        'equity': equity_curve,
    })

    if equity_out:
        eq_df.to_csv(equity_out, index=False)
        logging.info(f"Equity curve saved to {equity_out}")
    else:
        logging.info("Equity curve:\n%s", eq_df.tail().to_string(index=False))

    if stats_out:
        with open(stats_out, 'w') as f:
            json.dump(stats, f, indent=2)
        logging.info(f"Summary stats saved to {stats_out}")

    logging.info(f"Net PnL: {stats['net_pnl']:.2f}")
    logging.info(f"Win rate: {stats['win_rate']:.2f}%")
    logging.info(f"Max drawdown: {stats['max_drawdown']:.2f}%")

    if plot and chart_out:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 4))
        plt.plot(eq_df['timestamp'], eq_df['equity'])
        plt.xlabel('Time')
        plt.ylabel('Equity')
        plt.title('Equity Curve')
        plt.tight_layout()
        plt.savefig(chart_out)
        logging.info(f"Equity chart saved to {chart_out}")

    return stats
