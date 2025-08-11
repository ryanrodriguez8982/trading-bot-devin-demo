from __future__ import annotations

import inspect
import json
import logging
import os
from typing import Any, Callable, Optional, cast

import pandas as pd

from trading_bot.portfolio import Portfolio
from trading_bot.strategies import STRATEGY_REGISTRY
from trading_bot.utils.config import get_config

logger = logging.getLogger(__name__)

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

REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def load_csv_data(csv_path):
    """Load historical OHLCV data from CSV."""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:  # pragma: no cover - just log and re-raise
        logger.error("Failed to read CSV %s: %s", csv_path, e)
        raise

    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    if df.empty:
        raise ValueError("CSV file contains no rows")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    if not df["timestamp"].is_monotonic_increasing:
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
    stop_loss_pct: Optional[float] = None,
    take_profit_rr: Optional[float] = None,
    trailing_stop_pct: Optional[float] = None,
    symbol: str = "asset",
):
    """Simulate an equity curve given a stream of trade signals.

    Parameters
    ----------
    df : DataFrame
        Historical OHLC data for the asset.
    signals : Iterable[dict]
        Trading signals containing ``timestamp`` and ``action`` keys.
    initial_capital : float, default ``DEFAULT_INITIAL_CAPITAL``
        Starting cash balance for the simulated portfolio.
    trade_size : float, default ``DEFAULT_TRADE_SIZE``
        Quantity to buy or sell on each signal.
    fees_bps : float, default ``0.0``
        Trading fee in basis points applied to each transaction.
    slippage_bps : float, default ``0.0``
        Slippage in basis points applied to prices when executing trades.
    stop_loss_pct : float, optional
        Stop-loss distance expressed as a decimal (``0.02`` == 2%).
    take_profit_rr : float, optional
        Reward-to-risk multiplier used to derive take-profit from the stop
        distance.
    trailing_stop_pct : float, optional
        Trailing stop distance expressed as a decimal.  When provided the
        highest price seen since entry is tracked and the stop-loss is moved
        up accordingly.
    symbol : str, default ``"asset"``
        Symbol identifier for the simulated position.

    Returns
    -------
    tuple[list[float], dict[str, float]]
        A list representing the equity curve for each bar and a dictionary of
        summary statistics (``net_pnl``, ``win_rate`` and ``max_drawdown``).
    """

    portfolio = Portfolio(cash=initial_capital)
    equity_history: list[float] = []
    trade_profits: list[float] = []
    # Track highest prices per symbol to update trailing stops
    highest_prices: dict[str, float] = {}

    signal_iter = iter(sorted(signals, key=lambda x: x["timestamp"]))
    current_signal = next(signal_iter, None)

    for _, row in df.iterrows():
        ts = row["timestamp"]
        close_price = row["close"]

        pos = portfolio.positions.get(symbol)
        if pos and pos.qty > 0:
            if trailing_stop_pct is not None:
                # Maintain the highest price seen to compute the trailing level
                prev_high = highest_prices.get(symbol, pos.avg_cost)
                curr_high = max(prev_high, row["high"])
                highest_prices[symbol] = curr_high
                trail = curr_high * (1 - trailing_stop_pct)
                # Only move the stop upwards; never loosen it
                if pos.stop_loss is None or trail > pos.stop_loss:
                    pos.stop_loss = trail
            stop_hit = pos.stop_loss is not None and row["low"] <= pos.stop_loss
            tp_hit = pos.take_profit is not None and row["high"] >= pos.take_profit
            exit_price = None
            if stop_hit and tp_hit:
                exit_price = pos.stop_loss
            elif stop_hit:
                exit_price = pos.stop_loss
            elif tp_hit:
                exit_price = pos.take_profit
            if exit_price is not None:
                # Apply slippage to the exit price and realise the trade
                exec_price = exit_price * (1 - slippage_bps / 10_000)
                exit_avg_cost = pos.avg_cost
                qty = pos.qty
                portfolio.sell(symbol, qty, exec_price, fee_bps=fees_bps)
                trade_profits.append((exec_price - exit_avg_cost) * qty)
                highest_prices.pop(symbol, None)

        while current_signal is not None and current_signal["timestamp"] <= ts:
            action = current_signal["action"]
            try:
                if action == "buy":
                    buy_price = close_price * (1 + slippage_bps / 10_000)
                    stop_price = None
                    take_price = None
                    if stop_loss_pct:
                        # Derive stop-loss below the executed buy price
                        stop_price = buy_price * (1 - stop_loss_pct)
                        if take_profit_rr:
                            # Take-profit based on configured reward-to-risk
                            risk = buy_price - stop_price
                            take_price = buy_price + risk * take_profit_rr
                    if trailing_stop_pct:
                        # Start trailing stop at a fixed distance from entry
                        trail_price = buy_price * (1 - trailing_stop_pct)
                        stop_price = (
                            max(stop_price, trail_price)
                            if stop_price is not None
                            else trail_price
                        )
                        highest_prices[symbol] = buy_price
                    portfolio.buy(
                        symbol,
                        trade_size,
                        buy_price,
                        fee_bps=fees_bps,
                        stop_loss=stop_price,
                        take_profit=take_price,
                    )
                elif action == "sell":
                    sell_price = close_price * (1 - slippage_bps / 10_000)
                    pos = portfolio.positions.get(symbol)
                    avg_cost: Optional[float] = (
                        pos.avg_cost if pos and pos.qty >= trade_size else None
                    )
                    portfolio.sell(symbol, trade_size, sell_price, fee_bps=fees_bps)
                    highest_prices.pop(symbol, None)
                    if avg_cost is not None:
                        trade_profits.append((sell_price - avg_cost) * trade_size)
            except ValueError:
                pass
            current_signal = next(signal_iter, None)

        equity = portfolio.equity({symbol: close_price})
        equity_history.append(equity)

    final_equity = portfolio.equity({symbol: df.iloc[-1]["close"]})
    net_pnl = final_equity - initial_capital
    win_rate = 0.0
    if trade_profits:
        wins = len([p for p in trade_profits if p > 0])
        win_rate = wins / len(trade_profits) * 100

    max_drawdown = compute_drawdown(equity_history)
    return equity_history, {
        "net_pnl": float(net_pnl),
        "win_rate": float(win_rate),
        "max_drawdown": float(max_drawdown),
    }


