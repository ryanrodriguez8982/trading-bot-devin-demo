import pandas as pd
from typing import List, Tuple, Dict

from trading_bot.backtester import compute_drawdown
from trading_bot.portfolio import Portfolio
from trading_bot.config import get_config


CONFIG = get_config()
DEFAULT_INITIAL_BALANCE = 10000.0
DEFAULT_TRADE_SIZE = CONFIG.get("trade_size", 1.0)


def compute_equity_curve(
    signals: List[Dict],
    initial_balance: float = DEFAULT_INITIAL_BALANCE,
    trade_size: float = DEFAULT_TRADE_SIZE,
    fees_bps: float = 0.0,
    symbol: str = "asset",
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Compute equity curve and performance stats from trading signals.

    Parameters
    ----------
    signals : list of dict
        Signals with ``timestamp``, ``action`` and ``price`` keys.
    initial_balance : float, optional
        Starting portfolio balance in quote currency.
    trade_size : float, optional
        Quantity to trade on each signal.
    fees_bps : float, optional
        Trading fee in basis points.
    symbol : str, optional
        Symbol name used in the portfolio (default ``"asset"``).

    Returns
    -------
    pd.DataFrame
        DataFrame with ``timestamp`` and ``equity`` columns.
    dict
        Dictionary containing performance metrics.
    """
    if not signals:
        empty_df = pd.DataFrame(columns=["timestamp", "equity"])
        stats = {
            "total_return_pct": 0.0,
            "total_return_abs": 0.0,
            "num_trades": 0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
        }
        return empty_df, stats

    # Ensure signals are sorted chronologically
    sorted_signals = sorted(signals, key=lambda x: x["timestamp"])

    portfolio = Portfolio(cash=initial_balance)
    equity_curve = []
    wins = trades = 0

    for sig in sorted_signals:
        ts = pd.to_datetime(sig["timestamp"], utc=True)
        price = float(sig["price"])
        action = str(sig["action"]).lower()

        try:
            if action == "buy":
                portfolio.buy(symbol, trade_size, price, fee_bps=fees_bps)
            elif action == "sell":
                pos = portfolio.positions.get(symbol)
                if pos and pos.qty >= trade_size:
                    avg_cost = pos.avg_cost
                    portfolio.sell(symbol, trade_size, price, fee_bps=fees_bps)
                    trades += 1
                    if price > avg_cost:
                        wins += 1
        except ValueError:
            # Skip trades that violate portfolio constraints
            pass

        equity_curve.append({"timestamp": ts, "equity": portfolio.equity({symbol: price})})

    final_price = float(sorted_signals[-1]["price"])
    final_equity = portfolio.equity({symbol: final_price})
    total_return_abs = final_equity - initial_balance
    total_return_pct = (total_return_abs / initial_balance) * 100

    equity_values = [pt["equity"] for pt in equity_curve]
    max_dd = compute_drawdown(equity_values) if equity_values else 0.0
    win_rate = (wins / trades * 100) if trades else 0.0

    stats = {
        "total_return_pct": float(total_return_pct),
        "total_return_abs": float(total_return_abs),
        "num_trades": trades,
        "win_rate": float(win_rate),
        "max_drawdown": float(max_dd),
    }

    df = pd.DataFrame(equity_curve)
    return df, stats
