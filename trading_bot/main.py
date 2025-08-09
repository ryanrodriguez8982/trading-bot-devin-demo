import logging
import json
import argparse
import os
import time
import signal as sig
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Dict

# ? Absolute imports for package context
from trading_bot.backtester import run_backtest
from trading_bot.data_fetch import fetch_btc_usdt_data
from trading_bot.exchange import create_exchange, execute_trade
from trading_bot.signal_logger import log_signals_to_db, mark_signal_handled
from trading_bot.signal_logger import log_signals_to_db, log_trade_to_db
from trading_bot.portfolio import Portfolio
from trading_bot.risk.position_sizing import calculate_position_size
from trading_bot.broker import PaperBroker
from trading_bot.strategies import STRATEGY_REGISTRY, list_strategies

try:
    from plyer import notification
except Exception:
    notification = None

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning("config.json not found, using default values")
        return {
            "symbol": "BTC/USDT",
            "timeframe": "1m",
            "limit": 500,
            "sma_short": 5,
            "sma_long": 20
        }


def parse_args():
    parser = argparse.ArgumentParser(description='Crypto Trading Bot')
    parser.add_argument(
        "--exchange",
        type=str,
        default=None,
        help="Specify exchange to use (e.g., binance, coinbase, kraken). Overrides config.json.",
    )
    try:
        pkg_version = version('trading-bot')
    except PackageNotFoundError:
        try:
            from trading_bot import __version__ as pkg_version
        except Exception:
            pkg_version = '0.0.0'

    parser.add_argument('--version', action='version', version=f'%(prog)s {pkg_version}')
    parser.add_argument('--symbol', type=str, help='Trading pair symbol (e.g., BTC/USDT)')
    parser.add_argument('--timeframe', type=str, help='Timeframe for candles (e.g., 1m, 5m)')
    parser.add_argument('--limit', type=int, help='Number of candles to fetch')
    parser.add_argument('--sma-short', type=int, help='Short-period SMA window')
    parser.add_argument('--sma-long', type=int, help='Long-period SMA window')
    parser.add_argument('--live', action='store_true', help='Enable live trading simulation mode')
    parser.add_argument('--live-trade', action='store_true', help='Execute real orders when in live mode')
    parser.add_argument('--api-key', type=str, help='Exchange API key')
    parser.add_argument('--api-secret', type=str, help='Exchange API secret')
    parser.add_argument('--api-passphrase', type=str, help='Exchange API passphrase (if required)')
    parser.add_argument('--broker', type=str, help='Broker type to use (paper or ccxt)')
    parser.add_argument('--strategy', type=str, default='sma', help='Trading strategy to use')
    parser.add_argument('--list-strategies', action='store_true', help='List available strategies and exit')
    parser.add_argument('--alert-mode', action='store_true', help='Enable alert notifications for BUY/SELL signals')
    parser.add_argument('--backtest', type=str, help='Path to CSV file for historical backtesting')
    parser.add_argument('--tune', action='store_true', help='Run parameter tuning over a range of values')
    parser.add_argument('--optimize', nargs='*', help='Run grid search optimization with validation split')
    parser.add_argument('--save-chart', action='store_true', help='Save equity curve CSV/JSON and chart during backtest')
    parser.add_argument('--trade-size', type=float, default=None,
                        help='Default trade size in asset units')
    parser.add_argument('--fee-bps', type=float, default=None,
                        help='Trading fee in basis points')
    parser.add_argument('--position-sizing', type=str, choices=['fixed_fraction', 'fixed_cash'],
                        help='Position sizing mode')
    parser.add_argument('--fixed-fraction', type=float,
                        help='Fraction of equity to use per trade')
    parser.add_argument('--fixed-cash', type=float,
                        help='Fixed cash amount to use per trade')
    parser.add_argument(
        '--interval-seconds',
        type=int,
        default=60,
        help='Polling interval for live mode in seconds',
    )
    parser.add_argument(
        '--symbols',
        type=str,
        help='Comma-separated list of trading symbols for live mode',
    )
    parser.add_argument('--risk-profile', type=str, help='Risk profile name')
    args, unknown = parser.parse_known_args()

    risk_overrides = {}
    it = iter(unknown)
    for token in it:
        if token.startswith('--risk.'):
            key = token[2 + len('risk.') :]
            value = next(it, None)
            if value is None:
                raise SystemExit(f"Missing value for {token}")
            risk_overrides[key] = value
    if getattr(args, 'position_sizing', None):
        risk_overrides['position_sizing.mode'] = args.position_sizing
    if getattr(args, 'fixed_fraction', None) is not None:
        risk_overrides['position_sizing.fraction_of_equity'] = args.fixed_fraction
    if getattr(args, 'fixed_cash', None) is not None:
        risk_overrides['position_sizing.fixed_cash_amount'] = args.fixed_cash
    setattr(args, 'risk_overrides', risk_overrides)
    return args


