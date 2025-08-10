import pandas as pd
import logging
from datetime import datetime

from trading_bot.utils.config import get_config


logger = logging.getLogger(__name__)

CONFIG = get_config()
DEFAULT_SMA_SHORT = CONFIG.get("sma_short", 5)
DEFAULT_SMA_LONG = CONFIG.get("sma_long", 20)


def sma_crossover_strategy(df, sma_short=DEFAULT_SMA_SHORT, sma_long=DEFAULT_SMA_LONG):
    """
    Implement SMA crossover strategy.
    
    Buy when short-period SMA crosses above long-period SMA.
    Sell when short-period SMA crosses below long-period SMA.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLCV data
        sma_short (int): Short-period SMA window
        sma_long (int): Long-period SMA window
        
    Returns:
        list: List of dictionaries with 'timestamp', 'action' ('buy'/'sell')
    """
    if len(df) < sma_long:
        logger.warning(f"Not enough data for {sma_long}-period SMA calculation")
        return []
    
    df = df.copy()
    df[f'sma_{sma_short}'] = df['close'].rolling(window=sma_short).mean()
    df[f'sma_{sma_long}'] = df['close'].rolling(window=sma_long).mean()
    
    signals = []
    
    for i in range(1, len(df)):
        if pd.isna(df.iloc[i][f'sma_{sma_short}']) or pd.isna(df.iloc[i][f'sma_{sma_long}']):
            continue
            
        current_short_sma = df.iloc[i][f'sma_{sma_short}']
        current_long_sma = df.iloc[i][f'sma_{sma_long}']
        prev_short_sma = df.iloc[i-1][f'sma_{sma_short}']
        prev_long_sma = df.iloc[i-1][f'sma_{sma_long}']
        
        if (prev_short_sma <= prev_long_sma and current_short_sma > current_long_sma):
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'action': 'buy',
                'price': df.iloc[i]['close']
            })
        elif (prev_short_sma >= prev_long_sma and current_short_sma < current_long_sma):
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'action': 'sell',
                'price': df.iloc[i]['close']
            })
    
    logger.info(f"Generated {len(signals)} trading signals")
    return signals
