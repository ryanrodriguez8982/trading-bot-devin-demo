import pytest
import pandas as pd
import sqlite3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from trading_bot.signal_logger import log_signals_to_db, get_signals_from_db


def test_log_signals_to_db(tmp_path):
    """Test that signals are logged to SQLite database correctly."""
    import time
    unique_id = str(int(time.time() * 1000))
    test_symbol = f"TEST{unique_id}/USDT"
    test_strategy = f"test_strategy_{unique_id}"

    signals = [
        {'timestamp': pd.Timestamp('2024-01-01 10:00:00'), 'action': 'buy', 'price': 50000.0},
        {'timestamp': pd.Timestamp('2024-01-01 11:00:00'), 'action': 'sell', 'price': 51000.0}
    ]

    db_path = tmp_path / "signals.db"
    log_signals_to_db(signals, test_symbol, test_strategy, db_path=str(db_path))

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


def test_get_signals_from_db(tmp_path):
    """Test retrieving signals from database."""
    signals = [
        {'timestamp': pd.Timestamp('2024-01-01 12:00:00'), 'action': 'buy', 'price': 52000.0},
        {'timestamp': pd.Timestamp('2024-01-01 13:00:00'), 'action': 'sell', 'price': 53000.0}
    ]

    db_path = tmp_path / "signals.db"
    log_signals_to_db(signals, "ETH/USDT", "test_strategy", db_path=str(db_path))

    retrieved_signals = get_signals_from_db(symbol="ETH/USDT", strategy_id="test_strategy", limit=2, db_path=str(db_path))
    
    assert len(retrieved_signals) >= 2, "Should retrieve at least 2 signals"
    assert retrieved_signals[0][1] == 'sell', "Most recent should be sell signal"
    assert retrieved_signals[0][3] == 'ETH/USDT', "Symbol should match"
    assert retrieved_signals[0][4] == 'test_strategy', "Strategy ID should match"


def test_empty_signals_list(tmp_path):
    """Test that empty signals list is handled gracefully."""
    log_signals_to_db([], "BTC/USDT", "sma", db_path=str(tmp_path / "signals.db"))


def test_database_schema(tmp_path):
    """Test that database schema matches requirements."""
    signals = [
        {'timestamp': pd.Timestamp('2024-01-01 14:00:00'), 'action': 'buy', 'price': 54000.0}
    ]

    db_path = tmp_path / "signals.db"
    log_signals_to_db(signals, "TEST/USDT", "schema_test", db_path=str(db_path))

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


def test_missing_database_file(tmp_path):
    """Function should create missing directories for database path."""
    bad_db_path = tmp_path / "nonexistent" / "signals.db"
    signal = [{'timestamp': pd.Timestamp('2024-01-01 00:00:00'), 'action': 'buy', 'price': 100}]
    log_signals_to_db(signal, "BTC/USDT", db_path=str(bad_db_path))
    assert bad_db_path.exists()


def test_malformed_signal_entry(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE IF NOT EXISTS signals (timestamp TEXT, action TEXT, price REAL, symbol TEXT, strategy_id TEXT)")
    conn.close()

    bad_signal = [{'timestamp': pd.Timestamp('2024-01-01'), 'price': 100}]
    with pytest.raises(KeyError):
        log_signals_to_db(bad_signal, "BTC/USDT", db_path=str(db_file))


def test_locked_database(tmp_path):
    db_file = tmp_path / "locked.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE IF NOT EXISTS signals (timestamp TEXT, action TEXT, price REAL, symbol TEXT, strategy_id TEXT)")
    conn.execute("BEGIN EXCLUSIVE")

    good_signal = [{'timestamp': pd.Timestamp('2024-01-01'), 'action': 'buy', 'price': 100}]
    with pytest.raises(sqlite3.OperationalError):
        log_signals_to_db(good_signal, "BTC/USDT", db_path=str(db_file))


def test_invalid_schema_detection(tmp_path):
    """Logging should fail if schema is missing required columns."""
    db_file = tmp_path / "invalid.db"
    conn = sqlite3.connect(db_file)
    # Create table without strategy_id column
    conn.execute("CREATE TABLE signals (timestamp TEXT, action TEXT, price REAL, symbol TEXT)")
    conn.commit()
    conn.close()

    signal = [{'timestamp': pd.Timestamp('2024-01-01'), 'action': 'buy', 'price': 100}]
    with pytest.raises(sqlite3.OperationalError):
        log_signals_to_db(signal, "BTC/USDT", db_path=str(db_file))

def test_timestamp_parsing_failure(tmp_path):
    """Ensure graceful failure when timestamp cannot be parsed."""
    db_file = tmp_path / "timestamp.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE IF NOT EXISTS signals (timestamp TEXT, action TEXT, price REAL, symbol TEXT, strategy_id TEXT)")
    conn.close()

    malformed_signal = [{'timestamp': 'invalid-date', 'action': 'buy', 'price': 50}]
    with pytest.raises(AttributeError):
        log_signals_to_db(malformed_signal, "BTC/USDT", db_path=str(db_file))
