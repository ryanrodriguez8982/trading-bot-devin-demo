import logging
from typing import List, Dict, Any

import numpy as np
import pandas as pd

from trading_bot.utils.config import get_config

logger = logging.getLogger(__name__)

CONFIG = get_config()
DEFAULT_RSI_PERIOD: int = int(CONFIG.get("rsi_period", 14))
DEFAULT_RSI_LOWER: float = float(CONFIG.get("rsi_lower", 30))
DEFAULT_RSI_UPPER: float = float(CONFIG.get("rsi_upper", 70))


def rsi_crossover_strategy(
    df: pd.DataFrame,
    period: int = DEFAULT_RSI_PERIOD,
    lower_thresh: float = DEFAULT_RSI_LOWER,
    upper_thresh: float = DEFAULT_RSI_UPPER,
) -> List[Dict[str, Any]]:
    """Generate trading signals based on RSI threshold crossovers.

    Args:
        df: DataFrame with 'close' price column and 'timestamp'.
        period: Lookback period for RSI calculation.
        lower_thresh: Oversold threshold.
        upper_thresh: Overbought threshold.

    Returns:
        List of dicts: { 'timestamp': pd.Timestamp, 'action': 'buy'|'sell', 'price': float }.
    """
    if df is None or df.empty:
        logger.warning("Empty dataframe provided to RSI strategy")
        return []

    if 'close' not in df.columns or 'timestamp' not in df.columns:
        raise KeyError("DataFrame must include 'timestamp' and 'close' columns")

    if len(df) < period:
        logger.warning("Not enough data for %d-period RSI calculation", period)
        return []

    d = df.copy()

    # Ensure timestamp is pandas datetime for consistency
    if not pd.api.types.is_datetime64_any_dtype(d['timestamp']):
        d['timestamp'] = pd.to_datetime(d['timestamp'], utc=True, errors='coerce')

    # RSI (simple rolling mean variant; Wilder's smoothing can be added later if desired)
    delta = d['close'].diff()  # price change between consecutive closes
    gain = delta.clip(lower=0.0)  # positive gains
    loss = -delta.clip(upper=0.0)  # negative losses as positive numbers

    # Rolling mean of gains/losses over the lookback period
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Avoid division by zero then compute relative strength and RSI oscillator
    avg_loss = avg_loss.replace(0, np.nan)
    rs = avg_gain / avg_loss  # relative strength
    d['rsi'] = 100.0 - (100.0 / (1.0 + rs))

    signals: List[Dict[str, Any]] = []

    for i in range(1, len(d)):
        prev = d.iloc[i - 1]
        curr = d.iloc[i]

        if pd.isna(prev.get('rsi')) or pd.isna(curr.get('rsi')):
            continue

        prev_rsi = float(prev['rsi'])
        curr_rsi = float(curr['rsi'])
        curr_close = float(curr['close'])

        logger.debug("t=%s rsi=%.2f prev_rsi=%.2f", curr['timestamp'], curr_rsi, prev_rsi)

        # Cross up from below lower_thresh -> BUY
        if prev_rsi <= lower_thresh and curr_rsi > lower_thresh:
            signals.append({
                'timestamp': curr['timestamp'],
                'action': 'buy',
                'price': curr_close,
            })
        # Cross down from above upper_thresh -> SELL
        elif prev_rsi >= upper_thresh and curr_rsi < upper_thresh:
            signals.append({
                'timestamp': curr['timestamp'],
                'action': 'sell',
                'price': curr_close,
            })

    logger.info("Generated %d RSI crossover signals", len(signals))
    return signals

# TODO: Consider Wilder's RSI using ewm(alpha=1/period, adjust=False) for smoothing
