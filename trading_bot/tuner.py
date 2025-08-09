import logging
import itertools

from trading_bot.backtester import run_backtest


DEFAULT_GRIDS = {
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


def tune(csv_path, strategy="sma", param_grid=None):
    """Run parameter tuning for a given strategy using backtesting.

    Parameters
    ----------
    csv_path : str
        Path to historical CSV file.
    strategy : str
        Strategy name.
    param_grid : dict, optional
        Dictionary mapping parameter names to lists of values.

    Returns
    -------
    list of dict
        Sorted list of results with parameters and metrics.
    """
    if param_grid is None:
        if strategy not in DEFAULT_GRIDS:
            raise ValueError(f"No default grid for strategy: {strategy}")
        param_grid = DEFAULT_GRIDS[strategy]

    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]

    results = []
    for combo in itertools.product(*values):
        params = dict(zip(keys, combo))
        logging.info("Testing %s", params)
        stats = run_backtest(csv_path, strategy=strategy, **params)
        result = {"params": params}
        result.update(stats)
        results.append(result)

    results.sort(key=lambda x: x["net_pnl"], reverse=True)
    return results

