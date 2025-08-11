# Adding a New Strategy

The bot loads strategies from the `trading_bot/strategies` package.

## Steps

1. **Create the module**
   - Add a new Python file under `trading_bot/strategies/` named `<key>_strategy.py`.
   - Implement a function named `<key>_strategy` that accepts price data and returns buy/sell signals.
2. **Register the strategy**
   - Import your function in `trading_bot/strategies/__init__.py`.
   - Add it to `STRATEGY_REGISTRY` with a matching short key (`<key>`).
3. **Use the strategy**
   - Invoke the bot with `--strategy your_key` or set `"strategy": "your_key"` in `config.json`.
4. **Test**
   - Run `pytest` and try a backtest to confirm the strategy behaves as expected.

Following these steps makes the strategy available to both the CLI and the dashboard.
