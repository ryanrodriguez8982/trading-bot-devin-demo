import itertools
import json
import logging
from typing import Dict, List, Tuple

import pandas as pd

from trading_bot.backtester import load_csv_data, simulate_equity
from trading_bot.strategies import STRATEGY_REGISTRY

# Mapping for CLI param aliases to strategy function arguments
PARAM_ALIASES: Dict[str, Dict[str, str]] = {
    "macd": {
        "fast": "fast_period",
        "slow": "slow_period",
        "signal": "signal_period",
    }
}


def parse_optimize_args(tokens: List[str]) -> Dict:
    """Parse CLI tokens for optimization.

    Parameters
    ----------
    tokens: list of str
        Tokens like ["strategy=macd", "fast=[8,12]", ...].

    Returns
    -------
    dict
        Parsed options containing strategy, param_grid, split, metric.
    """
    options = {
        "strategy": "sma",
        "param_grid": {},
        "split": (0.7, 0.3),
        "metric": "sharpe",
    }
    for tok in tokens or []:
        if "=" not in tok:
            continue
        key, value = tok.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "strategy":
            options["strategy"] = value
        elif key == "split":
            try:
                train, valid = value.split("/")
                train_frac = float(train) / 100.0
                valid_frac = float(valid) / 100.0
                options["split"] = (train_frac, valid_frac)
            except ValueError as exc:
                raise ValueError(f"Invalid split: {value}") from exc
        elif key == "metric":
            options["metric"] = value
        else:
            # Treat as parameter grid, value should be JSON list
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid grid for {key}: {value}") from exc
            options["param_grid"][key] = parsed
    return options


def _run_strategy(df: pd.DataFrame, strategy: str, params: Dict) -> Tuple[List[float], Dict]:
    """Generate equity curve and stats for given params on dataframe."""
    strategy_fn = STRATEGY_REGISTRY[strategy]
    aliases = PARAM_ALIASES.get(strategy, {})
    call_params = {aliases.get(k, k): v for k, v in params.items()}
    if strategy == "rsi":
        signals = strategy_fn(df, period=call_params.get("period", params.get("period", 14)))
    else:
        signals = strategy_fn(df, **call_params)
    equity, stats = simulate_equity(df, signals)
    return equity, stats


def _compute_metric(equity: List[float], metric: str) -> float:
    """Compute requested metric from equity curve."""
    if not equity:
        return 0.0
    returns = pd.Series(equity).pct_change().dropna()
    if returns.empty or returns.std() == 0:
        return 0.0
    if metric == "sharpe":
        return (returns.mean() / returns.std()) * (len(returns) ** 0.5)
    # fallback to net pnl
    return equity[-1] - equity[0]


def optimize(csv_path: str, strategy: str, param_grid: Dict[str, List], split: Tuple[float, float], metric: str, results_csv: str, best_json: str):
    """Run grid search optimization with train/validation split."""
    df = load_csv_data(csv_path)
    train_size = int(len(df) * split[0])
    train_df = df.iloc[:train_size]
    valid_df = df.iloc[train_size:]

    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]

    records = []
    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        train_eq, _ = _run_strategy(train_df, strategy, params)
        valid_eq, _ = _run_strategy(valid_df, strategy, params)
        train_metric = _compute_metric(train_eq, metric)
        valid_metric = _compute_metric(valid_eq, metric)
        rec = {k: v for k, v in params.items()}
        rec.update({"train_metric": train_metric, "valid_metric": valid_metric})
        records.append(rec)

    df_results = pd.DataFrame(records)
    df_results.sort_values("valid_metric", ascending=False, inplace=True)
    df_results.to_csv(results_csv, index=False)

    best = df_results.iloc[0].to_dict() if not df_results.empty else {}
    with open(best_json, "w") as f:
        json.dump(best, f, indent=2)

    if best and best["train_metric"] > best["valid_metric"] * 1.5:
        logging.warning("Possible overfitting: train metric %.4f >> valid metric %.4f", best["train_metric"], best["valid_metric"])

    return df_results, best


def train_valid_split(df: pd.DataFrame, split: Tuple[float, float]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split dataframe into train and validation subsets."""
    train_size = int(len(df) * split[0])
    return df.iloc[:train_size], df.iloc[train_size:]
