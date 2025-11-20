'''import yfinance as yf
import pandas as pd

# Get tickers from Wikipedia (example: NASDAQ-100)
url = 'https://en.wikipedia.org/wiki/NASDAQ-100'
url2 = 'https://de.wikipedia.org/wiki/Swiss_Market_Index'
tables = pd.read_html(url2)

# The first table usually contains the tickers
df = tables[1]  # This can vary if Wikipedia page structure changes

tickers = df['Ticker'].tolist()
tickers = [ticker.replace('.', '-') for ticker in tickers]  # For BRK.B, etc.

print(tickers)
print(len(tickers))

# Now you can use it with yfinance:
data = yf.download(tickers, period="1d", group_by='ticker')[Close]
print(data)'''

import yfinance as yf
import pandas as pd

def extract_tickers_from_url(url):
    """Try to find and return ticker symbols from a Wikipedia page."""
    tables = pd.read_html(url)

    for idx, table in enumerate(tables):
        for column in table.columns:
            if column in ["Symbol", "Ticker"]:
                tickers = table[column].dropna().astype(str).tolist()
                tickers = [ticker.replace('.', '-') for ticker in tickers]  # e.g. BRK.B → BRK-B
                print(f"✅ Found tickers in table {idx}, column '{column}'")
                return tickers

    raise ValueError("❌ No column named 'Symbol' or 'Ticker' found on the page.")

def download_data(tickers, period="1d"):
    """Download historical data from yfinance"""
    return yf.download(tickers, period=period, group_by='ticker')

# Example: Change this to any valid Wikipedia index page
url = 'https://en.wikipedia.org/wiki/NASDAQ-100'
tickers = extract_tickers_from_url(url)
print(f"✅ Tickers:\n{tickers}\n")

# Optional: Download data
data = download_data(tickers)
print(data.head())
