"""Broker interfaces for trading bot."""
from .base import Broker
from .ccxt_spot import CcxtSpotBroker
from .paper import PaperBroker

__all__ = ["Broker", "PaperBroker", "CcxtSpotBroker"]
