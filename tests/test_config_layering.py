import json
import sys

from trading_bot.main import load_config, parse_args


def test_config_overlays_and_cli_precedence(tmp_path):
    base = {"symbol": "BTC/USDT", "timeframe": "1m"}
    local = {"symbol": "ETH/USDT"}
    config_path = tmp_path / "config.json"
    local_path = tmp_path / "config.local.json"
    config_path.write_text(json.dumps(base))
    local_path.write_text(json.dumps(local))

    config = load_config(config_dir=str(tmp_path))
    assert config["symbol"] == "ETH/USDT"  # local overlay

    original = sys.argv
    try:
        sys.argv = ["main.py", "--symbol", "DOGE/USDT"]
        args = parse_args()
    finally:
        sys.argv = original

    final_symbol = args.symbol or config.get("symbol")
    assert final_symbol == "DOGE/USDT"
