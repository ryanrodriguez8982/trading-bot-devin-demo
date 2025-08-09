from trading_bot.utils.precision import round_to_increment


def test_round_buy():
    assert round_to_increment(1.234, 0.01, "buy") == 1.23


def test_round_sell():
    assert round_to_increment(1.236, 0.01, "sell") == 1.24
