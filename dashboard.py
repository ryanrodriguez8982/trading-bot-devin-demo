import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from trading_bot.signal_logger import get_signals_from_db, log_signals_to_db
from trading_bot.data_fetch import fetch_btc_usdt_data
from trading_bot.strategy import sma_crossover_strategy
from trading_bot.strategies import STRATEGY_REGISTRY, list_strategies

st.set_page_config(
    page_title="Trading Bot Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Trading Bot Dashboard")
st.markdown(
    "Visualize trading signals and price data using SMA, RSI, MACD and "
    "Bollinger strategies"
)

st.sidebar.header("Filters")

symbol_options = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "DOT/USDT", "SOL/USDT"]
selected_symbol = st.sidebar.selectbox("Symbol", symbol_options, index=0)

strategy_options = ["All"] + list_strategies()
selected_strategy = st.sidebar.selectbox("Strategy", strategy_options, index=0)

limit = st.sidebar.slider("Number of signals to display", min_value=10,
                          max_value=500, value=50, step=10)

# Strategy specific parameters
sma_short = sma_long = None
rsi_period = lower_thresh = upper_thresh = None
macd_fast = macd_slow = macd_signal = None
boll_window = boll_std = None

if selected_strategy in ("All", "sma"):
    sma_short = st.sidebar.number_input(
        "Short SMA Period", min_value=1, max_value=50, value=5)
    sma_long = st.sidebar.number_input(
        "Long SMA Period", min_value=1, max_value=200, value=20)
elif selected_strategy == "rsi":
    rsi_period = st.sidebar.number_input(
        "RSI Period", min_value=2, max_value=100, value=14)
    lower_thresh = st.sidebar.number_input(
        "RSI Lower Threshold", min_value=1, max_value=100, value=30)
    upper_thresh = st.sidebar.number_input(
        "RSI Upper Threshold", min_value=1, max_value=100, value=70)
elif selected_strategy == "macd":
    macd_fast = st.sidebar.number_input(
        "MACD Fast Period", min_value=1, max_value=100, value=12)
    macd_slow = st.sidebar.number_input(
        "MACD Slow Period", min_value=1, max_value=200, value=26)
    macd_signal = st.sidebar.number_input(
        "MACD Signal Period", min_value=1, max_value=100, value=9)
elif selected_strategy == "bollinger":
    boll_window = st.sidebar.number_input(
        "Bollinger Window", min_value=1, max_value=200, value=20)
    boll_std = st.sidebar.number_input(
        "Bollinger Std Dev", min_value=0.5, max_value=5.0, value=2.0, step=0.1)

col1, col2 = st.columns([2, 1])

