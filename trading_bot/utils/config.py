import json
import logging
import os
from functools import lru_cache
from typing import Dict


def _deep_update(base: Dict, override: Dict) -> Dict:
    """Recursively merge ``override`` into ``base``."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def load_config(config_dir: str | None = None) -> Dict:
    """Load configuration with optional local overrides.

    Parameters
    ----------
    config_dir:
        Directory to load config files from. Defaults to the package root.

    Returns
    -------
    dict
        Merged configuration dictionary.
    """
    base_dir = config_dir or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )
    config_path = os.path.join(base_dir, "config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.warning("config.json not found, using default values")
        config = {
            "symbol": "BTC/USDT",
            "timeframe": "1m",
            "limit": 500,
            "sma_short": 5,
            "sma_long": 20,
            "rsi_period": 14,
            "rsi_lower": 30,
            "rsi_upper": 70,
            "trade_size": 1.0,
        }

    local_path = os.path.join(base_dir, "config.local.json")
    if os.path.exists(local_path):
        try:
            with open(local_path, "r") as f:
                local_cfg = json.load(f)
            config = _deep_update(config, local_cfg)
        except (OSError, json.JSONDecodeError) as e:  # noqa: BLE001
            logging.warning(f"Failed loading config.local.json: {e}")
    # Override sensitive values with environment variables if available
    env_api_key = os.getenv("TRADING_BOT_API_KEY")
    if env_api_key:
        config["api_key"] = env_api_key
    env_api_secret = os.getenv("TRADING_BOT_API_SECRET")
    if env_api_secret:
        config["api_secret"] = env_api_secret
    env_api_passphrase = os.getenv("TRADING_BOT_API_PASSPHRASE")
    if env_api_passphrase:
        config["api_passphrase"] = env_api_passphrase

    return config


@lru_cache(maxsize=1)
def get_config(config_dir: str | None = None) -> Dict:
    """Return the merged configuration, caching the result."""
    return load_config(config_dir)
