# Devin Trading Bot Demo

A test repo for Cognition AI's Devin agent to implement a basic crypto trading bot.

## Goal
Create a trading bot using `ccxt` that:
- Fetches historical data
- Applies a moving average crossover strategy
- Executes buy/sell logic
- Logs results and generates reports

## Usage

### Installation
```bash
pip install -r requirements.txt
```

### Running the Trading Bot

#### Basic usage (uses config.json defaults):
```bash
python trading_bot/main.py
```

#### With CLI arguments (overrides config.json):
```bash
# Change trading pair and timeframe
python trading_bot/main.py --symbol ETH/USDT --timeframe 5m

# Customize SMA periods
python trading_bot/main.py --sma-short 10 --sma-long 50

# Fetch more data points
python trading_bot/main.py --limit 1000

# Combine multiple parameters
python trading_bot/main.py --symbol ETH/USDT --timeframe 5m --sma-short 10 --sma-long 30
```

### Running Tests
```bash
pytest tests/
```

## Logging

The bot automatically logs all trading signals to timestamped files in the `logs/` directory:

- **Log Location**: `logs/{timestamp}_signals.log`
- **Log Format**: Each line contains timestamp, action, symbol, and price
- **Example**: `2024-01-01 10:30:00 | BUY | BTC/USDT | $50000.00`

The logs directory is created automatically if it doesn't exist. Each bot run generates a new log file with a timestamp in the filename format `YYYYMMDD_HHMMSS_signals.log`.

### Log File Example
```
Trading Signals Log - BTC/USDT
Generated at: 2024-01-01 10:30:00
==================================================
2024-01-01 10:15:00 | BUY | BTC/USDT | $49500.00
2024-01-01 10:25:00 | SELL | BTC/USDT | $50200.00
```

## Configuration

The bot uses a `config.json` file for default parameters:
```json
{
    "symbol": "BTC/USDT",
    "timeframe": "1m",
    "limit": 500,
    "sma_short": 5,
    "sma_long": 20
}
```

CLI arguments override config file values. Available parameters:
- `--symbol`: Trading pair (e.g., BTC/USDT, ETH/USDT)
- `--timeframe`: Candle timeframe (e.g., 1m, 5m, 1h)
- `--limit`: Number of candles to fetch
- `--sma-short`: Short-period SMA window
- `--sma-long`: Long-period SMA window

## Strategy
The bot implements a simple moving average (SMA) crossover strategy:
- **Buy Signal**: When the short-period SMA crosses above the long-period SMA
- **Sell Signal**: When the short-period SMA crosses below the long-period SMA

The bot fetches historical candles from Binance and displays the last 5 trading recommendations.
