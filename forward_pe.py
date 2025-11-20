import yfinance as yf
import requests
from bs4 import BeautifulSoup

def get_forward_pe(ticker):
    stock = yf.Ticker(ticker)
    pe = stock.info.get('forwardPE', None)
    return pe

def get_eps_growth_finviz(ticker):
    url = f'https://finviz.com/quote.ashx?t={ticker}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'lxml')
    
    try:
        # Find the growth value (label: 'EPS next 5Y')
        table = soup.find('table', class_='snapshot-table2')
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            for i in range(len(cols)):
                if cols[i].text.strip() == 'EPS next 5Y':
                    growth_text = cols[i+1].text.strip().replace('%', '')
                    return float(growth_text) / 100  # convert to decimal
    except Exception as e:
        print(f"Error scraping EPS growth: {e}")
        return None

def calculate_peg(ticker):
    pe = get_forward_pe(ticker)
    growth = get_eps_growth_finviz(ticker)

    if pe is None:
        print("Could not retrieve forward P/E.")
        return
    if growth is None or growth == 0:
        print("Could not retrieve valid EPS growth rate.")
        return
    
    peg = pe / (growth*100)
    print(f"\nTicker: {ticker}")
    print(f"Forward P/E: {pe:.2f}")
    print(f"Expected EPS Growth (5Y): {growth*100:.2f}% per year")
    print(f"PEG Ratio: {peg:.2f}")

# Run for Amazon
calculate_peg("PLTR")
