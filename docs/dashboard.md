# Streamlit Dashboard Guide

The dashboard visualizes price data and trading signals stored in `signals.db`.

## Running the Dashboard

```bash
streamlit run dashboard.py
```

Run this from the project root. Start the trading bot first so signals appear in the interface.

## Features

- Interactive charts with SMA, RSI, MACD and Bollinger Bands overlays
- Filterable signal table
- Equity curve tracking
- Strategy and symbol filters for quick comparisons

## Stopping

Use `Ctrl+C` in the terminal running Streamlit to stop the dashboard.
