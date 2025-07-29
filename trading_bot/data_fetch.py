import ccxt
import pandas as pd
import logging
from datetime import datetime

def fetch_btc_usdt_data(symbol="BTC/USDT", timeframe="1m", limit=500):
    """
    Fetch historical OHLCV data from Binance.
    
    Args:
        symbol (str): Trading pair symbol (e.g., BTC/USDT)
        timeframe (str): Timeframe for candles (e.g., 1m, 5m)
        limit (int): Number of candles to fetch
    
    Returns:
        pd.DataFrame: DataFrame with columns: timestamp, open, high, low, close, volume
    """
    try:
        exchange = ccxt.binance()
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        logging.info(f"Successfully fetched {len(df)} candles for {symbol}")
        return df
        
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        raise
