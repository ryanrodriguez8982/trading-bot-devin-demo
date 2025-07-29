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
```bash
python trading_bot/main.py
```

### Running Tests
```bash
pytest tests/
```

## Strategy
The bot implements a simple moving average (SMA) crossover strategy:
- **Buy Signal**: When the 5-period SMA crosses above the 20-period SMA
- **Sell Signal**: When the 5-period SMA crosses below the 20-period SMA

The bot fetches 500 1-minute candles of BTC/USDT data from Binance and displays the last 5 trading recommendations.
