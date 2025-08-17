# Strategy Simulation Matrix Report

**Generated:** 2025-08-17 01:08:31 UTC

## Environment & Data Ranges

- **Symbol:** BTC/USDT
- **Exchange:** coinbase
- **Timeframes:** 5m, 1h
- **Data Ranges:**
  - 5m: Last 60 days (~17280 candles)
  - 1h: Last 180 days (~4320 candles)
- **Position Sizes:** 2%, 5%, 10%
- **Trading Fees:** 0.1% per trade
- **Initial Capital:** $10,000

## Results Summary

Results sorted by Net PnL (descending), then Max Drawdown (ascending):

| Strategy | Timeframe | Position Size | Net PnL | Win Rate | Max Drawdown | Total Trades | Avg Trade PnL |
|----------|-----------|---------------|---------|----------|--------------|--------------|---------------|
| rsi | 1h | 10% | $145.05 | 100.0% | 0.29% | 0 | $0.00 |
| rsi | 1h | 5% | $72.53 | 100.0% | 0.15% | 0 | $0.00 |
| rsi | 1h | 2% | $29.01 | 100.0% | 0.06% | 0 | $0.00 |
| macd | 1h | 10% | $3.45 | 54.5% | 0.34% | 0 | $0.00 |
| macd | 1h | 5% | $1.73 | 54.5% | 0.17% | 0 | $0.00 |
| macd | 1h | 2% | $0.69 | 54.5% | 0.07% | 0 | $0.00 |
| rsi | 5m | 2% | $-0.79 | 100.0% | 0.01% | 0 | $0.00 |
| rsi | 5m | 5% | $-1.97 | 100.0% | 0.03% | 0 | $0.00 |
| sma | 1h | 2% | $-3.10 | 40.0% | 0.08% | 0 | $0.00 |
| rsi | 5m | 10% | $-3.94 | 100.0% | 0.06% | 0 | $0.00 |
| macd | 5m | 2% | $-4.15 | 33.3% | 0.04% | 0 | $0.00 |
| sma | 5m | 2% | $-4.42 | 12.5% | 0.04% | 0 | $0.00 |
| sma | 1h | 5% | $-7.74 | 40.0% | 0.19% | 0 | $0.00 |
| macd | 5m | 5% | $-10.38 | 33.3% | 0.11% | 0 | $0.00 |
| sma | 5m | 5% | $-11.05 | 12.5% | 0.11% | 0 | $0.00 |
| sma | 1h | 10% | $-15.48 | 40.0% | 0.38% | 0 | $0.00 |
| macd | 5m | 10% | $-20.76 | 33.3% | 0.22% | 0 | $0.00 |
| sma | 5m | 10% | $-22.11 | 12.5% | 0.22% | 0 | $0.00 |

## Top Configurations

### 1. RSI - 1h - 10%
- **Net PnL:** $145.05
- **Win Rate:** 100.0%
- **Max Drawdown:** 0.29%
- **Total Trades:** 0
- **Equity Curve:** ![rsi_1h_10pct](/home/ubuntu/repos/trading-bot-devin-demo/artifacts/simulations/equity_curves/rsi_1h_10pct.png)

### 2. RSI - 1h - 5%
- **Net PnL:** $72.53
- **Win Rate:** 100.0%
- **Max Drawdown:** 0.15%
- **Total Trades:** 0
- **Equity Curve:** ![rsi_1h_5pct](/home/ubuntu/repos/trading-bot-devin-demo/artifacts/simulations/equity_curves/rsi_1h_5pct.png)

### 3. RSI - 1h - 2%
- **Net PnL:** $29.01
- **Win Rate:** 100.0%
- **Max Drawdown:** 0.06%
- **Total Trades:** 0
- **Equity Curve:** ![rsi_1h_2pct](/home/ubuntu/repos/trading-bot-devin-demo/artifacts/simulations/equity_curves/rsi_1h_2pct.png)

### Worst Configuration: SMA - 5m - 10%
- **Net PnL:** $-22.11
- **Win Rate:** 12.5%
- **Max Drawdown:** 0.22%
- **Total Trades:** 0

## Caveats & Limitations

- Trading fees modeled at 0.1% per trade
- Spot-only trading, no leverage
- No slippage modeling beyond fees
- Historical data may not reflect future performance
- Position sizing based on fixed percentage of initial capital

## Reproducibility Information

- **Repository:** ryanrodriguez8982/trading-bot-devin-demo
- **Branch:** feature/sim-matrix-report
- **Commands Used:**
  ```bash
  python scripts/simulate_matrix.py
  ```
- **Total Simulation Runs:** 18
- **Strategies Tested:** sma, rsi, macd
- **Data Source:** coinbase exchange via CCXT
