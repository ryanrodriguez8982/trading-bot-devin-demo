from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PositionSizingConfig:
    mode: str = "fixed_fraction"
    fraction_of_equity: float = 0.10
    fixed_cash_amount: float = 100.0
    risk_pct: float = 0.01

    def __post_init__(self) -> None:
        if self.mode not in {"fixed_fraction", "fixed_cash", "risk_per_trade"}:
            raise ValueError("Invalid position sizing mode")
        if self.fraction_of_equity < 0 or self.fixed_cash_amount < 0 or self.risk_pct < 0:
            raise ValueError("Position sizing values must be non-negative")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PositionSizingConfig":
        return cls(**data)


@dataclass
class StopLossConfig:
    type: str = "percent"
    value: float = 0.02

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("stop_loss value must be non-negative")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StopLossConfig":
        return cls(**data)


@dataclass
class TakeProfitConfig:
    type: str = "rr"
    rr: float = 2.0

    def __post_init__(self) -> None:
        if self.rr < 0:
            raise ValueError("take_profit rr must be non-negative")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TakeProfitConfig":
        return cls(**data)


@dataclass
class TrailingConfig:
    enabled: bool = True
    trail_pct: float = 0.02

    def __post_init__(self) -> None:
        if self.trail_pct < 0:
            raise ValueError("trail_pct must be non-negative")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrailingConfig":
        return cls(**data)


@dataclass
class StopsConfig:
    stop_loss: StopLossConfig = field(default_factory=StopLossConfig)
    take_profit: TakeProfitConfig = field(default_factory=TakeProfitConfig)
    trailing: TrailingConfig = field(default_factory=TrailingConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StopsConfig":
        return cls(
            stop_loss=StopLossConfig.from_dict(data.get("stop_loss", {})),
            take_profit=TakeProfitConfig.from_dict(data.get("take_profit", {})),
            trailing=TrailingConfig.from_dict(data.get("trailing", {})),
        )


@dataclass
class MaxDrawdownConfig:
    monthly_pct: float = 0.10
    cooldown_bars: int = 0

    def __post_init__(self) -> None:
        if self.monthly_pct < 0 or self.cooldown_bars < 0:
            raise ValueError("max_drawdown values must be non-negative")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaxDrawdownConfig":
        return cls(**data)


@dataclass
class RiskConfig:
    slippage_bps: float = 5
    position_sizing: PositionSizingConfig = field(default_factory=PositionSizingConfig)
    stops: StopsConfig = field(default_factory=StopsConfig)
    max_drawdown: MaxDrawdownConfig = field(default_factory=MaxDrawdownConfig)

    def __post_init__(self) -> None:
        if self.slippage_bps < 0:
            raise ValueError("bps values must be non-negative")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskConfig":
        return cls(
            slippage_bps=data.get("slippage_bps", 5),
            position_sizing=PositionSizingConfig.from_dict(data.get("position_sizing", {})),
            stops=StopsConfig.from_dict(data.get("stops", {})),
            max_drawdown=MaxDrawdownConfig.from_dict(data.get("max_drawdown", {})),
        )


DEFAULT_RISK_DICT: Dict[str, Any] = {
    "slippage_bps": 5,
    "position_sizing": {
        "mode": "fixed_fraction",
        "fraction_of_equity": 0.10,
        "fixed_cash_amount": 100.0,
        "risk_pct": 0.01,
    },
    "stops": {
        "stop_loss": {"type": "percent", "value": 0.02},
        "take_profit": {"type": "rr", "rr": 2.0},
        "trailing": {"enabled": True, "trail_pct": 0.02},
    },
    "max_drawdown": {"monthly_pct": 0.10, "cooldown_bars": 0},
}

DEFAULT_RISK_CONFIG = RiskConfig.from_dict(DEFAULT_RISK_DICT)


def _deep_merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in updates.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def _apply_overrides(config: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in overrides.items():
        parts = key.split('.')
        d = config
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        # best-effort type conversion
        try:
            value = float(value)
            if value.is_integer():
                value = int(value)
        except (ValueError, TypeError):
            # Leave ``value`` as-is when it cannot be converted to a number
            pass
        d[parts[-1]] = value
    return config


def get_risk_config(
    config_dict: Optional[Dict[str, Any]] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> RiskConfig:
    """Merge defaults with config/CLI overrides and return a validated RiskConfig."""
    merged: Dict[str, Any] = {}
    _deep_merge(merged, DEFAULT_RISK_DICT.copy())
    if config_dict:
        _deep_merge(merged, config_dict)
    if overrides:
        _apply_overrides(merged, overrides)
    return RiskConfig.from_dict(merged)

