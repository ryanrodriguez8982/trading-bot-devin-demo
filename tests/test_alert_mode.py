import logging
from unittest import mock

import pandas as pd

from trading_bot.main import send_alert


def test_send_alert_outputs(caplog):
    signal = {
        "timestamp": pd.Timestamp("2024-01-01 10:00:00"),
        "action": "buy",
        "price": 12345.0,
    }
    with mock.patch("trading_bot.main.notification") as mock_notify:
        with caplog.at_level(logging.INFO):
            send_alert(signal)
        assert any("ALERT: BUY" in r.message for r in caplog.records)
        mock_notify.notify.assert_called_once()
