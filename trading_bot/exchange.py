import ccxt
import logging

def create_exchange(exchange_name="binance", api_key=None, api_secret=None, api_passphrase=None):
    """Create a CCXT exchange instance with optional credentials."""
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


def execute_trade(exchange, symbol, action, amount):
    """Execute a market order and return the order info."""
    side = 'buy' if action.lower() == 'buy' else 'sell'
    try:
        order = exchange.create_market_order(symbol, side, amount)
        logging.info(
            f"Executed {side} order for {amount} {symbol}: id={order.get('id')}")
        return order
    except Exception as e:
        logging.error(f"Order execution failed: {e}")
        return None

