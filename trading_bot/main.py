import logging
import json
import argparse
import os
import time
import signal as sig
import sys
from datetime import datetime

from importlib.metadata import PackageNotFoundError, version
try:
    from .backtester import run_backtest
except ImportError:  # when running as script without package context
    from backtester import run_backtest

try:
    from plyer import notification
except Exception:
    notification = None
try:
    from .data_fetch import fetch_btc_usdt_data
    from .signal_logger import log_signals_to_db
    from ..strategies import STRATEGY_REGISTRY, list_strategies
except ImportError:
    from data_fetch import fetch_btc_usdt_data
    from signal_logger import log_signals_to_db
    from strategies import STRATEGY_REGISTRY, list_strategies

def load_config():
    """Load configuration from config.json file."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning("config.json not found, using default values")
        return {
            "symbol": "BTC/USDT",
            "timeframe": "1m",
            "limit": 500,
            "sma_short": 5,
            "sma_long": 20
        }

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Crypto Trading Bot')
    try:
        pkg_version = version('trading-bot')
    except PackageNotFoundError:
        try:
            from trading_bot import __version__ as pkg_version
        except Exception:
            pkg_version = '0.0.0'

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {pkg_version}'
    )
    parser.add_argument('--symbol', type=str, help='Trading pair symbol (e.g., BTC/USDT)')
    parser.add_argument('--timeframe', type=str, help='Timeframe for candles (e.g., 1m, 5m)')
    parser.add_argument('--limit', type=int, help='Number of candles to fetch')
    parser.add_argument('--sma-short', type=int, help='Short-period SMA window')
    parser.add_argument('--sma-long', type=int, help='Long-period SMA window')
    parser.add_argument('--live', action='store_true', help='Enable live trading simulation mode')
    parser.add_argument('--strategy', type=str, default='sma',
                        help='Trading strategy to use')
    parser.add_argument('--list-strategies', action='store_true',
                        help='List available strategies and exit')
    parser.add_argument('--alert-mode', action='store_true',
                        help='Enable alert notifications for BUY/SELL signals')
    parser.add_argument('--backtest', type=str,
                        help='Path to CSV file for historical backtesting')
    parser.add_argument('--save-chart', action='store_true',
                        help='Save equity curve CSV/JSON and chart during backtest')
    return parser.parse_args()

def log_signals_to_file(signals, symbol):
    """
    Log trading signals to a timestamped file in logs/ directory.
    
    Args:
        signals (list): List of trading signals with timestamp, action, price
        symbol (str): Trading pair symbol
    """
    if not signals:
        return
    
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"{timestamp}_signals.log"
    log_path = os.path.join(logs_dir, log_filename)
    
    with open(log_path, 'w') as f:
        f.write(f"Trading Signals Log - {symbol}\n")
        f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n")
        
        for signal in signals:
            timestamp_str = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            action = signal['action'].upper()
            price = signal['price']
            f.write(f"{timestamp_str} | {action} | {symbol} | ${price:.2f}\n")
    
    logging.info(f"Logged {len(signals)} signals to {log_path}")

def send_alert(signal):
    """Send an alert for a trading signal."""
    timestamp_str = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    action = signal['action'].upper()
    price = signal['price']
    message = f"ALERT: {action} signal at {timestamp_str} price ${price:.2f}"
    print(message)
    if notification:
        try:
            notification.notify(title="Trading Bot Alert", message=message)
        except Exception as e:
            logging.debug(f"Notification error: {e}")

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    logging.info("Received interrupt signal. Shutting down live trading mode gracefully...")
    print("\n=== Live Trading Mode Shutdown ===")
    print("Gracefully shutting down. Thank you for using the trading bot!")
    sys.exit(0)

def run_single_analysis(symbol, timeframe, limit, sma_short, sma_long, strategy="sma", alert_mode=False):
    """Run a single analysis cycle and return signals."""
    try:
        if strategy not in STRATEGY_REGISTRY:
            raise ValueError("Unknown strategy. Use --list-strategies to view options.")

        data = fetch_btc_usdt_data(symbol, timeframe, limit)
        logging.info(f"Fetched {len(data)} data points")

        strategy_fn = STRATEGY_REGISTRY[strategy]
        if strategy == "rsi":
            signals = strategy_fn(data, period=14)
        elif strategy == "macd":
            signals = strategy_fn(data)
        else:
            signals = strategy_fn(data, sma_short, sma_long)
        logging.info(f"Generated {len(signals)} trading signals")
        
        if signals:
            log_signals_to_file(signals, symbol)
            log_signals_to_db(signals, symbol)
            if alert_mode:
                for s in signals:
                    send_alert(s)
        
        return signals
    except Exception as e:
        logging.error(f"Error in analysis cycle: {e}")
        return []

def run_live_mode(symbol, timeframe, sma_short, sma_long, strategy="sma", alert_mode=False):
    """Run the bot in live trading simulation mode."""
    live_limit = 25
    
    sig.signal(sig.SIGINT, signal_handler)
    
    if strategy not in STRATEGY_REGISTRY:
        raise ValueError("Unknown strategy. Use --list-strategies to view options.")

    print(f"\n=== Live Trading Mode Started ===")
    print(f"Symbol: {symbol}")
    if strategy == "rsi":
        print("Strategy: RSI crossover")
    elif strategy == "macd":
        print("Strategy: MACD crossover")
    else:
        print(f"Strategy: SMA({sma_short}) vs SMA({sma_long}) crossover")
    print(f"Fetching {live_limit} candles every 60 seconds")
    print("Press Ctrl+C to stop gracefully")
    print("=" * 50)
    
    iteration = 0
    
    while True:
        iteration += 1
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n[{current_time}] Iteration #{iteration}")
        logging.info(f"Starting live analysis iteration #{iteration}")
        
        signals = run_single_analysis(symbol, timeframe, live_limit, sma_short, sma_long, strategy=strategy, alert_mode=alert_mode)
        
        if signals:
            print(f"🚨 NEW SIGNALS DETECTED ({len(signals)} signals):")
            for signal in signals[-3:]:
                timestamp = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                action = signal['action'].upper()
                price = signal['price']
                print(f"  {timestamp} - {action} at ${price:.2f}")
        else:
            print("No new signals generated")
        
        print(f"Next analysis in 60 seconds...")
        time.sleep(60)

def main():
    """
    Main function to orchestrate the trading bot.
    Supports both one-time analysis and live trading simulation mode.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    config = load_config()
    args = parse_args()
    
    symbol = args.symbol or config['symbol']
    timeframe = args.timeframe or config['timeframe']
    limit = args.limit or config['limit']
    sma_short = getattr(args, 'sma_short') or config['sma_short']
    sma_long = getattr(args, 'sma_long') or config['sma_long']
    strategy_choice = getattr(args, 'strategy', 'sma')
    alert_mode = getattr(args, 'alert_mode', False)

    if getattr(args, 'list_strategies', False):
        print("Available strategies:")
        for name in list_strategies():
            print(f"- {name}")
        return

    if strategy_choice not in STRATEGY_REGISTRY:
        raise ValueError(
            "Unknown strategy. Use --list-strategies to view options.")

    strategy_fn = STRATEGY_REGISTRY[strategy_choice]

    try:
        if args.backtest:
            logging.info(
                f"Starting backtest using {args.backtest} with strategy={strategy_choice}")
            base = os.path.splitext(args.backtest)[0]
            equity_out = None
            stats_out = None
            chart_out = None
            if getattr(args, 'save_chart', False):
                equity_out = base + '_equity_curve.csv'
                stats_out = base + '_summary_stats.json'
                chart_out = base + '_equity_chart.png'

            run_backtest(args.backtest, strategy=strategy_choice,
                        sma_short=sma_short, sma_long=sma_long, plot=bool(chart_out),
                        equity_out=equity_out, stats_out=stats_out, chart_out=chart_out)
        elif args.live:
            logging.info(
                f"Starting live trading mode with {symbol}, {timeframe}, strategy={strategy_choice}" )
            run_live_mode(symbol, timeframe, sma_short, sma_long, strategy=strategy_choice, alert_mode=alert_mode)
        else:
            logging.info(
                f"Starting trading bot with {symbol}, {timeframe}, limit={limit}, strategy={strategy_choice}")

            signals = run_single_analysis(symbol, timeframe, limit, sma_short, sma_long, strategy=strategy_choice, alert_mode=alert_mode)
            
            print(f"\n=== Trading Bot Results for {symbol} ===")
            if strategy_choice == "rsi":
                print("Strategy: RSI crossover")
            elif strategy_choice == "macd":
                print("Strategy: MACD crossover")
            else:
                print(f"Strategy: SMA({sma_short}) vs SMA({sma_long}) crossover")
            print(f"Total signals generated: {len(signals)}")
            
            if signals:
                print("\nLast 5 recommended actions:")
                last_5_signals = signals[-5:]
                for i, signal in enumerate(last_5_signals, 1):
                    timestamp = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    action = signal['action'].upper()
                    print(f"{i}. {timestamp} - {action}")
            else:
                print("No trading signals generated with current data.")
                
    except Exception as e:
        logging.error(f"Error in main execution: {e}")
        raise

if __name__ == "__main__":
    main()