def log_signals_to_file(signals, symbol):
    if not signals:
        return
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(logs_dir, f"{timestamp}_signals.log")
    with open(log_path, 'w') as f:
        f.write(f"Trading Signals Log - {symbol}\n")
        f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n")
        for signal in signals:
            ts = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"{ts} | {signal['action'].upper()} | {symbol} | ${signal['price']:.2f}\n")
    logging.info(f"Logged {len(signals)} signals to {log_path}")

def log_order_to_file(order, symbol):
    if not order:
        return
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, 'orders.log')
    with open(log_path, 'a') as f:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        order_id = order.get('id', 'N/A')
        amount = order.get('amount')
        price = order.get('price')
        side = order.get('side')
        f.write(f"{ts} | {order_id} | {side} | {symbol} | {amount} @ {price}\n")
    logging.info(f"Logged order {order_id} to {log_path}")

def send_alert(signal):
    ts = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    message = f"ALERT: {signal['action'].upper()} at {ts} price ${signal['price']:.2f}"
    print(message)
    if notification:
        try:
            notification.notify(title="Trading Bot Alert", message=message)
        except Exception as e:
            logging.debug(f"Notification error: {e}")

def signal_handler(signum, frame):
    logging.info("Received interrupt signal. Shutting down live trading mode gracefully...")
    print("\n=== Live Trading Mode Shutdown ===")
    sys.exit(0)

def run_single_analysis(
    symbol,
    timeframe,
    limit,
    sma_short,
    sma_long,
    strategy="sma",
    alert_mode=False,
    exchange=None,
    confluence_members=None,
    confluence_required=2,
):
    try:
        if strategy not in STRATEGY_REGISTRY:
            raise ValueError("Unknown strategy. Use --list-strategies to view options.")

        if exchange:
            data = fetch_btc_usdt_data(symbol, timeframe, limit, exchange=exchange)
        else:
            data = fetch_btc_usdt_data(symbol, timeframe, limit)
        logging.info(f"Fetched {len(data)} data points")

        strategy_fn = STRATEGY_REGISTRY[strategy]
        if strategy == "rsi":
            signals = strategy_fn(data, period=14)
        elif strategy == "macd":
            signals = strategy_fn(data)
        elif strategy == "bbands":
            signals = strategy_fn(data, window=sma_long, num_std=2)
        elif strategy == "confluence":
            signals = strategy_fn(
                data,
                members=confluence_members,
                required=confluence_required,
            )
        else:
            signals = strategy_fn(data, sma_short, sma_long)

        logging.info(f"Generated {len(signals)} trading signals")
        if signals:
            log_signals_to_file(signals, symbol)
            log_signals_to_db(signals, symbol)
            if alert_mode:
                for s in signals:
                    send_alert(s)
        return signals
    except Exception as e:
        logging.error(f"Error in analysis cycle: {e}")
        return []

