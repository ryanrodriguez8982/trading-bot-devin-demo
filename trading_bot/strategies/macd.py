import logging
from typing import List, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)


def macd_strategy(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> List[Dict[str, Any]]:
    """Generate trading signals based on MACD crossovers.

    Args:
        df: DataFrame with 'close' and 'timestamp' columns.
        fast_period: Fast EMA period.
        slow_period: Slow EMA period.
        signal_period: Signal line EMA period.

    Returns:
        List of dicts with keys: 'timestamp', 'action', 'price'.
    """
    if df is None or df.empty:
        logger.warning("Empty dataframe provided to MACD strategy")
        return []

    if 'close' not in df.columns or 'timestamp' not in df.columns:
        raise KeyError("DataFrame must include 'close' and 'timestamp' columns")

    if len(df) < slow_period:
        logger.warning("Not enough data for %d-period EMA calculation", slow_period)
        return []

    d = df.copy()

    # Ensure timestamp is datetime for consistency
    if not pd.api.types.is_datetime64_any_dtype(d['timestamp']):
        d['timestamp'] = pd.to_datetime(d['timestamp'], utc=True, errors='coerce')

    # Exponential moving averages for the fast and slow windows
    d['ema_fast'] = d['close'].ewm(span=fast_period, adjust=False).mean()
    d['ema_slow'] = d['close'].ewm(span=slow_period, adjust=False).mean()
    # MACD line is simply the difference between the two EMAs
    d['macd'] = d['ema_fast'] - d['ema_slow']
    # Signal line: EMA of the MACD line used for crossovers
    d['signal'] = d['macd'].ewm(span=signal_period, adjust=False).mean()

    signals: List[Dict[str, Any]] = []

    for i in range(1, len(d)):
        prev = d.iloc[i - 1]
        curr = d.iloc[i]

        if pd.isna(prev['macd']) or pd.isna(prev['signal']) or pd.isna(curr['macd']) or pd.isna(curr['signal']):
            continue

        prev_macd = float(prev['macd'])
        prev_signal = float(prev['signal'])
        curr_macd = float(curr['macd'])
        curr_signal = float(curr['signal'])

        logger.debug(
            "t=%s macd=%.6f signal=%.6f",
            curr['timestamp'],
            curr_macd,
            curr_signal,
        )

        # Bullish crossover: MACD line crosses above the signal -> BUY
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            signals.append({
                'timestamp': curr['timestamp'],
                'action': 'buy',
                'price': float(curr['close']),
            })
        # Bearish crossover: MACD line crosses below the signal -> SELL
        elif prev_macd >= prev_signal and curr_macd < curr_signal:
            signals.append({
                'timestamp': curr['timestamp'],
                'action': 'sell',
                'price': float(curr['close']),
            })

    logger.info("Generated %d MACD crossover signals", len(signals))
    return signals
