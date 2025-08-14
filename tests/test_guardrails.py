from datetime import datetime, timedelta, timezone

from trading_bot.risk.guardrails import Guardrails
from trading_bot.notify import configure
import logging


def test_halt_when_drawdown_exceeded():
    g = Guardrails(max_dd_pct=0.1)
    g.reset_month(1000)
    assert not g.should_halt(950)
    assert g.should_halt(890)


def test_cooldown_after_consecutive_losses():
    g = Guardrails(max_dd_pct=1.0, cooldown_minutes=5)
    now = datetime.now(timezone.utc)

    g.record_trade(-1, now=now)
    g.record_trade(-1, now=now + timedelta(minutes=1))
    assert not g.cooling_down(now=now + timedelta(minutes=1))

    g.record_trade(-1, now=now + timedelta(minutes=2))
    assert g.cooling_down(now=now + timedelta(minutes=2))
    assert not g.cooling_down(now=now + timedelta(minutes=10))


def test_allow_trade_combines_checks():
    g = Guardrails(max_dd_pct=0.1, cooldown_minutes=5)
    g.reset_month(100)
    assert g.allow_trade(95)
    assert not g.allow_trade(80)  # drawdown breach

    now = datetime.now(timezone.utc)
    g.reset_month(100)
    g.record_trade(-1, now=now)
    g.record_trade(-1, now=now + timedelta(minutes=1))
    g.record_trade(-1, now=now + timedelta(minutes=2))
    assert not g.allow_trade(95, now=now + timedelta(minutes=2))
    assert g.allow_trade(95, now=now + timedelta(minutes=10))


def test_alert_emitted_on_drawdown(caplog):
    configure({"alerts": {"enabled": True}})
    g = Guardrails(max_dd_pct=0.1)
    g.reset_month(1000)
    with caplog.at_level(logging.ERROR):
        assert g.should_halt(880)
    assert any("Max drawdown exceeded" in r.message for r in caplog.records)


def test_max_trades_per_day_limit():
    g = Guardrails(max_trades_per_day=2)
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert g.allow_trade(1000, now=now)
    g.record_trade(0, now=now)
    g.record_trade(0, now=now)
    assert not g.allow_trade(1000, now=now)
    # Next day resets the counter
    assert g.allow_trade(1000, now=now + timedelta(days=1))


def test_max_position_pct_limit():
    g = Guardrails(max_position_pct=0.1)
    equity = 1000
    price = 100
    assert g.allow_trade(equity, price=price, qty=0.5)
    assert not g.allow_trade(equity, price=price, qty=2)


def test_trading_window():
    g = Guardrails(trading_start_hour=9, trading_end_hour=17)
    morning = datetime(2025, 1, 1, 10, tzinfo=timezone.utc)
    evening = datetime(2025, 1, 1, 18, tzinfo=timezone.utc)
    assert g.allow_trade(1000, now=morning)
    assert not g.allow_trade(1000, now=evening)
