import argparse
import json
import logging
import os
import signal as sig
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Dict, List, Optional, Sequence

from ccxt.base.exchange import Exchange

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from trading_bot.backtester import run_backtest
from trading_bot.broker import CcxtSpotBroker, PaperBroker
from trading_bot.data_fetch import fetch_market_data
from trading_bot.exchange import create_exchange, execute_trade
from trading_bot.notify import configure as configure_alerts
from trading_bot.portfolio import Portfolio
from trading_bot.risk.position_sizing import calculate_position_size
from trading_bot.risk.config import get_risk_config
from trading_bot.signal_logger import (
    log_signals_to_db,
    log_trade_to_db,
    mark_signal_handled,
)
from trading_bot.strategies import STRATEGY_REGISTRY
from trading_bot.config import get_config
from trading_bot.utils.logging_config import setup_logging
from trading_bot.utils.retry import RetryPolicy, default_retry
from trading_bot.utils.state import default_state_dir
from trading_bot import metrics

CONFIG = get_config()
DEFAULT_RSI_PERIOD = CONFIG.get("rsi_period", 14)
DEFAULT_RSI_LOWER = CONFIG.get("rsi_lower", 30)
DEFAULT_RSI_UPPER = CONFIG.get("rsi_upper", 70)
DEFAULT_BBANDS_STD = CONFIG.get("bbands_std", 2)

try:
    from plyer import notification
except ImportError:  # pragma: no cover - plyer is optional
    notification = None  # ensure attribute exists for tests

logger = logging.getLogger(__name__)


