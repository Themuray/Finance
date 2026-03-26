"""
CHF Hedging Efficiency Backtester for MSCI Index Funds

Compares hedged vs unhedged returns for a CHF-based investor holding
global index funds, using rolling 1-month FX forward hedges with
historical interest rate differentials.

Three return series per index:
  1. Unhedged CHF  — raw ETF return converted at spot USD/CHF
  2. USD-only hedged — hedge 100% of NAV from USD to CHF via 1M forward
  3. Full basket hedged — hedge each currency component to CHF independently

Usage:
    python hedging_backtest_msci_chf.py
"""

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import warnings

from cache import cached_download

warnings.filterwarnings("ignore", category=FutureWarning)

# =============================================================================
# Configuration
# =============================================================================

ETF_TICKERS = {
    "MSCI World": "URTH",   # iShares MSCI World ETF (inception 2012-01)
    "MSCI ACWI": "ACWI",    # iShares MSCI ACWI ETF (inception 2008-03)
    "MSCI EM": "EEM",        # iShares MSCI Emerging Markets ETF (inception 2003-04)
}

START_DATE = "2006-01-01"
END_DATE = "2026-03-24"

# Approximate currency weight breakdown for full basket hedge
# CHF and OTHER portions are left unhedged (no hedge P&L)
CURRENCY_WEIGHTS = {
    "MSCI World": {
        "USD": 0.70, "EUR": 0.10, "JPY": 0.06, "GBP": 0.04,
        "CAD": 0.03, "AUD": 0.02, "CHF": 0.03, "OTHER": 0.02,
    },
    "MSCI ACWI": {
        "USD": 0.63, "EUR": 0.08, "JPY": 0.05, "GBP": 0.03,
        "CNY": 0.04, "CAD": 0.03, "AUD": 0.02, "CHF": 0.02, "OTHER": 0.10,
    },
    "MSCI EM": {
        "USD": 0.00, "CNY": 0.30, "TWD": 0.18, "INR": 0.15,
        "KRW": 0.12, "BRL": 0.05, "ZAR": 0.04, "OTHER": 0.16,
    },
}

# FX tickers — direct CHF pairs for major currencies (reliable on yfinance)
FX_DIRECT_CHF = {
    "USD": "USDCHF=X",
    "EUR": "EURCHF=X",
    "JPY": "JPYCHF=X",
    "GBP": "GBPCHF=X",
    "CAD": "CADCHF=X",
    "AUD": "AUDCHF=X",
}

# For exotic/EM currencies, use USDXXX cross-rates (more reliable data)
# We compute XXXCHF = USDCHF / USDXXX
FX_VIA_USD = {
    "CNY": "CNY=X",    # USDCNY
    "TWD": "TWD=X",    # USDTWD
    "INR": "INR=X",    # USDINR
    "KRW": "KRW=X",    # USDKRW
    "BRL": "BRL=X",    # USDBRL
    "ZAR": "ZAR=X",    # USDZAR
}

# =============================================================================
# Hardcoded policy rate table (annualized, approximate)
# Format: list of (start_date, rate) tuples — rate applies from start_date
# until the next entry. Sources: SNB, Fed, ECB, BOJ, BOE, etc.
# =============================================================================

