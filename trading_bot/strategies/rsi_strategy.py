import pandas as pd
import logging

from trading_bot.utils.config import get_config

CONFIG = get_config()
DEFAULT_RSI_PERIOD = CONFIG.get("rsi_period", 14)
DEFAULT_RSI_LOWER = CONFIG.get("rsi_lower", 30)
DEFAULT_RSI_UPPER = CONFIG.get("rsi_upper", 70)


def rsi_crossover_strategy(
    df,
    period: int = DEFAULT_RSI_PERIOD,
    lower_thresh: int = DEFAULT_RSI_LOWER,
    upper_thresh: int = DEFAULT_RSI_UPPER,
):
    """Generate trading signals based on RSI crossovers.

    Args:
        df (pd.DataFrame): DataFrame with 'close' price column and 'timestamp'.
        period (int): Lookback period for RSI calculation.
        lower_thresh (int): Oversold threshold.
        upper_thresh (int): Overbought threshold.

    Returns:
        list: List of dictionaries with 'timestamp', 'action', 'price'.
    """
    if df is None or df.empty:
        logging.warning("Empty dataframe provided to RSI strategy")
        return []

    if len(df) < period:
        logging.warning(f"Not enough data for {period}-period RSI calculation")
        return []

    df = df.copy()
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    df['rsi'] = rsi

    signals = []
    for i in range(1, len(df)):
        if pd.isna(df.iloc[i-1]['rsi']) or pd.isna(df.iloc[i]['rsi']):
            continue

        prev_rsi = df.iloc[i-1]['rsi']
        curr_rsi = df.iloc[i]['rsi']

        if prev_rsi <= lower_thresh and curr_rsi > lower_thresh:
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'action': 'buy',
                'price': df.iloc[i]['close']
            })
        elif prev_rsi >= upper_thresh and curr_rsi < upper_thresh:
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'action': 'sell',
                'price': df.iloc[i]['close']
            })

    logging.info(f"Generated {len(signals)} RSI crossover signals")
    return signals

# TODO(Devin): integrate RSI signals into Streamlit dashboard
