"""Dashboard utility functions for database I/O and plotting."""

import pandas as pd
from typing import List, Tuple


def calculate_naive_pnl(signals: List[Tuple]) -> float:
    """Calculate naive P&L from buy/sell signal pairs."""
    if not signals:
        return 0.0

    df = pd.DataFrame(signals, columns=['timestamp', 'action', 'price', 'symbol', 'strategy'])

    pnl = 0.0
    position = 0.0
    avg_cost = 0.0
    for _, row in df.iterrows():
        if row['action'] == 'buy':
            position += 1.0
            avg_cost = row['price']
        elif row['action'] == 'sell' and position > 0:
            pnl += (row['price'] - avg_cost) * min(1.0, position)
            position = max(0.0, position - 1.0)

    return pnl


def calculate_trades_pnl(trades: List[Tuple]) -> dict:
    """Calculate P&L from trades table data."""
    if not trades:
        return {"realized_pnl": 0.0, "total_trades": 0}

    df = pd.DataFrame(trades, columns=['timestamp', 'symbol', 'side', 'qty', 'price', 'fee', 'strategy', 'broker'])

    total_pnl = 0.0
    position = 0.0
    avg_cost = 0.0
    for _, row in df.iterrows():
        if row['side'] == 'buy':
            if position == 0:
                avg_cost = row['price']
                position = row['qty']
            else:
                avg_cost = (avg_cost * position + row['price'] * row['qty']) / (position + row['qty'])
                position += row['qty']
        elif row['side'] == 'sell' and position > 0:
            sell_qty = min(row['qty'], position)
            pnl = (row['price'] - avg_cost) * sell_qty - row['fee']
            total_pnl += pnl
            position -= sell_qty

    return {
        "realized_pnl": total_pnl,
        "total_trades": len(df),
        "open_position": position
    }
