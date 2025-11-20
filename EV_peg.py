import yfinance as yf

def get_ev_metrics(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    try:
        ev = info['enterpriseValue']
        ebitda = info['netIncomeToCommon']
        pe_growth = info.get('earningsGrowth')  # Usually 1Y estimate
        print(info)


        print(f"EV/GP: {info['enterpriseValue']/info['grossProfits']:.2}")
        print(f"EV/GP/RevGrowth: {info['enterpriseValue']/info['grossProfits']/(info['revenueGrowth']*100):.2}")


        income = info['netIncomeToCommon']
        shares = info['sharesOutstanding']



        if ev and ebitda and pe_growth:
            ev_to_ebitda = ev / ebitda
            peg_ev = ev_to_ebitda / (pe_growth * 100)  # Growth must be in %
            print(f"EV/EBITDA: {ev_to_ebitda:.2f}")
            print(f"Growth Rate: {pe_growth * 100:.2f}%")
            print(f'EV-based PEG: {peg_ev:.2f}')
        else:
            print("Missing data for EV, EBITDA, or growth.")
    except Exception as e:
        print("Error:", e)

get_ev_metrics("AMZN")