class CLIArgsModel(BaseModel):
    # ✅ Use Optional[...] for Python 3.9 compatibility
    limit: Optional[int] = Field(default=None, gt=0)
    trade_size: Optional[float] = Field(default=None, gt=0)
    fee_bps: Optional[float] = Field(default=None, ge=0)
    interval_seconds: int = Field(default=60, gt=0)

    model_config = ConfigDict(extra="ignore")


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Crypto Trading Bot. Defaults come from config.json, overridden by "
            "config.local.json and finally by CLI flags."
        )
    )
    parser.add_argument(
        "--exchange",
        type=str,
        default=None,
        help="Specify exchange to use (e.g., binance, coinbase, kraken). Overrides config files.",
    )
    try:
        pkg_version = version("trading-bot")
    except PackageNotFoundError:
        try:
            from trading_bot import __version__ as pkg_version
        except Exception:
            pkg_version = "0.0.0"

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {pkg_version}"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        help="Trading pair symbol (e.g., BTC/USDT). Overrides config files.",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        help="Timeframe for candles (e.g., 1m, 5m). Overrides config files.",
    )
    parser.add_argument(
        "--limit", type=int, help="Number of candles to fetch. Overrides config files."
    )
    parser.add_argument(
        "--sma-short", type=int, help="Short-period SMA window. Overrides config files."
    )
    parser.add_argument(
        "--sma-long", type=int, help="Long-period SMA window. Overrides config files."
    )
    parser.add_argument(
        "--live", action="store_true", help="Enable live trading simulation mode"
    )
    parser.add_argument(
        "--live-trade",
        action="store_true",
        help="Execute real orders when in live mode",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print order payload without executing"
    )
    parser.add_argument("--api-key", type=str, help="Exchange API key")
    parser.add_argument("--api-secret", type=str, help="Exchange API secret")
    parser.add_argument(
        "--api-passphrase", type=str, help="Exchange API passphrase (if required)"
    )
    parser.add_argument("--broker", type=str, help="Broker type to use (paper or ccxt)")
    parser.add_argument(
        "--strategy", type=str, default="sma", help="Trading strategy to use"
    )
    parser.add_argument(
        "--list-strategies",
        action="store_true",
        help="List available strategies and exit",
    )
    parser.add_argument(
        "--alert-mode",
        action="store_true",
        help="Enable alert notifications for BUY/SELL signals",
    )
    parser.add_argument(
        "--metrics-port",
        type=int,
        default=None,
        help="Expose Prometheus metrics on this port",
    )
    parser.add_argument(
        "--health-port",
        type=int,
        default=None,
        help="Expose simple HTTP health check on this port",
    )
    parser.add_argument(
        "--backtest", type=str, help="Path to CSV file for historical backtesting"
    )
    parser.add_argument(
        "--tune",
        action="store_true",
        help="Run parameter tuning over a range of values",
    )
    parser.add_argument(
        "--walk-forward",
        action="store_true",
        help="Run walk-forward optimization over rolling windows",
    )
    parser.add_argument(
        "--train-size",
        type=int,
        help="Training window size for walk-forward optimization",
    )
    parser.add_argument(
        "--test-size",
        type=int,
        help="Testing window size for walk-forward optimization",
    )
    parser.add_argument(
        "--save-chart",
        action="store_true",
        help="Save equity curve CSV/JSON and chart during backtest",
    )
    parser.add_argument(
        "--trade-size",
        type=float,
        default=None,
        help="Default trade size in asset units. Overrides config files.",
    )
    parser.add_argument(
        "--fee-bps",
        type=float,
        default=None,
        help="Trading fee in basis points. Overrides config files.",
    )
    parser.add_argument(
        "--position-sizing",
        type=str,
        choices=["fixed_fraction", "fixed_cash"],
        help="Position sizing mode. Overrides config files.",
    )
    parser.add_argument(
        "--fixed-fraction",
        type=float,
        help="Fraction of equity to use per trade. Overrides config files.",
    )
    parser.add_argument(
        "--fixed-cash",
        type=float,
        help="Fixed cash amount to use per trade. Overrides config files.",
    )
    parser.add_argument(
        "--max-trades-per-day",
        type=int,
        help="Maximum number of trades allowed per day",
    )
    parser.add_argument(
        "--max-position-pct",
        type=float,
        help="Maximum fraction of equity allowed per trade (0-1)",
    )
    parser.add_argument(
        "--trading-window",
        type=str,
        help="Allowed trading window as START-END hours in UTC (e.g., 9-17)",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=60,
        help="Polling interval for live mode in seconds",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        help="Comma-separated list of trading symbols for live mode",
    )
    parser.add_argument(
        "--risk-profile", type=str, help="Risk profile name. Overrides config files."
    )
    parser.add_argument(
        "--state-dir", type=str, help="Directory for logs and database state"
    )
    parser.add_argument(
        "--log-level",
        type=str.upper,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level for the application",
    )
    parser.add_argument(
        "--json-logs", action="store_true", help="Output logs in JSON format"
    )

    # Parse known and collect --risk.* overrides
    args, unknown = parser.parse_known_args()

    risk_overrides = {}
    it = iter(unknown)
    for token in it:
        if token.startswith("--risk."):
            key = token[2 + len("risk."):]
            value = next(it, None)
            if value is None:
                raise SystemExit(f"Missing value for {token}")
            risk_overrides[key] = value
    if getattr(args, "position_sizing", None):
        risk_overrides["position_sizing.mode"] = args.position_sizing
    if getattr(args, "fixed_fraction", None) is not None:
        risk_overrides["position_sizing.fraction_of_equity"] = args.fixed_fraction
    if getattr(args, "fixed_cash", None) is not None:
        risk_overrides["position_sizing.fixed_cash_amount"] = args.fixed_cash
    if getattr(args, "max_trades_per_day", None) is not None:
        risk_overrides["max_drawdown.max_trades_per_day"] = args.max_trades_per_day
    if getattr(args, "max_position_pct", None) is not None:
        risk_overrides["max_drawdown.max_position_pct"] = args.max_position_pct
    if getattr(args, "trading_window", None):
        try:
            start, end = [int(x) for x in args.trading_window.split("-")]
        except ValueError as e:  # noqa: F841
            raise SystemExit("Invalid --trading-window format. Use START-END")
        risk_overrides["max_drawdown.trading_start_hour"] = start
        risk_overrides["max_drawdown.trading_end_hour"] = end
    setattr(args, "risk_overrides", risk_overrides)
    try:
        CLIArgsModel(**vars(args))
    except ValidationError as e:
        parser.error(str(e))
    return args


def log_signals_to_file(
    signals: List[Dict[str, Any]],
    symbol: str,
    state_dir: Optional[str] = None,
) -> None:
    if not signals:
        return None
    state_dir = state_dir or default_state_dir()
    logs_dir = os.path.join(state_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(logs_dir, f"{timestamp}_signals.log")
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"Trading Signals Log - {symbol}\n")
            f.write(f"Generated at: {datetime.now(timezone.utc).isoformat()}\n")
            f.write("=" * 50 + "\n")
            for signal in signals:
                ts = signal["timestamp"].isoformat()
                f.write(
                    f"{ts} | {signal['action'].upper()} | {symbol} | ${signal['price']:.2f}\n"
                )
        logger.info("Logged %d signals to %s", len(signals), log_path)
    except OSError as e:
        logger.error("Failed to log signals to %s: %s", log_path, e)


