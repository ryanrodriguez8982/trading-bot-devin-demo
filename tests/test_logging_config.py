import json
import logging
from pathlib import Path

from trading_bot.utils.logging_config import setup_logging


logger = logging.getLogger(__name__)


def test_setup_logging_creates_log_file(tmp_path):
    log_dir = tmp_path
    setup_logging(level="INFO", state_dir=str(log_dir))
    logger.info("hello world")
    log_file = Path(log_dir) / "logs" / "bot.log"
    assert log_file.exists()
    assert "hello world" in log_file.read_text()


def test_json_logging(tmp_path):
    setup_logging(level="INFO", state_dir=str(tmp_path), json_logs=True)
    logger.info("json message")
    log_file = Path(tmp_path) / "logs" / "bot.log"
    line = log_file.read_text().splitlines()[0]
    record = json.loads(line)
    assert record["message"] == "json message"
    assert record["level"] == "INFO"
