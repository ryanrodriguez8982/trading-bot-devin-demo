import pandas as pd
import logging


logger = logging.getLogger(__name__)


def bbands_strategy(df, window=20, num_std=2):
    """Generate trading signals based on Bollinger Bands.

    Args:
        df (pd.DataFrame): DataFrame with OHLCV data and 'timestamp'.
        window (int): Moving average window for the middle band.
        num_std (int or float): Number of standard deviations for the bands.

    Returns:
        list: List of signals with timestamp, action and price.
    """
    if df is None or df.empty:
        logger.warning("Empty dataframe provided to Bollinger strategy")
        return []

    if len(df) < window:
        logger.warning(f"Not enough data for {window}-period Bollinger Bands")
        return []

    df = df.copy()
    df['middle_band'] = df['close'].rolling(window=window).mean()
    df['std_dev'] = df['close'].rolling(window=window).std()
    df['upper_band'] = df['middle_band'] + num_std * df['std_dev']
    df['lower_band'] = df['middle_band'] - num_std * df['std_dev']

    signals = []
    for i in range(1, len(df)):
        if (pd.isna(df.iloc[i]['lower_band']) or
                pd.isna(df.iloc[i]['upper_band'])):
            continue
        prev_close = df.iloc[i-1]['close']
        curr_close = df.iloc[i]['close']
        prev_lower = df.iloc[i-1]['lower_band']
        curr_lower = df.iloc[i]['lower_band']
        prev_upper = df.iloc[i-1]['upper_band']
        curr_upper = df.iloc[i]['upper_band']

        if prev_close < prev_lower and curr_close >= curr_lower:
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'action': 'buy',
                'price': curr_close
            })
        elif prev_close > prev_upper and curr_close <= curr_upper:
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'action': 'sell',
                'price': curr_close
            })

    logger.info(f"Generated {len(signals)} Bollinger band signals")
    return signals