POLICY_RATES = {
    "CHF": [  # SNB target rate / LIBOR target band midpoint
        ("2000-01-01", 0.0175),
        ("2001-03-22", 0.0150),
        ("2001-09-17", 0.0125),
        ("2002-05-02", 0.0075),
        ("2003-03-06", 0.0025),
        ("2004-06-17", 0.0050),
        ("2005-06-16", 0.0075),
        ("2006-03-16", 0.0100),
        ("2006-09-14", 0.0150),
        ("2007-03-15", 0.0200),
        ("2007-09-13", 0.0250),
        ("2008-10-08", 0.0200),
        ("2008-11-06", 0.0100),
        ("2008-12-11", 0.0050),
        ("2009-03-12", 0.0025),
        ("2011-08-03", 0.0000),
        ("2015-01-15", -0.0075),
        ("2022-06-16", -0.0025),
        ("2022-09-22", 0.0050),
        ("2022-12-15", 0.0100),
        ("2023-03-23", 0.0150),
        ("2023-06-22", 0.0175),
        ("2024-03-21", 0.0150),
        ("2024-06-20", 0.0125),
        ("2024-09-26", 0.0100),
        ("2024-12-12", 0.0050),
        ("2025-03-20", 0.0025),
    ],
    "USD": [  # Federal Funds target rate (upper bound)
        ("2000-01-01", 0.0550),
        ("2001-01-03", 0.0500),
        ("2001-01-31", 0.0450),
        ("2001-03-20", 0.0400),
        ("2001-04-18", 0.0350),
        ("2001-05-15", 0.0300),
        ("2001-06-27", 0.0275),
        ("2001-08-21", 0.0250),
        ("2001-09-17", 0.0200),
        ("2001-10-02", 0.0175),
        ("2001-11-06", 0.0100),
        ("2001-12-11", 0.0075),
        ("2003-06-25", 0.0100),
        ("2004-06-30", 0.0125),
        ("2004-08-10", 0.0150),
        ("2004-09-21", 0.0175),
        ("2004-11-10", 0.0200),
        ("2004-12-14", 0.0225),
        ("2005-02-02", 0.0250),
        ("2005-03-22", 0.0275),
        ("2005-05-03", 0.0300),
        ("2005-06-30", 0.0325),
        ("2005-08-09", 0.0350),
        ("2005-09-20", 0.0375),
        ("2005-11-01", 0.0400),
        ("2005-12-13", 0.0425),
        ("2006-01-31", 0.0450),
        ("2006-03-28", 0.0475),
        ("2006-05-10", 0.0500),
        ("2006-06-29", 0.0525),
        ("2007-09-18", 0.0475),
        ("2007-10-31", 0.0450),
        ("2007-12-11", 0.0425),
        ("2008-01-22", 0.0350),
        ("2008-01-30", 0.0300),
        ("2008-03-18", 0.0225),
        ("2008-04-30", 0.0200),
        ("2008-10-08", 0.0150),
        ("2008-10-29", 0.0100),
        ("2008-12-16", 0.0025),
        ("2015-12-17", 0.0050),
        ("2016-12-14", 0.0075),
        ("2017-03-16", 0.0100),
        ("2017-06-15", 0.0125),
        ("2017-12-14", 0.0150),
        ("2018-03-22", 0.0175),
        ("2018-06-14", 0.0200),
        ("2018-09-27", 0.0225),
        ("2018-12-20", 0.0250),
        ("2019-08-01", 0.0225),
        ("2019-09-19", 0.0200),
        ("2019-10-31", 0.0175),
        ("2020-03-03", 0.0125),
        ("2020-03-16", 0.0025),
        ("2022-03-17", 0.0050),
        ("2022-05-05", 0.0100),
        ("2022-06-16", 0.0175),
        ("2022-07-28", 0.0250),
        ("2022-09-22", 0.0325),
        ("2022-11-03", 0.0400),
        ("2022-12-15", 0.0450),
        ("2023-02-02", 0.0475),
        ("2023-03-23", 0.0500),
        ("2023-05-04", 0.0525),
        ("2023-07-27", 0.0550),
        ("2024-09-19", 0.0500),
        ("2024-11-08", 0.0475),
        ("2024-12-19", 0.0450),
    ],
    "EUR": [  # ECB main refinancing / deposit facility rate
        ("2000-01-01", 0.0350),
        ("2000-02-04", 0.0325),
        ("2000-03-17", 0.0350),
        ("2000-04-28", 0.0375),
        ("2000-06-09", 0.0425),
        ("2001-05-11", 0.0400),
        ("2001-08-31", 0.0375),
        ("2001-09-18", 0.0325),
        ("2001-11-09", 0.0275),
        ("2002-12-06", 0.0250),
        ("2003-03-07", 0.0225),
        ("2003-06-06", 0.0200),
        ("2005-12-06", 0.0225),
        ("2006-03-08", 0.0250),
        ("2006-06-15", 0.0275),
        ("2006-08-09", 0.0300),
        ("2006-10-11", 0.0325),
        ("2006-12-13", 0.0350),
        ("2007-03-14", 0.0375),
        ("2007-06-13", 0.0400),
        ("2008-07-09", 0.0425),
        ("2008-10-08", 0.0375),
        ("2008-11-06", 0.0325),
        ("2008-12-04", 0.0250),
        ("2009-01-15", 0.0200),
        ("2009-03-05", 0.0150),
        ("2009-04-02", 0.0125),
        ("2009-05-07", 0.0100),
        ("2011-04-07", 0.0125),
        ("2011-07-07", 0.0150),
        ("2011-11-03", 0.0125),
        ("2011-12-08", 0.0100),
        ("2012-07-05", 0.0075),
        ("2013-05-02", 0.0050),
        ("2013-11-07", 0.0025),
        ("2014-06-05", 0.0015),
        ("2014-09-04", 0.0005),
        ("2016-03-10", 0.0000),
        ("2022-07-21", 0.0050),
        ("2022-09-08", 0.0125),
        ("2022-10-27", 0.0200),
        ("2022-12-15", 0.0250),
        ("2023-02-02", 0.0300),
        ("2023-03-16", 0.0350),
        ("2023-05-04", 0.0375),
        ("2023-06-15", 0.0400),
        ("2023-09-14", 0.0450),
        ("2024-06-06", 0.0425),
        ("2024-09-12", 0.0375),
        ("2024-10-17", 0.0325),
        ("2024-12-12", 0.0300),
        ("2025-01-30", 0.0275),
        ("2025-03-06", 0.0250),
    ],
    "JPY": [  # BOJ policy rate / overnight call rate
        ("2000-01-01", 0.0000),
        ("2006-07-14", 0.0025),
        ("2007-02-21", 0.0050),
        ("2008-10-31", 0.0030),
        ("2008-12-19", 0.0010),
        ("2010-10-05", 0.0000),
        ("2016-02-16", -0.0010),
        ("2024-03-19", 0.0000),
        ("2024-07-31", 0.0025),
        ("2025-01-24", 0.0050),
    ],
    "GBP": [  # Bank of England base rate
        ("2000-01-01", 0.0550),
        ("2001-02-08", 0.0525),
        ("2001-04-05", 0.0500),
        ("2001-05-10", 0.0475),
        ("2001-08-02", 0.0450),
        ("2001-09-18", 0.0425),
        ("2001-10-04", 0.0375),
        ("2001-11-08", 0.0350),
        ("2003-02-06", 0.0375),
        ("2003-07-10", 0.0350),
        ("2003-11-06", 0.0375),
        ("2004-02-05", 0.0400),
        ("2004-05-06", 0.0425),
        ("2004-06-10", 0.0450),
        ("2004-08-05", 0.0475),
        ("2005-08-04", 0.0450),
        ("2006-08-03", 0.0475),
        ("2006-11-09", 0.0500),
        ("2007-01-11", 0.0525),
        ("2007-05-10", 0.0550),
        ("2007-07-05", 0.0575),
        ("2007-12-06", 0.0550),
        ("2008-02-07", 0.0525),
        ("2008-04-10", 0.0500),
        ("2008-10-08", 0.0450),
        ("2008-11-06", 0.0300),
        ("2008-12-04", 0.0200),
        ("2009-01-08", 0.0150),
        ("2009-02-05", 0.0100),
        ("2009-03-05", 0.0050),
        ("2016-08-04", 0.0025),
        ("2017-11-02", 0.0050),
        ("2018-08-02", 0.0075),
        ("2020-03-11", 0.0025),
        ("2020-03-19", 0.0010),
        ("2021-12-16", 0.0025),
        ("2022-02-03", 0.0050),
        ("2022-03-17", 0.0075),
        ("2022-05-05", 0.0100),
        ("2022-06-16", 0.0125),
        ("2022-08-04", 0.0175),
        ("2022-09-22", 0.0225),
        ("2022-11-03", 0.0300),
        ("2022-12-15", 0.0350),
        ("2023-02-02", 0.0400),
        ("2023-03-23", 0.0425),
        ("2023-05-11", 0.0450),
        ("2023-06-22", 0.0500),
        ("2023-08-03", 0.0525),
        ("2024-08-01", 0.0500),
        ("2024-11-07", 0.0475),
        ("2025-02-06", 0.0450),
    ],
    "CAD": [  # Bank of Canada overnight rate
        ("2000-01-01", 0.0475),
        ("2001-01-23", 0.0450),
        ("2001-03-06", 0.0425),
        ("2001-04-17", 0.0400),
        ("2001-05-29", 0.0375),
        ("2001-09-17", 0.0300),
        ("2001-10-23", 0.0250),
        ("2002-01-15", 0.0200),
        ("2002-04-16", 0.0225),
        ("2002-07-16", 0.0275),
        ("2003-03-04", 0.0300),
        ("2003-04-15", 0.0325),
        ("2003-07-15", 0.0275),
        ("2004-04-13", 0.0200),
        ("2004-09-08", 0.0225),
        ("2004-10-19", 0.0250),
        ("2005-03-02", 0.0225),
        ("2005-09-07", 0.0250),
        ("2005-10-18", 0.0275),
        ("2006-01-25", 0.0325),
        ("2006-04-25", 0.0375),
        ("2006-05-24", 0.0400),
        ("2006-07-11", 0.0425),
        ("2007-07-10", 0.0450),
        ("2007-12-04", 0.0425),
        ("2008-01-22", 0.0400),
        ("2008-03-04", 0.0350),
        ("2008-04-22", 0.0300),
        ("2008-10-08", 0.0250),
        ("2008-10-21", 0.0225),
        ("2008-12-09", 0.0150),
        ("2009-01-20", 0.0100),
        ("2009-03-03", 0.0050),
        ("2009-04-21", 0.0025),
        ("2010-06-01", 0.0050),
        ("2010-07-20", 0.0075),
        ("2010-09-08", 0.0100),
        ("2015-01-21", 0.0075),
        ("2015-07-15", 0.0050),
        ("2017-07-12", 0.0075),
        ("2017-09-06", 0.0100),
        ("2018-01-17", 0.0125),
        ("2018-07-11", 0.0150),
        ("2018-10-24", 0.0175),
        ("2020-03-04", 0.0125),
        ("2020-03-13", 0.0075),
        ("2020-03-27", 0.0025),
        ("2022-03-02", 0.0050),
        ("2022-04-13", 0.0100),
        ("2022-06-01", 0.0150),
        ("2022-07-13", 0.0250),
        ("2022-09-07", 0.0325),
        ("2022-10-26", 0.0375),
        ("2022-12-07", 0.0425),
        ("2023-01-25", 0.0450),
        ("2023-06-07", 0.0475),
        ("2023-07-12", 0.0500),
        ("2024-06-05", 0.0475),
        ("2024-07-24", 0.0450),
        ("2024-09-04", 0.0425),
        ("2024-10-23", 0.0375),
        ("2024-12-11", 0.0325),
        ("2025-01-29", 0.0300),
        ("2025-03-12", 0.0275),
    ],
    "AUD": [  # RBA cash rate
        ("2000-01-01", 0.0500),
        ("2000-02-02", 0.0550),
        ("2000-04-05", 0.0575),
        ("2000-05-03", 0.0600),
        ("2000-08-02", 0.0625),
        ("2001-02-07", 0.0575),
        ("2001-03-07", 0.0525),
        ("2001-04-04", 0.0500),
        ("2001-05-02", 0.0475),
        ("2001-09-05", 0.0425),
        ("2001-10-03", 0.0400),
        ("2001-12-05", 0.0375),
        ("2002-05-08", 0.0425),
        ("2002-06-05", 0.0475),
        ("2003-07-02", 0.0475),
        ("2003-11-05", 0.0500),
        ("2003-12-03", 0.0525),
        ("2005-03-02", 0.0550),
        ("2006-05-03", 0.0575),
        ("2006-08-02", 0.0600),
        ("2006-11-08", 0.0625),
        ("2007-08-08", 0.0650),
        ("2007-11-07", 0.0675),
        ("2008-02-06", 0.0700),
        ("2008-03-05", 0.0725),
        ("2008-09-03", 0.0700),
        ("2008-10-08", 0.0600),
        ("2008-11-05", 0.0525),
        ("2008-12-03", 0.0425),
        ("2009-02-04", 0.0325),
        ("2009-04-08", 0.0300),
        ("2009-10-07", 0.0325),
        ("2009-11-04", 0.0350),
        ("2009-12-02", 0.0375),
        ("2010-03-03", 0.0400),
        ("2010-04-07", 0.0425),
        ("2010-05-05", 0.0450),
        ("2010-11-03", 0.0475),
        ("2011-05-04", 0.0475),
        ("2011-11-02", 0.0450),
        ("2011-12-06", 0.0425),
        ("2012-05-02", 0.0375),
        ("2012-06-06", 0.0350),
        ("2012-10-03", 0.0325),
        ("2012-12-05", 0.0300),
        ("2013-05-08", 0.0275),
        ("2013-08-07", 0.0250),
        ("2014-08-06", 0.0250),
        ("2015-02-04", 0.0225),
        ("2015-05-06", 0.0200),
        ("2016-05-04", 0.0175),
        ("2016-08-03", 0.0150),
        ("2020-03-04", 0.0050),
        ("2020-03-20", 0.0025),
        ("2020-11-04", 0.0010),
        ("2022-05-04", 0.0035),
        ("2022-06-08", 0.0085),
        ("2022-07-06", 0.0135),
        ("2022-08-03", 0.0185),
        ("2022-09-07", 0.0235),
        ("2022-10-05", 0.0260),
        ("2022-11-02", 0.0285),
        ("2022-12-07", 0.0310),
        ("2023-02-08", 0.0335),
        ("2023-03-08", 0.0360),
        ("2023-05-03", 0.0385),
        ("2023-06-07", 0.0410),
        ("2023-11-08", 0.0435),
        ("2024-11-05", 0.0435),
        ("2025-02-18", 0.0410),
    ],
    "CNY": [  # PBoC 1-year LPR (approximate short-term proxy)
        ("2000-01-01", 0.0531),
        ("2002-02-21", 0.0531),
        ("2004-10-29", 0.0558),
        ("2006-04-28", 0.0585),
        ("2006-08-19", 0.0612),
        ("2007-03-18", 0.0639),
        ("2007-05-19", 0.0666),
        ("2007-07-21", 0.0683),
        ("2007-08-22", 0.0693),
        ("2007-09-15", 0.0720),
        ("2007-12-21", 0.0747),
        ("2008-09-16", 0.0720),
        ("2008-10-09", 0.0693),
        ("2008-10-30", 0.0666),
        ("2008-11-27", 0.0558),
        ("2008-12-23", 0.0531),
        ("2010-10-20", 0.0556),
        ("2010-12-26", 0.0581),
        ("2011-02-09", 0.0606),
        ("2011-04-06", 0.0631),
        ("2011-07-07", 0.0656),
        ("2012-06-08", 0.0631),
        ("2012-07-06", 0.0600),
        ("2013-01-01", 0.0600),
        ("2014-11-22", 0.0560),
        ("2015-03-01", 0.0535),
        ("2015-05-11", 0.0510),
        ("2015-06-28", 0.0485),
        ("2015-08-26", 0.0460),
        ("2015-10-24", 0.0435),
        ("2019-08-20", 0.0425),
        ("2019-09-20", 0.0420),
        ("2019-11-20", 0.0415),
        ("2020-02-20", 0.0405),
        ("2020-04-20", 0.0385),
        ("2022-01-20", 0.0370),
        ("2022-08-22", 0.0365),
        ("2023-06-20", 0.0355),
        ("2023-08-21", 0.0345),
        ("2024-07-22", 0.0335),
        ("2024-10-21", 0.0310),
    ],
}

