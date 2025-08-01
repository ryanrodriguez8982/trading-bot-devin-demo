# Changelog

## [1.1.0] - 2025-08-01

### Added
- MACD strategy implementation with configurable fast/slow/signal periods
- Bollinger Bands strategy with configurable window and standard deviation
- Enhanced Streamlit dashboard with strategy selection and visualization
- Strategy-specific parameter configuration in dashboard sidebar
- Multi-strategy support in CLI with --strategy flag
- Parameter tuning module via --tune option
- Exchange API key support and --live-trade flag for real orders
- Equity curve and PnL visualization on dashboard
- Cached price and indicator data for faster dashboard refreshes

### Changed
- Updated package description to reflect multiple strategy support
- Enhanced README documentation with MACD and Bollinger examples

## [1.0.0] - Initial Release
- SMA crossover strategy implementation
- Basic dashboard functionality
- CLI interface and configuration system