with col1:
    strategy_title = (selected_strategy.upper()
                      if selected_strategy != "All" else "SMA")
    st.subheader(f"Price Chart with {strategy_title} Signals")

    def create_mock_data(symbol, limit=500):
        import numpy as np
        from datetime import datetime, timedelta

        base_price = 50000 if 'BTC' in symbol else 3000
        timestamps = [datetime.now() - timedelta(minutes=i)
                      for i in range(limit, 0, -1)]

        prices = []
        current_price = base_price
        for _ in range(limit):
            change = np.random.normal(0, base_price * 0.001)
            current_price += change
            prices.append(current_price)

        return pd.DataFrame({
            'timestamp': timestamps,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, 0.002)))
                     for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.002)))
                    for p in prices],
            'close': prices,
            'volume': [np.random.uniform(100, 1000)
                       for _ in range(limit)]
        })

    try:
        with st.spinner("Fetching price data..."):
            try:
                df = fetch_btc_usdt_data(symbol=selected_symbol,
                                         timeframe="1m", limit=500)
            except Exception as api_error:
                st.warning(f"API unavailable ({str(api_error)[:50]}...), "
                           f"using mock data for demonstration")
                df = create_mock_data(selected_symbol, 500)

        if not df.empty:
            df_copy = df.copy()

            if sma_short and sma_long:
                df_copy[f'sma_{sma_short}'] = df_copy['close'].rolling(
                    window=sma_short).mean()
                df_copy[f'sma_{sma_long}'] = df_copy['close'].rolling(
                    window=sma_long).mean()

            if selected_strategy == "rsi" and rsi_period:
                delta = df_copy['close'].diff()
                gain = delta.clip(lower=0)
                loss = -delta.clip(upper=0)
                avg_gain = gain.rolling(window=rsi_period,
                                        min_periods=rsi_period).mean()
                avg_loss = loss.rolling(window=rsi_period,
                                        min_periods=rsi_period).mean()
                rs = avg_gain / avg_loss.replace(0, pd.NA)
                df_copy['rsi'] = 100 - (100 / (1 + rs))
            elif (selected_strategy == "macd" and
                  all([macd_fast, macd_slow, macd_signal])):
                df_copy['ema_fast'] = df_copy['close'].ewm(
                    span=macd_fast, adjust=False).mean()
                df_copy['ema_slow'] = df_copy['close'].ewm(
                    span=macd_slow, adjust=False).mean()
                df_copy['macd'] = df_copy['ema_fast'] - df_copy['ema_slow']
                df_copy['signal_line'] = df_copy['macd'].ewm(
                    span=macd_signal, adjust=False).mean()
            elif (selected_strategy == "bollinger" and
                  all([boll_window, boll_std])):
                df_copy['middle_band'] = df_copy['close'].rolling(
                    window=boll_window).mean()
                df_copy['std_dev'] = df_copy['close'].rolling(
                    window=boll_window).std()
                df_copy['upper_band'] = (df_copy['middle_band'] +
                                         boll_std * df_copy['std_dev'])
                df_copy['lower_band'] = (df_copy['middle_band'] -
                                         boll_std * df_copy['std_dev'])

            if selected_strategy == "All" or selected_strategy == "sma":
                if sma_short and sma_long:
                    signals = sma_crossover_strategy(df_copy,
                                                     sma_short=sma_short,
                                                     sma_long=sma_long)
                else:
                    signals = []
            else:
                strategy_fn = STRATEGY_REGISTRY.get(
                    selected_strategy, sma_crossover_strategy
                )
                if (selected_strategy == "rsi" and
                        all([rsi_period, lower_thresh, upper_thresh])):
                    signals = strategy_fn(df_copy, period=rsi_period,
                                          lower_thresh=lower_thresh,
                                          upper_thresh=upper_thresh)
                elif (selected_strategy == "macd" and
                      all([macd_fast, macd_slow, macd_signal])):
                    signals = strategy_fn(df_copy, fast_period=macd_fast,
                                          slow_period=macd_slow,
                                          signal_period=macd_signal)
                elif (selected_strategy == "bollinger" and
                      all([boll_window, boll_std])):
                    signals = strategy_fn(df_copy, window=boll_window,
                                          num_std=boll_std)
                elif sma_short and sma_long:
                    signals = strategy_fn(
                        df_copy, sma_short=sma_short, sma_long=sma_long
                    )
                else:
                    signals = []

            if selected_strategy == "rsi":
                fig, (ax, ax_rsi) = plt.subplots(2, 1, sharex=True,
                                                 figsize=(12, 8))
                ax_rsi.plot(df_copy['timestamp'], df_copy['rsi'],
                            label='RSI', color='purple')
                ax_rsi.axhline(lower_thresh, color='green',
                               linestyle='--', label='Lower')
                ax_rsi.axhline(upper_thresh, color='red',
                               linestyle='--', label='Upper')
                ax_rsi.set_ylabel('RSI')
                ax_rsi.set_ylim(0, 100)
                ax_rsi.legend()
            elif selected_strategy == "macd":
                fig, (ax, ax_macd) = plt.subplots(2, 1, sharex=True,
                                                  figsize=(12, 8))
                ax_macd.plot(df_copy['timestamp'], df_copy['macd'],
                             label='MACD', color='blue')
                ax_macd.plot(df_copy['timestamp'], df_copy['signal_line'],
                             label='Signal', color='orange')
                hist = df_copy['macd'] - df_copy['signal_line']
                ax_macd.bar(df_copy['timestamp'], hist, label='Histogram',
                            color='gray', alpha=0.3)
                ax_macd.set_ylabel('MACD')
                ax_macd.legend()
            else:
                fig, ax = plt.subplots(figsize=(12, 6))

            ax.plot(df_copy['timestamp'], df_copy['close'], label='Price',
                    color='black', linewidth=1)

            if sma_short and sma_long:
                ax.plot(df_copy['timestamp'], df_copy[f'sma_{sma_short}'],
                        label=f'SMA {sma_short}', color='blue', alpha=0.7)
                ax.plot(df_copy['timestamp'], df_copy[f'sma_{sma_long}'],
                        label=f'SMA {sma_long}', color='red', alpha=0.7)

            if selected_strategy == "bollinger":
                ax.plot(df_copy['timestamp'], df_copy['upper_band'],
                        label='Upper Band', color='orange', alpha=0.6)
                ax.plot(df_copy['timestamp'], df_copy['middle_band'],
                        label='Middle Band', color='green', alpha=0.6)
                ax.plot(df_copy['timestamp'], df_copy['lower_band'],
                        label='Lower Band', color='orange', alpha=0.6)

            for signal in signals:
                color = 'green' if signal['action'] == 'buy' else 'red'
                marker = '^' if signal['action'] == 'buy' else 'v'
                ax.scatter(signal['timestamp'], signal['price'],
                           color=color, marker=marker, s=100, alpha=0.8,
                           zorder=5)

            ax.set_xlabel('Time')
            ax.set_ylabel('Price (USDT)')
            title_strategy = (
                selected_strategy.upper() if selected_strategy != "All"
                else "SMA"
            )
            ax.set_title(f'{selected_symbol} Price with {title_strategy} '
                         f'Signals')
            ax.legend()
            ax.grid(True, alpha=0.3)

            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
            plt.xticks(rotation=45)

            plt.tight_layout()
            st.pyplot(fig)

            if signals:
                st.success(f"Generated {len(signals)} signals from current "
                           f"data")
                if st.button("Save Signals to Database"):
                    try:
                        strategy_id = (selected_strategy
                                       if selected_strategy != "All"
                                       else 'sma')
                        log_signals_to_db(signals, selected_symbol,
                                          strategy_id)
                        st.success(f"Saved {len(signals)} signals to "
                                   "database!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving signals: {str(e)}")
            else:
                st.info("No crossover signals detected in current data")
        else:
            st.error("Failed to fetch price data")
    except Exception as e:
        st.error(f"Error fetching or processing data: {str(e)}")

