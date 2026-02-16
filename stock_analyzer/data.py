"""
Stock data fetching layer using yfinance.

Handles all API communication, caching, and data transformation.
All network calls run in background threads to keep the UI responsive.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class StockQuote:
    """Snapshot of current stock data and key metrics."""
    ticker: str
    name: str = ""
    price: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    market_cap: float = 0.0
    pe_ratio: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    high_52w: Optional[float] = None
    low_52w: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_margin: Optional[float] = None
    prev_close: float = 0.0
    open_price: float = 0.0
    day_high: float = 0.0
    day_low: float = 0.0
    avg_volume: int = 0
    sector: str = ""
    industry: str = ""
    # Valuation & financial health
    pb_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None
    price_to_sales: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    beta: Optional[float] = None
    free_cash_flow: Optional[float] = None
    book_value: Optional[float] = None
    next_earnings: str = ""
    error: str = ""


@dataclass
class AnalystData:
    """Analyst consensus and price target data."""
    ticker: str
    recommendation: str = ""
    target_mean: Optional[float] = None
    target_high: Optional[float] = None
    target_low: Optional[float] = None
    target_median: Optional[float] = None
    num_analysts: int = 0
    current_price: float = 0.0
    recommendations: Optional[pd.DataFrame] = None
    error: str = ""


# Period labels mapped to yfinance period strings
CHART_PERIODS = {
    "1M": "1mo",
    "3M": "3mo",
    "1Y": "1y",
    "5Y": "5y",
}


def fetch_quote(ticker: str) -> StockQuote:
    """Fetch current quote and key metrics for a single ticker.

    Returns a StockQuote with the error field set if anything goes wrong,
    rather than raising exceptions, so the UI can display a message.
    """
    quote = StockQuote(ticker=ticker.upper())
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # yfinance returns an empty-ish dict for invalid tickers
        if not info or info.get("regularMarketPrice") is None:
            # Try fast_info as fallback
            try:
                fi = stock.fast_info
                if fi and hasattr(fi, "last_price") and fi.last_price:
                    quote.price = fi.last_price
                    quote.prev_close = getattr(fi, "previous_close", 0) or 0
                    quote.market_cap = getattr(fi, "market_cap", 0) or 0
                    if quote.prev_close:
                        quote.change = quote.price - quote.prev_close
                        quote.change_pct = (quote.change / quote.prev_close) * 100
                    quote.name = ticker.upper()
                    return quote
            except Exception:
                pass
            quote.error = f"No data found for ticker '{ticker.upper()}'"
            return quote

        quote.name = info.get("shortName") or info.get("longName") or ticker.upper()
        quote.price = info.get("regularMarketPrice") or info.get("currentPrice") or 0
        quote.prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose") or 0
        quote.open_price = info.get("regularMarketOpen") or info.get("open") or 0
        quote.day_high = info.get("regularMarketDayHigh") or info.get("dayHigh") or 0
        quote.day_low = info.get("regularMarketDayLow") or info.get("dayLow") or 0
        quote.volume = info.get("regularMarketVolume") or info.get("volume") or 0
        quote.avg_volume = info.get("averageDailyVolume10Day") or info.get("averageVolume") or 0
        quote.market_cap = info.get("marketCap") or 0
        quote.pe_ratio = info.get("trailingPE") or info.get("forwardPE")
        quote.eps = info.get("trailingEps")
        quote.dividend_yield = info.get("dividendYield")
        quote.high_52w = info.get("fiftyTwoWeekHigh")
        quote.low_52w = info.get("fiftyTwoWeekLow")
        quote.revenue_growth = info.get("revenueGrowth")
        quote.profit_margin = info.get("profitMargins")
        quote.sector = info.get("sector") or ""
        quote.industry = info.get("industry") or ""

        # Valuation & financial health
        quote.pb_ratio = info.get("priceToBook")
        quote.peg_ratio = info.get("pegRatio")
        quote.price_to_sales = info.get("priceToSalesTrailing12Months")
        quote.ev_to_ebitda = info.get("enterpriseToEbitda")
        quote.debt_to_equity = info.get("debtToEquity")
        quote.current_ratio = info.get("currentRatio")
        quote.beta = info.get("beta")
        quote.free_cash_flow = info.get("freeCashflow")
        quote.book_value = info.get("bookValue")

        # Next earnings date
        try:
            cal = stock.calendar
            if cal is not None:
                if isinstance(cal, dict):
                    earnings_dates = cal.get("Earnings Date", [])
                    if earnings_dates:
                        ed = earnings_dates[0]
                        quote.next_earnings = ed.strftime("%Y-%m-%d") if hasattr(ed, "strftime") else str(ed)
                elif isinstance(cal, pd.DataFrame) and not cal.empty:
                    if "Earnings Date" in cal.columns:
                        ed = cal["Earnings Date"].iloc[0]
                        quote.next_earnings = ed.strftime("%Y-%m-%d") if hasattr(ed, "strftime") else str(ed)
        except Exception:
            pass

        if quote.prev_close and quote.price:
            quote.change = quote.price - quote.prev_close
            quote.change_pct = (quote.change / quote.prev_close) * 100

    except Exception as e:
        quote.error = f"Failed to fetch data: {e}"

    return quote


def fetch_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Fetch historical OHLCV data.

    Args:
        ticker: Stock ticker symbol.
        period: yfinance period string (1mo, 3mo, 1y, 5y).

    Returns:
        DataFrame with Date index and Open/High/Low/Close/Volume columns.
        Returns an empty DataFrame on failure.
    """
    try:
        stock = yf.Ticker(ticker)
        # Pick an appropriate interval for the period
        interval_map = {"1mo": "1d", "3mo": "1d", "1y": "1d", "5y": "1wk"}
        interval = interval_map.get(period, "1d")
        df = stock.history(period=period, interval=interval)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    return pd.DataFrame()


