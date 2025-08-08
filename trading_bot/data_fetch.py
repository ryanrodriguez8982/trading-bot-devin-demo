import pandas as pd
import logging
from datetime import datetime

from trading_bot.exchange import create_exchange

def fetch_btc_usdt_data(symbol="BTC/USDT", timeframe="1m", limit=500, exchange=None, exchange_name=None, **creds):
    """
    Fetch historical OHLCV data from the specified exchange.
    
    Args:
        symbol (str): Trading pair symbol (e.g., BTC/USDT)
        timeframe (str): Timeframe for candles (e.g., 1m, 5m)
        limit (int): Number of candles to fetch
        exchange (ccxt.Exchange, optional): Pre-instantiated exchange client
        exchange_name (str, optional): Exchange name string to instantiate dynamically
        creds (dict): Optional credentials

    Returns:
        pd.DataFrame: DataFrame with OHLCV data
    """
    try:
        if exchange is None:
            if exchange_name:
                exchange = create_exchange(**creds, exchange_name=exchange_name)
            elif creds:
                exchange = create_exchange(**creds)
            else:
                exchange = create_exchange()
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        logging.info(f"Successfully fetched {len(df)} candles for {symbol} from {exchange.id}")
        return df
        
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        raise
