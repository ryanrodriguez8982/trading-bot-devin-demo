from __future__ import annotations

import pandas as pd
import logging
import os
import json

# ? Absolute import for package compatibility
from trading_bot.signal_logger import log_signals_to_db
from trading_bot.strategies import STRATEGY_REGISTRY
from trading_bot.portfolio import Portfolio
from trading_bot.utils.config import get_config


CONFIG = get_config()
DEFAULT_INITIAL_CAPITAL = 10000.0
DEFAULT_TRADE_SIZE = CONFIG.get("trade_size", 1.0)
DEFAULT_SMA_SHORT = CONFIG.get("sma_short", 5)
DEFAULT_SMA_LONG = CONFIG.get("sma_long", 20)
DEFAULT_RSI_PERIOD = CONFIG.get("rsi_period", 14)
DEFAULT_MACD_FAST = CONFIG.get("macd_fast", 12)
DEFAULT_MACD_SLOW = CONFIG.get("macd_slow", 26)
DEFAULT_MACD_SIGNAL = CONFIG.get("macd_signal", 9)
DEFAULT_BBANDS_WINDOW = CONFIG.get("bbands_window", 20)
DEFAULT_BBANDS_STD = CONFIG.get("bbands_std", 2)

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

    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
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


def simulate_equity(
    df,
    signals,
    initial_capital: float = DEFAULT_INITIAL_CAPITAL,
    trade_size: float = DEFAULT_TRADE_SIZE,
    fees_bps: float = 0.0,
    slippage_bps: float = 0.0,
    stop_loss_pct: float | None = None,
    take_profit_rr: float | None = None,
    trailing_stop_pct: float | None = None,
    symbol: str = "asset",
):
    portfolio = Portfolio(cash=initial_capital)
    equity_history: list[float] = []
    trade_profits: list[float] = []
    highest_prices: dict[str, float] = {}

    signal_iter = iter(sorted(signals, key=lambda x: x['timestamp']))
    current_signal = next(signal_iter, None)

    for _, row in df.iterrows():
        ts = row['timestamp']
        close_price = row['close']

        # Check for stop-loss / take-profit before new signals
        pos = portfolio.positions.get(symbol)
        if pos and pos.qty > 0:
            if trailing_stop_pct is not None:
                prev_high = highest_prices.get(symbol, pos.avg_cost)
                curr_high = max(prev_high, row['high'])
                highest_prices[symbol] = curr_high
                trail = curr_high * (1 - trailing_stop_pct)
                if pos.stop_loss is None or trail > pos.stop_loss:
                    pos.stop_loss = trail
            stop_hit = pos.stop_loss is not None and row['low'] <= pos.stop_loss
            tp_hit = pos.take_profit is not None and row['high'] >= pos.take_profit
            exit_price = None
            if stop_hit and tp_hit:
                exit_price = pos.stop_loss
            elif stop_hit:
                exit_price = pos.stop_loss
            elif tp_hit:
                exit_price = pos.take_profit
            if exit_price is not None:
                exec_price = exit_price * (1 - slippage_bps / 10_000)
                avg_cost = pos.avg_cost
                qty = pos.qty
                portfolio.sell(symbol, qty, exec_price, fee_bps=fees_bps)
                trade_profits.append((exec_price - avg_cost) * qty)
                highest_prices.pop(symbol, None)

        while current_signal is not None and current_signal['timestamp'] <= ts:
            action = current_signal['action']
            try:
                if action == 'buy':
                    buy_price = close_price * (1 + slippage_bps / 10_000)
                    stop_price = None
                    take_price = None
                    if stop_loss_pct:
                        stop_price = buy_price * (1 - stop_loss_pct)
                        if take_profit_rr:
                            risk = buy_price - stop_price
                            take_price = buy_price + risk * take_profit_rr
                    if trailing_stop_pct:
                        trail_price = buy_price * (1 - trailing_stop_pct)
                        stop_price = max(stop_price, trail_price) if stop_price is not None else trail_price
                        highest_prices[symbol] = buy_price
                    portfolio.buy(
                        symbol,
                        trade_size,
                        buy_price,
                        fee_bps=fees_bps,
                        stop_loss=stop_price,
                        take_profit=take_price,
                    )
                elif action == 'sell':
                    sell_price = close_price * (1 - slippage_bps / 10_000)
                    pos = portfolio.positions.get(symbol)
                    avg_cost = pos.avg_cost if pos and pos.qty >= trade_size else None
                    portfolio.sell(symbol, trade_size, sell_price, fee_bps=fees_bps)
                    highest_prices.pop(symbol, None)
                    if avg_cost is not None:
                        trade_profits.append((sell_price - avg_cost) * trade_size)
            except ValueError:
                pass
            current_signal = next(signal_iter, None)

        equity = portfolio.equity({symbol: close_price})
        equity_history.append(equity)

    final_equity = portfolio.equity({symbol: df.iloc[-1]['close']})
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


def run_backtest(
    csv_path,
    strategy='sma',
    sma_short=DEFAULT_SMA_SHORT,
    sma_long=DEFAULT_SMA_LONG,
    rsi_period=DEFAULT_RSI_PERIOD,
    macd_fast=DEFAULT_MACD_FAST,
    macd_slow=DEFAULT_MACD_SLOW,
    macd_signal=DEFAULT_MACD_SIGNAL,
    bbands_window=DEFAULT_BBANDS_WINDOW,
    bbands_std=DEFAULT_BBANDS_STD,
    plot=False,
    equity_out=None,
    stats_out=None,
    chart_out=None,
    trade_size=DEFAULT_TRADE_SIZE,
    fees_bps=0.0,
    slippage_bps: float = 0.0,
    stop_loss_pct: float | None = None,
    take_profit_rr: float | None = None,
    trailing_stop_pct: float | None = None,
    confluence_members=None,
    confluence_required=2,
):
    """Run backtest on CSV data using specified strategy."""
    df = load_csv_data(csv_path)

    if strategy not in STRATEGY_REGISTRY:
        raise ValueError("Unknown strategy")

    strategy_fn = STRATEGY_REGISTRY[strategy]
    if strategy == 'rsi':
        signals = strategy_fn(df, period=rsi_period)
    elif strategy == 'macd':
        signals = strategy_fn(
            df,
            fast_period=macd_fast,
            slow_period=macd_slow,
            signal_period=macd_signal,
        )
    elif strategy == 'bbands':
        signals = strategy_fn(df, window=bbands_window, num_std=bbands_std)
    elif strategy == 'confluence':
        signals = strategy_fn(
            df,
            members=confluence_members,
            required=confluence_required,
        )
    else:
        signals = strategy_fn(df, sma_short, sma_long)

    equity_curve, stats = simulate_equity(
        df,
        signals,
        trade_size=trade_size,
        fees_bps=fees_bps,
        slippage_bps=slippage_bps,
        stop_loss_pct=stop_loss_pct,
        take_profit_rr=take_profit_rr,
        trailing_stop_pct=trailing_stop_pct,
    )

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
