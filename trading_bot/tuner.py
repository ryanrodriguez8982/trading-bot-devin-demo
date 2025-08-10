import logging
import itertools
from typing import Dict, List, Any

from trading_bot.backtester import run_backtest

logger = logging.getLogger(__name__)

# Default grids use the parameter names expected by the backtester for each strategy.
DEFAULT_GRIDS: Dict[str, Dict[str, List[Any]]] = {
    "sma": {
        "sma_short": [5, 10, 15],
        "sma_long": [20, 30, 50],
    },
    "rsi": {
        # Backtester maps these onto the RSI strategy params
        "rsi_period": [14, 21],
        # Uncomment to sweep thresholds too:
        # "rsi_lower": [25, 30, 35],
        # "rsi_upper": [65, 70, 75],
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


def tune(csv_path: str, strategy: str = "sma", param_grid: Dict[str, List[Any]] | None = None) -> List[Dict[str, Any]]:
    """Run parameter tuning for a given strategy using backtesting.

    Parameters
    ----------
    csv_path : str
        Path to historical CSV file.
    strategy : str
        Strategy name (e.g., 'sma', 'rsi', 'macd', 'bbands').
    param_grid : dict, optional
        Dict mapping parameter names to lists of values. If not provided,
        a default grid for the selected strategy is used.

    Returns
    -------
    list of dict
        Sorted list of results with parameters ("params") and metrics.
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
        logger.info("Testing params: %s", params)
        try:
            stats = run_backtest(csv_path, strategy=strategy, **params)
        except Exception:
            logger.exception("Backtest failed for params: %s", params)
            continue

        result = {"params": params}
        if isinstance(stats, dict):
            result.update(stats)
        else:
            # If run_backtest returns a tuple or object, store it under a key
            result["stats"] = stats
        results.append(result)

    # Prefer 'net_pnl' when present; otherwise leave order unchanged
    try:
        results.sort(key=lambda x: x.get("net_pnl", float("-inf")), reverse=True)
    except Exception:
        logger.debug("Results not sortable by net_pnl; leaving original order")

    logger.info("Tuning complete: %d combinations evaluated", len(results))
    return results
