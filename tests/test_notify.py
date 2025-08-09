import time

from trading_bot.notify import configure, check_heartbeat


def test_heartbeat_alert(capfd):
    configure({"alerts": {"enabled": True, "heartbeat_lapse": 1}})
    past = time.time() - 2
    assert not check_heartbeat(past, now=time.time())
    captured = capfd.readouterr()
    assert "Heartbeat missed" in captured.out
