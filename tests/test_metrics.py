import time
import urllib.request
import socket

from trading_bot import metrics


def _free_port():
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_metrics_and_health_endpoints():
    m_port = _free_port()
    h_port = _free_port()
    metrics.start_metrics_server(m_port)
    metrics.start_health_server(h_port)

    metrics.SIGNALS_GENERATED.inc(2)
    metrics.TRADES_EXECUTED.inc()
    metrics.ERRORS_TOTAL.inc(3)
    metrics.PNL_GAUGE.set(1.5)

    time.sleep(0.1)
    data = urllib.request.urlopen(f"http://localhost:{m_port}/").read().decode()
    assert "signals_generated_total" in data
    assert "trades_executed_total" in data
    assert "error_total" in data
    assert "pnl" in data

    resp = urllib.request.urlopen(f"http://localhost:{h_port}/health").read().decode()
    assert resp == "ok"
