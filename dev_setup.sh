#!/bin/bash


set -e  # Exit on any error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

get_python_version() {
    python --version 2>&1 | sed 's/Python //' | cut -d. -f1,2
}

check_python_version() {
    local version
    version=$(get_python_version)
    
    case "$version" in
        3.9|3.10|3.11|3.12)
            print_success "Python $version detected - compatible!"
            return 0
            ;;
        *)
            print_error "Python $version detected - requires Python 3.9, 3.10, 3.11, or 3.12"
            print_error "Please install a compatible Python version and try again"
            return 1
            ;;
    esac
}

setup_virtualenv() {
    print_status "Setting up virtual environment..."
    
    if [ -d ".venv" ]; then
        print_warning "Virtual environment already exists, removing old one..."
        rm -rf .venv
    fi
    
    python -m venv .venv
    
    if [ -f ".venv/bin/activate" ]; then
        . .venv/bin/activate
        print_success "Virtual environment created and activated"
    else
        print_error "Failed to create virtual environment"
        return 1
    fi
}

install_dependencies() {
    print_status "Installing dependencies..."
    
    python -m pip install --upgrade pip
    
    if pip install -e .; then
        print_success "Package installed in development mode"
    else
        print_error "Failed to install package in development mode"
        return 1
    fi
    
    if [ -f "requirements-dev.txt" ]; then
        if pip install -r requirements-dev.txt; then
            print_success "Development dependencies installed"
        else
            print_error "Failed to install development dependencies"
            return 1
        fi
    else
        print_warning "requirements-dev.txt not found, skipping dev dependencies"
    fi
}

run_validation_checks() {
    print_status "Running validation checks..."
    
    local tools_missing=0
    
    for tool in flake8 mypy pytest black isort; do
        if ! command_exists "$tool"; then
            print_warning "$tool not found, skipping check"
            tools_missing=1
        fi
    done
    
    if [ $tools_missing -eq 1 ]; then
        print_warning "Some tools are missing, but continuing with available ones..."
    fi
    
    if command_exists flake8; then
        print_status "Running flake8 linter..."
        if flake8 .; then
            print_success "flake8 checks passed"
        else
            print_warning "flake8 found some issues (this is normal for initial setup)"
        fi
    fi
    
    if command_exists mypy; then
        print_status "Running mypy type checker..."
        if mypy .; then
            print_success "mypy checks passed"
        else
            print_warning "mypy found some issues (this is normal for initial setup)"
        fi
    fi
    
    if command_exists pytest; then
        print_status "Running test suite..."
        if pytest -q --tb=short; then
            print_success "All tests passed"
        else
            print_warning "Some tests failed (this might be expected for initial setup)"
        fi
    fi
    
    if command_exists black && command_exists isort; then
        print_status "Code formatting tools available (black, isort)"
    fi
}

print_usage_instructions() {
    echo ""
    echo "======================================================"
    print_success "Development environment setup complete!"
    echo "======================================================"
    echo ""
    echo "To activate the virtual environment in future sessions:"
    echo "  source .venv/bin/activate"
    echo ""
    echo "Available commands:"
    echo "  trading-bot --help                    # View CLI help"
    echo "  trading-bot --version                 # Check version"
    echo "  trading-bot --symbol BTC/USDT         # Run with BTC/USDT"
    echo "  trading-bot live --symbol ETH/USDT    # Live simulation mode"
    echo ""
    echo "Dashboard:"
    echo "  streamlit run dashboard.py            # Launch web dashboard"
    echo ""
    echo "Sample backtest:"
    echo "  trading-bot backtest --file data.csv --strategy sma"
    echo ""
    echo "Development commands:"
    echo "  pytest -q                            # Run tests (quiet)"
    echo "  pytest -v                            # Run tests (verbose)"
    echo "  mypy .                               # Type checking"
    echo "  flake8 .                             # Linting"
    echo "  black .                              # Code formatting"
    echo "  isort .                              # Import sorting"
    echo ""
    echo "Pre-commit hooks (optional):"
    echo "  pre-commit install                   # Install git hooks"
    echo "  pre-commit run --all-files           # Run all hooks"
    echo ""
    print_status "Happy coding! 🚀"
}

cleanup_on_error() {
    print_error "Setup failed. Cleaning up..."
    if [ -d ".venv" ]; then
        rm -rf .venv
        print_status "Removed incomplete virtual environment"
    fi
    exit 1
}

main() {
    echo "======================================================"
    echo "Trading Bot Development Environment Setup"
    echo "======================================================"
    echo ""
    
    trap cleanup_on_error ERR
    
    if [ ! -f "pyproject.toml" ] || [ ! -f "requirements-dev.txt" ]; then
        print_error "This script must be run from the trading-bot project root directory"
        print_error "Make sure you're in the directory containing pyproject.toml"
        exit 1
    fi
    
    if ! command_exists python; then
        print_error "Python is not installed or not in PATH"
        print_error "Please install Python 3.9-3.12 and try again"
        exit 1
    fi
    
    check_python_version
    
    setup_virtualenv
    
    install_dependencies
    
    run_validation_checks
    
    print_usage_instructions
    
    print_success "Setup completed successfully!"
}

main "$@"
