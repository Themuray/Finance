import yfinance as yf
import pandas as pd
from datetime import datetime


# Mapping of index names to Yahoo Finance tickers
INDEX_TICKERS = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "Nasdaq Composite": "^IXIC",
    "DAX": "^GDAXI",
    "SMI": "^SSMI",
    "Euro Stoxx 50": "^STOXX50E",
    "MSCI China": "MCHI",
    "MSCI World": "URTH",
    "MSCI Emerging Markets": "EEM",
}


def download_index_data(
    start: str = "2000-01-01",
    end: str | None = None,
    interval: str = "1d",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Download price history for major indices and return:
      - prices: daily adjusted close prices for each index
      - returns: daily percentage returns for each index

    Parameters
    ----------
    start : str
        Start date (YYYY-MM-DD).
    end : str | None
        End date (YYYY-MM-DD). Defaults to today's date when None.
    interval : str
        Data frequency, e.g. "1d", "1wk", "1mo".
    """
    if end is None:
        end = datetime.today().strftime("%Y-%m-%d")

    price_frames: list[pd.Series] = []

    for name, ticker in INDEX_TICKERS.items():
        print(f"Downloading {name} ({ticker})...")
        df = yf.download(
            ticker,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )

        if df.empty:
            print(f"Warning: no data returned for {name} ({ticker})")
            continue

        # Use adjusted close if available, otherwise close
        col = "Adj Close" if "Adj Close" in df.columns else "Close"
        price_series = df[col].rename(name)
        price_frames.append(price_series)

    if not price_frames:
        raise RuntimeError("No index data was downloaded; check tickers or internet connection.")

    prices = pd.concat(price_frames, axis=1).sort_index()
    returns = prices.pct_change().dropna(how="all")

    # Persist to CSV for later analysis
    prices.to_csv("indices_prices.csv")
    returns.to_csv("indices_returns.csv")

    print("Saved prices to 'indices_prices.csv' and returns to 'indices_returns.csv'.")
    return prices, returns


if __name__ == "__main__":
    # Example usage: daily data from 2000-01-01 to today
    download_index_data()



INDEX_TICKERS = {
    "SP500": "^GSPC",              # S&P 500
    "NASDAQ100": "^NDX",           # Nasdaq 100
    "NASDAQComposite": "^IXIC",    # Nasdaq Composite
    "DAX": "^GDAXI",               # DAX
    "SMI": "^SSMI",                # Swiss Market Index
    "EuroStoxx50": "^STOXX50E",    # Euro Stoxx 50
    # China: using CSI 300 as a broad large-cap China proxy
    "China_CSI300": "000300.SS",
    # MSCI World / Emerging Markets: using liquid ETF proxies
    "MSCI_World_ETF": "URTH",
    "MSCI_EM_ETF": "EEM",
}


def download_indices(start: str = "2000-01-01",
                     end: str | None = None,
                     interval: str = "1d",
                     auto_adjust: bool = True) -> pd.DataFrame:
    """
    Download historical price data for a set of major indices using yfinance.

    Parameters
    ----------
    start : str
        Start date in 'YYYY-MM-DD' format.
    end : str | None
        End date in 'YYYY-MM-DD' format. If None, uses today's date.
    interval : str
        Data interval ('1d', '1wk', '1mo', ...).
    auto_adjust : bool
        If True, use adjusted (total return) prices.

    Returns
    -------
    pd.DataFrame
        Wide DataFrame with one column per index (Adj Close if auto_adjust,
        otherwise Close).
    """
    if end is None:
        end = datetime.today().strftime("%Y-%m-%d")

    tickers = list(INDEX_TICKERS.values())

    data = yf.download(
        tickers=tickers,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=auto_adjust,
        progress=False,
    )

    # If multiple tickers, yfinance returns a column MultiIndex
    if isinstance(data.columns, pd.MultiIndex):
        # Use 'Adj Close' if available, otherwise 'Close'
        price_field = "Adj Close" if "Adj Close" in data.columns.levels[0] else "Close"
        prices = data[price_field].copy()
    else:
        prices = data.copy()

    # Rename columns from ticker to friendly index name
    ticker_to_name = {v: k for k, v in INDEX_TICKERS.items()}
    prices = prices.rename(columns=ticker_to_name)

    return prices


def save_indices_to_csv(
    filepath: str = "indices_prices.csv",
    start: str = "2000-01-01",
    end: str | None = None,
    interval: str = "1d",
    auto_adjust: bool = True,
) -> None:
    """
    Convenience wrapper to download indices and save them to a CSV.
    """
    prices = download_indices(
        start=start,
        end=end,
        interval=interval,
        auto_adjust=auto_adjust,
    )
    prices.to_csv(filepath, index=True)
    print(f"Saved index prices to {filepath}")


if __name__ == "__main__":
    # Example: download from 2000-01-01 to today (daily data)
    save_indices_to_csv(
        filepath="indices_prices.csv",
        start="2000-01-01",
        end=None,
        interval="1d",
        auto_adjust=True,
    )