def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add moving averages and RSI columns to a price history DataFrame."""
    if df.empty or "Close" not in df.columns:
        return df

    df = df.copy()

    # Simple Moving Averages
    df["SMA_20"] = df["Close"].rolling(window=20).mean()
    df["SMA_50"] = df["Close"].rolling(window=50).mean()

    # RSI (14-period)
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    # Bollinger Bands (20-period, 2 std dev)
    bb_mid = df["Close"].rolling(window=20).mean()
    bb_std = df["Close"].rolling(window=20).std()
    df["BB_Upper"] = bb_mid + 2 * bb_std
    df["BB_Lower"] = bb_mid - 2 * bb_std

    # MACD (12, 26, 9)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Signal"]

    # EMA 200 — key institutional trend line
    df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()

    return df


def fetch_news(ticker: str) -> list[dict]:
    """Fetch recent news headlines for a ticker.

    Returns a list of dicts with 'title', 'link', and 'publisher' keys.
    """
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if not news:
            return []
        results = []
        for item in news[:10]:
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "publisher": item.get("publisher", ""),
            })
        return results
    except Exception:
        return []


def fetch_analyst_data(ticker: str) -> AnalystData:
    """Fetch analyst recommendations and price targets for a ticker."""
    result = AnalystData(ticker=ticker.upper())
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        result.current_price = info.get("regularMarketPrice") or info.get("currentPrice") or 0
        result.recommendation = info.get("recommendationKey") or ""
        result.target_mean = info.get("targetMeanPrice")
        result.target_high = info.get("targetHighPrice")
        result.target_low = info.get("targetLowPrice")
        result.target_median = info.get("targetMedianPrice")
        result.num_analysts = info.get("numberOfAnalystOpinions") or 0

        try:
            recs = stock.recommendations
            if recs is not None and not recs.empty:
                result.recommendations = recs.tail(10)
        except Exception:
            pass

    except Exception as e:
        result.error = str(e)

    return result


def validate_ticker(ticker: str) -> bool:
    """Quick check whether a ticker symbol appears valid."""
    if not ticker or not ticker.strip():
        return False
    try:
        stock = yf.Ticker(ticker.strip().upper())
        fi = stock.fast_info
        return fi is not None and hasattr(fi, "last_price") and fi.last_price is not None
    except Exception:
        return False


def format_large_number(n: Optional[float]) -> str:
    """Format a number like 1_500_000_000 as '1.50B'."""
    if n is None:
        return "N/A"
    abs_n = abs(n)
    sign = "-" if n < 0 else ""
    if abs_n >= 1e12:
        return f"{sign}{abs_n / 1e12:.2f}T"
    if abs_n >= 1e9:
        return f"{sign}{abs_n / 1e9:.2f}B"
    if abs_n >= 1e6:
        return f"{sign}{abs_n / 1e6:.2f}M"
    if abs_n >= 1e3:
        return f"{sign}{abs_n / 1e3:.2f}K"
    return f"{sign}{abs_n:.2f}"
