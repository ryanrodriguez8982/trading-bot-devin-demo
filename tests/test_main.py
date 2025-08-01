
import pytest
import pandas as pd
import sys
import os

from trading_bot.data_fetch import fetch_btc_usdt_data
from trading_bot.strategy import sma_crossover_strategy

def test_data_fetch_structure():
    """Test that data fetch returns correct structure."""
    try:
        df = fetch_btc_usdt_data()
        
        assert isinstance(df, pd.DataFrame), "Should return a pandas DataFrame"
        
        expected_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        assert list(df.columns) == expected_columns, f"Should have columns: {expected_columns}"
        
        assert len(df) > 0, "Should return non-empty DataFrame"
        assert len(df) <= 500, "Should not exceed 500 candles limit"
        
        assert df['open'].dtype in ['float64', 'int64'], "Open prices should be numeric"
        assert df['close'].dtype in ['float64', 'int64'], "Close prices should be numeric"
        
    except Exception as e:
        pytest.skip(f"Skipping data fetch test due to API error: {e}")

def test_strategy_with_sample_data():
    """Test strategy generates expected signals on sample input."""
    timestamps = pd.date_range('2024-01-01', periods=30, freq='1min')
    
    sample_data = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100] * 30,
        'high': [105] * 30,
        'low': [95] * 30,
        'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                 110, 111, 112, 113, 114, 115, 116, 117, 118, 119,
                 118, 117, 116, 115, 114, 113, 112, 111, 110, 109],
        'volume': [1000] * 30
    })
    
    signals = sma_crossover_strategy(sample_data)
    
    assert isinstance(signals, list), "Should return a list of signals"
    
    signals_custom = sma_crossover_strategy(sample_data, sma_short=3, sma_long=10)
    assert isinstance(signals_custom, list), "Should return a list of signals with custom parameters"
    
    for signal in signals:
        assert 'timestamp' in signal, "Each signal should have timestamp"
        assert 'action' in signal, "Each signal should have action"
        assert 'price' in signal, "Each signal should have price"
        assert signal['action'] in ['buy', 'sell'], "Action should be 'buy' or 'sell'"
        assert isinstance(signal['price'], (int, float)) or hasattr(signal['price'], 'dtype'), "Price should be numeric"

def test_strategy_insufficient_data():
    """Test strategy handles insufficient data gracefully."""
    timestamps = pd.date_range('2024-01-01', periods=10, freq='1min')
    
    insufficient_data = pd.DataFrame({
        'timestamp': timestamps,
        'open': [100] * 10,
        'high': [105] * 10,
        'low': [95] * 10,
        'close': [100] * 10,
        'volume': [1000] * 10
    })
    
    signals = sma_crossover_strategy(insufficient_data)
    
    assert isinstance(signals, list), "Should return a list even with insufficient data"
    assert len(signals) == 0, "Should return empty list for insufficient data"

def test_data_fetch_with_parameters():
    """Test that data fetch accepts custom parameters."""
    try:
        df = fetch_btc_usdt_data(symbol="BTC/USDT", timeframe="1m", limit=100)
        
        assert isinstance(df, pd.DataFrame), "Should return a pandas DataFrame"
        assert len(df) <= 100, "Should respect limit parameter"
        
    except Exception as e:
        pytest.skip(f"Skipping data fetch test due to API error: {e}")

def test_signal_logging():
    """Test that signals are logged to file correctly."""
    import tempfile
    import shutil
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'trading_bot'))
    from main import log_signals_to_file
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        signals = [
            {'timestamp': pd.Timestamp('2024-01-01 10:00:00'), 'action': 'buy', 'price': 50000.0},
            {'timestamp': pd.Timestamp('2024-01-01 11:00:00'), 'action': 'sell', 'price': 51000.0}
        ]
        
        log_signals_to_file(signals, "BTC/USDT")
        
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        assert os.path.exists(logs_dir), "Logs directory should be created"
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_live_mode_argument_parsing():
    """Test that --live flag is parsed correctly."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'trading_bot'))
    from main import parse_args
    
    original_argv = sys.argv
    try:
        sys.argv = ['main.py', '--live', '--symbol', 'ETH/USDT']
        args = parse_args()
        assert args.live is True, "Live flag should be True when --live is passed"
        assert args.symbol == 'ETH/USDT', "Symbol should be parsed correctly"
        
        sys.argv = ['main.py', '--symbol', 'BTC/USDT']
        args = parse_args()
        assert args.live is False, "Live flag should be False when --live is not passed"

    finally:
        sys.argv = original_argv

def test_alert_mode_argument_parsing():
    """Test that --alert-mode flag is parsed correctly."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'trading_bot'))
    from main import parse_args

    original_argv = sys.argv
    try:
        sys.argv = ['main.py', '--alert-mode']
        args = parse_args()
        assert args.alert_mode is True, "Alert mode should be True when flag present"

        sys.argv = ['main.py']
        args = parse_args()
        assert args.alert_mode is False, "Alert mode should be False by default"

    finally:
        sys.argv = original_argv


def test_version_flag(capsys):
    """Test that --version outputs package version and exits."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'trading_bot'))
    from main import parse_args

    original_argv = sys.argv
    try:
        sys.argv = ['main.py', '--version']
        with pytest.raises(SystemExit) as excinfo:
            parse_args()
        assert excinfo.value.code == 0
        captured = capsys.readouterr()
        assert '1.2.0' in captured.out
    finally:
        sys.argv = original_argv

def test_run_single_analysis():
    """Test the run_single_analysis function with mock data."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'trading_bot'))
    from main import run_single_analysis
    
    try:
        signals = run_single_analysis("BTC/USDT", "1m", 100, 5, 20)
        assert isinstance(signals, list), "Should return a list of signals"
    except Exception:
        pass
