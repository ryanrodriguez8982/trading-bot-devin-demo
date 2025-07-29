import sqlite3
import logging
import os
from datetime import datetime

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

def log_signals_to_db(signals, symbol, strategy_id='sma'):
    """
    Log trading signals to SQLite database.
    
    Args:
        signals (list): List of trading signals with timestamp, action, price
        symbol (str): Trading pair symbol
        strategy_id (str): Strategy identifier (default: 'sma')
    """
    if not signals:
        return
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signals.db')
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            create_signals_table(cursor)
            
            for signal in signals:
                timestamp_str = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    INSERT INTO signals (timestamp, action, price, symbol, strategy_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (timestamp_str, signal['action'], float(signal['price']), symbol, strategy_id))
            
            conn.commit()
            logging.info(f"Logged {len(signals)} signals to database {db_path}")
            
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        raise
    except Exception as e:
        logging.error(f"Error logging signals to database: {e}")
        raise

def get_signals_from_db(symbol=None, strategy_id=None, limit=None):
    """
    Retrieve signals from the database.
    
    Args:
        symbol (str, optional): Filter by trading pair symbol
        strategy_id (str, optional): Filter by strategy identifier
        limit (int, optional): Limit number of results
        
    Returns:
        list: List of signal records as tuples
    """
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signals.db')
    
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
    except Exception as e:
        logging.error(f"Error retrieving signals from database: {e}")
        return []
