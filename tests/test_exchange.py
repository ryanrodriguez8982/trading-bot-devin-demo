import sys
import os
from unittest import mock

project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(project_root, 'trading_bot'))

from exchange import create_exchange


def test_create_exchange_with_keys():
    with mock.patch('ccxt.binance') as mock_binance:
        create_exchange('key', 'secret', 'pass')
        mock_binance.assert_called_once()
        args, kwargs = mock_binance.call_args
        params = args[0]
        assert params['apiKey'] == 'key'
        assert params['secret'] == 'secret'
        assert params['password'] == 'pass'

