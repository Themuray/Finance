import yfinance as yf

# QQQ ETF tracks the NASDAQ-100
qqq = yf.Ticker("QQQ")

# Get the holdings
holdings = qqq.fund_holdings

# Get tickers as a list
tickers = holdings['symbol'].tolist()
print(tickers)