# For exotic EM currencies without rate data, use a default proxy rate
EM_DEFAULT_RATE = 0.05  # rough average EM policy rate


# =============================================================================
# Data download functions
# =============================================================================

def download_etf_prices(start_date=None, end_date=None, log=print):
    """Download adjusted close prices for all ETF proxies."""
    start_date = start_date or START_DATE
    end_date = end_date or END_DATE
    tickers = list(ETF_TICKERS.values())
    data = cached_download(tickers, start_date, end_date, tag="etf", log=log)

    # Handle both single and multi-ticker return formats
    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        prices = data[["Close"]].rename(columns={"Close": tickers[0]})

    # Rename columns from ticker to index name
    ticker_to_name = {v: k for k, v in ETF_TICKERS.items()}
    prices = prices.rename(columns=ticker_to_name)

    for name, ticker in ETF_TICKERS.items():
        if name in prices.columns:
            first_valid = prices[name].first_valid_index()
            if first_valid is not None and first_valid > pd.Timestamp(start_date):
                log(f"  WARNING: {name} ({ticker}) data starts {first_valid.date()}, "
                    f"not {start_date}")

    return prices


def download_fx_rates(currencies, start_date=None, end_date=None, log=print):
    """Download daily FX rates vs CHF for the given currency codes.

    Uses direct XXXCHF pairs for major currencies, and computes cross-rates
    via USD (XXXCHF = USDCHF / USDXXX) for exotic/EM currencies to avoid
    data quality issues in yfinance direct exotic/CHF pairs.
    """
    start_date = start_date or START_DATE
    end_date = end_date or END_DATE
    direct_needed = {}
    cross_needed = {}
    unavailable = []

    for ccy in currencies:
        if ccy in ("CHF", "OTHER"):
            continue
        if ccy in FX_DIRECT_CHF:
            direct_needed[ccy] = FX_DIRECT_CHF[ccy]
        elif ccy in FX_VIA_USD:
            cross_needed[ccy] = FX_VIA_USD[ccy]
        else:
            unavailable.append(ccy)

    if unavailable:
        log(f"  WARNING: No FX ticker for {unavailable} — treating as unhedged")

    # Download direct CHF pairs
    all_tickers = list(direct_needed.values()) + list(cross_needed.values())
    if not all_tickers:
        return pd.DataFrame()

    data = cached_download(all_tickers, start_date, end_date, tag="fx", log=log)

    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"]
    else:
        close = data[["Close"]].rename(columns={"Close": all_tickers[0]})

    # Build result DataFrame with currency codes as columns (values = CCY/CHF rate)
    fx = pd.DataFrame(index=close.index)

    # Direct pairs: already in XXXCHF format
    for ccy, ticker in direct_needed.items():
        if ticker in close.columns:
            fx[ccy] = close[ticker]

    # Cross-rate pairs: XXXCHF = USDCHF / USDXXX
    usdchf_ticker = FX_DIRECT_CHF["USD"]
    if usdchf_ticker in close.columns and cross_needed:
        usdchf = close[usdchf_ticker]
        for ccy, ticker in cross_needed.items():
            if ticker in close.columns:
                usdxxx = close[ticker]
                fx[ccy] = usdchf / usdxxx

    # Check for missing/empty columns
    for ccy in list(fx.columns):
        if fx[ccy].dropna().empty:
            log(f"  WARNING: No data for {ccy}/CHF — treating as unhedged")
            fx = fx.drop(columns=[ccy])

    return fx


