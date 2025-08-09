from decimal import Decimal, ROUND_DOWN, ROUND_UP


def round_to_increment(value: float, increment: float, side: str) -> float:
    """Round ``value`` to the nearest ``increment`` respecting order side.

    Parameters
    ----------
    value:
        The original quantity or price.
    increment:
        The smallest allowable step for the value.
    side:
        "buy" to round down, "sell" to round up.
    """
    if increment <= 0:
        raise ValueError("increment must be positive")

    quant = Decimal(str(increment))
    val = Decimal(str(value))

    if side == "buy":
        rounding = ROUND_DOWN
    elif side == "sell":
        rounding = ROUND_UP
    else:
        raise ValueError("side must be 'buy' or 'sell'")

    adjusted = (val / quant).to_integral_value(rounding=rounding) * quant
    return float(adjusted)
