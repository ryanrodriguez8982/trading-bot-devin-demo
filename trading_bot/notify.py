import logging
import time
from typing import Iterable, Optional

try:  # pragma: no cover - optional dependency
    from plyer import notification as desktop_notify
except ImportError:  # pragma: no cover
    desktop_notify = None

ALERTS_ENABLED = False
HEARTBEAT_LAPSE: int = 0
MAX_DD_PCT: float = 0.0


logger = logging.getLogger(__name__)

def configure(config: Optional[dict]) -> None:
    """Configure alert settings from ``config`` dictionary."""
    global ALERTS_ENABLED, HEARTBEAT_LAPSE, MAX_DD_PCT
    alerts = (config or {}).get("alerts", {})
    ALERTS_ENABLED = alerts.get("enabled", False)
    HEARTBEAT_LAPSE = alerts.get("heartbeat_lapse", 0)
    MAX_DD_PCT = alerts.get("max_dd_pct", 0.0)


def send(message: str, channels: Optional[Iterable[str]] = None) -> None:
    """Send ``message`` via specified channels if alerts enabled."""
    if not ALERTS_ENABLED:
        return
    channels = list(channels or ["console"])
    if "console" in channels:
        logger.error(f"ALERT: {message}")
    if "desktop" in channels and desktop_notify:
        try:  # pragma: no cover - desktop notifications not testable
            desktop_notify.notify(title="Trading Bot Alert", message=message)
        except Exception as exc:  # pragma: no cover
            logger.exception("send: Notification error via desktop channel: %s", exc)
    if "email" in channels:
        pass  # Stub for future email integration
    if "webhook" in channels:
        pass  # Stub for future webhook integration


def check_heartbeat(last_beat: float, now: Optional[float] = None) -> bool:
    """Return ``True`` if heartbeat is within allowed lapse.

    Emits an alert and returns ``False`` when the time since ``last_beat``
    exceeds :data:`HEARTBEAT_LAPSE`.
    """
    if HEARTBEAT_LAPSE <= 0:
        return True
    now = now or time.time()
    if now - last_beat > HEARTBEAT_LAPSE:
        send("Heartbeat missed")
        return False
    return True


__all__ = ["configure", "send", "check_heartbeat"]
