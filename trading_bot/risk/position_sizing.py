"""Utility for computing position size based on risk configuration."""
from __future__ import annotations

import math
from typing import Optional

from trading_bot.risk_config import PositionSizingConfig


def _floor_to_step(value: float, step: float) -> float:
    """Floor ``value`` to the nearest multiple of ``step``."""
    return math.floor(value / step) * step


def calculate_position_size(
    cfg: PositionSizingConfig,
    price: float,
    equity: float,
    *,
    lot_size: Optional[float] = None,
    precision: Optional[int] = None,
) -> float:
    """Return the trade quantity for a given price and account equity.

    Parameters
    ----------
    cfg: PositionSizingConfig
        Configuration specifying the sizing mode and amounts.
    price: float
        Current asset price.
    equity: float
        Current portfolio equity in quote currency (e.g., USD).
    lot_size: float or None
        Minimum tradable increment.  If provided the result is floored to a
        multiple of ``lot_size``.
    precision: int or None
        Optional decimal precision.  If given, the result is rounded down to
        this number of decimal places.
    """
    if price <= 0 or equity <= 0:
        return 0.0

    if cfg.mode == "fixed_cash":
        cash_to_use = min(cfg.fixed_cash_amount, equity)
    elif cfg.mode == "fixed_fraction":
        cash_to_use = equity * cfg.fraction_of_equity
    elif cfg.mode == "risk_per_trade":
        cash_to_use = equity * cfg.risk_pct
    else:
        raise ValueError(f"Unknown position sizing mode: {cfg.mode}")

    if cash_to_use <= 0:
        return 0.0

    qty = cash_to_use / price

    if lot_size:
        qty = _floor_to_step(qty, lot_size)
    if precision is not None:
        factor = 10 ** precision
        qty = math.floor(qty * factor) / factor

    if lot_size and qty < lot_size:
        return 0.0
    if qty <= 0:
        return 0.0
    return qty
