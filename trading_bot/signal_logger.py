import sqlite3
import logging
import os
from typing import Optional

from trading_bot.utils.state import default_state_dir


def _default_db_path() -> str:
    return os.path.join(default_state_dir(), "signals.db")

def create_signals_table(cursor):
    """Create the signals table if it doesn't exist."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            price REAL NOT NULL,
            symbol TEXT NOT NULL,
            strategy_id TEXT NOT NULL
        )
    ''')


def create_trades_table(cursor):
    """Create the trades table if it doesn't exist."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            qty REAL NOT NULL,
            price REAL NOT NULL,
            fee REAL NOT NULL,
            strategy TEXT NOT NULL,
            broker TEXT NOT NULL
        )
    ''')

def log_signals_to_db(signals, symbol, strategy_id='sma', db_path=None):
    """
    Log trading signals to SQLite database.
    
    Args:
        signals (list): List of trading signals with timestamp, action, price
        symbol (str): Trading pair symbol
        strategy_id (str): Strategy identifier (default: 'sma')
        db_path (str, optional): Path to SQLite database file
    """
    if not signals:
        return
    
    if db_path is None:
        db_path = _default_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            create_signals_table(cursor)
            
            for signal in signals:
                timestamp_str = signal['timestamp'].isoformat()
                cursor.execute(
                    '''
                    INSERT INTO signals (timestamp, action, price, symbol, strategy_id)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (timestamp_str, signal['action'], float(signal['price']), symbol, strategy_id),
                )
            
            conn.commit()
            logging.debug(
                "Logged %d signals to database %s", len(signals), db_path
            )
            
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        raise


def log_trade_to_db(trade, db_path=None):
    """Log a single trade execution to the trades table."""
    if db_path is None:
        db_path = _default_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            create_trades_table(cursor)
            cursor.execute(
                '''
                INSERT INTO trades (timestamp, symbol, side, qty, price, fee, strategy, broker)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    trade['timestamp'],
                    trade['symbol'],
                    trade['side'],
                    float(trade['qty']),
                    float(trade['price']),
                    float(trade.get('fee', 0.0)),
                    trade.get('strategy', ''),
                    trade.get('broker', ''),
                ),
            )
            conn.commit()
            logging.debug(
                "Logged trade %s %s to database %s",
                trade['side'],
                trade['symbol'],
                db_path,
            )
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        raise
    except (KeyError, ValueError, TypeError) as e:
        logging.error(f"Error logging trade to database: {e}")
        raise


def get_trades_from_db(symbol=None, limit=None, db_path=None):
    """Retrieve executed trades from the database.

    Parameters
    ----------
    symbol: str, optional
        Filter by trading pair symbol.
    limit: int, optional
        Maximum number of records to return.
    db_path: str, optional
        Path to the SQLite database file.

    Returns
    -------
    list
        List of trade tuples ordered by newest first.
    """
    if db_path is None:
        db_path = _default_db_path()

    if not os.path.exists(db_path):
        return []

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = (
                "SELECT timestamp, symbol, side, qty, price, fee, strategy, broker FROM trades"
            )
            params = []
            conditions = []

            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY timestamp DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor.execute(query, params)
            return cursor.fetchall()

    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return []

def get_signals_from_db(symbol=None, strategy_id=None, limit=None, db_path=None):
    """
    Retrieve signals from the database.
    
    Args:
        symbol (str, optional): Filter by trading pair symbol
        strategy_id (str, optional): Filter by strategy identifier
        limit (int, optional): Limit number of results
        db_path (str, optional): Path to SQLite database file
        
    Returns:
        list: List of signal records as tuples
    """
    if db_path is None:
        db_path = _default_db_path()
    
    if not os.path.exists(db_path):
        return []
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            query = "SELECT timestamp, action, price, symbol, strategy_id FROM signals"
            params = []
            conditions = []
            
            if symbol:
                conditions.append("symbol = ?")
                params.append(symbol)
            
            if strategy_id:
                conditions.append("strategy_id = ?")
                params.append(strategy_id)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall()
            
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        return []


def _create_processed_table(cursor):
    """Ensure table for processed signals exists."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_signals (
            strategy_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            signal_ts TEXT NOT NULL,
            action TEXT NOT NULL,
            PRIMARY KEY (strategy_id, symbol, timeframe, signal_ts, action)
        )
        """
    )


def mark_signal_handled(
    symbol: str,
    strategy_id: str,
    timeframe: str,
    signal_ts: str,
    action: str,
    db_path: Optional[str] = None,
) -> bool:
    """Record a signal and return True if it was already processed.

    The unique key ``(strategy_id, symbol, timeframe, signal_ts, action)``
    is stored in ``processed_signals``.  Subsequent calls with the same key
    return ``True`` without modifying state, allowing callers to skip
    duplicate work.
    """
    if db_path is None:
        db_path = _default_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            _create_processed_table(cursor)
            try:
                cursor.execute(
                    """
                    INSERT INTO processed_signals(strategy_id, symbol, timeframe, signal_ts, action)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (strategy_id, symbol, timeframe, signal_ts, action),
                )
                conn.commit()
                return False
            except sqlite3.IntegrityError:
                return True
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        raise
