
import pandas as pd
import numpy as np
import yfinance as yf

# ===== User flags =====
# Set to True to use log returns, False to use simple arithmetic returns
USE_LOG_RETURNS = True

# ===== Ticker mappings =====
# Bloomberg-style tickers (as you use them) to Yahoo Finance tickers
# Index mappings use broad, liquid proxies on Yahoo.
# AXA funds are CHF share classes listed in Switzerland; Yahoo tickers are approximated by ISIN-based tickers where available.

bloomberg_to_yahoo = {
    # Equity indices
    "SX5E Index": "^STOXX50E",   # EURO STOXX 50 [EUR]
    "SPX Index": "^GSPC",       # S&P 500 [USD]
    "NKY Index": "^N225",       # Nikkei 225 [JPY]
    "UKX Index": "^FTSE",       # FTSE 100 [GBP]
    "SMI Index": "^SSMI",       # Swiss Market Index [CHF]

    # AXA funds – CHF share classes on SIX
    # AXW71AC LX Index: AXA World Funds - Euro 7-10 (Luxembourg UCITS, EUR) – no direct Yahoo symbol is standard; keep as placeholder
    "AXW71AC LX Index": None,

    # AXA30AA SW Equity: AXA (CH) Strategy Fund - Portfolio 30 A Cap CHF [CHF]
    # AXA40AA SW Equity: AXA (CH) Strategy Fund - Portfolio 40 A Cap CHF [CHF]
    # If you know their exact Yahoo symbols, replace the None values below.
    "AXA30AA SW Equity": None,
    "AXA40AA SW Equity": None,
}

# ===== Currency and FX tickers =====
# Base currencies of each Yahoo price series
base_currency = {
    "SX5E Index": "EUR",
    "SPX Index": "USD",
    "NKY Index": "JPY",
    "UKX Index": "GBP",
    "SMI Index": "CHF",
    "AXW71AC LX Index": "EUR",
    "AXA30AA SW Equity": "CHF",
    "AXA40AA SW Equity": "CHF",
}

# Yahoo FX tickers: currency vs CHF, quoted as XXXCHF=X (price of 1 unit of XXX in CHF)
fx_to_chf = {
    "EUR": "EURCHF=X",
    "USD": "USDCHF=X",
    "JPY": "JPYCHF=X",
    "GBP": "GBPCHF=X",
    "CHF": None,
}

# ===== Build list of available Yahoo tickers =====
yahoo_price_tickers = {k: v for k, v in bloomberg_to_yahoo.items() if v is not None}

# FX tickers needed (exclude CHF which is already in CHF)
needed_fx = sorted({fx_to_chf[c] for c in base_currency.values() if fx_to_chf.get(c) is not None})

# ===== Download data =====
start_date = "1970-01-01"

print("Downloading index/fund prices from Yahoo Finance...")
price_data = yf.download(list(yahoo_price_tickers.values()), start=start_date, auto_adjust=True)["Adj Close"]

print("Downloading FX rates vs CHF from Yahoo Finance...")
fx_data = yf.download(needed_fx, start=start_date)["Adj Close"]

# ===== Prepare price data with Bloomberg-style column names =====
col_map = {v: k for k, v in yahoo_price_tickers.items()}
prices_orig = price_data.rename(columns=col_map)
prices_orig = prices_orig.sort_index().dropna(how="all")

# ===== Convert all series to CHF =====
# For each instrument, divide its original price (in base currency) by the FX rate (base/CHF)

prices_chf = pd.DataFrame(index=prices_orig.index)

for bb_ticker in prices_orig.columns:
    cur = base_currency.get(bb_ticker, "CHF")
    series = prices_orig[bb_ticker]

    if cur == "CHF" or fx_to_chf.get(cur) is None:
        # Already in CHF
        prices_chf[bb_ticker] = series
    else:
        fx_ticker = fx_to_chf[cur]
        fx_series = fx_data[fx_ticker].reindex(prices_orig.index)
        prices_chf[bb_ticker] = series / fx_series

# Drop rows where all CHF prices are NaN
prices_chf = prices_chf.dropna(how="all")

# ===== Compute returns (log or simple) in CHF =====
if USE_LOG_RETURNS:
    returns_chf = np.log(prices_chf / prices_chf.shift(1))
else:
    returns_chf = prices_chf.pct_change()

returns_chf = returns_chf.dropna(how="all")

# ===== Correlation matrix based on CHF returns =====
corr_matrix_chf = returns_chf.corr()

# ===== Save outputs =====
prices_chf.to_csv("prices_chf.csv")
returns_chf.to_csv("returns_chf.csv")
corr_matrix_chf.to_csv("correlation_matrix_chf.csv")

print("Saved prices_chf.csv, returns_chf.csv, correlation_matrix_chf.csv")
print("
Correlation matrix (CHF returns):")
print(corr_matrix_chf)

