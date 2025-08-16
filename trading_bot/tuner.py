import logging
import itertools
from typing import List, Dict, Any, Optional

from trading_bot.backtester import (
    run_backtest,
    load_csv_data,
    generate_signals,
    simulate_equity,
)

logger = logging.getLogger(__name__)

DEFAULT_GRIDS: Dict[str, Dict[str, List[Any]]] = {
    "sma": {
        "sma_short": [5, 10, 15],
        "sma_long": [20, 30, 50],
    },
    "rsi": {
        "rsi_period": [14, 21],
    },
    "macd": {
        "macd_fast": [12, 15],
        "macd_slow": [26, 30],
        "macd_signal": [9],
    },
    "bbands": {
        "bbands_window": [20, 30],
        "bbands_std": [2, 3],
    },
}


def tune(
    csv_path: str,
    strategy: str = "sma",
    param_grid: Optional[Dict[str, List[Any]]] = None,
) -> List[Dict[str, Any]]:
    """Run parameter tuning for a given strategy using backtesting.

    Args:
        csv_path: Path to historical CSV file.
        strategy: Strategy name.
        param_grid: Dictionary mapping parameter names to lists of values.

    Returns:
        Sorted list of results (dict) with parameters and backtest metrics.
    """
    if param_grid is None:
        if strategy not in DEFAULT_GRIDS:
            raise ValueError(f"No default grid for strategy: {strategy}")
        param_grid = DEFAULT_GRIDS[strategy]

    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]

    results: List[Dict[str, Any]] = []
    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        logger.info("Testing parameters: %s", params)
        try:
            stats = run_backtest(csv_path, strategy=strategy, **params)
        except Exception as e:  # pragma: no cover - log and continue
            logger.exception("Error during backtest with params %s: %s", params, e)
            continue

        result = {"params": params}
        result.update(stats)
        results.append(result)

    results.sort(key=lambda x: x.get("net_pnl", float("-inf")), reverse=True)
    return results


def walk_forward_optimize(
    csv_path: str,
    strategy: str = "sma",
    param_grid: Optional[Dict[str, List[Any]]] = None,
    train_size: int = 100,
    test_size: int = 20,
) -> List[Dict[str, Any]]:
    """Perform walk-forward optimization over rolling windows.

    The dataset is split into successive training and testing segments. Each
    training segment is optimized using a grid search and the best parameters
    are then evaluated on the following test segment.

    Returns a list of dictionaries with the best parameters and test statistics
    for each window.
    """
    if train_size <= 0 or test_size <= 0:
        raise ValueError("train_size and test_size must be positive")

    df = load_csv_data(csv_path)

    if param_grid is None:
        if strategy not in DEFAULT_GRIDS:
            raise ValueError(f"No default grid for strategy: {strategy}")
        param_grid = DEFAULT_GRIDS[strategy]

    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]

    results: List[Dict[str, Any]] = []
    start = 0
    total_len = len(df)

    while start + train_size + test_size <= total_len:
        train_df = df.iloc[start : start + train_size].reset_index(drop=True)
        test_df = df.iloc[start + train_size : start + train_size + test_size].reset_index(drop=True)

        best_params: Optional[Dict[str, Any]] = None
        best_stats: Optional[Dict[str, Any]] = None

        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            signals = generate_signals(train_df, strategy=strategy, **params)
            _, stats = simulate_equity(train_df, signals)
            if best_stats is None or stats.get("net_pnl", float("-inf")) > best_stats.get("net_pnl", float("-inf")):
                best_stats = stats
                best_params = params

        assert best_params is not None

        test_signals = generate_signals(test_df, strategy=strategy, **best_params)
        _, test_stats = simulate_equity(test_df, test_signals)

        results.append(
            {
                "train_start": train_df["timestamp"].iloc[0],
                "train_end": train_df["timestamp"].iloc[-1],
                "test_start": test_df["timestamp"].iloc[0],
                "test_end": test_df["timestamp"].iloc[-1],
                "best_params": best_params,
                "test_stats": test_stats,
            }
        )

        start += test_size

    return results
