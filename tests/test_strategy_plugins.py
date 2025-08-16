import importlib


def test_plugin_discovery(tmp_path, monkeypatch):
    """Strategies placed in plugin directories are auto-discovered."""

    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()

    plugin_file = plugin_dir / "dummy_plugin.py"
    plugin_file.write_text(
        "from trading_bot.strategies import register_strategy\n"
        "@register_strategy('dummy')\n"
        "def dummy_strategy(df):\n"
        "    return []\n"
    )

    monkeypatch.setenv("TRADING_BOT_PLUGIN_PATH", str(plugin_dir))

    import trading_bot.strategies as strategies

    importlib.reload(strategies)

    try:
        assert "dummy" in strategies.STRATEGY_REGISTRY
    finally:
        strategies.STRATEGY_REGISTRY.pop("dummy", None)
        monkeypatch.delenv("TRADING_BOT_PLUGIN_PATH", raising=False)
        importlib.reload(strategies)