def build_rate_series(currencies, index, start_date=None, log=print):
    """Build a DataFrame of daily interest rates for each currency, aligned to index."""
    start_date = start_date or START_DATE
    rates = pd.DataFrame(index=index)

    for ccy in currencies:
        if ccy in ("CHF", "OTHER"):
            continue

        if ccy in POLICY_RATES:
            entries = POLICY_RATES[ccy]
        else:
            # Use EM default rate for exotic currencies
            entries = [(start_date, EM_DEFAULT_RATE)]
            log(f"  Using default rate ({EM_DEFAULT_RATE:.1%}) for {ccy}")

        # Build series from step function
        rate_series = pd.Series(dtype=float, index=index)
        for i, (date_str, rate) in enumerate(entries):
            start = pd.Timestamp(date_str)
            if i + 1 < len(entries):
                end = pd.Timestamp(entries[i + 1][0]) - pd.Timedelta(days=1)
            else:
                end = index[-1]
            mask = (index >= start) & (index <= end)
            rate_series[mask] = rate

        # Forward-fill any gaps at the start
        rate_series = rate_series.ffill().bfill()
        rates[ccy] = rate_series

    # Always include CHF
    chf_series = pd.Series(dtype=float, index=index)
    for i, (date_str, rate) in enumerate(POLICY_RATES["CHF"]):
        start = pd.Timestamp(date_str)
        if i + 1 < len(POLICY_RATES["CHF"]):
            end = pd.Timestamp(POLICY_RATES["CHF"][i + 1][0]) - pd.Timedelta(days=1)
        else:
            end = index[-1]
        mask = (index >= start) & (index <= end)
        chf_series[mask] = rate
    chf_series = chf_series.ffill().bfill()
    rates["CHF"] = chf_series

    return rates


