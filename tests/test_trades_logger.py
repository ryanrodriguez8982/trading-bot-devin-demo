import time

from trading_bot.signal_logger import get_trades_from_db, log_trade_to_db


def test_log_and_get_trades():
    unique_id = str(int(time.time() * 1000))
    symbol = f"TRADE{unique_id}/USDT"
    trade = {
        "timestamp": "2024-01-01 00:00:00",
        "symbol": symbol,
        "side": "buy",
        "qty": 1.5,
        "price": 100.0,
        "fee": 0.1,
        "strategy": "test",
        "broker": "paper",
    }
    log_trade_to_db(trade)
    trades = get_trades_from_db(symbol=symbol, limit=1)
    assert trades, "Should retrieve logged trade"
    row = trades[0]
    assert row[1] == symbol
    assert row[2] == "buy"
    assert abs(row[3] - 1.5) < 1e-9
    assert abs(row[4] - 100.0) < 1e-9
    assert row[6] == "test"
    assert row[7] == "paper"


def test_get_trades_missing_db(tmp_path):
    missing = tmp_path / "no.db"
    result = get_trades_from_db(db_path=str(missing))
    assert result == []
