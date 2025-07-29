import pandas as pd
import logging
from datetime import datetime

def sma_crossover_strategy(df):
    """
    Implement SMA crossover strategy.
    
    Buy when 5-period SMA crosses above 20-period SMA.
    Sell when 5-period SMA crosses below 20-period SMA.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLCV data
        
    Returns:
        list: List of dictionaries with 'timestamp', 'action' ('buy'/'sell')
    """
    if len(df) < 20:
        logging.warning("Not enough data for 20-period SMA calculation")
        return []
    
    df = df.copy()
    df['sma_5'] = df['close'].rolling(window=5).mean()
    df['sma_20'] = df['close'].rolling(window=20).mean()
    
    signals = []
    
    for i in range(1, len(df)):
        if pd.isna(df.iloc[i]['sma_5']) or pd.isna(df.iloc[i]['sma_20']):
            continue
            
        current_5_sma = df.iloc[i]['sma_5']
        current_20_sma = df.iloc[i]['sma_20']
        prev_5_sma = df.iloc[i-1]['sma_5']
        prev_20_sma = df.iloc[i-1]['sma_20']
        
        if (prev_5_sma <= prev_20_sma and current_5_sma > current_20_sma):
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'action': 'buy'
            })
        elif (prev_5_sma >= prev_20_sma and current_5_sma < current_20_sma):
            signals.append({
                'timestamp': df.iloc[i]['timestamp'],
                'action': 'sell'
            })
    
    logging.info(f"Generated {len(signals)} trading signals")
    return signals