# =============================================================================
# Hedging computation
# =============================================================================

def compute_hedged_returns(etf_prices, fx_rates, rates, currency_weights):
    """
    Compute monthly return series for each index:
      - unhedged_chf: ETF in USD converted to CHF at spot
      - usd_hedged_chf: hedge 100% NAV from USD to CHF via 1M forward
      - basket_hedged_chf: hedge each currency component independently to CHF
    """
    results = {}

    for index_name in etf_prices.columns:
        if etf_prices[index_name].dropna().empty:
            continue

        # Resample to month-end
        etf_m = etf_prices[index_name].dropna().resample("ME").last().dropna()
        usdchf_m = fx_rates["USD"].reindex(etf_prices.index).ffill().resample("ME").last()

        # Align
        common_idx = etf_m.index.intersection(usdchf_m.dropna().index)
        if len(common_idx) < 3:
            print(f"  Skipping {index_name}: insufficient overlapping data")
            continue

        etf_m = etf_m.loc[common_idx]
        usdchf_m = usdchf_m.loc[common_idx]

        # Monthly returns
        r_etf_usd = etf_m.pct_change()  # ETF return in USD

        # Unhedged CHF return: (1 + R_usd) * (1 + R_usdchf) - 1
        usdchf_ret = usdchf_m.pct_change()
        r_unhedged_chf = (1 + r_etf_usd) * (1 + usdchf_ret) - 1

        # Monthly rates (resample to month-end, use last known rate)
        rates_m = rates.reindex(etf_prices.index).ffill().resample("ME").last()
        rates_m = rates_m.loc[common_idx]

        # --- USD-only hedge ---
        r_chf = rates_m["CHF"]
        r_usd = rates_m["USD"] if "USD" in rates_m.columns else pd.Series(0.0, index=common_idx)
        # 1M forward rate: F = S * (1 + r_CHF * 30/360) / (1 + r_USD * 30/360)
        fwd_ratio_usd = (1 + r_chf * 30 / 360) / (1 + r_usd * 30 / 360)
        # Hedged return: (1 + R_etf_usd) * fwd_ratio - 1
        r_usd_hedged = (1 + r_etf_usd) * fwd_ratio_usd - 1

        # --- Full basket hedge ---
        weights = currency_weights.get(index_name, {"USD": 1.0})

        # Compute weighted FX return of the basket vs CHF
        fx_basket_ret = pd.Series(0.0, index=common_idx)
        fwd_carry = pd.Series(0.0, index=common_idx)

        for ccy, w in weights.items():
            if ccy in ("CHF", "OTHER") or w == 0:
                continue

            # FX return for this currency vs CHF
            if ccy == "USD":
                fx_ccy_ret = usdchf_ret
            elif ccy in fx_rates.columns:
                fx_ccy_m = fx_rates[ccy].reindex(etf_prices.index).ffill().resample("ME").last()
                fx_ccy_m = fx_ccy_m.loc[common_idx]
                fx_ccy_ret = fx_ccy_m.pct_change()
            else:
                # Currency not available — skip (treated as unhedged / zero contribution)
                continue

            # Fill NaN FX returns with 0 (treat as unhedged in periods with missing data)
            fx_ccy_ret = fx_ccy_ret.fillna(0)

            # Clip extreme FX returns (data quality issues in exotic pairs)
            MAX_MONTHLY_FX_RET = 0.25  # ±25% monthly FX move cap
            clipped = fx_ccy_ret.clip(-MAX_MONTHLY_FX_RET, MAX_MONTHLY_FX_RET)
            n_clipped = (clipped != fx_ccy_ret).sum()
            if n_clipped > 0:
                print(f"    Clipped {n_clipped} extreme {ccy}/CHF monthly returns")
            fx_ccy_ret = clipped

            fx_basket_ret = fx_basket_ret + w * fx_ccy_ret

            # Forward carry for this currency
            r_foreign = rates_m[ccy] if ccy in rates_m.columns else EM_DEFAULT_RATE
            carry = w * (r_chf - r_foreign) * 30 / 360
            fwd_carry = fwd_carry + carry.fillna(0)

        # Basket hedged = unhedged - actual FX moves + forward carry
        r_basket_hedged = r_unhedged_chf - fx_basket_ret + fwd_carry

        # Drop first row (NaN from pct_change)
        r_unhedged_chf = r_unhedged_chf.iloc[1:]
        r_usd_hedged = r_usd_hedged.iloc[1:]
        r_basket_hedged = r_basket_hedged.iloc[1:]

        results[index_name] = pd.DataFrame({
            "Unhedged CHF": r_unhedged_chf,
            "USD-hedged CHF": r_usd_hedged,
            "Basket-hedged CHF": r_basket_hedged,
        })

    return results


