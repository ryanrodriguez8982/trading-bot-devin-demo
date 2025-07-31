import os
import sys
import pandas as pd
from unittest import mock

project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(project_root, 'trading_bot'))
sys.path.insert(0, project_root)

from main import send_alert


def test_send_alert_outputs(capsys):
    signal = {'timestamp': pd.Timestamp('2024-01-01 10:00:00'), 'action': 'buy', 'price': 12345.0}
    with mock.patch('main.notification') as mock_notify:
        send_alert(signal)
        captured = capsys.readouterr()
        assert "ALERT: BUY" in captured.out
        mock_notify.notify.assert_called_once()
