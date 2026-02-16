"""
Data fetching layer for the robo-advisor.

Handles yfinance communication, historical price retrieval, returns
computation, covariance matrix calculation, and risk-free rate fetching.
All functions return structured dataclasses and never raise to the caller.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

TRADING_DAYS = 252


@dataclass
class AssetData:
    """Fetched data for a single asset."""
    ticker: str
    name: str = ""
    prices: Optional[pd.Series] = None
    returns: Optional[pd.Series] = None
    annual_return: float = 0.0
    annual_volatility: float = 0.0
    error: str = ""


@dataclass
class PortfolioData:
    """Combined multi-asset dataset ready for optimization."""
    tickers: list[str] = field(default_factory=list)
    names: dict[str, str] = field(default_factory=dict)
    prices: Optional[pd.DataFrame] = None
    returns: Optional[pd.DataFrame] = None
    expected_returns: Optional[np.ndarray] = None
    cov_matrix: Optional[np.ndarray] = None
    correlation_matrix: Optional[np.ndarray] = None
    individual_stats: dict[str, AssetData] = field(default_factory=dict)
    risk_free_rate: float = 0.045
    errors: list[str] = field(default_factory=list)


def fetch_risk_free_rate() -> float:
    """Fetch the current 10-year Treasury yield from ^TNX.

    Returns the yield as a decimal (e.g. 0.045 for 4.5%).
    Falls back to 0.045 on any failure.
    """
    try:
        tnx = yf.Ticker("^TNX")
        fi = tnx.fast_info
        if fi and hasattr(fi, "last_price") and fi.last_price:
            return fi.last_price / 100.0
    except Exception:
        pass
    return 0.045


def validate_ticker(ticker: str) -> tuple[bool, str]:
    """Quick check whether a ticker exists and has price data.

    Returns:
        (is_valid, display_name_or_error_message)
    """
    if not ticker or not ticker.strip():
        return False, "Empty ticker"
    ticker = ticker.strip().upper()
    try:
        stock = yf.Ticker(ticker)
        fi = stock.fast_info
        if fi and hasattr(fi, "last_price") and fi.last_price is not None:
            info = stock.info
            name = info.get("shortName") or info.get("longName") or ticker
            return True, name
    except Exception:
        pass
    return False, f"No data found for '{ticker}'"


def fetch_asset_history(ticker: str, period: str = "5y") -> AssetData:
    """Fetch historical adjusted close prices for a single asset.

    Computes daily log returns and annualized statistics.
    Sets the error field on failure instead of raising.
    """
    asset = AssetData(ticker=ticker.upper())
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        asset.name = info.get("shortName") or info.get("longName") or ticker.upper()

        df = stock.history(period=period, interval="1d")
        if df is None or df.empty or "Close" not in df.columns:
            asset.error = f"No price history for '{ticker.upper()}'"
            return asset

        prices = df["Close"].dropna()
        if len(prices) < 30:
            asset.error = f"Insufficient history for '{ticker.upper()}' ({len(prices)} days)"
            return asset

        asset.prices = prices
        asset.returns = np.log(prices / prices.shift(1)).dropna()
        asset.annual_return = float(asset.returns.mean() * TRADING_DAYS)
        asset.annual_volatility = float(asset.returns.std() * np.sqrt(TRADING_DAYS))

    except Exception as e:
        asset.error = f"Failed to fetch '{ticker.upper()}': {e}"

    return asset


def fetch_portfolio_data(tickers: list[str], period: str = "5y",
                         risk_free_rate: Optional[float] = None) -> PortfolioData:
    """Fetch and align historical data for multiple assets.

    This is the main entry point called by the GUI worker thread.
    Fetches each asset, aligns dates via inner join, and computes
    the expected returns vector, covariance matrix, and correlation matrix.
    """
    result = PortfolioData()

    # Risk-free rate
    if risk_free_rate is not None:
        result.risk_free_rate = risk_free_rate
    else:
        result.risk_free_rate = fetch_risk_free_rate()

    # Fetch each asset
    valid_assets: dict[str, AssetData] = {}
    for t in tickers:
        asset = fetch_asset_history(t, period)
        if asset.error:
            result.errors.append(asset.error)
        else:
            valid_assets[asset.ticker] = asset

    if len(valid_assets) < 2:
        result.errors.append("Need at least 2 valid assets for optimization.")
        return result

    # Build aligned price DataFrame (inner join on dates)
    price_dict = {t: a.prices for t, a in valid_assets.items()}
    prices = pd.DataFrame(price_dict).dropna()

    if len(prices) < 30:
        result.errors.append(
            f"Only {len(prices)} overlapping trading days — need at least 30.")
        return result

    # Compute returns, expected returns, covariance
    returns = np.log(prices / prices.shift(1)).dropna()

    result.tickers = list(valid_assets.keys())
    result.names = {t: a.name for t, a in valid_assets.items()}
    result.prices = prices
    result.returns = returns
    result.expected_returns = (returns.mean().values * TRADING_DAYS).astype(float)
    result.cov_matrix = (returns.cov().values * TRADING_DAYS).astype(float)
    result.correlation_matrix = returns.corr().values.astype(float)
    result.individual_stats = valid_assets

    return result