# =============================================================================
# Metrics
# =============================================================================

def compute_metrics(monthly_returns):
    """Compute annualized return, vol, Sharpe, and max drawdown."""
    n_months = len(monthly_returns)
    cum = (1 + monthly_returns).cumprod()
    total_return = cum.iloc[-1] - 1

    if total_return > -1:
        ann_return = (1 + total_return) ** (12 / n_months) - 1
    else:
        ann_return = -1.0  # total loss
    ann_vol = monthly_returns.std() * np.sqrt(12)
    sharpe = ann_return / ann_vol

    # Max drawdown
    peak = cum.cummax()
    drawdown = (cum - peak) / peak
    max_dd = drawdown.min()

    return {
        "Ann. Return": ann_return,
        "Ann. Vol": ann_vol,
        "Sharpe": sharpe,
        "Max Drawdown": max_dd,
        "Total Return": total_return,
        "Months": n_months,
    }


def print_summary(results):
    """Print a formatted summary table to terminal."""
    print("\n" + "=" * 90)
    print("HEDGING EFFICIENCY BACKTEST — MSCI INDEX FUNDS IN CHF")
    print("=" * 90)

    for index_name, df in results.items():
        first_date = df.index[0].strftime("%Y-%m")
        last_date = df.index[-1].strftime("%Y-%m")
        print(f"\n{index_name}  ({first_date} to {last_date})")
        print("-" * 80)
        print(f"  {'Strategy':<22} {'Ann.Ret':>8} {'Ann.Vol':>8} {'Sharpe':>8} "
              f"{'MaxDD':>8} {'Total':>9}")
        print(f"  {'-'*22} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*9}")

        for col in df.columns:
            m = compute_metrics(df[col])
            print(f"  {col:<22} {m['Ann. Return']:>7.1%} {m['Ann. Vol']:>7.1%} "
                  f"{m['Sharpe']:>8.2f} {m['Max Drawdown']:>7.1%} {m['Total Return']:>8.1%}")

    print("\n" + "=" * 90)


