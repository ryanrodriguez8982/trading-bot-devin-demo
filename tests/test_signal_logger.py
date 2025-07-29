import pytest
import pandas as pd
import sqlite3
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'trading_bot'))

from signal_logger import log_signals_to_db, get_signals_from_db

def test_log_signals_to_db():
    """Test that signals are logged to SQLite database correctly."""
    import time
    unique_id = str(int(time.time() * 1000))
    test_symbol = f"TEST{unique_id}/USDT"
    test_strategy = f"test_strategy_{unique_id}"
    
    signals = [
        {'timestamp': pd.Timestamp('2024-01-01 10:00:00'), 'action': 'buy', 'price': 50000.0},
        {'timestamp': pd.Timestamp('2024-01-01 11:00:00'), 'action': 'sell', 'price': 51000.0}
    ]
    
    log_signals_to_db(signals, test_symbol, test_strategy)
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signals.db')
    assert os.path.exists(db_path), "Database file should be created"
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals'")
        table_exists = cursor.fetchone()
        assert table_exists, "Signals table should exist"
        
        cursor.execute("SELECT COUNT(*) FROM signals WHERE symbol = ? AND strategy_id = ?", 
                      (test_symbol, test_strategy))
        count = cursor.fetchone()[0]
        assert count == 2, "Exactly 2 signals should be inserted"
        
        cursor.execute("""
            SELECT timestamp, action, price, symbol, strategy_id 
            FROM signals 
            WHERE symbol = ? AND strategy_id = ?
            ORDER BY timestamp ASC
        """, (test_symbol, test_strategy))
        records = cursor.fetchall()
        
        assert len(records) == 2, "Should retrieve exactly 2 test records"
        assert records[0][1] == 'buy', "First record should be buy"
        assert records[0][2] == 50000.0, "First record price should be 50000.0"
        assert records[1][1] == 'sell', "Second record should be sell"
        assert records[1][2] == 51000.0, "Second record price should be 51000.0"

def test_get_signals_from_db():
    """Test retrieving signals from database."""
    signals = [
        {'timestamp': pd.Timestamp('2024-01-01 12:00:00'), 'action': 'buy', 'price': 52000.0},
        {'timestamp': pd.Timestamp('2024-01-01 13:00:00'), 'action': 'sell', 'price': 53000.0}
    ]
    
    log_signals_to_db(signals, "ETH/USDT", "test_strategy")
    
    retrieved_signals = get_signals_from_db(symbol="ETH/USDT", strategy_id="test_strategy", limit=2)
    
    assert len(retrieved_signals) >= 2, "Should retrieve at least 2 signals"
    assert retrieved_signals[0][1] == 'sell', "Most recent should be sell signal"
    assert retrieved_signals[0][3] == 'ETH/USDT', "Symbol should match"
    assert retrieved_signals[0][4] == 'test_strategy', "Strategy ID should match"

def test_empty_signals_list():
    """Test that empty signals list is handled gracefully."""
    log_signals_to_db([], "BTC/USDT", "sma")

def test_database_schema():
    """Test that database schema matches requirements."""
    signals = [
        {'timestamp': pd.Timestamp('2024-01-01 14:00:00'), 'action': 'buy', 'price': 54000.0}
    ]
    
    log_signals_to_db(signals, "TEST/USDT", "schema_test")
    
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'signals.db')
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(signals)")
        columns = cursor.fetchall()
        
        column_names = [col[1] for col in columns]
        expected_columns = ['id', 'timestamp', 'action', 'price', 'symbol', 'strategy_id']
        
        for expected_col in expected_columns:
            assert expected_col in column_names, f"Column {expected_col} should exist in signals table"
        
        column_types = {col[1]: col[2] for col in columns}
        assert column_types['timestamp'] == 'TEXT', "timestamp should be TEXT type"
        assert column_types['action'] == 'TEXT', "action should be TEXT type"
        assert column_types['price'] == 'REAL', "price should be REAL type"
        assert column_types['symbol'] == 'TEXT', "symbol should be TEXT type"
        assert column_types['strategy_id'] == 'TEXT', "strategy_id should be TEXT type"
