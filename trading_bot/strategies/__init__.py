from .sma_strategy import sma_crossover_strategy
from .rsi_strategy import rsi_crossover_strategy
from .macd import macd_strategy
from .bbands import bbands_strategy

STRATEGY_REGISTRY = {
    "sma": sma_crossover_strategy,
    "rsi": rsi_crossover_strategy,
    "macd": macd_strategy,
    "bbands": bbands_strategy,
}


def list_strategies():
    return list(STRATEGY_REGISTRY.keys())
