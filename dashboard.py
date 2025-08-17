import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import json
import os
import logging
import sqlite3
import ccxt
import time
from typing import Optional
from trading_bot.exchange import create_exchange

from trading_bot.config import get_config
from trading_bot.signal_logger import (
    get_signals_from_db,
    log_signals_to_db,
    get_trades_from_db,
)
from trading_bot.data_fetch import fetch_market_data
from trading_bot.strategy import sma_strategy
from trading_bot.strategies import STRATEGY_REGISTRY, list_strategies
from trading_bot.performance import compute_equity_curve
from trading_bot.portfolio import Portfolio
from trading_bot.backtester import run_backtest
from dashboard.utils import calculate_naive_pnl, calculate_trades_pnl

logger = logging.getLogger(__name__)

config = get_config()
exchange_name = config.get("exchange", "binance")
exchange = create_exchange(exchange_name=exchange_name)

DEFAULT_STARTING_BALANCE = 10000.0
DEFAULT_SMA_SHORT = config.get("sma_short", 5)
DEFAULT_SMA_LONG = config.get("sma_long", 20)
DEFAULT_RSI_PERIOD = config.get("rsi_period", 14)
DEFAULT_RSI_LOWER = config.get("rsi_lower", 30)
DEFAULT_RSI_UPPER = config.get("rsi_upper", 70)
DEFAULT_MACD_FAST = config.get("macd_fast", 12)
DEFAULT_MACD_SLOW = config.get("macd_slow", 26)
DEFAULT_MACD_SIGNAL = config.get("macd_signal", 9)
DEFAULT_BBANDS_WINDOW = config.get("bbands_window", 20)
DEFAULT_BBANDS_STD = config.get("bbands_std", 2.0)

# Optional debug line in sidebar:
st.sidebar.markdown(f"**Exchange:** `{exchange_name}`")

st.sidebar.subheader("Theme")
theme_choice = st.sidebar.selectbox("Theme", ["dark", "light"], index=0)
if theme_choice != st.session_state.get('theme', 'dark'):
    st.session_state.theme = theme_choice
    st.info(f"Theme changed to {theme_choice}. Restart the app to apply changes.")

if 'auto_refresh' in st.session_state and st.session_state.auto_refresh:
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()

    refresh_interval = st.session_state.get('refresh_interval', 30)
    if time.time() - st.session_state.last_refresh > refresh_interval:
        st.session_state.last_refresh = time.time()
        st.rerun()


@st.cache_data(show_spinner=False)
def _fetch_price_data(symbol: str):
    return fetch_market_data(
        symbol=symbol,
        timeframe="1m",
        limit=500,
        exchange=exchange,
        exchange_name=exchange_name,  # not strictly needed since exchange is passed
    )


@st.cache_data(show_spinner=False)
def _add_indicators(
    df: pd.DataFrame,
    strategy: str,
    sma_short: Optional[int] = None,
    sma_long: Optional[int] = None,
    rsi_period: Optional[int] = None,
    lower_thresh: Optional[int] = None,
    upper_thresh: Optional[int] = None,
    macd_fast: Optional[int] = None,
    macd_slow: Optional[int] = None,
    macd_signal: Optional[int] = None,
    bbands_window: Optional[int] = None,
    bbands_std: Optional[float] = None,
):
    """Return copy of df with strategy-specific indicator columns."""
    df = df.copy()
    if sma_short and sma_long:
        df[f"sma_{sma_short}"] = df["close"].rolling(window=sma_short).mean()
        df[f"sma_{sma_long}"] = df["close"].rolling(window=sma_long).mean()

    if strategy == "rsi" and rsi_period:
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=rsi_period, min_periods=rsi_period).mean()
        avg_loss = loss.rolling(window=rsi_period, min_periods=rsi_period).mean()
        rs = avg_gain / avg_loss.replace(0, pd.NA)
        df["rsi"] = 100 - (100 / (1 + rs))
    elif strategy == "macd" and all([macd_fast, macd_slow, macd_signal]):
        df["ema_fast"] = df["close"].ewm(span=macd_fast, adjust=False).mean()
        df["ema_slow"] = df["close"].ewm(span=macd_slow, adjust=False).mean()
        df["macd"] = df["ema_fast"] - df["ema_slow"]
        df["signal_line"] = df["macd"].ewm(span=macd_signal, adjust=False).mean()
    elif strategy == "bbands" and all([bbands_window, bbands_std]):
        df["middle_band"] = df["close"].rolling(window=bbands_window).mean()
        df["std_dev"] = df["close"].rolling(window=bbands_window).std()
        df["upper_band"] = df["middle_band"] + bbands_std * df["std_dev"]
        df["lower_band"] = df["middle_band"] - bbands_std * df["std_dev"]
    return df


