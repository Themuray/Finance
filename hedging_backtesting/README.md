# CHF Hedging Efficiency Backtester

Backtesting tool that compares hedged vs unhedged returns for a CHF-based investor holding global MSCI index funds. Uses rolling 1-month FX forward contracts with historical interest rate differentials to simulate realistic hedging costs.

## What it does

For each index (MSCI World, MSCI ACWI, MSCI EM), the script computes three return series:

1. **Unhedged CHF** — ETF return in USD converted to CHF at spot exchange rate
2. **USD-only hedged to CHF** — Hedges 100% of NAV from USD to CHF via 1-month forward. This is what most hedged ETF share classes do in practice.
3. **Full basket hedged to CHF** — Hedges each underlying currency component (USD, EUR, JPY, GBP, etc.) to CHF independently based on MSCI regional weight breakdown. Removes all FX risk, not just USD/CHF.

## How hedging is modeled

The hedge uses **covered interest rate parity** to compute 1-month forward rates:

```
F = S × (1 + r_CHF × 30/360) / (1 + r_foreign × 30/360)
```

- Forward contracts are rolled monthly
- Interest rates come from a hardcoded policy rate table (SNB, Fed, ECB, BOJ, BOE, etc.) spanning 2006–2026
- Negative rates (e.g. SNB -0.75% from 2015–2022) are handled natively
- When CHF rates < foreign rates (most of the period), hedging has a **negative carry cost**

## Data sources

| Data | Source |
|------|--------|
| ETF prices | yfinance (URTH, ACWI, EEM as USD-denominated proxies) |
| Major FX rates (USD, EUR, JPY, GBP, CAD, AUD) | yfinance direct CHF pairs |
| EM FX rates (CNY, TWD, INR, KRW, BRL, ZAR) | yfinance USD pairs, cross-rated via USDCHF |
| Interest rates | Hardcoded central bank policy rate history |

## Usage

```bash
pip install pandas numpy yfinance matplotlib
python hedging_backtest_msci_chf.py
```

### Configuration

All parameters are at the top of `hedging_backtest_msci_chf.py`:

- `ETF_TICKERS` — ETF proxies for each MSCI index
- `CURRENCY_WEIGHTS` — approximate currency breakdown per index (drives the basket hedge)
- `START_DATE` / `END_DATE` — backtest period (default: 2006–2026)
- `POLICY_RATES` — historical central bank rate table

## Output

### Terminal summary

Prints a table with annualized return, volatility, Sharpe ratio, max drawdown, and total return for each index × strategy combination.

### Charts (saved to `work/`)

- `hedging_cumulative_returns.png` — cumulative return indexed to 100, one subplot per index
- `hedging_rolling_volatility.png` — rolling 12-month annualized volatility

### CSV files (saved to `work/`)

- `hedging_msci_world_monthly_returns.csv`
- `hedging_msci_acwi_monthly_returns.csv`
- `hedging_msci_em_monthly_returns.csv`

## Limitations

- **MSCI World (URTH)** only has data from 2012, not the full 20-year window
- **EM currency rates** for TWD, INR, KRW, BRL, ZAR use a flat 5% default policy rate (approximate)
- **Currency weights are static** — in reality MSCI regional weights shift over time
- **Exotic FX data quality** — yfinance EM cross-rates occasionally have outliers; monthly returns are clipped at ±25% as a safeguard
- The "OTHER" currency bucket (2–16% depending on index) is left unhedged