with col2:
    st.subheader("Recent Signals")
    try:
        strategy_filter = (None if selected_strategy == "All"
                           else selected_strategy)

        signals_data = get_signals_from_db(
            symbol=selected_symbol,
            strategy_id=strategy_filter,
            limit=limit
        )

        if signals_data:
            signals_df = pd.DataFrame(signals_data,
                                      columns=['Timestamp', 'Action', 'Price',
                                               'Symbol', 'Strategy'])

            signals_df['Price'] = signals_df['Price'].apply(
                lambda x: f"${x:,.2f}")
            signals_df['Timestamp'] = pd.to_datetime(
                signals_df['Timestamp'])
            signals_df['Timestamp'] = signals_df['Timestamp'].dt.strftime(
                '%Y-%m-%d %H:%M:%S')

            def color_action(val):
                color = 'green' if val.lower() == 'buy' else 'red'
                return f'color: {color}; font-weight: bold'

            signals_df_display = signals_df.copy()

            def highlight_action(row):
                if row['Action'].lower() == 'buy':
                    return ['background-color: lightgreen'
                            if col == 'Action' else '' for col in row.index]
                elif row['Action'].lower() == 'sell':
                    return ['background-color: lightcoral'
                            if col == 'Action' else '' for col in row.index]
                else:
                    return ['' for col in row.index]

            styled_df = signals_df_display.style.apply(highlight_action,
                                                       axis=1)

            st.dataframe(styled_df, use_container_width=True,
                         height=400)

            st.metric("Total Signals", len(signals_data))

            buy_signals = sum(1 for signal in signals_data
                              if signal[1] == 'buy')
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

    except Exception as e:
        st.error(f"Error loading signals: {str(e)}")

st.markdown("---")
st.markdown("**Note:** Run the trading bot to generate signals that will "
            "appear in this dashboard.")
st.code("python trading_bot/main.py --symbol BTC/USDT", language="bash")