st.set_page_config(page_title="Trading Bot Dashboard", page_icon="??", layout="wide")

st.title("?? Trading Bot Dashboard")
st.markdown("Visualize trading signals and price data using SMA, RSI, MACD and Bollinger Bands strategies")

st.sidebar.header("Filters")

symbol_options = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "DOT/USDT", "SOL/USDT"]
selected_symbol = st.sidebar.selectbox("Symbol", symbol_options, index=0)

strategy_options = ["All"] + list_strategies()
selected_strategy = st.sidebar.selectbox("Strategy", strategy_options, index=0)

limit = st.sidebar.slider(
    "Number of signals to display",
    min_value=10,
    max_value=500,
    value=50,
    step=10,
)

# Starting balance for equity curve
starting_balance = st.sidebar.number_input(
    "Starting Balance (USDT)",
    min_value=100.0,
    value=DEFAULT_STARTING_BALANCE,
    step=100.0,
)

# Strategy specific parameters
sma_short = sma_long = None
rsi_period = lower_thresh = upper_thresh = None
macd_fast = macd_slow = macd_signal = None
bbands_window = bbands_std = None

if selected_strategy in ("All", "sma"):
    sma_short = st.sidebar.number_input("Short SMA Period", min_value=1, max_value=50, value=DEFAULT_SMA_SHORT)
    sma_long = st.sidebar.number_input("Long SMA Period", min_value=1, max_value=200, value=DEFAULT_SMA_LONG)
elif selected_strategy == "rsi":
    rsi_period = st.sidebar.number_input("RSI Period", min_value=2, max_value=100, value=DEFAULT_RSI_PERIOD)
    lower_thresh = st.sidebar.number_input("RSI Lower Threshold", min_value=1, max_value=100, value=DEFAULT_RSI_LOWER)
    upper_thresh = st.sidebar.number_input("RSI Upper Threshold", min_value=1, max_value=100, value=DEFAULT_RSI_UPPER)
elif selected_strategy == "macd":
    macd_fast = st.sidebar.number_input("MACD Fast Period", min_value=1, max_value=100, value=DEFAULT_MACD_FAST)
    macd_slow = st.sidebar.number_input("MACD Slow Period", min_value=1, max_value=200, value=DEFAULT_MACD_SLOW)
    macd_signal = st.sidebar.number_input("MACD Signal Period", min_value=1, max_value=100, value=DEFAULT_MACD_SIGNAL)
elif selected_strategy == "bbands":
    bbands_window = st.sidebar.number_input("Bollinger Window", min_value=1, max_value=200, value=DEFAULT_BBANDS_WINDOW)
    bbands_std = st.sidebar.number_input(
        "Bollinger Std Dev",
        min_value=0.5,
        max_value=5.0,
        value=DEFAULT_BBANDS_STD,
        step=0.1,
    )

st.sidebar.subheader("Trading Parameters")
trade_size = st.sidebar.number_input("Trade Size", min_value=0.1, value=1.0, step=0.1)
fee_bps = st.sidebar.number_input("Fee (bps)", min_value=0.0, value=0.0, step=0.1)

st.sidebar.subheader("Data Source")
try:
    csv_files = [f for f in os.listdir("artifacts/simulations") if f.endswith('.csv') and 'equity' not in f]
    if not csv_files:
        csv_files = ["summary.csv"]
    default_csv = csv_files[0] if csv_files else "summary.csv"
    data_file = st.sidebar.selectbox("CSV File", csv_files, index=0)
    data_path = f"artifacts/simulations/{data_file}"