def generate_signals(
    df,
    strategy="sma",
    sma_short: int = DEFAULT_SMA_SHORT,
    sma_long: int = DEFAULT_SMA_LONG,
    rsi_period: int = DEFAULT_RSI_PERIOD,
    macd_fast: int = DEFAULT_MACD_FAST,
    macd_slow: int = DEFAULT_MACD_SLOW,
    macd_signal: int = DEFAULT_MACD_SIGNAL,
    bbands_window: int = DEFAULT_BBANDS_WINDOW,
    bbands_std: int = DEFAULT_BBANDS_STD,
    confluence_members=None,
    confluence_required: int = 2,
):
    """Generate trading signals using the specified strategy."""

    if strategy not in STRATEGY_REGISTRY:
        raise ValueError("Unknown strategy")

    strategy_fn = cast(Callable[..., list[dict[str, Any]]], STRATEGY_REGISTRY[strategy])

    available_params = {
        "df": df,
        "sma_short": sma_short,
        "sma_long": sma_long,
        "period": rsi_period,
        "fast_period": macd_fast,
        "slow_period": macd_slow,
        "signal_period": macd_signal,
        "window": bbands_window,
        "num_std": bbands_std,
        "members": confluence_members,
        "required": confluence_required,
    }

    sig = inspect.signature(strategy_fn)
    strategy_kwargs = {
        name: value
        for name, value in available_params.items()
        if name in sig.parameters and value is not None
    }

    return strategy_fn(**strategy_kwargs)


def save_backtest_outputs(
    eq_df: pd.DataFrame,
    stats: dict[str, Any],
    equity_out: Optional[str] = None,
    stats_out: Optional[str] = None,
    plot: bool = False,
    chart_out: Optional[str] = None,
):
    """Persist equity curve, stats and optional chart to disk."""

    if equity_out:
        try:
            eq_df.to_csv(equity_out, index=False)
            logger.info(f"Equity curve saved to {equity_out}")
        except OSError as e:  # pragma: no cover - I/O errors are uncommon
            logger.error("Failed to save equity curve to %s: %s", equity_out, e)
    else:
        logger.info("Equity curve:\n%s", eq_df.tail().to_string(index=False))

    if stats_out:
        try:
            with open(stats_out, "w") as f:
                json.dump(stats, f, indent=2)
            logger.info(f"Summary stats saved to {stats_out}")
        except OSError as e:  # pragma: no cover - I/O errors are uncommon
            logger.error("Failed to save summary stats to %s: %s", stats_out, e)

    logger.info(f"Net PnL: {stats['net_pnl']:.2f}")
    logger.info(f"Win rate: {stats['win_rate']:.2f}%")
    logger.info(f"Max drawdown: {stats['max_drawdown']:.2f}%")

    if plot and chart_out:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.figure(figsize=(10, 4))
        plt.plot(eq_df["timestamp"], eq_df["equity"])
        plt.xlabel("Time")
        plt.ylabel("Equity")
        plt.title("Equity Curve")
        plt.tight_layout()
        try:
            plt.savefig(chart_out)
            logger.info(f"Equity chart saved to {chart_out}")
        except OSError as e:  # pragma: no cover - I/O errors are uncommon
            logger.error("Failed to save equity chart to %s: %s", chart_out, e)


def run_backtest(
    csv_path,
    strategy="sma",
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
    stop_loss_pct: Optional[float] = None,
    take_profit_rr: Optional[float] = None,
    trailing_stop_pct: Optional[float] = None,
    confluence_members=None,
    confluence_required=2,
):
    """Run backtest on CSV data using specified strategy."""
    df = load_csv_data(csv_path)

    signals = generate_signals(
        df,
        strategy=strategy,
        sma_short=sma_short,
        sma_long=sma_long,
        rsi_period=rsi_period,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
        bbands_window=bbands_window,
        bbands_std=bbands_std,
        confluence_members=confluence_members,
        confluence_required=confluence_required,
    )

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

    eq_df = pd.DataFrame(
        {
            "timestamp": df["timestamp"],
            "equity": equity_curve,
        }
    )

    save_backtest_outputs(
        eq_df,
        stats,
        equity_out=equity_out,
        stats_out=stats_out,
        plot=plot,
        chart_out=chart_out,
    )

    return stats
