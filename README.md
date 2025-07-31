# Devin Trading Bot Demo

A test repo for Cognition AI's Devin agent to implement a basic crypto trading bot.

## Goal
Create a trading bot using `ccxt` that:
- Fetches historical data
- Applies a moving average crossover strategy
- Executes buy/sell logic
- Logs results and generates reports

## Installation

### Option 1: Pip Installation (Recommended)

Install the trading bot as a CLI tool:

```bash
# Standard installation
pip install .

# Development installation (editable)
pip install -e .
```

After installation, you can use the `trading-bot` command from anywhere:

```bash
# Basic usage
trading-bot --symbol BTC/USDT

# With custom parameters
trading-bot --symbol ETH/USDT --timeframe 5m --sma-short 10 --sma-long 30

# Live trading mode
trading-bot --live --symbol BTC/USDT

# Check version
trading-bot --version

# View help
trading-bot --help
```

### Option 2: Direct Python Execution

For development or if you prefer not to install:

```bash
# Install dependencies
pip install -r requirements.txt

# Run directly
python trading_bot/main.py --symbol BTC/USDT
```

## Usage

### Running the Trading Bot

#### Using the CLI tool (after pip installation):
```bash
# Basic usage (uses config.json defaults)
trading-bot

# Change trading pair and timeframe
trading-bot --symbol ETH/USDT --timeframe 5m

# Customize SMA periods
trading-bot --sma-short 10 --sma-long 50

# Fetch more data points
trading-bot --limit 1000

# Combine multiple parameters
trading-bot --symbol ETH/USDT --timeframe 5m --sma-short 10 --sma-long 30
```

#### Live Trading Simulation Mode:
```bash
# Run in live mode (fetches latest data every 60 seconds)
trading-bot --live

# Live mode with custom parameters
trading-bot --live --symbol ETH/USDT --sma-short 10 --sma-long 30

# Stop live mode gracefully with Ctrl+C
```

#### Alternative: Direct Python execution:
```bash
# Basic usage (uses config.json defaults)
python trading_bot/main.py

# With CLI arguments
python trading_bot/main.py --symbol ETH/USDT --timeframe 5m
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

The bot implements several trading strategies:

- **SMA Crossover**: Buy when the short-period SMA crosses above the long period SMA and sell on the opposite cross.
- **RSI Crossover**: Buy when the RSI rises above the oversold threshold and sell when it falls below the overbought threshold.
- **MACD Crossover**: Buy when the MACD line crosses above its signal line and sell when it crosses below.
- **Bollinger Bands**: Buy when price crosses above the lower band (oversold) and sell when price crosses below the upper band (overbought).

Use the `--strategy` flag with `sma`, `rsi`, `macd`, or `bollinger` to choose a strategy.The bot fetches historical candles from Binance and displays the last 5 trading recommendations.

## Live Trading Simulation Mode

The bot supports a live trading simulation mode that continuously monitors the market:

### Features
- **Real-time Analysis**: Fetches the latest 25 candles every 60 seconds
- **Continuous Monitoring**: Applies SMA crossover strategy in each iteration
- **Live Logging**: Signals are logged to both files and database as they occur
- **Graceful Shutdown**: Press Ctrl+C to stop with proper cleanup

### Usage
```bash
# Start live mode with default settings (CLI tool)
trading-bot --live

# Live mode with custom parameters (CLI tool)
trading-bot --live --symbol ETH/USDT --sma-short 10 --sma-long 30

# Alternative: Direct Python execution
python trading_bot/main.py --live
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

## Historical Backtesting

Run a simulation on CSV price data to evaluate strategy performance:

```bash
trading-bot --backtest path/to/data.csv --strategy sma
```

The backtester outputs metrics like net PnL, win rate, and max drawdown. Use `--list-strategies` to see all supported strategies.

## Dashboard

The project includes a Streamlit dashboard for visualizing trading signals and price data.

### Running the Dashboard
```bash
streamlit run dashboard.py
```

### Dashboard Features
- **Interactive Price Charts**: View price data with SMA overlays and signal markers
- **Signal Table**: Browse recent trading signals with filtering options
- **Real-time Filters**: Filter by symbol, strategy, and number of signals
- **SMA Configuration**: Adjust SMA periods to see different crossover patterns

The dashboard loads signals from the `signals.db` database and displays:
- Price charts with configurable SMA crossover visualization
- Buy/sell signal markers overlaid on price data
- Filterable table showing timestamp, action, price, symbol, and strategy
- Signal statistics and metrics

**Note**: Run the trading bot first to generate signals that will appear in the dashboard.
