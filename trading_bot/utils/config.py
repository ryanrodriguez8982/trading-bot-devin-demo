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
        }

    local_path = os.path.join(base_dir, "config.local.json")
    if os.path.exists(local_path):
        try:
            with open(local_path, "r") as f:
                local_cfg = json.load(f)
            config = _deep_update(config, local_cfg)
        except (OSError, json.JSONDecodeError) as e:  # noqa: BLE001
            logging.warning(f"Failed loading config.local.json: {e}")

    return config


@lru_cache(maxsize=1)
def get_config(config_dir: str | None = None) -> Dict:
    """Return the merged configuration, caching the result."""
    return load_config(config_dir)
