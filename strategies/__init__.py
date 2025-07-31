from .sma_strategy import sma_crossover_strategy
from .rsi_strategy import rsi_crossover_strategy
from .bollinger_strategy import bollinger_bands_strategy

STRATEGY_REGISTRY = {
    "sma": sma_crossover_strategy,
    "rsi": rsi_crossover_strategy,
    "bollinger": bollinger_bands_strategy,
}

def list_strategies():
    return list(STRATEGY_REGISTRY.keys())
