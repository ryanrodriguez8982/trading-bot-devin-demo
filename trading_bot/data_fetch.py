import pandas as pd
import logging
from datetime import datetime

from trading_bot.exchange import create_exchange

def fetch_btc_usdt_data(symbol="BTC/USDT", timeframe="1m", limit=500, exchange=None, **creds):
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
        if exchange is None:
            if creds:
                exchange = create_exchange(**creds)
            else:
                exchange = create_exchange()
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        logging.info(f"Successfully fetched {len(df)} candles for {symbol}")
        return df
        
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        raise
