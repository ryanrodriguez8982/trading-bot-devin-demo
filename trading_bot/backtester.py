from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional, Sequence


import pandas as pd

from trading_bot.portfolio import Portfolio
from trading_bot.strategies import STRATEGY_REGISTRY
from trading_bot.config import get_config
from trading_bot.risk.exits import ExitManager

logger = logging.getLogger(__name__)

CONFIG = get_config()
DEFAULT_INITIAL_CAPITAL = 10000.0
DEFAULT_TRADE_SIZE = CONFIG.get("trade_size", 1.0)
DEFAULT_MAX_POSITION_PCT = CONFIG.get("max_position_pct", 1.0)

REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def load_csv_data(csv_path: str) -> pd.DataFrame:
    """Load historical OHLCV data from a CSV file.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file containing price data.

    Returns
    -------
    DataFrame
        Dataframe with the required OHLCV columns and a timezone-aware
        ``timestamp`` column.
    """
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


def compute_drawdown(equity_curve: Sequence[float]) -> float:
    """Return the maximum drawdown percentage for an equity curve."""
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
    max_position_pct: float = DEFAULT_MAX_POSITION_PCT,
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
    max_position_pct : float, default ``DEFAULT_MAX_POSITION_PCT``
        Maximum fraction of equity allocated to the position.
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

    exits: Optional[ExitManager] = None
    if any([stop_loss_pct, take_profit_rr, trailing_stop_pct]):
        take_pct = None
        if stop_loss_pct is not None and take_profit_rr is not None:
            take_pct = stop_loss_pct * take_profit_rr * 100
        exits = ExitManager(
            stop_loss_pct=(stop_loss_pct * 100 if stop_loss_pct is not None else None),
            take_profit_pct=take_pct,
            trailing_stop_pct=(trailing_stop_pct * 100 if trailing_stop_pct is not None else None),
        )

    signal_iter = iter(sorted(signals, key=lambda x: x["timestamp"]))
    current_signal = next(signal_iter, None)

    for _, row in df.iterrows():
        ts = row["timestamp"]
        close_price = row["close"]

        pos = portfolio.positions.get(symbol)
        if pos and pos.qty > 0 and exits is not None:
            exit_price = exits.check_ohlc(symbol, row["high"], row["low"])
            if exit_price is not None:
                exec_price = exit_price * (1 - slippage_bps / 10_000)
                exit_avg_cost = pos.avg_cost
                qty = pos.qty
                portfolio.sell(symbol, qty, exec_price, fee_bps=fees_bps)
                trade_profits.append((exec_price - exit_avg_cost) * qty)

        while current_signal is not None and current_signal["timestamp"] <= ts:
            action = current_signal["action"]
            try:
                if action == "buy":
                    buy_price = close_price * (1 + slippage_bps / 10_000)
                    stop_price = None
                    take_price = None
                    if stop_loss_pct is not None:
                        stop_price = buy_price * (1 - stop_loss_pct)
                        if take_profit_rr is not None:
                            risk = buy_price - stop_price
                            take_price = buy_price + risk * take_profit_rr
                    if trailing_stop_pct is not None:
                        trail_price = buy_price * (1 - trailing_stop_pct)
                        stop_price = max(stop_price, trail_price) if stop_price is not None else trail_price
                    qty = trade_size
                    if max_position_pct < 1.0:
                        equity = portfolio.equity({symbol: buy_price})
                        current_val = portfolio.position_qty(symbol) * buy_price
                        allowed_val = equity * max_position_pct - current_val
                        if allowed_val <= 0:
                            qty = 0.0
                        else:
                            qty = min(qty, allowed_val / buy_price)
                        if qty < trade_size:
                            logger.debug("Capping buy to %.8f due to max_position_pct", qty)
                    if qty > 0:
                        portfolio.buy(
                            symbol,
                            qty,
                            buy_price,
                            fee_bps=fees_bps,
                            stop_loss=stop_price,
                            take_profit=take_price,
                        )
                        if exits is not None:
                            exits.arm(symbol, buy_price)
                elif action == "sell":
                    sell_price = close_price * (1 - slippage_bps / 10_000)
                    pos = portfolio.positions.get(symbol)
                    avg_cost: Optional[float] = pos.avg_cost if pos and pos.qty >= trade_size else None
                    portfolio.sell(symbol, trade_size, sell_price, fee_bps=fees_bps)
                    if exits is not None:
                        exits.disarm(symbol)
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
        "final_position_qty": portfolio.position_qty(symbol),
        "cash": portfolio.cash,
    }


def generate_signals(
    df,
    strategy: str = "sma",
    **strategy_kwargs,
):
    """Generate trading signals using the specified strategy.

    Extra keyword arguments are forwarded directly to the strategy
    function.  Strategies are expected to declare the parameters they need
    and may accept ``**kwargs`` to ignore irrelevant ones.
    """

    if strategy not in STRATEGY_REGISTRY:
        raise ValueError("Unknown strategy")

    entry = STRATEGY_REGISTRY[strategy]
    strategy_fn = entry.func
    metadata = entry.metadata

    # Provide default confluence parameters from metadata when not
    # explicitly supplied
    if "requires" in metadata and "members" not in strategy_kwargs:
        strategy_kwargs["members"] = metadata["requires"]
    if "required_count" in metadata and "required" not in strategy_kwargs:
        strategy_kwargs["required"] = metadata["required_count"]

    return strategy_fn(df, **strategy_kwargs)


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
    strategy: str = "sma",
    plot: bool = False,
    equity_out=None,
    stats_out=None,
    chart_out=None,
    trade_size: float = DEFAULT_TRADE_SIZE,
    fees_bps: float = 0.0,
    slippage_bps: float = 0.0,
    stop_loss_pct: Optional[float] = None,
    take_profit_rr: Optional[float] = None,
    trailing_stop_pct: Optional[float] = None,
    max_position_pct: float = DEFAULT_MAX_POSITION_PCT,
    **strategy_kwargs,
):
    """Run backtest on CSV data using specified strategy.

    Additional keyword arguments are forwarded to the strategy function.
    """
    df = load_csv_data(csv_path)

    signals = generate_signals(
        df,
        strategy=strategy,
        **strategy_kwargs,
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
        max_position_pct=max_position_pct,
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
