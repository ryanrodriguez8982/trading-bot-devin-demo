# Contributing to Trading Bot

Welcome to the Trading Bot project! This guide will help you get started as a contributor to our cryptocurrency trading signal generator with multiple strategies (SMA, RSI, MACD, Bollinger Bands).

## Table of Contents

- [Repository Overview](#repository-overview)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Quality](#code-quality)
- [Usage Examples](#usage-examples)
- [Coding Standards](#coding-standards)
- [Contributing Workflow](#contributing-workflow)
- [ACU-Efficient Devin Usage](#acu-efficient-devin-usage)

## Repository Overview

This project is a comprehensive cryptocurrency trading bot system designed for algorithmic trading signal generation and analysis. The system abstracts the complexity of exchange APIs, technical indicator calculations, and performance analysis into a user-friendly interface accessible via both command-line tools and a web dashboard.

### Project Structure

```
├── trading_bot/                    # Main package directory
│   ├── main.py                    # CLI orchestrator and entry point
│   ├── strategies/                # Strategy implementations
│   │   ├── __init__.py           # STRATEGY_REGISTRY definition
│   │   ├── sma_strategy.py       # Simple Moving Average strategy
│   │   ├── rsi_strategy.py       # RSI strategy
│   │   ├── macd_strategy.py      # MACD strategy
│   │   └── bollinger_strategy.py # Bollinger Bands strategy
│   ├── data_fetch.py             # Market data acquisition
│   ├── signal_logger.py          # Signal persistence layer
│   ├── exchange.py               # Exchange API integration
│   ├── backtester.py             # Historical backtesting engine
│   ├── performance.py            # Performance metrics calculation
│   └── tuner.py                  # Parameter optimization
├── tests/                         # Comprehensive test suite
├── dashboard.py                   # Streamlit web dashboard
├── signals.db                     # SQLite database for signal storage
├── config.json                    # Default configuration parameters
├── requirements.txt               # Python dependencies
├── requirements-dev.txt           # Development dependencies
├── setup.py                       # Package configuration and CLI setup
└── .github/workflows/test.yml     # CI/CD pipeline
```

### Key Components

- **Strategy Engine**: Pluggable trading algorithm implementations
- **Data Management**: Market data acquisition and signal persistence
- **Execution Engine**: Exchange API integration for live trading
- **Analysis Engine**: Historical analysis and performance metrics
- **Optimization Engine**: Parameter tuning and grid search
- **Web Dashboard**: Interactive visualization with Streamlit

## Getting Started

### Prerequisites

- Python 3.9, 3.10, 3.11, or 3.12
- Git for version control
- Virtual environment (recommended)

### Quick Setup

The fastest way to get started is using our automated setup script:

```bash
# Clone the repository
git clone https://github.com/ryanrodriguez8982/trading-bot-devin-demo.git
cd trading-bot-devin-demo

# Run the automated setup script
./dev_setup.sh
```

This script will:
- Check your Python version compatibility
- Create and activate a virtual environment
- Install all development dependencies
- Run initial validation checks
- Display usage instructions

## Development Setup

### Manual Setup

If you prefer to set up manually or need more control:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package in development mode
pip install -e .

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks (optional but recommended)
pre-commit install
```

### Verify Installation

```bash
# Check that the CLI tool is available
trading-bot --version

# Run a quick test
pytest tests/test_main.py -v
```

## Running Tests

We use pytest for our test suite with comprehensive coverage:

```bash
# Run all tests (quiet mode)
pytest -q

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_strategies_common.py

# Run tests with coverage report
pytest --cov=trading_bot --cov-report=html
```

### Test Structure

- `tests/conftest.py`: Shared fixtures and test utilities
- `tests/test_*.py`: Individual test modules
- Tests use parametrized fixtures for strategy testing
- Mock data generators for consistent testing

## Code Quality

We maintain high code quality standards with automated tools:

### Type Checking

```bash
# Run mypy type checker
mypy .

# Check specific module
mypy trading_bot/strategies/
```

### Linting

```bash
# Run flake8 linter
flake8 .

# Check specific files
flake8 trading_bot/main.py
```

### Code Formatting

```bash
# Format code with black
black .

# Sort imports with isort
isort .

# Run ruff for additional linting
ruff check .
```

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality:

```bash
# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

Our pre-commit configuration includes:
- **black**: Code formatting
- **isort**: Import sorting
- **ruff**: Fast Python linter
- **mypy**: Type checking
- **detect-secrets**: Secret scanning

## Usage Examples

### Command Line Interface

```bash
# Basic usage (uses config.json defaults)
trading-bot

# Run with custom parameters
trading-bot --symbol ETH/USDT --timeframe 5m --sma-short 10 --sma-long 30

# Use different strategy
trading-bot --strategy macd --symbol BTC/USDT

# Live trading simulation
trading-bot live --symbol BTC/USDT

# Run backtests
trading-bot backtest --file path/to/data.csv --strategy sma

# Parameter optimization
trading-bot optimize --tune --file data.csv --strategy bbands
```

### Dashboard

Launch the interactive Streamlit dashboard:

```bash
streamlit run dashboard.py
```

The dashboard provides:
- Interactive price charts with technical indicators
- Signal visualization and filtering
- Real-time strategy configuration
- Equity curve analysis
- Performance metrics

### Sample Backtest

```bash
# Download sample data (if available) and run backtest
trading-bot backtest --file btc_sample.csv --strategy sma --sma-short 5 --sma-long 20
```

## Coding Standards

### Type Hints

All functions and methods must include type hints:

```python
from typing import List, Dict, Optional
import pandas as pd

def process_signals(
    data: pd.DataFrame, 
    strategy_params: Dict[str, float]
) -> List[Dict[str, Any]]:
    """Process trading signals with given parameters."""
    # Implementation here
    pass
```

### Docstrings

All public functions, classes, and methods require docstrings:

```python
def sma_crossover_strategy(
    data: pd.DataFrame, 
    sma_short: int = 5, 
    sma_long: int = 20
) -> List[Dict[str, Any]]:
    """
    Generate trading signals based on SMA crossover strategy.
    
    Args:
        data: OHLCV DataFrame with timestamp, open, high, low, close, volume
        sma_short: Short-period SMA window (default: 5)
        sma_long: Long-period SMA window (default: 20)
        
    Returns:
        List of signal dictionaries with timestamp, action, and price
        
    Raises:
        ValueError: If data is insufficient for calculation
    """
    # Implementation here
    pass
```

### Code Style

- Follow PEP 8 guidelines
- Use descriptive variable names
- Keep functions focused and small
- Prefer composition over inheritance
- Use dataclasses for structured data
- Handle errors gracefully with proper logging

### Testing Requirements

- Write tests for all new functionality
- Maintain test coverage above 80%
- Use descriptive test names
- Include edge cases and error conditions
- Mock external dependencies (APIs, databases)

## Contributing Workflow

### Fork and Branch

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/trading-bot-devin-demo.git
   cd trading-bot-devin-demo
   ```

3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Development Process

1. **Make your changes** following the coding standards
2. **Add tests** for new functionality
3. **Run the full test suite**:
   ```bash
   pytest -q
   mypy .
   flake8 .
   black --check .
   isort --check-only .
   ```

4. **Commit your changes**:
   ```bash
   git add specific-files  # Don't use git add .
   git commit -m "feat: add new strategy implementation"
   ```

### Commit Message Format

Use conventional commit format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions/changes
- `refactor:` for code refactoring
- `chore:` for maintenance tasks

### Pull Request Process

1. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a Pull Request** on GitHub with:
   - Clear title describing the change
   - Detailed description of what was changed and why
   - Reference any related issues
   - Include test results and screenshots if applicable

3. **Address review feedback** by pushing additional commits

4. **Ensure CI passes** before requesting final review

### Code Review Guidelines

- Be respectful and constructive
- Focus on code quality and maintainability
- Test the changes locally when possible
- Ask questions if something is unclear
- Approve when satisfied with the implementation

## ACU-Efficient Devin Usage

When working with Devin AI on this project, consider these tips for efficient ACU usage:

### Planning Phase
- Start with `trading-bot --help` to understand CLI structure
- Review existing strategy implementations before creating new ones
- Check `tests/` directory for testing patterns
- Examine `config.json` for parameter defaults

### Development Phase
- Use `pytest tests/test_specific_module.py` for focused testing
- Run `mypy trading_bot/specific_module.py` for targeted type checking
- Test changes with `trading-bot --strategy your_strategy --symbol BTC/USDT`
- Use the dashboard for visual verification: `streamlit run dashboard.py`

### Common Patterns
- Strategy functions follow the pattern: `(data, **params) -> List[Dict]`
- All strategies are registered in `trading_bot/strategies/__init__.py`
- Database operations use `trading_bot/signal_logger.py`
- Configuration layering: `config.json` < `config.local.json` < CLI args

### Testing Shortcuts
- Use `pytest -k "test_name_pattern"` for specific tests
- Mock external APIs in tests to avoid rate limits
- Use `generate_ohlcv_factory` fixture for test data
- Test with `--strategy sma` first as it's the simplest

### Debugging Tips
- Enable debug logging: `trading-bot --log-level DEBUG`
- Check signal database: `sqlite3 signals.db "SELECT * FROM signals LIMIT 10;"`
- Use dashboard filters to isolate specific signals
- Test backtests with small datasets first

This approach helps minimize ACU usage while maintaining development velocity and code quality.
