import pytest
import pandas as pd
import sqlite3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import trading_bot.signal_logger as signal_logger
from trading_bot.signal_logger import (
    get_signals_from_db,
    get_trades_from_db,
    log_signals_to_db,
    log_trade_to_db,
    mark_signal_handled,
)


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


def test_log_signals_default_path(monkeypatch, tmp_path):
    monkeypatch.setattr(
        signal_logger, "_default_db_path", lambda: str(tmp_path / "signals.db")
    )
    signals = [{"timestamp": pd.Timestamp("2024-01-01"), "action": "buy", "price": 1}]
    log_signals_to_db(signals, "BTC/USDT")
    assert (tmp_path / "signals.db").exists()


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


def test_log_trade_and_get_trades(tmp_path):
    trade = {
        "timestamp": "2024-01-01T00:00:00",
        "symbol": "BTC/USDT",
        "side": "buy",
        "qty": 1,
        "price": 100,
        "fee": 0,
        "strategy": "sma",
        "broker": "paper",
    }
    db_path = tmp_path / "trades.db"
    log_trade_to_db(trade, db_path=str(db_path))
    trades = get_trades_from_db(symbol="BTC/USDT", db_path=str(db_path))
    assert len(trades) == 1
    assert trades[0][1] == "BTC/USDT"


def test_log_trade_invalid(tmp_path):
    db_path = tmp_path / "bad.db"
    with pytest.raises(KeyError):
        log_trade_to_db({"timestamp": "2024-01-01"}, db_path=str(db_path))


def test_log_trade_db_error(monkeypatch):
    trade = {
        "timestamp": "2024-01-01T00:00:00",
        "symbol": "BTC/USDT",
        "side": "buy",
        "qty": 1,
        "price": 100,
    }

    def bad_connect(*args, **kwargs):  # pragma: no cover - used for testing error path
        raise sqlite3.OperationalError("locked")

    monkeypatch.setattr(sqlite3, "connect", bad_connect)
    with pytest.raises(sqlite3.OperationalError):
        log_trade_to_db(trade)


def test_mark_signal_handled(tmp_path):
    db_path = tmp_path / "processed.db"
    first = mark_signal_handled(
        "BTC/USDT", "sma", "1m", "123", "buy", db_path=str(db_path)
    )
    second = mark_signal_handled(
        "BTC/USDT", "sma", "1m", "123", "buy", db_path=str(db_path)
    )
    assert first is False
    assert second is True


def test_mark_signal_handled_default_path(monkeypatch, tmp_path):
    monkeypatch.setattr(
        signal_logger, "_default_db_path", lambda: str(tmp_path / "proc.db")
    )
    assert mark_signal_handled("BTC/USDT", "sma", "1m", "1", "buy") is False


def test_mark_signal_handled_db_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        signal_logger, "_default_db_path", lambda: str(tmp_path / "proc.db")
    )

    def bad_connect(*args, **kwargs):
        raise sqlite3.OperationalError("locked")

    monkeypatch.setattr(sqlite3, "connect", bad_connect)
    with pytest.raises(sqlite3.OperationalError):
        mark_signal_handled("BTC/USDT", "sma", "1m", "1", "buy")


def test_get_trades_db_error(monkeypatch, tmp_path):
    def bad_connect(*args, **kwargs):
        raise sqlite3.OperationalError("boom")

    monkeypatch.setattr(sqlite3, "connect", bad_connect)
    result = get_trades_from_db(db_path=str(tmp_path / "t.db"))
    assert result == []


def test_get_signals_default_path(monkeypatch, tmp_path):
    monkeypatch.setattr(
        signal_logger, "_default_db_path", lambda: str(tmp_path / "sigs.db")
    )
    assert get_signals_from_db() == []


def test_get_signals_db_error(monkeypatch, tmp_path):
    db = tmp_path / "sigs.db"
    db.touch()

    def bad_connect(*args, **kwargs):
        raise sqlite3.OperationalError("boom")

    monkeypatch.setattr(sqlite3, "connect", bad_connect)
    assert get_signals_from_db(db_path=str(db)) == []
