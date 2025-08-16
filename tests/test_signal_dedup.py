import os
import sys
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from trading_bot.signal_logger import mark_signal_handled


def test_mark_signal_handled(tmp_path):
    db_file = tmp_path / "signals.db"
    ts = pd.Timestamp("2024-01-01 00:00:00").isoformat()
    first = mark_signal_handled("BTC/USDT", "sma", "1m", ts, "buy", db_path=str(db_file))
    assert first is False
    second = mark_signal_handled("BTC/USDT", "sma", "1m", ts, "buy", db_path=str(db_file))
    assert second is True
