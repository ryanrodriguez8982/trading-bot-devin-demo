import logging
import itertools
from typing import List, Dict, Any

from trading_bot.backtester import run_backtest

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

def tune(csv_path: str, strategy: str = "sma", param_grid: Dict[str, List[Any]] = None) -> List[Dict[str, Any]]:
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
        except Exception as e:
            logger.exception("Error during backtest with params %s: %s", params, e)
            continue

        result = {"params": params}
        result.update(stats)
        results.append(result)

    results.sort(key=lambda x: x.get("net_pnl", float('-inf')), reverse=True)
    return results