def run_live_mode(
    symbols,
    timeframe,
    sma_short,
    sma_long,
    strategy="sma",
    alert_mode=False,
    exchange=None,
    live_trade=False,
    trade_amount=0.0,
    fee_bps=0.0,
    risk_config=None,
    interval_seconds=60,
    broker=None,
    confluence_members=None,
    confluence_required=2,
):
    live_limit = 25
    sig.signal(sig.SIGINT, signal_handler)
    if strategy not in STRATEGY_REGISTRY:
        raise ValueError("Unknown strategy. Use --list-strategies to view options.")

    print(f"\n=== Live Trading Mode Started ===")
    print(f"Symbols: {', '.join(symbols)}")
    print(f"Strategy: {strategy.upper()}")
    print(f"Fetching {live_limit} candles every {interval_seconds} seconds")
    print("Press Ctrl+C to stop gracefully")
    print("=" * 50)

    iteration = 0
    portfolio = None
    if broker is None:
        portfolio = Portfolio(cash=trade_amount * 100 if trade_amount else 0)

    guardrails = None
    if risk_config is not None:
        md_cfg = getattr(risk_config, "max_drawdown", None)
        if md_cfg and (md_cfg.monthly_pct > 0 or md_cfg.cooldown_bars > 0):
            from trading_bot.risk.guardrails import Guardrails

            guardrails = Guardrails(
                max_dd_pct=md_cfg.monthly_pct,
                cooldown_minutes=md_cfg.cooldown_bars,
            )
            if portfolio:
                guardrails.reset_month(portfolio.equity())

    while True:
        iteration += 1
        if guardrails and portfolio and not guardrails.allow_trade(
            portfolio.equity()
        ):
            logging.info("Guardrails active - skipping iteration")
            time.sleep(interval_seconds)
            continue

        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iteration #{iteration}")
        for symbol in symbols:
            signals = run_single_analysis(
                symbol,
                timeframe,
                live_limit,
                sma_short,
                sma_long,
                strategy=strategy,
                alert_mode=alert_mode,
                exchange=exchange,
                confluence_members=confluence_members,
                confluence_required=confluence_required,
            )
            if signals:
                print(f"?? NEW SIGNALS for {symbol} ({len(signals)}):")
                for signal in signals[-3:]:
                    ts = signal["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
                    if mark_signal_handled(
                        symbol,
                        strategy,
                        timeframe,
                        signal["timestamp"].isoformat(),
                        signal["action"],
                    ):
                        logging.info(
                            json.dumps(
                                {
                                    "symbol": symbol,
                                    "action": signal["action"],
                                    "timestamp": signal["timestamp"].isoformat(),
                                    "status": "duplicate",
                                }
                            )
                        )
                        continue
                    print(
                        f"  {ts} - {signal['action'].upper()} at ${signal['price']:.2f}"
                    )
                    if live_trade and exchange:
                        order = execute_trade(exchange, symbol, signal["action"], trade_amount)
                        log_order_to_file(order, symbol)
                        logging.info(
                            json.dumps(
                                {
                                    "symbol": symbol,
                                    "action": signal["action"],
                                    "timestamp": signal["timestamp"].isoformat(),
                                    "status": "placed",
                                }
                            )
                        )
                    else:
                        try:
                            if signal["action"] == "buy":
                                portfolio.buy(symbol, trade_amount, signal["price"], fee_bps=fee_bps)
                            else:
                                portfolio.sell(symbol, trade_amount, signal["price"], fee_bps=fee_bps)
                            logging.info(
                                json.dumps(
                                    {
                                        "symbol": symbol,
                                        "action": signal["action"],
                                        "timestamp": signal["timestamp"].isoformat(),
                                        "status": "executed",
                                    }
                                )
                            )
                        except ValueError:
                            logging.debug("Trade skipped due to portfolio constraints")
            else:
                print(f"No new signals for {symbol}.")
        print(f"Next analysis in {interval_seconds} seconds...")
        time.sleep(interval_seconds)
        signals = run_single_analysis(
            symbol,
            timeframe,
            live_limit,
            sma_short,
            sma_long,
            strategy=strategy,
            alert_mode=alert_mode,
            exchange=exchange,
            confluence_members=confluence_members,
            confluence_required=confluence_required,
        )
        if signals:
            print(f"?? NEW SIGNALS ({len(signals)}):")
            for signal in signals[-3:]:
                ts = signal['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                print(f"  {ts} - {signal['action'].upper()} at ${signal['price']:.2f}")
                price = signal['price']
                if trade_amount:
                    qty = trade_amount
                elif risk_config:
                    equity = portfolio.equity({symbol: price})
                    qty = calculate_position_size(
                        risk_config.position_sizing, price, equity
                    )
                else:
                    qty = 0
                if qty <= 0:
                    continue
                if live_trade and exchange:
                    order = execute_trade(exchange, symbol, signal['action'], qty)
                    log_order_to_file(order, symbol)
                else:
                    try:
                        if signal['action'] == 'buy':
                            portfolio.buy(symbol, qty, price, fee_bps=fee_bps)
                        else:
                            portfolio.sell(symbol, qty, price, fee_bps=fee_bps)
                        if broker:
                            broker.set_price(symbol, signal['price'])
                            trade = broker.create_order(signal['action'], symbol, trade_amount)
                            trade['strategy'] = strategy
                            log_trade_to_db(trade)
                        else:
                            if signal['action'] == 'buy':
                                portfolio.buy(symbol, trade_amount, signal['price'], fee_bps=fee_bps)
                            else:
                                portfolio.sell(symbol, trade_amount, signal['price'], fee_bps=fee_bps)
                    except ValueError:
                        logging.debug("Trade skipped due to portfolio/broker constraints")
        else:
            print("No new signals.")
        print("Next analysis in 60 seconds...")
        time.sleep(60)

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    config = load_config()
    args = parse_args()
    risk_config = get_risk_config(config.get('risk'), getattr(args, 'risk_overrides', {}))

    symbol = args.symbol or config['symbol']
    symbols = args.symbols.split(',') if getattr(args, 'symbols', None) else [symbol]
    timeframe = args.timeframe or config['timeframe']
    limit = args.limit or config['limit']
    sma_short = getattr(args, 'sma_short') or config['sma_short']
    sma_long = getattr(args, 'sma_long') or config['sma_long']
    strategy_choice = getattr(args, 'strategy', 'sma')
    alert_mode = getattr(args, 'alert_mode', False)
    interval_seconds = getattr(args, 'interval_seconds', 60)

    confluence_cfg = config.get("confluence", {})
    confluence_members = confluence_cfg.get("members", ["sma", "rsi", "macd"])
    confluence_required = confluence_cfg.get("required", 2)

    api_key = args.api_key or os.getenv('TRADING_BOT_API_KEY') or config.get('api_key')
    api_secret = args.api_secret or os.getenv('TRADING_BOT_API_SECRET') or config.get('api_secret')
    api_passphrase = args.api_passphrase or os.getenv('TRADING_BOT_API_PASSPHRASE') or config.get('api_passphrase')
    trade_size = args.trade_size if args.trade_size is not None else config.get('trade_size', 1.0)
    broker_cfg = config.get('broker', {})
    fee_bps = args.fee_bps if args.fee_bps is not None else broker_cfg.get('fees_bps', config.get('fee_bps', 0.0))
    slippage_bps = broker_cfg.get('slippage_bps', 5.0)
    broker_type = getattr(args, 'broker', None) or broker_cfg.get('type', 'paper')
    exchange_name = args.exchange or config.get("exchange", "binance")
    exchange = None

    if api_key and api_secret:
        exchange = create_exchange(api_key, api_secret, api_passphrase, exchange_name)
    else:
        exchange = create_exchange(exchange_name=exchange_name)
    broker = None
    if broker_type == 'paper':
        broker = PaperBroker(starting_cash=trade_size * 100 if trade_size else 0,
                             fees_bps=fee_bps,
                             slippage_bps=slippage_bps)

    if getattr(args, 'list_strategies', False):
        print("Available strategies:")
        for name in list_strategies():
            print(f"- {name}")
        return

    if strategy_choice not in STRATEGY_REGISTRY:
        raise ValueError("Unknown strategy. Use --list-strategies to view options.")

    try:
        if getattr(args, 'optimize', None):
            if not args.backtest:
                raise ValueError("--backtest CSV path required for optimization")
            from trading_bot.backtest.optimizer import parse_optimize_args, optimize
            opt_opts = parse_optimize_args(args.optimize)
            base = os.path.splitext(args.backtest)[0]
            results_csv = base + '_opt_results.csv'
            best_json = base + '_best_params.json'
            optimize(
                args.backtest,
                strategy=opt_opts['strategy'],
                param_grid=opt_opts['param_grid'],
                split=opt_opts['split'],
                metric=opt_opts['metric'],
                results_csv=results_csv,
                best_json=best_json,
            )
            print(f"Optimization results saved to {results_csv}")
            print(f"Best parameters saved to {best_json}")
            return
        if getattr(args, 'tune', False):
            if not args.backtest:
                raise ValueError("--backtest CSV path required for tuning")
            from trading_bot.tuner import tune
            results = tune(args.backtest, strategy=strategy_choice)
            print("=== Tuning Results ===")
            for res in results:
                params_str = ", ".join(f"{k}={v}" for k, v in res['params'].items())
                print(f"{params_str} -> PnL {res['net_pnl']:.2f}, Win "
                      f"{res['win_rate']:.2f}%")
            if results:
                print(f"Best parameters: {results[0]['params']}")
            return
        if args.backtest:
            base = os.path.splitext(args.backtest)[0]
            equity_out = base + '_equity_curve.csv' if args.save_chart else None
            stats_out = base + '_summary_stats.json' if args.save_chart else None
            chart_out = base + '_equity_chart.png' if args.save_chart else None
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
                fee_bps=fee_bps,
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
            )

            print(f"\n=== Trading Bot Results for {symbol} ===")
            print(f"Strategy: {strategy_choice.upper()}")
            print(f"Total signals: {len(signals)}")
            if signals:
                print("\nLast 5 signals:")
                for i, s in enumerate(signals[-5:], 1):
                    ts = s['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{i}. {ts} - {s['action'].upper()} @ ${s['price']:.2f}")
            else:
                print("No trading signals generated.")
    except Exception as e:
        logging.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main()