def log_order_to_file(
    order: Dict[str, Any],
    symbol: str,
    state_dir: Optional[str] = None,
) -> None:
    if not order:
        return
    state_dir = state_dir or default_state_dir()
    logs_dir = os.path.join(state_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "orders.log")
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            ts = datetime.now(timezone.utc).isoformat()
            order_id = order.get("id", "N/A")
            amount = order.get("amount")
            price = order.get("price")
            side = order.get("side")
            f.write(f"{ts} | {order_id} | {side} | {symbol} | {amount} @ {price}\n")
        logger.info("Logged order %s to %s", order.get("id", "N/A"), log_path)
    except OSError as e:
        logger.error("Failed to log order to %s: %s", log_path, e)


def send_alert(signal):
    ts = signal["timestamp"].isoformat()
    message = f"ALERT: {signal['action'].upper()} at {ts} price ${signal['price']:.2f}"
    logger.info(message)
    if notification:
        try:
            notification.notify(title="Trading Bot Alert", message=message)
        except Exception as e:
            logger.exception("send_alert: Notification error: %s", e)


def signal_handler(signum, frame):  # noqa: ARG001 (frame unused)
    logger.info(
        "Received interrupt signal. Shutting down live trading mode gracefully..."
    )
    logger.info("=== Live Trading Mode Shutdown ===")
    sys.exit(0)


