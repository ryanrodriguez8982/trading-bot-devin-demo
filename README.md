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

#### Live Trading Simulation Mode:
```bash
# Run in live mode (fetches latest data every 60 seconds)
python trading_bot/main.py --live

# Live mode with custom parameters
python trading_bot/main.py --live --symbol ETH/USDT --sma-short 10 --sma-long 30

# Stop live mode gracefully with Ctrl+C
```

### Running Tests
```bash
pytest tests/
```

## Logging

The bot automatically logs all trading signals to both files and a SQLite database:

### File Logging
- **Log Location**: `logs/{timestamp}_signals.log`
- **Log Format**: Each line contains timestamp, action, symbol, and price
- **Example**: `2024-01-01 10:30:00 | BUY | BTC/USDT | $50000.00`

The logs directory is created automatically if it doesn't exist. Each bot run generates a new log file with a timestamp in the filename format `YYYYMMDD_HHMMSS_signals.log`.

#### Log File Example
```
Trading Signals Log - BTC/USDT
Generated at: 2024-01-01 10:30:00
==================================================
2024-01-01 10:15:00 | BUY | BTC/USDT | $49500.00
2024-01-01 10:25:00 | SELL | BTC/USDT | $50200.00
```

### Database Logging
- **Database Location**: `signals.db` (SQLite database in project root)
- **Table Schema**: `signals(timestamp TEXT, action TEXT, price REAL, symbol TEXT, strategy_id TEXT)`
- **Strategy ID**: Defaults to 'sma' for the SMA crossover strategy

The database is created automatically if it doesn't exist. All signals are stored persistently and can be queried for analysis and visualization.

#### Database Schema
```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    action TEXT NOT NULL,
    price REAL NOT NULL,
    symbol TEXT NOT NULL,
    strategy_id TEXT NOT NULL
);
```

#### Example Database Query
```python
from trading_bot.signal_logger import get_signals_from_db

# Get last 10 BTC/USDT signals
signals = get_signals_from_db(symbol="BTC/USDT", limit=10)

# Get all signals for a specific strategy
sma_signals = get_signals_from_db(strategy_id="sma")
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
- `--limit`: Number of candles to fetch (ignored in live mode)
- `--sma-short`: Short-period SMA window
- `--sma-long`: Long-period SMA window
- `--live`: Enable live trading simulation mode

## Strategy
The bot implements a simple moving average (SMA) crossover strategy:
- **Buy Signal**: When the short-period SMA crosses above the long-period SMA
- **Sell Signal**: When the short-period SMA crosses below the long-period SMA

The bot fetches historical candles from Binance and displays the last 5 trading recommendations.

## Live Trading Simulation Mode

The bot supports a live trading simulation mode that continuously monitors the market:

### Features
- **Real-time Analysis**: Fetches the latest 25 candles every 60 seconds
- **Continuous Monitoring**: Applies SMA crossover strategy in each iteration
- **Live Logging**: Signals are logged to both files and database as they occur
- **Graceful Shutdown**: Press Ctrl+C to stop with proper cleanup

### Usage
```bash
# Start live mode with default settings
python trading_bot/main.py --live

# Live mode with custom parameters
python trading_bot/main.py --live --symbol ETH/USDT --sma-short 10 --sma-long 30
```

### Live Mode Output
```
=== Live Trading Mode Started ===
Symbol: BTC/USDT
Strategy: SMA(5) vs SMA(20) crossover
Fetching 25 candles every 60 seconds
Press Ctrl+C to stop gracefully
==================================================

[2024-01-01 10:30:00] Iteration #1
🚨 NEW SIGNALS DETECTED (2 signals):
  2024-01-01 10:25:00 - BUY at $50000.00
  2024-01-01 10:29:00 - SELL at $50200.00
Next analysis in 60 seconds...
```

### Stopping Live Mode
Press `Ctrl+C` at any time to gracefully shutdown:
```
^C=== Live Trading Mode Shutdown ===
Gracefully shutting down. Thank you for using the trading bot!
```
