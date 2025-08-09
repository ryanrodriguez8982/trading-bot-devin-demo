import ccxt
import logging
from typing import Optional

from trading_bot.utils.retry import RetryPolicy, default_retry


def create_exchange(api_key=None, api_secret=None, api_passphrase=None, exchange_name="binance"):
    """Create a CCXT exchange instance with optional credentials.

    The function signature places credential arguments first so callers may
    provide only API keys without specifying the exchange name. This aligns
    with tests that call ``create_exchange('key', 'secret', 'pass')`` and
    expect the default exchange (binance) to be used.
    """
    try:
        params = {}
        if api_key and api_secret:
            params.update({"apiKey": api_key, "secret": api_secret})
            if api_passphrase:
                params["password"] = api_passphrase

        # Dynamically get the exchange class by name
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class(params)
        return exchange

    except Exception as e:
        logging.error(f"Failed to initialize exchange '{exchange_name}': {e}")
        raise

def execute_trade(
    exchange,
    symbol,
    action,
    amount,
    retry_policy: Optional[RetryPolicy] = None,
):
    """Execute a market order and return the order info."""
    side = 'buy' if action.lower() == 'buy' else 'sell'
    policy = retry_policy or default_retry()
    try:
        order = policy.call(exchange.create_market_order, symbol, side, amount)
        logging.info(
            f"Executed {side} order for {amount} {symbol}: id={order.get('id')}")
        return order
    except Exception as e:
        logging.error(f"Order execution failed: {e}")
        return None