def run_single_analysis(
    symbol: str,
    timeframe: str,
    limit: int,
    sma_short: int,
    sma_long: int,
    strategy: str = "sma",
    alert_mode: bool = False,
    exchange: Optional[Exchange] = None,
    confluence_members: Optional[Sequence[str]] = None,
    confluence_required: Optional[int] = None,
    state_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    try:
        if strategy not in STRATEGY_REGISTRY:
            raise ValueError("Unknown strategy. Use --list-strategies to view options.")

        if exchange:
            data = fetch_market_data(symbol, timeframe, limit, exchange=exchange)
        else:
            data = fetch_market_data(symbol, timeframe, limit)
        logger.info("Fetched %d data points for %s (%s)", len(data), symbol, timeframe)

        entry = STRATEGY_REGISTRY[strategy]
        strategy_fn = entry.func
        metadata = entry.metadata

        if strategy == "rsi":
            signals = strategy_fn(
                data,
                period=DEFAULT_RSI_PERIOD,
                lower_thresh=DEFAULT_RSI_LOWER,
                upper_thresh=DEFAULT_RSI_UPPER,
            )
        elif strategy == "macd":
            signals = strategy_fn(data)
        elif strategy == "bbands":
            signals = strategy_fn(
                data,
                window=sma_long,
                num_std=DEFAULT_BBANDS_STD,
            )
        elif strategy == "confluence":
            if confluence_members is None:
                confluence_members = metadata.get("requires")
            if confluence_required is None:
                confluence_required = metadata.get("required_count")
            signals = strategy_fn(
                data,
                members=confluence_members,
                required=confluence_required,
            )
        else:  # SMA, EMA, etc. that accept two windows
            signals = strategy_fn(data, sma_short, sma_long)

        logger.info("Generated %d trading signals for %s", len(signals), symbol)
        if signals:
            for s in signals:
                s["strategy"] = strategy
                logger.info(
                    "Signal generated: symbol=%s action=%s price=%.4f strategy=%s",
                    symbol,
                    s["action"],
                    float(s["price"]),
                    strategy,
                )
            log_signals_to_file(signals, symbol, state_dir)
            db_path = os.path.join(state_dir or default_state_dir(), "signals.db")
            log_signals_to_db(signals, symbol, db_path=db_path)
            if alert_mode:
                for s in signals:
                    send_alert(s)
        return signals
    except Exception:
        logger.exception("Error in analysis cycle for %s", symbol)
        return []


def run_live_mode(
    symbols: Sequence[str],
    timeframe: str,
    sma_short: int,
    sma_long: int,
    strategy: str = "sma",
    alert_mode: bool = False,
    exchange: Optional[Exchange] = None,
    live_trade: bool = False,
    trade_amount: float = 0.0,
    fee_bps: float = 0.0,
    risk_config: Optional[Any] = None,
    interval_seconds: int = 60,
    broker: Optional[Any] = None,
    confluence_members: Optional[Sequence[str]] = None,
    confluence_required: Optional[int] = None,
    state_dir: Optional[str] = None,
    retry_policy: Optional[RetryPolicy] = None,
    metrics_port: Optional[int] = None,
    health_port: Optional[int] = None,
) -> None:
    state_dir = state_dir or default_state_dir()
    retry_policy = retry_policy or default_retry()
    db_path = os.path.join(state_dir, "signals.db")
    live_limit = 25
    sig.signal(sig.SIGINT, signal_handler)

    if strategy not in STRATEGY_REGISTRY:
        raise ValueError("Unknown strategy. Use --list-strategies to view options.")

    logger.info("=== Live Trading Mode Started ===")
    logger.info("Symbols: %s", ", ".join(symbols))
    logger.info("Strategy: %s", strategy.upper())
    logger.info("Fetching %d candles every %d seconds", live_limit, interval_seconds)
    logger.info("Press Ctrl+C to stop gracefully")
    logger.info("=" * 50)

    if metrics_port is not None:
        metrics.start_metrics_server(metrics_port)
    if health_port is not None:
        metrics.start_health_server(health_port)

    iteration = 0
    portfolio = None
    if broker is None:
        portfolio = Portfolio(cash=trade_amount * 100 if trade_amount else 0)

    guardrails = None
    if risk_config is not None:
        md_cfg = getattr(risk_config, "max_drawdown", None)
        if md_cfg and (
            getattr(md_cfg, "monthly_pct", 0) > 0
            or getattr(md_cfg, "cooldown_bars", 0) > 0
        ):
            from trading_bot.risk.guardrails import Guardrails

            guardrails = Guardrails(
                max_dd_pct=md_cfg.monthly_pct,
                cooldown_minutes=md_cfg.cooldown_bars,
                max_trades_per_day=md_cfg.max_trades_per_day,
                max_position_pct=md_cfg.max_position_pct,
                trading_start_hour=md_cfg.trading_start_hour,
                trading_end_hour=md_cfg.trading_end_hour,
            )
            if portfolio:
                guardrails.reset_month(portfolio.equity())

    while True:
        iteration += 1
        if guardrails and portfolio:
            eq = portfolio.equity()
            now = datetime.now(timezone.utc)
            if guardrails.should_halt(eq):
                logger.warning("Guardrails triggered - halting trading")
                break
            if not guardrails.allow_trade(eq, now=now):
                logger.info("Guardrails active - skipping iteration")
                time.sleep(interval_seconds)
                continue

        now_iso = datetime.now(timezone.utc).isoformat()
        logger.info("[%s] Iteration #%d", now_iso, iteration)

        def _iteration_body():
            for sym in symbols:
                signals = run_single_analysis(
                    sym,
                    timeframe,
                    live_limit,
                    sma_short,
                    sma_long,
                    strategy=strategy,
                    alert_mode=alert_mode,
                    exchange=exchange,
                    confluence_members=confluence_members,
                    confluence_required=confluence_required,
                    state_dir=state_dir,
                )
                metrics.SIGNALS_GENERATED.inc(len(signals))
                if not signals:
                    logger.info("No new signals for %s.", sym)
                    continue

                logger.info("✅ NEW SIGNALS for %s (%d)", sym, len(signals))

                for signal in signals[-3:]:  # show last few
                    ts = signal["timestamp"].isoformat()
                    action = signal["action"]
                    price = signal["price"]

                    if mark_signal_handled(
                        sym,
                        strategy,
                        timeframe,
                        ts,
                        action,
                        db_path=db_path,
                    ):
                        logger.info(
                            json.dumps(
                                {
                                    "symbol": sym,
                                    "action": action,
                                    "timestamp": ts,
                                    "status": "duplicate",
                                }
                            )
                        )
                        continue

                    # Determine quantity and equity
                    equity = portfolio.equity({sym: price}) if portfolio else 0
                    qty = trade_amount or 0.0
                    if not trade_amount and risk_config:
                        qty = calculate_position_size(
                            risk_config.position_sizing, price, equity
                        )

                    if guardrails and not guardrails.allow_trade(
                        equity, price=price, qty=qty
                    ):
                        logger.info("Guardrails blocked trade due to limits")
                        continue

                    logger.info(
                        "Processing signal: symbol=%s action=%s price=%.4f qty=%f strategy=%s",
                        sym,
                        action.upper(),
                        float(price),
                        qty,
                        signal.get("strategy", strategy),
                    )

                    # Execute trade
                    if live_trade and exchange:
                        order = execute_trade(exchange, sym, action, qty)
                        log_order_to_file(order, sym, state_dir)
                        logger.info(
                            json.dumps(
                                {
                                    "symbol": sym,
                                    "action": action,
                                    "price": price,
                                    "qty": qty,
                                    "strategy": signal.get("strategy", strategy),
                                    "timestamp": ts,
                                    "status": "placed",
                                }
                            )
                        )
                        metrics.TRADES_EXECUTED.inc()
                    else:
                        try:
                            if broker:
                                # Price update + broker order
                                broker.set_price(sym, price)
                                trade = broker.create_order(action, sym, qty)
                                trade["strategy"] = strategy
                                log_trade_to_db(trade, db_path=db_path)
                            elif portfolio:
                                if action == "buy":
                                    portfolio.buy(sym, qty, price, fee_bps=fee_bps)
                                else:
                                    portfolio.sell(sym, qty, price, fee_bps=fee_bps)
                            logger.info(
                                json.dumps(
                                    {
                                        "symbol": sym,
                                        "action": action,
                                        "price": price,
                                        "qty": qty,
                                        "strategy": signal.get("strategy", strategy),
                                        "timestamp": ts,
                                        "status": "executed",
                                    }
                                )
                            )
                            metrics.TRADES_EXECUTED.inc()
                        except ValueError:
                            logger.debug(
                                "Trade skipped due to portfolio/broker constraints"
                            )

                    if guardrails and qty > 0:
                        guardrails.record_trade(0)

        try:
            retry_policy.call(_iteration_body)
        except Exception:
            metrics.ERRORS_TOTAL.inc()
            logger.error("Error during live trading iteration", exc_info=True)

        if portfolio:
            metrics.PNL_GAUGE.set(portfolio.realized_pnl)

        logger.info("Next analysis in %d seconds...", interval_seconds)
        time.sleep(interval_seconds)


def main() -> None:
    args = parse_args()
    state_dir = args.state_dir or default_state_dir()
    setup_logging(level=args.log_level, state_dir=state_dir, json_logs=args.json_logs)
    config = get_config()
    configure_alerts(config)
    risk_config = get_risk_config(
        config.get("risk"), getattr(args, "risk_overrides", {})
    )

    symbol = args.symbol or config["symbol"]
    symbols = args.symbols.split(",") if getattr(args, "symbols", None) else [symbol]
    timeframe = args.timeframe or config["timeframe"]
    limit = args.limit or config["limit"]
    sma_short = getattr(args, "sma_short") or config["sma_short"]
    sma_long = getattr(args, "sma_long") or config["sma_long"]
    strategy_choice = getattr(args, "strategy", "sma")
    alert_mode = getattr(args, "alert_mode", False)
    interval_seconds = getattr(args, "interval_seconds", 60)

    confluence_cfg = config.get("confluence", {})
    confluence_meta = STRATEGY_REGISTRY["confluence"].metadata
    confluence_members = confluence_cfg.get(
        "members", confluence_meta.get("requires")
    )
    confluence_required = confluence_cfg.get(
        "required", confluence_meta.get("required_count")
    )

    os.makedirs(state_dir, exist_ok=True)
    api_key = args.api_key or config.get("api_key")
    api_secret = args.api_secret or config.get("api_secret")
    api_passphrase = args.api_passphrase or config.get("api_passphrase")
    trade_size = (
        args.trade_size
        if args.trade_size is not None
        else config.get("trade_size", 1.0)
    )
    broker_cfg = config.get("broker", {})
    fee_bps = (
        args.fee_bps if args.fee_bps is not None else broker_cfg.get("fees_bps", 0.0)
    )
    slippage_bps = broker_cfg.get("slippage_bps", 5.0)
    broker_type = getattr(args, "broker", None) or broker_cfg.get("type", "paper")
    exchange_name = args.exchange or config.get("exchange", "binance")

    # Exchange
    if api_key and api_secret:
        exchange = create_exchange(api_key, api_secret, api_passphrase, exchange_name)
    else:
        exchange = create_exchange(exchange_name=exchange_name)

    # Broker
    broker: Optional[Any] = None
    if broker_type == "paper":
        broker = PaperBroker(
            starting_cash=trade_size * 100 if trade_size else 0,
            fees_bps=fee_bps,
            slippage_bps=slippage_bps,
        )
    elif broker_type == "ccxt":
        broker = CcxtSpotBroker(
            exchange=exchange, fees_bps=fee_bps, dry_run=getattr(args, "dry_run", False)
        )

    # List strategies and exit
    if getattr(args, "list_strategies", False):
        logger.info("Available strategies:")
        for name, entry in STRATEGY_REGISTRY.items():
            meta = entry.metadata
            if meta:
                logger.info("- %s: %s", name, meta)
            else:
                logger.info("- %s", name)
        return

    if strategy_choice not in STRATEGY_REGISTRY:
        raise ValueError("Unknown strategy. Use --list-strategies to view options.")

    try:
        if getattr(args, "tune", False):
            if not args.backtest:
                raise ValueError("--backtest CSV path required for tuning")
            from trading_bot.tuner import tune

            results = tune(args.backtest, strategy=strategy_choice)
            logger.info("=== Tuning Results ===")
            for res in results:
                params_str = ", ".join(f"{k}={v}" for k, v in res["params"].items())
                logger.info(
                    f"{params_str} -> PnL {res['net_pnl']:.2f}, Win {res['win_rate']:.2f}%"
                )
            if results:
                logger.info("Best parameters: %s", results[0]["params"])
            return

        if getattr(args, "walk_forward", False):
            if not args.backtest:
                raise ValueError(
                    "--backtest CSV path required for walk-forward optimization"
                )
            from trading_bot.tuner import walk_forward_optimize

            train_size = getattr(args, "train_size", None) or 100
            test_size = getattr(args, "test_size", None) or 20
            results = walk_forward_optimize(
                args.backtest,
                strategy=strategy_choice,
                train_size=train_size,
                test_size=test_size,
            )
            logger.info("=== Walk-Forward Results ===")
            for res in results:
                params_str = ", ".join(
                    f"{k}={v}" for k, v in res["best_params"].items()
                )
                stats = res["test_stats"]
                logger.info(
                    f"{params_str} -> Test PnL {stats.get('net_pnl', 0.0):.2f}, "
                    f"Win {stats.get('win_rate', 0.0):.2f}%"
                )
            return

        if args.backtest:
            base = os.path.splitext(args.backtest)[0]
            equity_out = base + "_equity_curve.csv" if args.save_chart else None
            stats_out = base + "_summary_stats.json" if args.save_chart else None
            chart_out = base + "_equity_chart.png" if args.save_chart else None
            run_backtest(
                args.backtest,
                strategy=strategy_choice,
                sma_short=sma_short,
                sma_long=sma_long,
                plot=bool(chart_out),
                equity_out=equity_out,
                stats_out=stats_out,
                chart_out=chart_out,
                trade_size=trade_size,
                fees_bps=fee_bps,
            )
        elif args.live:
            run_live_mode(
                symbols,
                timeframe,
                sma_short,
                sma_long,
                strategy=strategy_choice,
                alert_mode=alert_mode,
                exchange=exchange,
                live_trade=args.live_trade,
                trade_amount=trade_size,
                fee_bps=fee_bps,
                risk_config=risk_config,
                interval_seconds=interval_seconds,
                broker=broker,
                confluence_members=confluence_members,
                confluence_required=confluence_required,
                state_dir=state_dir,
                metrics_port=args.metrics_port,
                health_port=args.health_port,
            )
        else:
            signals = run_single_analysis(
                symbol,
                timeframe,
                limit,
                sma_short,
                sma_long,
                strategy=strategy_choice,
                alert_mode=alert_mode,
                exchange=exchange,
                confluence_members=confluence_members,
                confluence_required=confluence_required,
                state_dir=state_dir,
            )

            logger.info("=== Trading Bot Results for %s ===", symbol)
            logger.info("Strategy: %s", strategy_choice.upper())
            logger.info("Total signals: %d", len(signals))
            if signals:
                logger.info("Last 5 signals:")
                for i, s in enumerate(signals[-5:], 1):
                    ts = s["timestamp"].isoformat()
                    logger.info(
                        "%d. %s - %s @ $%.2f", i, ts, s["action"].upper(), s["price"]
                    )
            else:
                logger.info("No trading signals generated.")
    except Exception:
        logger.exception("Error in main")
        raise


if __name__ == "__main__":
    main()