# =============================================================================
# Plotting
# =============================================================================

STRATEGY_COLORS = {
    "Unhedged CHF": "#e74c3c",
    "USD-hedged CHF": "#3498db",
    "Basket-hedged CHF": "#2ecc71",
}


def plot_cumulative_returns(results, fig=None, save_path="work/hedging_cumulative_returns.png"):
    """Plot cumulative return comparison: one subplot per index.

    If fig is provided, draws into it (for GUI embedding). Otherwise creates a new figure.
    Returns the figure.
    """
    n = len(results)
    if fig is None:
        fig, axes = plt.subplots(n, 1, figsize=(12, 5 * n), sharex=False)
    else:
        fig.clear()
        axes = [fig.add_subplot(n, 1, i + 1) for i in range(n)]
    if n == 1:
        axes = [axes] if not isinstance(axes, list) else axes

    for ax, (index_name, df) in zip(axes, results.items()):
        cum = (1 + df).cumprod() * 100  # indexed to 100
        for col in df.columns:
            ax.plot(cum.index, cum[col], label=col, color=STRATEGY_COLORS.get(col, "gray"),
                    linewidth=1.5)
        ax.set_title(f"{index_name} — Cumulative Return (indexed to 100)", fontsize=13)
        ax.set_ylabel("Value")
        ax.legend(loc="upper left")
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator(2))

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved: {save_path}")
    return fig


