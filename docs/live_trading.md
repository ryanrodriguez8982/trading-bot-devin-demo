# Live Trading Guide & Safety Checklist

This guide helps you move from paper trading to small real trades safely.

## 1. Configure Environment Variables
Set your exchange API keys so the bot can authenticate:

```bash
export TRADING_BOT_API_KEY="your_api_key"
export TRADING_BOT_API_SECRET="your_api_secret"
export TRADING_BOT_API_PASSPHRASE="your_api_passphrase" # if required
```
Keep these secrets secure and never commit them to source control. When set, they automatically override any values stored in config files.

## 2. Start with a Dry Run
Run the bot in live mode **without** enabling real trades to verify behaviour and logging:

```bash
trading-bot --live --symbol BTC/USDT
```
Confirm that orders are not executed and outputs look correct.

## 3. Understand Fees and Minimum Lot Sizes
Check your exchange for trading fees and minimum order quantities. Configure the bot accordingly using `--fee-bps` and `--trade-size` so orders satisfy exchange rules.

## 4. Execute a Tiny Real Trade
When confident, place the smallest possible trade to ensure everything works end to end:

```bash
TRADING_BOT_API_KEY=your_api_key TRADING_BOT_API_SECRET=your_api_secret \
trading-bot --live --live-trade --symbol BTC/USDT --trade-size 0.001
```
Monitor the trade result and logs closely.

## 5. Have a Rollback Plan
Be prepared to disable API keys or stop the bot immediately if unexpected behaviour occurs. Keep a manual record of changes and trades so you can revert settings or positions quickly.

Following this checklist helps reduce risk as you transition from simulation to real markets.

