import time
import logging

from trading_bot.notify import configure, check_heartbeat


def test_heartbeat_alert(caplog):
    configure({"alerts": {"enabled": True, "heartbeat_lapse": 1}})
    past = time.time() - 2
    with caplog.at_level(logging.ERROR):
        assert not check_heartbeat(past, now=time.time())
    assert any("Heartbeat missed" in r.message for r in caplog.records)
