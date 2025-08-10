import logging
import os
import json
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional

from trading_bot.utils.state import default_state_dir


class JsonFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record):
        log_record = {
            "time": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def setup_logging(level: str = "INFO", state_dir: Optional[str] = None, json_logs: bool = False) -> str:
    """Configure root logging with console and rotating file handlers.

    Returns the path to the log file.
    """
    state_dir = state_dir or default_state_dir()
    logs_dir = os.path.join(state_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "bot.log")

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers so reconfiguration works
    for handler in list(root.handlers):
        root.removeHandler(handler)

    if json_logs:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
        formatter.converter = time.gmtime

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    file_handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    return log_path