except (FileNotFoundError, OSError):
    st.sidebar.warning("artifacts/simulations directory not found")
    data_file = st.sidebar.text_input("CSV File Path", value="data/sample.csv")
    data_path = data_file

st.sidebar.subheader("Refresh Settings")
auto_refresh = st.sidebar.checkbox("Auto-refresh")
refresh_interval = st.sidebar.number_input("Refresh Interval (seconds)", min_value=5, value=30, step=5)

st.session_state.auto_refresh = auto_refresh
st.session_state.refresh_interval = refresh_interval

col1, col2 = st.columns([2, 1])

with col1:
    strategy_title = selected_strategy.upper() if selected_strategy != "All" else "SMA"
    st.subheader(f"Price Chart with {strategy_title} Signals")

    def create_mock_data(symbol, limit=500):
        import numpy as np
        from datetime import datetime, timedelta, timezone

        base_price = 50000 if "BTC" in symbol else 3000
        timestamps = [datetime.now(timezone.utc) - timedelta(minutes=i) for i in range(limit, 0, -1)]

        prices = []
        current_price = base_price
        for _ in range(limit):
            change = np.random.normal(0, base_price * 0.001)
            current_price += change
            prices.append(current_price)

        return pd.DataFrame(
            {
                "timestamp": timestamps,
                "open": prices,
                "high": [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
                "low": [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
                "close": prices,
                "volume": [np.random.uniform(100, 1000) for _ in range(limit)],
            }
        )

    try:
        with st.spinner("Fetching price data..."):
            try:
                df = _fetch_price_data(selected_symbol)
            except (ccxt.BaseError, RuntimeError) as api_error:
                logger.exception("Price data fetch failed")
                st.warning(f"API unavailable ({str(api_error)[:50]}...), using mock data for demonstration")
                df = create_mock_data(selected_symbol, 500)

        if not df.empty:
            df_copy = _add_indicators(
                df,
                selected_strategy,
                sma_short=sma_short,
                sma_long=sma_long,
                rsi_period=rsi_period,
                lower_thresh=lower_thresh,
                upper_thresh=upper_thresh,
                macd_fast=macd_fast,
                macd_slow=macd_slow,
                macd_signal=macd_signal,
                bbands_window=bbands_window,
                bbands_std=bbands_std,
            )

            if selected_strategy == "All" or selected_strategy == "sma":
                if sma_short and sma_long:
                    signals = sma_strategy(df_copy, sma_short=sma_short, sma_long=sma_long)
                else:
                    signals = []
            else:
                # Be compatible whether STRATEGY_REGISTRY stores callables directly
                # or registry entries with a `.func` attribute.
                entry = STRATEGY_REGISTRY.get(selected_strategy, sma_strategy)
                strategy_fn = entry.func if hasattr(entry, "func") else entry

                if selected_strategy == "rsi" and all([rsi_period, lower_thresh, upper_thresh]):
                    signals = strategy_fn(
                        df_copy, period=rsi_period, lower_thresh=lower_thresh, upper_thresh=upper_thresh
                    )
                elif selected_strategy == "macd" and all([macd_fast, macd_slow, macd_signal]):
                    signals = strategy_fn(
                        df_copy, fast_period=macd_fast, slow_period=macd_slow, signal_period=macd_signal
                    )
                elif selected_strategy == "bbands" and all([bbands_window, bbands_std]):
                    signals = strategy_fn(df_copy, window=bbands_window, num_std=bbands_std)
                elif sma_short and sma_long:
                    signals = strategy_fn(df_copy, sma_short=sma_short, sma_long=sma_long)
                else:
                    signals = []

            if selected_strategy == "rsi":
                fig, (ax, ax_rsi) = plt.subplots(2, 1, sharex=True, figsize=(12, 8))  # type: ignore[misc]
                ax_rsi.plot(df_copy["timestamp"], df_copy["rsi"], label="RSI", color="purple")
                ax_rsi.axhline(lower_thresh, color="green", linestyle="--", label="Lower")
                ax_rsi.axhline(upper_thresh, color="red", linestyle="--", label="Upper")
                ax_rsi.set_ylabel("RSI")
                ax_rsi.set_ylim(0, 100)
                ax_rsi.legend()
            elif selected_strategy == "macd":
                fig, (ax, ax_macd) = plt.subplots(2, 1, sharex=True, figsize=(12, 8))  # type: ignore[misc]
                ax_macd.plot(df_copy["timestamp"], df_copy["macd"], label="MACD", color="blue")
                ax_macd.plot(df_copy["timestamp"], df_copy["signal_line"], label="Signal", color="orange")
                hist = df_copy["macd"] - df_copy["signal_line"]
                ax_macd.bar(df_copy["timestamp"], hist, label="Histogram", color="gray", alpha=0.3)
                ax_macd.set_ylabel("MACD")
                ax_macd.legend()
            else:
                fig, ax = plt.subplots(figsize=(12, 6))

            ax.plot(df_copy["timestamp"], df_copy["close"], label="Price", color="black", linewidth=1)

            if sma_short and sma_long:
                ax.plot(
                    df_copy["timestamp"], df_copy[f"sma_{sma_short}"], label=f"SMA {sma_short}", color="blue", alpha=0.7
                )
                ax.plot(
                    df_copy["timestamp"], df_copy[f"sma_{sma_long}"], label=f"SMA {sma_long}", color="red", alpha=0.7
                )

            if selected_strategy == "bbands":
                ax.plot(df_copy["timestamp"], df_copy["upper_band"], label="Upper Band", color="orange", alpha=0.6)
                ax.plot(df_copy["timestamp"], df_copy["middle_band"], label="Middle Band", color="green", alpha=0.6)
                ax.plot(df_copy["timestamp"], df_copy["lower_band"], label="Lower Band", color="orange", alpha=0.6)

            for signal in signals:
                color = "green" if signal["action"] == "buy" else "red"
                marker = "^" if signal["action"] == "buy" else "v"
                ax.scatter(signal["timestamp"], signal["price"], color=color, marker=marker, s=100, alpha=0.8, zorder=5)

            ax.set_xlabel("Time")
            ax.set_ylabel("Price (USDT)")
            title_strategy = selected_strategy.upper() if selected_strategy != "All" else "SMA"
            ax.set_title(f"{selected_symbol} Price with {title_strategy} Signals")
            ax.legend()
            ax.grid(True, alpha=0.3)

            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
            plt.xticks(rotation=45)

            plt.tight_layout()
            st.pyplot(fig)

            st.subheader("Equity Curve")

            if st.button("Run Backtest") or auto_refresh:
                try:
                    # Prepare strategy parameters
                    strategy_params = {}
                    strategy_name = selected_strategy if selected_strategy != "All" else "sma"
                    if strategy_name == "sma":
                        strategy_params = {"sma_short": sma_short, "sma_long": sma_long}
                    elif strategy_name == "rsi":
                        strategy_params = {"period": rsi_period, "lower_thresh": lower_thresh, "upper_thresh": upper_thresh}
                    elif strategy_name == "macd":
                        strategy_params = {"fast_period": macd_fast, "slow_period": macd_slow, "signal_period": macd_signal}
                    elif strategy_name == "bbands":
                        strategy_params = {"window": bbands_window, "num_std": bbands_std}

                    if os.path.exists(data_path):
                        stats = run_backtest(
                            data_path,
                            strategy=strategy_name,
                            trade_size=trade_size,
                            fees_bps=fee_bps,
                            **strategy_params
                        )

                        col_a, col_b, col_c = st.columns(3)
                        col_a.metric("Net P&L", f"${stats['net_pnl']:,.2f}")
                        col_b.metric("Win Rate", f"{stats['win_rate']:.1f}%")
                        col_c.metric("Max Drawdown", f"{stats['max_drawdown']:.1f}%")

                        st.success("Backtest completed successfully!")
                    else:
                        st.error(f"Data file not found: {data_path}")
                except Exception as e:
                    st.error(f"Backtest failed: {str(e)}")
            else:
                # Fallback: Show equity curve from stored signals
                db_strategy = None if selected_strategy == "All" else selected_strategy
                db_signals = get_signals_from_db(symbol=selected_symbol, strategy_id=db_strategy, limit=None)
                eq_df, stats = compute_equity_curve(
                    [
                        {
                            "timestamp": pd.to_datetime(s[0], utc=True),
                            "action": s[1],
                            "price": s[2],
                        }
                        for s in reversed(db_signals)
                    ],
                    initial_balance=starting_balance,
                )

                if not eq_df.empty:
                    fig_eq, ax_eq = plt.subplots(figsize=(12, 4))
                    ax_eq.plot(eq_df["timestamp"], eq_df["equity"], color="purple")
                    ax_eq.set_xlabel("Time")
                    ax_eq.set_ylabel("Equity (USDT)")
                    ax_eq.set_title("Equity Curve (from stored signals)")
                    ax_eq.grid(True, alpha=0.3)
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    st.pyplot(fig_eq)

                    col_a, col_b, col_c, col_d, col_e = st.columns(5)
                    col_a.metric(
                        "Total PnL",
                        f"${stats['total_return_abs']:,.2f}",
                    )
                    col_b.metric(
                        "Return %",
                        f"{stats['total_return_pct']:.2f}%",
                    )
                    col_c.metric("Trades", stats["num_trades"])
                    col_d.metric(
                        "Win Rate",
                        f"{stats['win_rate']:.2f}%",
                    )
                    col_e.metric(
                        "Max Drawdown",
                        f"{stats['max_drawdown']:.2f}%",
                    )
                else:
                    st.info("No signals available for equity curve. Click 'Run Backtest' to generate new equity curve.")

            if signals:
                st.success(f"Generated {len(signals)} signals from current data")
                if st.button("Save Signals to Database"):
                    try:
                        strategy_id = selected_strategy if selected_strategy != "All" else "sma"
                        log_signals_to_db(signals, selected_symbol, strategy_id)
                        st.success(f"Saved {len(signals)} signals to database!")
                        st.rerun()
                    except sqlite3.Error as e:
                        logger.exception("Error saving signals to database")
                        st.error(f"Error saving signals: {str(e)}")
            else:
                st.info("No crossover signals detected in current data")
        else:
            st.error("Failed to fetch price data")
    except Exception as e:  # Catch-all to prevent dashboard crash
        logger.exception("Error fetching or processing data")
        st.error(f"Error fetching or processing data: {str(e)}")

with col2:
    st.subheader("Live Status")
    try:
        latest_trade = get_trades_from_db(limit=1)
        if latest_trade:
            last_ts = pd.to_datetime(latest_trade[0][0], utc=True)
            st.metric("Last Trade", last_ts.strftime("%Y-%m-%d %H:%M:%S%z"))
        else:
            st.metric("Last Trade", "No trades")
    except sqlite3.Error as e:
        logger.exception("Error loading last trade")
        st.error(f"Error loading last trade: {str(e)}")

    status_file = "status.json"
    if os.path.exists(status_file):
        try:
            with open(status_file) as sf:
                status = json.load(sf)
            hb = status.get("heartbeat")
            last_loop = status.get("last_loop")
            if hb:
                st.metric("Heartbeat", hb)
            if last_loop:
                st.metric("Last Loop", last_loop)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Error reading status file: %s", exc)

    risk_cfg = config.get("risk", {})
    md = risk_cfg.get("max_drawdown", {}).get("monthly_pct", 0.0)
    cooldown = risk_cfg.get("max_drawdown", {}).get("cooldown_bars", 0)
    if md or cooldown:
        st.info(f"Guardrails active: max DD {md * 100:.1f}% | cooldown {cooldown}")
    else:
        st.info("Guardrails disabled")

    st.subheader("Live Signals & P&L")

    @st.cache_data(ttl=refresh_interval if auto_refresh else 300)
    def get_cached_signals(symbol, strategy, limit):
        return get_signals_from_db(symbol=symbol, strategy_id=strategy, limit=limit)

    @st.cache_data(ttl=refresh_interval if auto_refresh else 300)
    def get_cached_trades(symbol, limit):
        return get_trades_from_db(symbol=symbol, limit=limit)

    strategy_filter = None if selected_strategy == "All" else selected_strategy
    recent_signals = get_cached_signals(selected_symbol, strategy_filter, 20)
    if recent_signals:
        signals_df = pd.DataFrame(recent_signals, columns=['timestamp', 'action', 'price', 'symbol', 'strategy'])
        signals_df['timestamp'] = pd.to_datetime(signals_df['timestamp'])
        st.dataframe(signals_df, use_container_width=True)
    else:
        st.info("No signals found in database")

    st.subheader("P&L Summary")
    trades = get_cached_trades(selected_symbol, 100)
    if trades:
        pnl_data = calculate_trades_pnl(trades)
        col_p1, col_p2, col_p3 = st.columns(3)
        col_p1.metric("Realized P&L", f"${pnl_data['realized_pnl']:,.2f}")
        col_p2.metric("Total Trades", pnl_data['total_trades'])
        col_p3.metric("Open Position", f"{pnl_data['open_position']:.2f}")
    else:
        if recent_signals:
            naive_pnl = calculate_naive_pnl(recent_signals)
            st.metric("Naive P&L (from signals)", f"${naive_pnl:,.2f}")
            st.info("Using naive P&L calculation from signals (no trades table data)")
        else:
            st.info("No P&L data available")

    st.subheader("Recent Signals")
    try:
        strategy_filter = None if selected_strategy == "All" else selected_strategy

        signals_data = get_signals_from_db(
            symbol=selected_symbol,
            strategy_id=strategy_filter,
            limit=limit,
        )

        if signals_data:
            signals_df = pd.DataFrame(
                signals_data,
                columns=["Timestamp", "Action", "Price", "Symbol", "Strategy"],
            )

            signals_df["Price"] = signals_df["Price"].apply(lambda x: f"${x:,.2f}")
            signals_df["Timestamp"] = pd.to_datetime(signals_df["Timestamp"], utc=True)
            signals_df["Timestamp"] = signals_df["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S%z")

            def highlight_action(row):
                if row["Action"].lower() == "buy":
                    return ["background-color: lightgreen" if col == "Action" else "" for col in row.index]
                elif row["Action"].lower() == "sell":
                    return ["background-color: lightcoral" if col == "Action" else "" for col in row.index]
                return ["" for col in row.index]

            styled_df = signals_df.style.apply(highlight_action, axis=1)

            st.dataframe(styled_df, use_container_width=True, height=400)

            st.metric("Total Signals", len(signals_data))

            buy_signals = sum(1 for signal in signals_data if signal[1] == "buy")
            sell_signals = len(signals_data) - buy_signals

            col_buy, col_sell = st.columns(2)
            with col_buy:
                st.metric("Buy Signals", buy_signals)
            with col_sell:
                st.metric("Sell Signals", sell_signals)

        else:
            st.info("No signals found in database")
            st.markdown("**To generate signals:**")
            st.code("python trading_bot/main.py", language="bash")

    except sqlite3.Error as e:
        logger.exception("Error loading signals from database")
        st.error(f"Error loading signals: {str(e)}")

    st.subheader("Recent Trades")
    try:
        trades_data = get_trades_from_db(symbol=selected_symbol, limit=limit)
        if trades_data:
            trades_df = pd.DataFrame(
                trades_data,
                columns=[
                    "Timestamp",
                    "Symbol",
                    "Side",
                    "Qty",
                    "Price",
                    "Fee",
                    "Strategy",
                    "Broker",
                ],
            )
            trades_df["Timestamp"] = pd.to_datetime(trades_df["Timestamp"], utc=True)
            display_df = trades_df.copy()
            display_df["Price"] = display_df["Price"].apply(lambda x: f"${x:,.2f}")
            display_df["Timestamp"] = display_df["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S%z")
            st.dataframe(display_df, use_container_width=True, height=300)

            portfolio = Portfolio(cash=starting_balance)
            history = []
            for row in trades_df.sort_values("Timestamp").itertuples():
                price = float(row.Price)
                qty = float(row.Qty)
                ts = row.Timestamp
                side = row.Side.lower()
                sym = row.Symbol
                try:
                    if side == "buy":
                        portfolio.buy(sym, qty, price, fee_bps=config.get("broker", {}).get("fees_bps", 0))
                    else:
                        portfolio.sell(sym, qty, price, fee_bps=config.get("broker", {}).get("fees_bps", 0))
                except ValueError as exc:
                    logger.warning("Skipping trade %s %s due to error: %s", side, sym, exc)
                history.append({"timestamp": ts, "equity": portfolio.equity({sym: price})})

            if history:
                eq_df = pd.DataFrame(history)
                st.line_chart(eq_df.set_index("timestamp")["equity"])

            if portfolio.positions:
                pos_rows = []
                for sym, pos in portfolio.positions.items():
                    current_price = None
                    try:
                        ticker = exchange.fetch_ticker(sym)
                        current_price = ticker.get("last") or ticker.get("close")
                    except Exception as exc:  # pragma: no cover - best effort only
                        logger.warning("Error fetching price for %s: %s", sym, exc)
                    if current_price is not None:
                        pnl = (current_price - pos.avg_cost) * pos.qty
                        pnl_pct = ((current_price / pos.avg_cost) - 1) * 100
                    else:
                        pnl = pnl_pct = None
                    pos_rows.append(
                        {
                            "Symbol": sym,
                            "Qty": pos.qty,
                            "Avg Cost": pos.avg_cost,
                            "Last Price": current_price,
                            "Unrealized PnL": pnl,
                            "Unrealized PnL %": pnl_pct,
                            "Stop Loss": pos.stop_loss,
                            "Take Profit": pos.take_profit,
                        }
                    )
                st.subheader("Open Positions")
                df_pos = pd.DataFrame(pos_rows)
                if not df_pos.empty:
                    for col in ["Avg Cost", "Last Price", "Unrealized PnL"]:
                        df_pos[col] = df_pos[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "N/A")
                    df_pos["Unrealized PnL %"] = df_pos["Unrealized PnL %"].apply(
                        lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A"
                    )
                st.dataframe(df_pos, use_container_width=True)
        else:
            st.info("No trades found in database")
    except sqlite3.Error as e:
        logger.exception("Error loading trades from database")
        st.error(f"Error loading trades: {str(e)}")

    st.subheader("Error Log")
    log_path = "trading_bot.log"
    if os.path.exists(log_path):
        with open(log_path) as f:
            lines = f.readlines()[-50:]
        st.text("".join(lines))
    else:
        st.info("No log file found")

with st.expander("Parameters Snapshot"):
    st.write("**Current Configuration:**")
    st.write(f"- Strategy: {selected_strategy}")
    st.write(f"- Symbol: {selected_symbol}")
    st.write(f"- Data Source: {data_path}")
    st.write(f"- Trade Size: {trade_size}")
    st.write(f"- Fees: {fee_bps} bps")
    st.write(f"- Starting Balance: ${starting_balance:,.2f}")

    if selected_strategy == "sma" or selected_strategy == "All":
        st.write(f"- SMA Short: {sma_short}, SMA Long: {sma_long}")
    elif selected_strategy == "rsi":
        st.write(f"- RSI Period: {rsi_period}, Lower: {lower_thresh}, Upper: {upper_thresh}")
    elif selected_strategy == "macd":
        st.write(f"- MACD Fast: {macd_fast}, Slow: {macd_slow}, Signal: {macd_signal}")
    elif selected_strategy == "bbands":
        st.write(f"- Bollinger Window: {bbands_window}, Std Dev: {bbands_std}")

    st.write(f"- Auto-refresh: {auto_refresh}")
    if auto_refresh:
        st.write(f"- Refresh Interval: {refresh_interval}s")

st.markdown("---")
st.markdown("**Note:** Run the trading bot to generate signals that will appear in this dashboard.")
st.code("python trading_bot/main.py --symbol BTC/USDT", language="bash")
