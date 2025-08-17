"""Internal shared typing aliases for the trading bot.

These aliases are used for static analysis and readability; they do not affect runtime behavior.
"""

from typing import Any, Dict, List

SignalDict = Dict[str, Any]
Signals = List[SignalDict]
Price = float
Symbol = str
Row = Dict[str, Any]
Rows = List[Row]
