import pytest
from trading_bot.portfolio import Portfolio


def test_buy_reduces_cash_and_increases_position():
    p = Portfolio(cash=1000)
    p.buy("BTC", 1, 100, fee_bps=10)
    assert p.cash == pytest.approx(1000 - 100 - 0.1)
    assert p.position_qty("BTC") == 1
    assert p.positions["BTC"].avg_cost == 100
    assert p.realized_pnl == pytest.approx(-0.1)


def test_selling_updates_cash_and_realized_pnl():
    p = Portfolio(cash=1000)
    p.buy("BTC", 2, 100)
    p.sell("BTC", 1, 110, fee_bps=10)
    assert p.cash == pytest.approx(1000 - 200 + 110 - 0.11)
    assert p.position_qty("BTC") == 1
    assert p.realized_pnl == pytest.approx(9.89)


def test_sell_disallows_more_than_held():
    p = Portfolio(cash=1000)
    p.buy("BTC", 1, 100)
    with pytest.raises(ValueError):
        p.sell("BTC", 2, 110)


def test_failed_sell_does_not_change_state():
    p = Portfolio(cash=1000)
    p.buy("BTC", 1, 100)
    with pytest.raises(ValueError):
        p.sell("BTC", 2, 110)
    assert p.cash == pytest.approx(900)
    assert p.position_qty("BTC") == 1
    assert p.realized_pnl == pytest.approx(0)


def test_sell_unowned_disallowed():
    p = Portfolio(cash=1000)
    with pytest.raises(ValueError):
        p.sell("BTC", 1, 100)


def test_equity_calculation():
    p = Portfolio(cash=1000)
    p.buy("BTC", 1, 100)
    equity = p.equity({"BTC": 120})
    assert equity == pytest.approx(p.cash + 120)


def test_equity_multiple_positions():
    p = Portfolio(cash=1000)
    p.buy("BTC", 1, 100)
    p.buy("ETH", 2, 50)
    prices = {"BTC": 120, "ETH": 40}
    equity = p.equity(prices)
    expected = p.cash + 1 * 120 + 2 * 40
    assert equity == pytest.approx(expected)


def test_total_position_value():
    p = Portfolio(cash=1000)
    p.buy("BTC", 1, 100)
    value = p.total_position_value({"BTC": 150})
    assert value == pytest.approx(150)


def test_buy_requires_cash():
    p = Portfolio(cash=50)
    with pytest.raises(ValueError):
        p.buy("BTC", 1, 100)
    assert p.cash == 50
    assert p.position_qty("BTC") == 0


def test_positive_price_and_qty_required():
    p = Portfolio(cash=1000)
    with pytest.raises(ValueError):
        p.buy("BTC", 0, 100)
    with pytest.raises(ValueError):
        p.buy("BTC", 1, 0)
    p.buy("BTC", 1, 100)
    with pytest.raises(ValueError):
        p.sell("BTC", 0, 110)
    with pytest.raises(ValueError):
        p.sell("BTC", 1, 0)


def test_rejects_non_positive_qty_or_price():
    p = Portfolio(cash=1000)
    with pytest.raises(ValueError):
        p.buy("BTC", -1, 100)


def test_buy_sell_positive_qty_price():
    p = Portfolio(cash=1000)
    with pytest.raises(ValueError):
        p.buy("BTC", -1, 100)
    with pytest.raises(ValueError):
        p.buy("BTC", 1, -100)

    p.buy("BTC", 1, 100)
    with pytest.raises(ValueError):
        p.sell("BTC", -1, 100)
    with pytest.raises(ValueError):
        p.sell("BTC", 1, -100)


def test_equity_uses_cached_prices():
    """Equity should use last known prices if none are provided."""
    p = Portfolio(cash=1000)
    p.buy("BTC", 1, 100)
    # first call updates cached price
    p.equity({"BTC": 120})
    # subsequent call without prices uses cached value
    expected = p.cash + 120
    assert p.equity() == pytest.approx(expected)


def test_fractional_trades_and_fees():
    p = Portfolio(cash=1000)
    p.buy("BTC", 0.5, 100, fee_bps=25)
    assert p.cash == pytest.approx(1000 - 50 - 0.125)
    p.sell("BTC", 0.2, 110, fee_bps=25)
    assert p.cash == pytest.approx(1000 - 50 - 0.125 + 22 - 0.055)
    assert p.position_qty("BTC") == pytest.approx(0.3)
    assert p.realized_pnl == pytest.approx(1.82)


def test_sell_closes_position_and_clears_price():
    p = Portfolio(cash=1000)
    p.buy("BTC", 1, 100)
    p.sell("BTC", 1, 110, fee_bps=0)
    assert "BTC" not in p.positions
    assert "BTC" not in p.last_prices
