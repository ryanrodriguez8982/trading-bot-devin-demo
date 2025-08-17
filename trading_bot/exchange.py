import ccxt
import logging
from typing import Any, Optional

from ccxt.base.exchange import Exchange
from trading_bot.utils.retry import RetryPolicy, default_retry


logger = logging.getLogger(__name__)


def create_exchange(
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    api_passphrase: Optional[str] = None,
    exchange_name: str = "binance",
) -> Exchange:
    """Create a CCXT exchange instance with optional credentials.

    Parameters
    ----------
    api_key, api_secret, api_passphrase : str, optional
        API credentials for the exchange.
    exchange_name : str, default ``"binance"``
        Name of the exchange to instantiate.
    """
    try:
        params: dict[str, str] = {}
        if api_key and api_secret:
            params.update({"apiKey": api_key, "secret": api_secret})
            if api_passphrase:
                params["password"] = api_passphrase

        exchange_class = getattr(ccxt, exchange_name)
        return exchange_class(params)

    except (AttributeError, ccxt.BaseError) as e:
        logger.error(
            "Failed to initialize exchange '%s': %s",
            exchange_name,
            e,
        )
        raise


def execute_trade(
    exchange: Exchange,
    symbol: str,
    action: str,
    amount: float,
    retry_policy: Optional[RetryPolicy] = None,
) -> Optional[dict[str, Any]]:
    """Execute a market order and return the order info.

    Before submitting the order, check that sufficient balance is available
    for the trade. For buys this means the quote currency covers the
    expected cost (plus fees). For sells the base asset quantity must be
    available. If balances are insufficient the trade is skipped and
    ``None`` is returned.
    """
    side = "buy" if action.lower() == "buy" else "sell"
    policy = retry_policy or default_retry()
    try:
        balances = policy.call(exchange.fetch_balance)
        free = balances.get("free", {})
        base, quote = symbol.split("/")
        if side == "buy":
            ticker = policy.call(exchange.fetch_ticker, symbol)
            price = ticker.get("last") or ticker.get("ask") or ticker.get("close")
            if price is None:
                logger.error("No price available for %s", symbol)
                return None
            fee_rate = (
                getattr(exchange, "fees", {})
                .get("trading", {})
                .get("taker", 0.0)
            )
            total_cost = amount * float(price) * (1 + float(fee_rate))
            if free.get(quote, 0.0) < total_cost:
                logger.warning(
                    "Insufficient quote balance for buy order, skipping trade."
                )
                return None
        else:
            if free.get(base, 0.0) < amount:
                logger.warning(
                    "Insufficient base balance for sell order, skipping trade."
                )
                return None

        order = policy.call(exchange.create_market_order, symbol, side, amount)
        logger.info(
            "Executed %s order for %s %s: id=%s",
            side,
            amount,
            symbol,
            order.get("id"),
        )
        return order
    except ccxt.BaseError as e:
        logger.error("Order execution failed: %s", e)
        return None
