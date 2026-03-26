"""
Data caching layer for yfinance downloads.
Saves DataFrames as CSV with age-based expiry to avoid redundant API calls.
"""

import hashlib
import os
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

CACHE_DIR = Path(__file__).parent / "cache"
DEFAULT_MAX_AGE_HOURS = 12


def _cache_path(tag, tickers, start_date, end_date):
    """Build a deterministic cache filename from download parameters."""
    key = f"{tag}_{'_'.join(sorted(tickers))}_{start_date}_{end_date}"
    h = hashlib.md5(key.encode()).hexdigest()[:10]
    return CACHE_DIR / f"{tag}_{h}.csv"


def is_fresh(path, max_age_hours):
    """Check if a cache file exists and is younger than max_age_hours."""
    if not path.exists():
        return False
    age_hours = (time.time() - os.path.getmtime(path)) / 3600
    return age_hours < max_age_hours


def cached_download(tickers, start_date, end_date, tag,
                    max_age_hours=DEFAULT_MAX_AGE_HOURS, log=print):
    """Download data via yfinance, using cached CSV if fresh enough.

    Returns the raw DataFrame from yf.download().
    """
    CACHE_DIR.mkdir(exist_ok=True)
    path = _cache_path(tag, tickers, start_date, end_date)

    if is_fresh(path, max_age_hours):
        log(f"  Using cached {tag} data ({path.name})")
        df = pd.read_csv(path, index_col=0, parse_dates=True, header=[0, 1])
        # Flatten single-ticker case back to simple columns if needed
        if isinstance(df.columns, pd.MultiIndex) and df.columns.nlevels == 2:
            # Check if all second-level labels are empty strings (artifact of CSV round-trip)
            if all(c[1] == "" for c in df.columns):
                df.columns = [c[0] for c in df.columns]
        return df

    log(f"  Downloading {tag}: {tickers}")
    data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True)

    # Save to cache — use multi-level header to preserve structure
    if not data.empty:
        data.to_csv(path)

    return data


def clear_cache():
    """Remove all cached files."""
    if CACHE_DIR.exists():
        for f in CACHE_DIR.glob("*.csv"):
            f.unlink()
