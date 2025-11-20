import yfinance as yf
import requests
from bs4 import BeautifulSoup
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

def get_eps_next_y_growth_percent(ticker):
    url = f'https://finviz.com/quote.ashx?t={ticker}'
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'lxml')

    try:
        table = soup.find('table', class_='snapshot-table2')
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            for i in range(len(cells)):
                if cells[i].text.strip() == 'EPS next Y':
                    value = cells[i + 1].text.strip()
                    if '%' in value:
                        return float(value.replace('%', ''))
        print(f"No percentage EPS next Y found for {ticker}")
        return None
    except Exception as e:
        print(f"Error parsing Finviz data for {ticker}: {e}")
        return None

def safe_round(val, digits=2):
    try:
        return round(val, digits) if val is not None else float('nan')
    except:
        return float('nan')

def safe_div(a, b):
    try:
        return a / b if a is not None and b not in [0, None] else float('nan')
    except:
        return float('nan')

def get_metrics(ticker):
    print(f"Retrieving: {ticker}")
    stock = yf.Ticker(ticker)

    try:
        info = stock.info
    except Exception as e:
        print(f"Skipping {ticker} due to error fetching info: {e}")
        return {"Ticker": ticker}

    try:
        # Base info
        price = info.get("currentPrice")
        target = info.get("targetMeanPrice")
        tPE = info.get('trailingPE')
        fPE = info.get('forwardPE')
        ps = info.get('priceToSalesTrailing12Months')
        ev = info.get("enterpriseValue")
        gp = info.get("grossProfits")
        rg = safe_div(info.get('revenueGrowth'), 1) * 100
        ebitda = info.get("ebitda")
        trailing_peg_yf = info.get("trailingPegRatio")
        insiders = safe_div(info.get("heldPercentInsiders"), 1) * 100
        analyst_num = info.get("numberOfAnalystOpinions")
        status = info.get("recommendationKey", "N/A")
        growth_pct = get_eps_next_y_growth_percent(ticker) or float('nan')

        # Calculations
        trailing_peg = safe_div(tPE, growth_pct)
        ev_to_ebitda = safe_div(ev, ebitda)
        ev_peg = safe_div(ev_to_ebitda, growth_pct)
        ev_gp = safe_div(ev, gp)
        ev_gp_rg = safe_div(ev_gp, rg)
        upside = safe_div(target, price) - 1
        upside_pct = upside * 100

        return {
            "Ticker": ticker,
            "Price": safe_round(price),
            "Target": safe_round(target),
            "Upside %": safe_round(upside_pct),
            "PE": safe_round(tPE),
            "fPE": safe_round(fPE),
            "P/S": safe_round(ps),
            "EPS Growth %": safe_round(growth_pct),
            "PEG": safe_round(trailing_peg),
            "EV-based PEG": safe_round(ev_peg),
            "PEG 5Y": safe_round(trailing_peg_yf),
            "EV/GP": safe_round(ev_gp),
            "EV/GP/RG": safe_round(ev_gp_rg),
            "Status": status,
            "Analysts": analyst_num,
            "Insiders %": safe_round(insiders)
        }

    except Exception as e:
        print(f"Skipping {ticker} due to error: {e}")
        return {"Ticker": ticker}
        
def plot_peg_comparison(df):
    peg_data = df[["Ticker", "PEG", "EV-based PEG", "PEG 5Y"]].melt(
        id_vars="Ticker", var_name="Metric", value_name="Value")

    plt.figure(figsize=(10, 6))
    sns.barplot(data=peg_data, x="Ticker", y="Value", hue="Metric")
    plt.title("PEG Ratio Comparison (Using EPS Growth %)")
    plt.axhline(1, ls='--', c='gray', label="Fair PEG = 1")
    plt.ylabel("PEG Ratio")
    plt.tight_layout()
    plt.show()

def plot_upside(df):
    sorted_df = df.sort_values(by="Upside %", ascending=False)
    plt.figure(figsize=(10, 5))
    sns.barplot(data=sorted_df, x="Ticker", y="Upside %", palette="coolwarm")
    plt.axhline(0, ls='--', c='black')
    plt.title("Upside to Analyst Price Target (%)")
    plt.ylabel("Upside (%)")
    plt.tight_layout()
    plt.show()

def plot_insiders(df):
    sorted_df = df.sort_values(by="Insiders %", ascending=False)
    plt.figure(figsize=(10, 5))
    sns.barplot(data=sorted_df, x="Ticker", y="Insiders %", color='green')
    plt.title("Insider Ownership (%)")
    plt.ylabel("Held by Insiders (%)")
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    MAG7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    new_list = ["NU", "MELI", "NBIS", "OSCR", "IREN", "MSTR", "SOFI", "HIMS", "LFMD"]
    nasdaq_100 = ["AAPL","MSFT","GOOGL","GOOG","AMZN","NVDA","TSLA","META","ADBE","AVGO", 
                    "INTC","CSCO","CMCSA","NFLX","TXN","QCOM","PEP","COST","TMUS","AMD",
                    "AMGN","ADP","LRCX","MDLZ","ILMN","ASML","ATRI","BKNG","BIIB","CHKP",
                    "CERN","CDNS","CERN","CTSH","CSX","EA","EXC","FISV","GILD","HON",
                    "LULU","MAR","MELI","MRVL","MU","MSCI","NXPI","ORLY","PANW","PAYX",
                    "QCOM","REGN","ROST","SBUX","SNPS","TDOC","TTWO","WDAY","XLNX","ZTS",
                    "BIDU","ZM","DOCU","WORK","SNX","EXPE","EBAY","OKE","IDXX","MCHP",
                    "ADSK","FTNT","CTXS","SIRI","DLTR","PAYL","BBWI","PDD","MELI","PCAR",
                    "PLTR","PVH","TMUS","RUBI","KLAC","KHC","EBAY"] 

    stocks = nasdaq_100
    results = [get_metrics(ticker) for ticker in stocks]
    df = pd.DataFrame(results)

    df = df.sort_values(by="EV/GP")
    df.to_csv("stocks_metrics.csv", index=False)
    print(df.to_string(index=False))
    # Drop rows with missing key values for plotting
    df_clean = df.dropna(subset=["PEG", "EV-based PEG", "PEG 5Y", "Upside %", "Insiders %"])

    plot_peg_comparison(df)
    plot_upside(df)
    plot_insiders(df)
