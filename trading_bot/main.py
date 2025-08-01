import logging
import json
import argparse
import os
import time
import signal as sig
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version

# ? Absolute imports for package context
from trading_bot.backtester import run_backtest
from trading_bot.data_fetch import fetch_btc_usdt_data
from trading_bot.signal_logger import log_signals_to_db
from trading_bot.strategies import STRATEGY_REGISTRY, list_strategies

try:
    from plyer import notification
except Exception:
    notification = None

def load_config():
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
    parser = argparse.ArgumentParser(description='Crypto Trading Bot')
    try:
        pkg_version = version('trading-bot')
    except PackageNotFoundError:
        try:
            from trading_bot import __version__ as pkg_version
        except Exception:
            pkg_version = '0.0.0'

    parser.add_argument('--version', action='version', version=f'%(prog)s {pkg_version}')
    parser.add_argument('--symbol', type=str, help='Trading pair symbol (e.g., BTC/USDT)')
    parser.add_argument('--timeframe', type=str, help='Timeframe for candles (e.g., 1m, 5m)')
    parser.add_argument('--limit', type=int, help='Number of candles to fetch')
    parser.add_argument('--sma-short', type=int, help='Short-period SMA window')
    parser.add_argument('--sma-long', type=int, help='Long-period SMA window')
    parser.add_argument('--live', action='store_true', help='Enable live trading simulation mode')
    parser.add_argument('--strategy', type=str, default='sma', help='Trading strategy to use')
    parser.add_argument('--list-strategies', action='store_true', help='List available strategies and exit')
    parser.add_argument('--alert-mode', action='store_true', help='Enable alert notifications for BUY/SELL signals')
    parser.add_argument('--backtest', type=str, help='Path to CSV file for historical backtesting')
    parser.add_argument('--tune', action='store_true', help='Run parameter tuning over a range of values')
    parser.add_argument('--save-chart', action='store_true', help='Save equity curve CSV/JSON and chart during backtest')
    return parser.parse_args()

def log_signals_to_file(signals, symbol):
    if not signals:
        return
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(logs_dir, f"{timestamp}_signals.log")
    with open(log_path, 'w') as f:
        f.write(f"Trading Signals Log - {symbol}\n")
        f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n")
        for signal in signals:
            ts = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{ts} | {signal['action'].upper()} | {symbol} | ${signal['price']:.2f}\n")
    logging.info(f"Logged {len(signals)} signals to {log_path}")

def send_alert(signal):
    ts = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    message = f"ALERT: {signal['action'].upper()} at {ts} price ${signal['price']:.2f}"
    print(message)
    if notification:
        try:
            notification.notify(title="Trading Bot Alert", message=message)
        except Exception as e:
            logging.debug(f"Notification error: {e}")

def signal_handler(signum, frame):
    logging.info("Received interrupt signal. Shutting down live trading mode gracefully...")
    print("\n=== Live Trading Mode Shutdown ===")
    sys.exit(0)

def run_single_analysis(symbol, timeframe, limit, sma_short, sma_long, strategy="sma", alert_mode=False):
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
        elif strategy == "bollinger":
            signals = strategy_fn(data, window=sma_long, num_std=2)
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
    live_limit = 25
    sig.signal(sig.SIGINT, signal_handler)
    if strategy not in STRATEGY_REGISTRY:
        raise ValueError("Unknown strategy. Use --list-strategies to view options.")

    print(f"\n=== Live Trading Mode Started ===")
    print(f"Symbol: {symbol}")
    print(f"Strategy: {strategy.upper()}")
    print(f"Fetching {live_limit} candles every 60 seconds")
    print("Press Ctrl+C to stop gracefully")
    print("=" * 50)

    iteration = 0
    while True:
        iteration += 1
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iteration #{iteration}")
        signals = run_single_analysis(symbol, timeframe, live_limit, sma_short, sma_long, strategy=strategy, alert_mode=alert_mode)
        if signals:
            print(f"?? NEW SIGNALS ({len(signals)}):")
            for signal in signals[-3:]:
                ts = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                print(f"  {ts} - {signal['action'].upper()} at ${signal['price']:.2f}")
        else:
            print("No new signals.")
        print("Next analysis in 60 seconds...")
        time.sleep(60)

def main():
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
        raise ValueError("Unknown strategy. Use --list-strategies to view options.")

    try:
        if getattr(args, 'tune', False):
            if not args.backtest:
                raise ValueError("--backtest CSV path required for tuning")
            from trading_bot.tuner import tune
            results = tune(args.backtest, strategy=strategy_choice)
            print("=== Tuning Results ===")
            for res in results:
                params_str = ", ".join(f"{k}={v}" for k, v in res['params'].items())
                print(f"{params_str} -> PnL {res['net_pnl']:.2f}, Win "
                      f"{res['win_rate']:.2f}%")
            if results:
                print(f"Best parameters: {results[0]['params']}")
            return
        if args.backtest:
            base = os.path.splitext(args.backtest)[0]
            equity_out = base + '_equity_curve.csv' if args.save_chart else None
            stats_out = base + '_summary_stats.json' if args.save_chart else None
            chart_out = base + '_equity_chart.png' if args.save_chart else None
            run_backtest(args.backtest, strategy=strategy_choice,
                         sma_short=sma_short, sma_long=sma_long,
                         plot=bool(chart_out), equity_out=equity_out,
                         stats_out=stats_out, chart_out=chart_out)
        elif args.live:
            run_live_mode(symbol, timeframe, sma_short, sma_long, strategy=strategy_choice, alert_mode=alert_mode)
        else:
            signals = run_single_analysis(symbol, timeframe, limit, sma_short, sma_long, strategy=strategy_choice, alert_mode=alert_mode)
            print(f"\n=== Trading Bot Results for {symbol} ===")
            print(f"Strategy: {strategy_choice.upper()}")
            print(f"Total signals: {len(signals)}")
            if signals:
                print("\nLast 5 signals:")
                for i, s in enumerate(signals[-5:], 1):
                    ts = s['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{i}. {ts} - {s['action'].upper()} @ ${s['price']:.2f}")
            else:
                print("No trading signals generated.")
    except Exception as e:
        logging.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main()
