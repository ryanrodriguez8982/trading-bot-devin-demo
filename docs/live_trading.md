# Live Trading Guide & Safety Checklist

This guide helps you move from paper trading to small real trades safely.

## 1. Configure Environment Variables
Set your exchange API keys so the bot can authenticate. You can copy
`.env.example` to `.env` and fill in your credentials:

```bash
export TRADING_BOT_API_KEY="your_api_key"
export TRADING_BOT_API_SECRET="your_api_secret"
export TRADING_BOT_API_PASSPHRASE="your_api_passphrase" # if required
export TRADING_BOT_EXCHANGE="coinbase" # default exchange
```
Keep these secrets secure and never commit them to source control. When set, they automatically override any values stored in config files.

## 2. Start with a Dry Run
Run the bot in live mode **without** enabling real trades to verify behaviour and logging:

```bash
trading-bot live --symbol BTC/USDT
```
Confirm that orders are not executed and outputs look correct.

## 3. Understand Fees and Minimum Lot Sizes
Check your exchange for trading fees and minimum order quantities. Configure the bot accordingly using `--fee-bps` and `--trade-size` so orders satisfy exchange rules.

## 4. Execute a Tiny Real Trade
When confident, place the smallest possible trade to ensure everything works end to end:

```bash
TRADING_BOT_API_KEY=your_api_key TRADING_BOT_API_SECRET=your_api_secret \
trading-bot live --live-trade --symbol BTC/USDT --trade-size 0.001
```
Monitor the trade result and logs closely.

## 5. Error Handling
The live trading loop logs unexpected errors with traceback and retries, so transient failures won't halt the bot. Review the logs to diagnose any recurring issues.

## 6. Have a Rollback Plan
Be prepared to disable API keys or stop the bot immediately if unexpected behaviour occurs. Keep a manual record of changes and trades so you can revert settings or positions quickly.

## 7. Monitor with Metrics and Health Checks
Expose Prometheus metrics and a simple health endpoint to track the bot during live runs:

```bash
trading-bot live --metrics-port 8000 --health-port 8001
```

The metrics endpoint reports counters for generated signals, executed trades, errors and realised P&L, while `/health` returns `ok` for quick liveness probes.

## 8. Enable Additional Risk Controls

The bot supports extra guardrails to keep risk in check during live runs. You
can limit the number of trades per day, cap the portion of equity used for any
single trade and restrict trading to a specific window of hours. Example:

```bash
trading-bot --live --max-trades-per-day 5 --max-position-pct 0.1 --trading-window 9-17
```

These safeguards complement stop-loss and take-profit rules by preventing
over-trading in unfavourable conditions.

To automatically attach protective exits to each trade, configure
`stop_loss_pct` and `take_profit_pct` in `config.json`.
For example:

```json
"stop_loss_pct": 0.02,
"take_profit_pct": 0.05
```

This will sell a position if price falls 2% below entry or rises 5% above it.

To automatically limit exposure in both backtests and live trading, set
`max_position_pct` in your `config.json`. For example, adding

```json
"max_position_pct": 0.2
```

ensures no more than 20% of portfolio equity is allocated to a single asset.

Following this checklist helps reduce risk as you transition from simulation to real markets.

