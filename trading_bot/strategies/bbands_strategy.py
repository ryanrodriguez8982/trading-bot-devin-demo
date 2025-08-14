import logging
from typing import Any, Dict, List

import pandas as pd

from trading_bot.strategies import register_strategy

logger = logging.getLogger(__name__)


@register_strategy("bbands")
def bbands_strategy(
    df: pd.DataFrame,
    window: int = 20,
    num_std: float = 2,
    **_kwargs,
) -> List[Dict[str, Any]]:
    """Generate trading signals using Bollinger Bands crossovers.

    Args:
        df: DataFrame with at least ['timestamp', 'close'] columns.
        window: Rolling window used for the middle band SMA.
        num_std: Number of standard deviations for upper/lower bands.

    Returns:
        A list of dicts: { 'timestamp': pd.Timestamp, 'action': 'buy'|'sell', 'price': float }.
    """
    if df is None or df.empty:
        logger.warning("Empty dataframe provided to Bollinger strategy")
        return []

    if 'timestamp' not in df.columns or 'close' not in df.columns:
        raise KeyError("DataFrame must include 'timestamp' and 'close' columns")

    if len(df) < window:
        logger.warning("Not enough data for %d-period Bollinger Bands", window)
        return []

    d = df.copy()

    # Ensure timestamp is pandas datetime for consistency
    if not pd.api.types.is_datetime64_any_dtype(d['timestamp']):
        try:
            d['timestamp'] = pd.to_datetime(d['timestamp'], utc=True, errors='coerce')
        except Exception:
            # Fall back: leave as-is; invalid timestamps will become NaT
            pass

    # Compute bands
    d['middle_band'] = d['close'].rolling(window=window, min_periods=window).mean()
    d['std_dev'] = d['close'].rolling(window=window, min_periods=window).std()
    d['upper_band'] = d['middle_band'] + num_std * d['std_dev']
    d['lower_band'] = d['middle_band'] - num_std * d['std_dev']

    signals: List[Dict[str, Any]] = []

    # Iterate to detect crossovers: below->above lower => BUY; above->below upper => SELL
    for i in range(1, len(d)):
        prev = d.iloc[i - 1]
        curr = d.iloc[i]

        # Skip until bands are fully formed
        if pd.isna(curr['lower_band']) or pd.isna(curr['upper_band']):
            continue

        prev_close = float(prev['close'])
        curr_close = float(curr['close'])
        prev_lower = float(prev['lower_band']) if pd.notna(prev['lower_band']) else float('nan')
        curr_lower = float(curr['lower_band'])
        prev_upper = float(prev['upper_band']) if pd.notna(prev['upper_band']) else float('nan')
        curr_upper = float(curr['upper_band'])

        # BUY when price crosses up over the lower band
        if pd.notna(prev_lower) and (prev_close < prev_lower) and (curr_close >= curr_lower):
            signals.append({
                'timestamp': curr['timestamp'],
                'action': 'buy',
                'price': curr_close,
            })
        # SELL when price crosses down under the upper band
        elif pd.notna(prev_upper) and (prev_close > prev_upper) and (curr_close <= curr_upper):
            signals.append({
                'timestamp': curr['timestamp'],
                'action': 'sell',
                'price': curr_close,
            })

    logger.info("Generated %d Bollinger band signals", len(signals))
    return signals
