import logging
import json
import argparse
import os
from datetime import datetime
from data_fetch import fetch_btc_usdt_data
from strategy import sma_crossover_strategy

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
    parser.add_argument('--symbol', type=str, help='Trading pair symbol (e.g., BTC/USDT)')
    parser.add_argument('--timeframe', type=str, help='Timeframe for candles (e.g., 1m, 5m)')
    parser.add_argument('--limit', type=int, help='Number of candles to fetch')
    parser.add_argument('--sma-short', type=int, help='Short-period SMA window')
    parser.add_argument('--sma-long', type=int, help='Long-period SMA window')
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

def main():
    """
    Main function to orchestrate the trading bot.
    Fetches data, applies strategy, and prints last 5 recommended actions.
    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    config = load_config()
    args = parse_args()
    
    symbol = args.symbol or config['symbol']
    timeframe = args.timeframe or config['timeframe']
    limit = args.limit or config['limit']
    sma_short = getattr(args, 'sma_short') or config['sma_short']
    sma_long = getattr(args, 'sma_long') or config['sma_long']
    
    try:
        logging.info(f"Starting trading bot with {symbol}, {timeframe}, limit={limit}, SMA({sma_short},{sma_long})")
        
        data = fetch_btc_usdt_data(symbol, timeframe, limit)
        logging.info(f"Fetched {len(data)} data points")
        
        signals = sma_crossover_strategy(data, sma_short, sma_long)
        logging.info(f"Generated {len(signals)} trading signals")
        
        log_signals_to_file(signals, symbol)
        
        print(f"\n=== Trading Bot Results for {symbol} ===")
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

