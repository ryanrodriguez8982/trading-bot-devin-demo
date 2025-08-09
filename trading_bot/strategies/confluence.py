import logging
from collections import defaultdict
from typing import List, Optional
import pandas as pd


def confluence_strategy(df: pd.DataFrame, members: Optional[List[str]] = None, required: int = 2):
    """Generate signals only when multiple strategies agree.

    Args:
        df (pd.DataFrame): Price data.
        members (List[str], optional): Strategy names to evaluate. Defaults
            to ["sma", "rsi", "macd"].
        required (int): Number of strategies that must agree. Defaults to 2.

    Returns:
        list[dict]: Consolidated trading signals.
    """
    if members is None:
        members = ["sma", "rsi", "macd"]

    try:
        from trading_bot.strategies import STRATEGY_REGISTRY  # avoid circular import
    except Exception as e:
        logging.error(f"Failed to import STRATEGY_REGISTRY: {e}")
        return []

    # Collect signals from member strategies
    signals_map = defaultdict(list)
    for name in members:
        strategy_fn = STRATEGY_REGISTRY.get(name)
        if not callable(strategy_fn):
            logging.warning(f"Unknown strategy in confluence: {name}")
            continue
        try:
            signals = strategy_fn(df)
        except Exception as exc:
            logging.error(f"Error executing strategy '{name}': {exc}")
            continue
        for sig in signals:
            ts = sig["timestamp"]
            signals_map[ts].append(sig)

    # Determine consensus
    consensus_signals = []
    for ts, sigs in signals_map.items():
        if len(sigs) < required:
            continue
        counts = defaultdict(list)
        for sig in sigs:
            counts[sig["action"].lower()].append(sig["price"])
        for action, prices in counts.items():
            if len(prices) >= required:
                avg_price = sum(prices) / len(prices)
                consensus_signals.append({
                    "timestamp": ts,
                    "action": action,
                    "price": avg_price,
                })
                break

    return sorted(consensus_signals, key=lambda s: s["timestamp"])