def plot_rolling_volatility(results, window=12, fig=None,
                            save_path="work/hedging_rolling_volatility.png"):
    """Plot rolling 12-month annualized volatility.

    If fig is provided, draws into it (for GUI embedding). Otherwise creates a new figure.
    Returns the figure.
    """
    n = len(results)
    if fig is None:
        fig, axes = plt.subplots(n, 1, figsize=(12, 5 * n), sharex=False)
    else:
        fig.clear()
        axes = [fig.add_subplot(n, 1, i + 1) for i in range(n)]
    if n == 1:
        axes = [axes] if not isinstance(axes, list) else axes

    for ax, (index_name, df) in zip(axes, results.items()):
        rolling_vol = df.rolling(window).std() * np.sqrt(12) * 100  # in %
        for col in df.columns:
            ax.plot(rolling_vol.index, rolling_vol[col], label=col,
                    color=STRATEGY_COLORS.get(col, "gray"), linewidth=1.5)
        ax.set_title(f"{index_name} — Rolling {window}M Annualized Volatility", fontsize=13)
        ax.set_ylabel("Volatility (%)")
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator(2))

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Saved: {save_path}")
    return fig


# =============================================================================
# Backtest pipeline
# =============================================================================

def run_backtest(start_date=None, end_date=None, log=print):
    """Run the full backtest pipeline and return results dict.

    Args:
        start_date: Start date string (YYYY-MM-DD). Defaults to START_DATE.
        end_date: End date string (YYYY-MM-DD). Defaults to END_DATE.
        log: Logging function (print for CLI, or a GUI callback).

    Returns:
        dict mapping index name -> DataFrame of monthly returns,
        or None if no results could be computed.
    """
    log("Downloading ETF prices...")
    etf_prices = download_etf_prices(start_date, end_date, log=log)

    all_currencies = set()
    for weights in CURRENCY_WEIGHTS.values():
        all_currencies.update(weights.keys())
    all_currencies.discard("CHF")
    all_currencies.discard("OTHER")

    log("Downloading FX rates...")
    fx_rates = download_fx_rates(all_currencies, start_date, end_date, log=log)

    log("Building interest rate series...")
    rates = build_rate_series(all_currencies, etf_prices.index,
                              start_date=start_date, log=log)

    log("Computing hedged returns...")
    results = compute_hedged_returns(etf_prices, fx_rates, rates, CURRENCY_WEIGHTS)

    if not results:
        log("ERROR: No results computed. Check data availability.")
        return None

    return results


# =============================================================================
# Main (CLI entry point)
# =============================================================================

def main():
    results = run_backtest()
    if results is None:
        return

    print_summary(results)
    plot_cumulative_returns(results)
    plot_rolling_volatility(results)
    plt.close("all")

    for index_name, df in results.items():
        safe_name = index_name.replace(" ", "_").lower()
        path = f"work/hedging_{safe_name}_monthly_returns.csv"
        df.to_csv(path)
        print(f"Saved: {path}")


if __name__ == "__main__":
    main()
