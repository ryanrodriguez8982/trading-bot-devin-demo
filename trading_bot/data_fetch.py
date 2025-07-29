import ccxt
import pandas as pd
import logging
from datetime import datetime

def fetch_btc_usdt_data():
    """
    Fetch historical OHLCV data for BTC/USDT from Binance.
    
    Returns:
        pd.DataFrame: DataFrame with columns: timestamp, open, high, low, close, volume
    """
    try:
        exchange = ccxt.binance()
        symbol = 'BTC/USDT'
        timeframe = '1m'
        limit = 500
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        logging.info(f"Successfully fetched {len(df)} candles for {symbol}")
        return df
        
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        raise
