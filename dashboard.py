import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'trading_bot'))

from signal_logger import get_signals_from_db, log_signals_to_db  # noqa: E402
from data_fetch import fetch_btc_usdt_data  # noqa: E402
from strategy import sma_crossover_strategy  # noqa: E402
from strategies import STRATEGY_REGISTRY, list_strategies  # noqa: E402

st.set_page_config(
    page_title="Trading Bot Dashboard",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Trading Bot Dashboard")
st.markdown("Visualize trading signals and price data with SMA "
            "crossover analysis")

st.sidebar.header("Filters")

symbol_options = ["BTC/USDT", "ETH/USDT", "ADA/USDT", "DOT/USDT", "SOL/USDT"]
selected_symbol = st.sidebar.selectbox("Symbol", symbol_options, index=0)

strategy_options = ["All"] + list_strategies()
selected_strategy = st.sidebar.selectbox("Strategy", strategy_options, index=0)

limit = st.sidebar.slider("Number of signals to display", min_value=10,
                          max_value=500, value=50, step=10)

sma_short = st.sidebar.number_input(
    "Short SMA Period", min_value=1, max_value=50, value=5)
sma_long = st.sidebar.number_input("Long SMA Period", min_value=1,
                                   max_value=200, value=20)

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Price Chart with SMA Crossovers")

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
            df_copy[f'sma_{sma_short}'] = df_copy['close'].rolling(
                window=sma_short).mean()
            df_copy[f'sma_{sma_long}'] = df_copy['close'].rolling(
                window=sma_long).mean()

            if selected_strategy == "All" or selected_strategy == "sma":
                signals = sma_crossover_strategy(df_copy, sma_short=sma_short,
                                                 sma_long=sma_long)
            else:
                strategy_fn = STRATEGY_REGISTRY.get(
                    selected_strategy, sma_crossover_strategy
                )
                if selected_strategy == "rsi":
                    signals = strategy_fn(df_copy, period=14)
                elif selected_strategy == "macd":
                    signals = strategy_fn(df_copy)
                else:
                    signals = strategy_fn(
                        df_copy, sma_short=sma_short, sma_long=sma_long
                    )

            fig, ax = plt.subplots(figsize=(12, 6))

            ax.plot(df_copy['timestamp'], df_copy['close'], label='Price',
                    color='black', linewidth=1)
            ax.plot(df_copy['timestamp'], df_copy[f'sma_{sma_short}'],
                    label=f'SMA {sma_short}', color='blue', alpha=0.7)
            ax.plot(df_copy['timestamp'], df_copy[f'sma_{sma_long}'],
                    label=f'SMA {sma_long}', color='red', alpha=0.7)

            for signal in signals:
                color = 'green' if signal['action'] == 'buy' else 'red'
                marker = '^' if signal['action'] == 'buy' else 'v'
                ax.scatter(signal['timestamp'], signal['price'],
                           color=color, marker=marker, s=100, alpha=0.8,
                           zorder=5)

            ax.set_xlabel('Time')
            ax.set_ylabel('Price (USDT)')
            ax.set_title(f'{selected_symbol} Price with SMA Crossover '
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
                                   f"database!")
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
