"""
Setup configuration for trading-bot package.
"""

from setuptools import setup, find_packages
import os

def read_requirements():
    """Read requirements from requirements.txt file."""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    with open(requirements_path, 'r') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return requirements

def read_readme():
    """Read the README file for long description."""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "A cryptocurrency trading bot with SMA crossover strategy"

setup(
    name="trading-bot",
    version="1.0.0",
    author="Trading Bot Team",
    author_email="trading-bot@example.com",
    description="A cryptocurrency trading signal generator using SMA crossover strategy",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/ryanrodriguez8982/trading-bot-devin-demo",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "trading-bot=trading_bot.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "trading_bot": ["*.json"],
    },
    keywords="cryptocurrency trading bot sma crossover signals binance",
    project_urls={
        "Bug Reports": "https://github.com/ryanrodriguez8982/trading-bot-devin-demo/issues",
        "Source": "https://github.com/ryanrodriguez8982/trading-bot-devin-demo",
    },
)
