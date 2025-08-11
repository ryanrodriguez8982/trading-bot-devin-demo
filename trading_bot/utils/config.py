import json
import logging
import os
from functools import lru_cache
from typing import Dict, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


logger = logging.getLogger(__name__)


def _deep_update(base: Dict, override: Dict) -> Dict:
    """Recursively merge ``override`` into ``base``."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def load_config(config_dir: Optional[str] = None) -> Dict:
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
        logger.warning(
            "load_config: config.json not found at %s, using default values",
            config_path,
        )
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
            logger.warning(
                "load_config: Failed loading config.local.json at %s: %s",
                local_path,
                e,
            )
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
    env_exchange = os.getenv("TRADING_BOT_EXCHANGE")
    if env_exchange:
        config["exchange"] = env_exchange

    try:
        validated = ConfigModel(**config)
    except ValidationError as e:  # noqa: BLE001
        raise ValueError(f"Invalid configuration: {e}") from e
    return validated.model_dump()


class ConfluenceModel(BaseModel):
    required: int = Field(gt=0)
    members: list[str]

    model_config = ConfigDict(extra="forbid")

    @field_validator("members")
    @classmethod
    def members_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("confluence.members must be a non-empty list")
        return v

    @model_validator(mode="after")
    def check_required(self) -> "ConfluenceModel":
        if self.required > len(self.members):
            raise ValueError(
                "confluence.required cannot exceed number of members"
            )
        return self


class ConfigModel(BaseModel):
    symbol: str
    timeframe: str
    limit: int = Field(gt=0)
    sma_short: int = Field(gt=0)
    sma_long: int = Field(gt=0)
    rsi_period: int = Field(gt=0)
    rsi_lower: int = Field(ge=0, le=100)
    rsi_upper: int = Field(ge=0, le=100)
    trade_size: float = Field(gt=0)
    confluence: ConfluenceModel

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def check_rsi_bounds(self) -> "ConfigModel":
        if self.rsi_upper <= self.rsi_lower:
            raise ValueError("rsi_upper must be greater than rsi_lower")
        return self


@lru_cache(maxsize=1)
def get_config(config_dir: Optional[str] = None) -> Dict:
    """Return the merged configuration, caching the result."""
    return load_config(config_dir)
