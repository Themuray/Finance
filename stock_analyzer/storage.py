"""
Watchlist persistence using JSON files.

Stores watchlists in ~/.stock_analyzer/watchlists.json so they survive
across sessions. Each watchlist is a named list of ticker symbols.
"""

import json
import os
from pathlib import Path
from typing import Optional

# Default storage directory inside the user's home folder
STORAGE_DIR = Path.home() / ".stock_analyzer"
WATCHLIST_FILE = STORAGE_DIR / "watchlists.json"
PORTFOLIO_FILE = STORAGE_DIR / "portfolio.json"


def _ensure_storage_dir() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def load_watchlists() -> dict[str, list[str]]:
    """Load all saved watchlists from disk.

    Returns:
        Dict mapping watchlist name to list of ticker strings.
        Returns a default watchlist if no file exists yet.
    """
    _ensure_storage_dir()
    if not WATCHLIST_FILE.exists():
        return {"My Watchlist": []}
    try:
        with open(WATCHLIST_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"My Watchlist": []}


def save_watchlists(watchlists: dict[str, list[str]]) -> None:
    """Persist all watchlists to disk."""
    _ensure_storage_dir()
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlists, f, indent=2)


def add_ticker(watchlist_name: str, ticker: str,
               watchlists: Optional[dict] = None) -> dict[str, list[str]]:
    """Add a ticker to a watchlist, save, and return updated watchlists."""
    if watchlists is None:
        watchlists = load_watchlists()
    ticker = ticker.strip().upper()
    if watchlist_name not in watchlists:
        watchlists[watchlist_name] = []
    if ticker not in watchlists[watchlist_name]:
        watchlists[watchlist_name].append(ticker)
    save_watchlists(watchlists)
    return watchlists


def remove_ticker(watchlist_name: str, ticker: str,
                  watchlists: Optional[dict] = None) -> dict[str, list[str]]:
    """Remove a ticker from a watchlist, save, and return updated watchlists."""
    if watchlists is None:
        watchlists = load_watchlists()
    ticker = ticker.strip().upper()
    if watchlist_name in watchlists and ticker in watchlists[watchlist_name]:
        watchlists[watchlist_name].remove(ticker)
    save_watchlists(watchlists)
    return watchlists


def create_watchlist(name: str,
                     watchlists: Optional[dict] = None) -> dict[str, list[str]]:
    """Create a new empty watchlist."""
    if watchlists is None:
        watchlists = load_watchlists()
    if name not in watchlists:
        watchlists[name] = []
    save_watchlists(watchlists)
    return watchlists


def delete_watchlist(name: str,
                     watchlists: Optional[dict] = None) -> dict[str, list[str]]:
    """Delete a watchlist by name."""
    if watchlists is None:
        watchlists = load_watchlists()
    watchlists.pop(name, None)
    if not watchlists:
        watchlists["My Watchlist"] = []
    save_watchlists(watchlists)
    return watchlists


def export_to_csv(watchlist_name: str, filepath: str,
                  quotes: list) -> None:
    """Export watchlist data to a CSV file.

    Args:
        watchlist_name: Name for the header.
        filepath: Destination CSV path.
        quotes: List of StockQuote objects to export.
    """
    import csv
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Ticker", "Name", "Price", "Change", "Change %", "Volume",
            "Market Cap", "P/E", "EPS", "Dividend Yield",
            "52W High", "52W Low", "Sector", "Industry",
            "P/B", "PEG", "P/S", "EV/EBITDA", "D/E",
            "Current Ratio", "Beta", "FCF", "Book Value",
        ])
        for q in quotes:
            writer.writerow([
                q.ticker, q.name, f"{q.price:.2f}",
                f"{q.change:+.2f}", f"{q.change_pct:+.2f}%",
                q.volume, q.market_cap,
                f"{q.pe_ratio:.2f}" if q.pe_ratio else "N/A",
                f"{q.eps:.2f}" if q.eps else "N/A",
                f"{q.dividend_yield * 100:.2f}%" if q.dividend_yield else "N/A",
                q.high_52w or "N/A", q.low_52w or "N/A",
                q.sector, q.industry,
                f"{q.pb_ratio:.2f}" if q.pb_ratio else "N/A",
                f"{q.peg_ratio:.2f}" if q.peg_ratio else "N/A",
                f"{q.price_to_sales:.2f}" if q.price_to_sales else "N/A",
                f"{q.ev_to_ebitda:.2f}" if q.ev_to_ebitda else "N/A",
                f"{q.debt_to_equity:.1f}" if q.debt_to_equity is not None else "N/A",
                f"{q.current_ratio:.2f}" if q.current_ratio else "N/A",
                f"{q.beta:.2f}" if q.beta else "N/A",
                q.free_cash_flow or "N/A",
                f"{q.book_value:.2f}" if q.book_value else "N/A",
            ])


# ---------------------------------------------------------------------------
# Portfolio persistence
# ---------------------------------------------------------------------------

def load_portfolio() -> list[dict]:
    """Load portfolio positions from disk.

    Returns list of dicts with 'ticker', 'shares', 'cost_basis' keys.
    """
    _ensure_storage_dir()
    if not PORTFOLIO_FILE.exists():
        return []
    try:
        with open(PORTFOLIO_FILE, "r") as f:
            port_data = json.load(f)
        if isinstance(port_data, list):
            return port_data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_portfolio(positions: list[dict]) -> None:
    """Persist portfolio positions to disk."""
    _ensure_storage_dir()
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(positions, f, indent=2)


def add_position(ticker: str, shares: float, cost_basis: float,
                 positions: Optional[list] = None) -> list[dict]:
    """Add or update a portfolio position (weighted-average cost basis)."""
    if positions is None:
        positions = load_portfolio()
    ticker = ticker.strip().upper()
    for pos in positions:
        if pos["ticker"] == ticker:
            total_shares = pos["shares"] + shares
            if total_shares > 0:
                pos["cost_basis"] = (
                    (pos["shares"] * pos["cost_basis"]) + (shares * cost_basis)
                ) / total_shares
            pos["shares"] = total_shares
            save_portfolio(positions)
            return positions
    positions.append({"ticker": ticker, "shares": shares, "cost_basis": cost_basis})
    save_portfolio(positions)
    return positions


def remove_position(ticker: str,
                    positions: Optional[list] = None) -> list[dict]:
    """Remove a position from the portfolio."""
    if positions is None:
        positions = load_portfolio()
    ticker = ticker.strip().upper()
    positions = [p for p in positions if p["ticker"] != ticker]
    save_portfolio(positions)
    return positions
