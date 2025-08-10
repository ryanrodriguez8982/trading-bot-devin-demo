"""Portfolio protection guardrails.

This module provides a small helper class, :class:`Guardrails`, used to
enforce risk limits during live trading.  Two safeguards are implemented:

* **Monthly max drawdown** – trading halts if equity falls by more than the
  configured percentage from the month's starting equity.
* **Loss cooldown** – after a number of consecutive losing trades a cooldown
  period is triggered during which new trades are blocked.

The implementation is intentionally lightweight so it can be used both inside
the live trading loop and in unit tests where behaviour is simulated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from trading_bot.notify import send as notify_send


@dataclass
class Guardrails:
    """Runtime state for portfolio guardrails.

    Parameters
    ----------
    max_dd_pct:
        Maximum allowed month‑to‑date drawdown expressed as a decimal
        (``0.10`` for 10%).  If set to ``0`` the drawdown check is disabled.
    loss_limit:
        Number of consecutive losing trades allowed before entering a
        cooldown period.
    cooldown_minutes:
        Duration of the cooldown period in minutes.  A value of ``0``
        disables the cooldown behaviour.
    """

    max_dd_pct: float = 0.0
    loss_limit: int = 3
    cooldown_minutes: int = 0

    # Internal state
    month_start_equity: Optional[float] = None
    consecutive_losses: int = 0
    cooldown_until: Optional[datetime] = None

    def reset_month(self, equity: float) -> None:
        """Reset the month starting equity."""
        self.month_start_equity = equity

    # ------------------------------------------------------------------
    # Drawdown checks
    def _drawdown(self, equity: float) -> float:
        if self.month_start_equity is None:
            self.month_start_equity = equity
            return 0.0
        if self.month_start_equity <= 0:
            return 0.0
        return (self.month_start_equity - equity) / self.month_start_equity

    def should_halt(self, equity: float) -> bool:
        """Return ``True`` if trading should halt due to drawdown."""
        if self.max_dd_pct <= 0:
            return False
        dd = self._drawdown(equity)
        if dd > self.max_dd_pct:
            notify_send("Max drawdown exceeded")
            return True
        return False

    # ------------------------------------------------------------------
    # Cooldown checks
    def record_trade(self, pnl: float, *, now: Optional[datetime] = None) -> None:
        """Record the outcome of a trade.

        Negative ``pnl`` values count as losses and may trigger a cooldown
        period after ``loss_limit`` consecutive losses.
        """

        now = now or datetime.now(timezone.utc)
        if pnl < 0:
            self.consecutive_losses += 1
            if (
                self.cooldown_minutes > 0
                and self.consecutive_losses >= self.loss_limit
            ):
                self.cooldown_until = now + timedelta(minutes=self.cooldown_minutes)
        else:
            self.consecutive_losses = 0

    def cooling_down(self, *, now: Optional[datetime] = None) -> bool:
        """Return ``True`` if currently in a cooldown period."""
        if self.cooldown_until is None:
            return False
        now = now or datetime.now(timezone.utc)
        return now < self.cooldown_until

    # ------------------------------------------------------------------
    def allow_trade(self, equity: float, *, now: Optional[datetime] = None) -> bool:
        """Return ``True`` if trading is allowed.

        Trading is disallowed if either the drawdown threshold has been
        breached or the system is in a cooldown period.
        """

        if self.should_halt(equity):
            return False
        if self.cooling_down(now=now):
            return False
        return True


__all__ = ["Guardrails"]

