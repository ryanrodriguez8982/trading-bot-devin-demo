import logging
from typing import List, Dict, Any

import pandas as pd

from trading_bot.utils.config import get_config
from trading_bot.strategies import register_strategy

logger = logging.getLogger(__name__)

CONFIG = get_config()
DEFAULT_SMA_SHORT: int = int(CONFIG.get("sma_short", 5))
DEFAULT_SMA_LONG: int = int(CONFIG.get("sma_long", 20))


@register_strategy("sma")
def sma_strategy(
    df: pd.DataFrame,
    sma_short: int = DEFAULT_SMA_SHORT,
    sma_long: int = DEFAULT_SMA_LONG,
) -> List[Dict[str, Any]]:
    """
    SMA crossover strategy.

    Buy when short SMA crosses above long SMA.
    Sell when short SMA crosses below long SMA.

    Args:
        df: DataFrame with at least ['timestamp', 'close'] columns.
        sma_short: Short-period SMA window.
        sma_long: Long-period SMA window.

    Returns:
        List of dicts: { 'timestamp': pd.Timestamp, 'action': 'buy'|'sell', 'price': float }.
    """
    if df is None or df.empty:
        logger.warning("Empty dataframe provided to SMA strategy")
        return []

    required_cols = {"timestamp", "close"}
    if not required_cols.issubset(df.columns):
        raise KeyError("DataFrame must include 'timestamp' and 'close' columns")

    if sma_short <= 0 or sma_long <= 0:
        raise ValueError("sma_short and sma_long must be positive integers")

    if sma_short >= sma_long:
        logger.warning("sma_short (%d) >= sma_long (%d) may reduce signal quality", sma_short, sma_long)

    if len(df) < sma_long:
        logger.warning("Not enough data for %d-period SMA calculation", sma_long)
        return []

    d = df.copy()

    # Ensure timestamp is datetime for consistency
    if not pd.api.types.is_datetime64_any_dtype(d['timestamp']):
        d['timestamp'] = pd.to_datetime(d['timestamp'], utc=True, errors='coerce')

    d[f'sma_{sma_short}'] = d['close'].rolling(window=sma_short, min_periods=sma_short).mean()
    d[f'sma_{sma_long}'] = d['close'].rolling(window=sma_long, min_periods=sma_long).mean()

    signals: List[Dict[str, Any]] = []

    for i in range(1, len(d)):
        prev = d.iloc[i - 1]
        curr = d.iloc[i]

        # Skip until both SMAs are available
        if pd.isna(curr[f'sma_{sma_short}']) or pd.isna(curr[f'sma_{sma_long}']):
            continue

        prev_short = prev[f'sma_{sma_short}']
        prev_long = prev[f'sma_{sma_long}']
        curr_short = curr[f'sma_{sma_short}']
        curr_long = curr[f'sma_{sma_long}']

        logger.debug(
            "t=%s price=%.6f short=%.6f long=%.6f",
            curr['timestamp'],
            float(curr['close']),
            float(curr_short),
            float(curr_long),
        )

        # Bullish crossover: short crosses above long
        if (prev_short <= prev_long) and (curr_short > curr_long):
            signals.append({
                'timestamp': curr['timestamp'],
                'action': 'buy',
                'price': float(curr['close']),
            })
        # Bearish crossover: short crosses below long
        elif (prev_short >= prev_long) and (curr_short < curr_long):
            signals.append({
                'timestamp': curr['timestamp'],
                'action': 'sell',
                'price': float(curr['close']),
            })

    logger.info("Generated %d SMA signals", len(signals))
    return signals
