import sqlite3
import logging
import os
from typing import Optional, List, Tuple, Dict, Any

from trading_bot.utils.state import default_state_dir

logger = logging.getLogger(__name__)


def _default_db_path() -> str:
    return os.path.join(default_state_dir(), "signals.db")


def create_signals_table(cursor: sqlite3.Cursor) -> None:
    """Create the signals table if it doesn't exist."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            price REAL NOT NULL,
            symbol TEXT NOT NULL,
            strategy_id TEXT NOT NULL
        )
        """
    )
    # Helpful index for common lookups
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_signals_symbol_time
        ON signals(symbol, timestamp DESC)
        """
    )


def create_trades_table(cursor: sqlite3.Cursor) -> None:
    """Create the trades table if it doesn't exist."""
    cursor.execute(
        """
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
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_trades_symbol_time
        ON trades(symbol, timestamp DESC)
        """
    )


def log_signals_to_db(
    signals: List[Dict[str, Any]],
    symbol: str,
    strategy_id: str = "sma",
    db_path: Optional[str] = None,
) -> None:
    """
    Log trading signals to SQLite database.

    Args:
        signals: List of trading signals with timestamp, action, price
        symbol: Trading pair symbol
        strategy_id: Strategy identifier (default: 'sma')
        db_path: Path to SQLite database file
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

            rows = [
                (
                    s["timestamp"].isoformat(),
                    s["action"],
                    float(s["price"]),
                    symbol,
                    strategy_id,
                )
                for s in signals
            ]
            cursor.executemany(
                """
                INSERT INTO signals (timestamp, action, price, symbol, strategy_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
            logger.info(
                "Logged %d signals for %s (strategy=%s) to database %s",
                len(signals),
                symbol,
                strategy_id,
                db_path,
            )

    except sqlite3.Error:
        logger.exception(
            "log_signals_to_db: Database error for symbol=%s strategy=%s db_path=%s",
            symbol,
            strategy_id,
            db_path,
        )
        raise


def log_trade_to_db(trade: Dict[str, Any], db_path: Optional[str] = None) -> None:
    """Log a single trade execution to the trades table."""
    if db_path is None:
        db_path = _default_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            create_trades_table(cursor)
            cursor.execute(
                """
                INSERT INTO trades (timestamp, symbol, side, qty, price, fee, strategy, broker)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade["timestamp"],
                    trade["symbol"],
                    trade["side"],
                    float(trade["qty"]),
                    float(trade["price"]),
                    float(trade.get("fee", 0.0)),
                    trade.get("strategy", ""),
                    trade.get("broker", ""),
                ),
            )
            conn.commit()
            logger.info(
                "Logged trade %s %s qty=%s price=%.4f strategy=%s to database %s",
                trade["side"],
                trade["symbol"],
                trade.get("qty"),
                float(trade.get("price", 0.0)),
                trade.get("strategy", ""),
                db_path,
            )
    except sqlite3.Error:
        logger.exception(
            "log_trade_to_db: Database error for trade=%s db_path=%s",
            trade,
            db_path,
        )
        raise
    except (KeyError, ValueError, TypeError):
        logger.exception(
            "log_trade_to_db: Error logging trade payload %s to %s",
            trade,
            db_path,
        )
        raise


def get_trades_from_db(
    symbol: Optional[str] = None,
    limit: Optional[int] = None,
    db_path: Optional[str] = None,
) -> List[Tuple[Any, ...]]:
    """Retrieve executed trades from the database.

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
            query = "SELECT timestamp, symbol, side, qty, price, fee, strategy, broker FROM trades"
            params: List[Any] = []
            conditions: List[str] = []

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

    except sqlite3.Error:
        logger.exception(
            "get_trades_from_db: Database error for symbol=%s limit=%s db_path=%s",
            symbol,
            limit,
            db_path,
        )
        return []


def get_signals_from_db(
    symbol: Optional[str] = None,
    strategy_id: Optional[str] = None,
    limit: Optional[int] = None,
    db_path: Optional[str] = None,
) -> List[Tuple[Any, ...]]:
    """
    Retrieve signals from the database.

    Args:
        symbol: Filter by trading pair symbol
        strategy_id: Filter by strategy identifier
        limit: Limit number of results
        db_path: Path to SQLite database file

    Returns:
        List of signal records as tuples
    """
    if db_path is None:
        db_path = _default_db_path()

    if not os.path.exists(db_path):
        return []

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            query = "SELECT timestamp, action, price, symbol, strategy_id FROM signals"
            params: List[Any] = []
            conditions: List[str] = []

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

    except sqlite3.Error:
        logger.exception(
            "get_signals_from_db: Database error for symbol=%s strategy=%s limit=%s db_path=%s",
            symbol,
            strategy_id,
            limit,
            db_path,
        )
        return []


def _create_processed_table(cursor: sqlite3.Cursor) -> None:
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
    is stored in ``processed_signals``. Subsequent calls with the same key
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
    except sqlite3.Error:
        logger.exception(
            "mark_signal_handled: Database error for symbol=%s strategy=%s timeframe=%s db_path=%s",
            symbol,
            strategy_id,
            timeframe,
            db_path,
        )
        raise
