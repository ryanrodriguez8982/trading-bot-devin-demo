#!/usr/bin/env python3
"""
Simulation matrix orchestrator for running backtests across strategies × timeframes × position sizes.
Generates reproducible artifacts and comprehensive performance report for Issue #253.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from trading_bot.data_fetch import fetch_market_data
from trading_bot.backtester import run_backtest
from trading_bot.strategies import STRATEGY_REGISTRY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimulationMatrix:
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data" / "sim"
        self.artifacts_dir = self.base_dir / "artifacts" / "simulations"
        self.reports_dir = self.base_dir / "reports"

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        (self.artifacts_dir / "equity_curves").mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.symbol = "BTC/USDT"
        self.exchange_name = "coinbase"
        self.timeframes = {
            "5m": {"days": 60, "limit": 17280},
            "1h": {"days": 180, "limit": 4320}
        }
        self.position_sizes = [0.02, 0.05, 0.10]
        self.fees_bps = 10
        self.initial_capital = 10000.0

        self.target_strategies = ["sma", "rsi", "macd", "bbands"]
        self.results = []

    def get_available_strategies(self) -> List[str]:
        available = []
        for strategy in self.target_strategies:
            if strategy in STRATEGY_REGISTRY:
                available.append(strategy)
                logger.info(f"Found strategy: {strategy}")
            else:
                logger.warning(f"Strategy {strategy} not found in registry")

        if len(available) > 3:
            logger.info(f"Limiting to first 3 strategies: {available[:3]}")
            return available[:3]
        return available

    def get_cached_data_path(self, timeframe: str, start_date: str, end_date: str) -> Path:
        symbol_clean = self.symbol.replace("/", "_")
        filename = f"{symbol_clean}_{timeframe}_{start_date}_{end_date}.csv"
        return self.data_dir / filename

    def fetch_and_cache_data(self, timeframe: str) -> Path:
        config = self.timeframes[timeframe]
        end_date = datetime.now()
        start_date = end_date - timedelta(days=config["days"])

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        cache_path = self.get_cached_data_path(timeframe, start_str, end_str)

        if cache_path.exists():
            logger.info(f"Using cached data: {cache_path}")
            return cache_path

        logger.info(f"Fetching {self.symbol} {timeframe} data for {config['days']} days...")
        try:
            df = fetch_market_data(
                self.symbol,
                timeframe,
                config["limit"],
                exchange_name=self.exchange_name
            )

            if df.empty:
                raise ValueError(f"No data fetched for {self.symbol} {timeframe}")

            df.to_csv(cache_path, index=False)
            logger.info(f"Cached {len(df)} rows to {cache_path}")
            return cache_path

        except Exception as e:
            logger.error(f"Failed to fetch data for {timeframe}: {e}")
            raise

    def calculate_trade_size(self, position_pct: float, last_close: float) -> float:
        trade_value = self.initial_capital * position_pct
        trade_size = trade_value / last_close
        return max(trade_size, 0.001)

    def run_single_simulation(self, strategy: str, timeframe: str, position_pct: float, data_path: Path) -> Dict[str, Any]:
        df = pd.read_csv(data_path)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        last_close = df.iloc[-1]['close']
        trade_size = self.calculate_trade_size(position_pct, last_close)

        size_label = f"{int(position_pct * 100)}pct"
        run_id = f"{strategy}_{timeframe}_{size_label}"

        logger.info(f"Running simulation: {run_id} (trade_size={trade_size})")

        equity_out = self.artifacts_dir / "equity_curves" / f"{run_id}_equity.csv"
        stats_out = self.artifacts_dir / "equity_curves" / f"{run_id}_stats.json"
        chart_out = self.artifacts_dir / "equity_curves" / f"{run_id}.png"

        try:
            result = run_backtest(
                str(data_path),
                strategy=strategy,
                trade_size=trade_size,
                fees_bps=self.fees_bps,
                plot=True,
                equity_out=str(equity_out),
                stats_out=str(stats_out),
                chart_out=str(chart_out)
            )

            simulation_result = {
                "strategy": strategy,
                "timeframe": timeframe,
                "position_size": f"{int(position_pct * 100)}%",
                "position_pct": position_pct,
                "trade_size": trade_size,
                "last_close": last_close,
                "net_pnl": result.get("net_pnl", 0.0),
                "win_rate": result.get("win_rate", 0.0),
                "max_drawdown": result.get("max_drawdown", 0.0),
                "total_trades": result.get("total_trades", 0),
                "avg_trade_pnl": result.get("avg_trade_pnl", 0.0),
                "total_return": result.get("total_return", 0.0),
                "equity_curve_path": str(chart_out),
                "run_id": run_id
            }

            logger.info(f"Completed {run_id}: PnL={result.get('net_pnl', 0):.2f}, Win Rate={result.get('win_rate', 0):.1f}%")
            return simulation_result

        except Exception as e:
            logger.error(f"Simulation failed for {run_id}: {e}")
            return {
                "strategy": strategy,
                "timeframe": timeframe,
                "position_size": f"{int(position_pct * 100)}%",
                "position_pct": position_pct,
                "trade_size": trade_size,
                "last_close": last_close,
                "net_pnl": 0.0,
                "win_rate": 0.0,
                "max_drawdown": 0.0,
                "total_trades": 0,
                "avg_trade_pnl": 0.0,
                "total_return": 0.0,
                "equity_curve_path": "",
                "run_id": run_id,
                "error": str(e)
            }

    def run_matrix(self) -> List[Dict[str, Any]]:
        strategies = self.get_available_strategies()
        if not strategies:
            raise ValueError("No target strategies found in STRATEGY_REGISTRY")

        logger.info(f"Running simulation matrix: {len(strategies)} strategies × {len(self.timeframes)} timeframes × {len(self.position_sizes)} position sizes")

        data_paths = {}
        for timeframe in self.timeframes.keys():
            data_paths[timeframe] = self.fetch_and_cache_data(timeframe)

        results = []
        total_runs = len(strategies) * len(self.timeframes) * len(self.position_sizes)
        current_run = 0

        for strategy in strategies:
            for timeframe in self.timeframes.keys():
                for position_pct in self.position_sizes:
                    current_run += 1
                    logger.info(f"Progress: {current_run}/{total_runs}")

                    result = self.run_single_simulation(
                        strategy, timeframe, position_pct, data_paths[timeframe]
                    )
                    results.append(result)

        self.results = results
        return results

    def save_summary_csv(self) -> Path:
        if not self.results:
            raise ValueError("No results to save")

        df = pd.DataFrame(self.results)
        summary_path = self.artifacts_dir / "summary.csv"
        df.to_csv(summary_path, index=False)
        logger.info(f"Saved summary to {summary_path}")
        return summary_path

    def generate_report(self) -> Path:
        if not self.results:
            raise ValueError("No results to generate report")

        df = pd.DataFrame(self.results)
        df_sorted = df.sort_values(["net_pnl", "max_drawdown"], ascending=[False, True])

        report_path = self.reports_dir / "simulations.md"

        with open(report_path, "w") as f:
            f.write("# Strategy Simulation Matrix Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")

            f.write("## Environment & Data Ranges\n\n")
            f.write(f"- **Symbol:** {self.symbol}\n")
            f.write(f"- **Exchange:** {self.exchange_name}\n")
            f.write(f"- **Timeframes:** {', '.join(self.timeframes.keys())}\n")
            f.write("- **Data Ranges:**\n")
            for tf, config in self.timeframes.items():
                f.write(f"  - {tf}: Last {config['days']} days (~{config['limit']} candles)\n")
            f.write(f"- **Position Sizes:** {', '.join([f'{int(p * 100)}%' for p in self.position_sizes])}\n")
            f.write(f"- **Trading Fees:** {self.fees_bps / 100:.1f}% per trade\n")
            f.write(f"- **Initial Capital:** ${self.initial_capital:,.0f}\n\n")

            f.write("## Results Summary\n\n")
            f.write("Results sorted by Net PnL (descending), then Max Drawdown (ascending):\n\n")

            f.write("| Strategy | Timeframe | Position Size | Net PnL | Win Rate | Max Drawdown | Total Trades | Avg Trade PnL |\n")
            f.write("|----------|-----------|---------------|---------|----------|--------------|--------------|---------------|\n")

            for _, row in df_sorted.iterrows():
                f.write(f"| {row['strategy']} | {row['timeframe']} | {row['position_size']} | ")
                f.write(f"${row['net_pnl']:.2f} | {row['win_rate']:.1f}% | ")
                f.write(f"{row['max_drawdown']:.2f}% | {row['total_trades']} | ${row['avg_trade_pnl']:.2f} |\n")

            f.write("\n## Top Configurations\n\n")

            top_3 = df_sorted.head(3)
            for i, (_, row) in enumerate(top_3.iterrows(), 1):
                f.write(f"### {i}. {row['strategy'].upper()} - {row['timeframe']} - {row['position_size']}\n")
                f.write(f"- **Net PnL:** ${row['net_pnl']:.2f}\n")
                f.write(f"- **Win Rate:** {row['win_rate']:.1f}%\n")
                f.write(f"- **Max Drawdown:** {row['max_drawdown']:.2f}%\n")
                f.write(f"- **Total Trades:** {row['total_trades']}\n")
                if os.path.exists(row['equity_curve_path']):
                    f.write(f"- **Equity Curve:** ![{row['run_id']}]({row['equity_curve_path']})\n")
                f.write("\n")

            worst = df_sorted.tail(1).iloc[0]
            f.write(f"### Worst Configuration: {worst['strategy'].upper()} - {worst['timeframe']} - {worst['position_size']}\n")
            f.write(f"- **Net PnL:** ${worst['net_pnl']:.2f}\n")
            f.write(f"- **Win Rate:** {worst['win_rate']:.1f}%\n")
            f.write(f"- **Max Drawdown:** {worst['max_drawdown']:.2f}%\n")
            f.write(f"- **Total Trades:** {worst['total_trades']}\n\n")

            f.write("## Caveats & Limitations\n\n")
            f.write("- Trading fees modeled at 0.1% per trade\n")
            f.write("- Spot-only trading, no leverage\n")
            f.write("- No slippage modeling beyond fees\n")
            f.write("- Historical data may not reflect future performance\n")
            f.write("- Position sizing based on fixed percentage of initial capital\n\n")

            f.write("## Reproducibility Information\n\n")
            f.write("- **Repository:** ryanrodriguez8982/trading-bot-devin-demo\n")
            f.write("- **Branch:** feature/sim-matrix-report\n")
            f.write("- **Commands Used:**\n")
            f.write("  ```bash\n")
            f.write("  python scripts/simulate_matrix.py\n")
            f.write("  ```\n")
            f.write(f"- **Total Simulation Runs:** {len(self.results)}\n")
            f.write(f"- **Strategies Tested:** {', '.join(df['strategy'].unique())}\n")
            f.write(f"- **Data Source:** {self.exchange_name} exchange via CCXT\n")

        logger.info(f"Generated report: {report_path}")
        return report_path

    def run_full_simulation(self):
        logger.info("Starting full simulation matrix...")

        try:
            self.run_matrix()
            self.save_summary_csv()
            self.generate_report()

            logger.info("Simulation matrix completed successfully!")
            logger.info(f"Artifacts saved to: {self.artifacts_dir}")
            logger.info(f"Report saved to: {self.reports_dir / 'simulations.md'}")

            return True

        except Exception as e:
            logger.error(f"Simulation matrix failed: {e}")
            raise


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Usage: python scripts/simulate_matrix.py")
        print("Runs strategy × timeframe × position size simulation matrix")
        return

    sim = SimulationMatrix()
    sim.run_full_simulation()


if __name__ == "__main__":
    main()
