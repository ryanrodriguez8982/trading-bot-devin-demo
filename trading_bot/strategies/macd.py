import pandas as pd
import logging


def macd_strategy(df, fast_period=12, slow_period=26, signal_period=9):
    """Generate trading signals based on MACD crossovers.

    Args:
        df (pd.DataFrame): DataFrame with ``close`` and ``timestamp`` columns.
        fast_period (int): Fast EMA period.
        slow_period (int): Slow EMA period.
        signal_period (int): Signal line EMA period.

    Returns:
        list: dictionaries with ``timestamp``, ``action`` and ``price``.
    """
    if df is None or df.empty:
        logging.warning("Empty dataframe provided to MACD strategy")
        return []

    if 'close' not in df.columns:
        raise KeyError('close')

    if len(df) < slow_period:
        logging.warning(
            f"Not enough data for {slow_period}-period EMA calculation"
        )
        return []

    df = df.copy()
    df['ema_fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal'] = df['macd'].ewm(span=signal_period, adjust=False).mean()

    signals = []
    for i in range(1, len(df)):
        if pd.isna(df.iloc[i-1]['macd']) or pd.isna(df.iloc[i-1]['signal']):
            continue
        prev_macd = df.iloc[i-1]['macd']
        prev_signal = df.iloc[i-1]['signal']
        curr_macd = df.iloc[i]['macd']
        curr_signal = df.iloc[i]['signal']

        logging.debug(
            "t=%s macd=%.2f signal=%.2f",
            df.iloc[i]['timestamp'],
            curr_macd,
            curr_signal,
        )

        if prev_macd <= prev_signal and curr_macd > curr_signal:
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'action': 'buy',
                'price': df.iloc[i]['close']
            })
        elif prev_macd >= prev_signal and curr_macd < curr_signal:
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'action': 'sell',
                'price': df.iloc[i]['close']
            })

    logging.debug("Generated %d MACD crossover signals", len(signals))
    return signals
