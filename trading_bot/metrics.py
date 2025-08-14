"""Prometheus metrics and health check utilities for live trading."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

from prometheus_client import Counter, Gauge, start_http_server

# Prometheus metric instances
SIGNALS_GENERATED = Counter(
    "signals_generated_total", "Total number of trading signals generated"
)
TRADES_EXECUTED = Counter(
    "trades_executed_total", "Total number of trades executed"
)
ERRORS_TOTAL = Counter("error_total", "Total number of errors encountered")
PNL_GAUGE = Gauge(
    "pnl", "Realized profit and loss of the portfolio"
)


def start_metrics_server(port: int) -> None:
    """Start Prometheus metrics HTTP server on ``port``."""
    start_http_server(port)


def start_health_server(port: int) -> HTTPServer:
    """Start a simple health check HTTP server.

    Returns the running :class:`HTTPServer` instance.
    """

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # pragma: no cover - simple I/O
            if self.path == "/health":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):  # pragma: no cover - I/O noise
            return

    server = HTTPServer(("", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


__all__ = [
    "SIGNALS_GENERATED",
    "TRADES_EXECUTED",
    "ERRORS_TOTAL",
    "PNL_GAUGE",
    "start_metrics_server",
    "start_health_server",
]
