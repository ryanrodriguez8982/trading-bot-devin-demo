import pandas as pd
from typing import List, Tuple, Dict

from trading_bot.backtester import compute_drawdown


def compute_equity_curve(
    signals: List[Dict], initial_balance: float = 10000.0
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Compute equity curve and performance stats from trading signals.

    Parameters
    ----------
    signals : list of dict
        Signals with ``timestamp``, ``action`` and ``price`` keys.
    initial_balance : float, optional
        Starting portfolio balance in quote currency.

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

    balance = float(initial_balance)
    position = 0.0
    last_buy_price = None
    equity_curve = []
    wins = trades = 0

    for sig in sorted_signals:
        ts = pd.to_datetime(sig["timestamp"])
        price = float(sig["price"])
        action = str(sig["action"]).lower()

        if action == "buy" and balance > 0:
            qty = balance / price
            position += qty
            balance -= qty * price
            last_buy_price = price
        elif action == "sell" and position > 0:
            balance += position * price
            if last_buy_price is not None:
                trades += 1
                if price > last_buy_price:
                    wins += 1
                last_buy_price = None
            position = 0.0

        equity = balance + position * price
        equity_curve.append({"timestamp": ts, "equity": equity})

    final_price = float(sorted_signals[-1]["price"])
    final_equity = balance + position * final_price
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
