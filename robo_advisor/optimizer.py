"""
Markowitz Mean-Variance Optimization engine.

Pure mathematical module — no Qt or yfinance dependencies.
Takes numpy arrays (expected returns, covariance matrix) and produces
optimal portfolio allocations via scipy SLSQP.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from dataclasses import dataclass, field

TRADING_DAYS = 252


@dataclass
class PortfolioResult:
    """A single portfolio point (on or near the efficient frontier)."""
    weights: np.ndarray
    expected_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0


@dataclass
class EfficientFrontierResult:
    """Complete result of efficient frontier computation."""
    frontier_returns: np.ndarray = field(default_factory=lambda: np.array([]))
    frontier_volatilities: np.ndarray = field(default_factory=lambda: np.array([]))
    frontier_weights: np.ndarray = field(default_factory=lambda: np.array([]))
    min_variance_portfolio: PortfolioResult = field(
        default_factory=lambda: PortfolioResult(np.array([])))
    max_sharpe_portfolio: PortfolioResult = field(
        default_factory=lambda: PortfolioResult(np.array([])))
    # Random portfolios for scatter cloud
    random_returns: np.ndarray = field(default_factory=lambda: np.array([]))
    random_volatilities: np.ndarray = field(default_factory=lambda: np.array([]))
    random_sharpes: np.ndarray = field(default_factory=lambda: np.array([]))


def portfolio_performance(weights: np.ndarray, expected_returns: np.ndarray,
                          cov_matrix: np.ndarray,
                          risk_free_rate: float = 0.045) -> PortfolioResult:
    """Compute return, volatility, and Sharpe ratio for given weights.

    E[R_p] = w^T * mu
    sigma_p = sqrt(w^T * Sigma * w)
    Sharpe = (E[R_p] - r_f) / sigma_p
    """
    port_return = float(np.dot(weights, expected_returns))
    port_vol = float(np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))))
    sharpe = (port_return - risk_free_rate) / port_vol if port_vol > 0 else 0.0
    return PortfolioResult(weights, port_return, port_vol, sharpe)


def minimize_variance(expected_returns: np.ndarray, cov_matrix: np.ndarray,
                      target_return: float,
                      risk_free_rate: float = 0.045) -> PortfolioResult:
    """Find the minimum-variance portfolio for a given target return.

    min   w^T * Sigma * w
    s.t.  w^T * mu = target_return
          w^T * 1 = 1
          w_i >= 0  (no short selling)
    """
    n = len(expected_returns)
    w0 = np.ones(n) / n

    constraints = [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        {"type": "eq", "fun": lambda w: np.dot(w, expected_returns) - target_return},
    ]
    bounds = tuple((0.0, 1.0) for _ in range(n))

    result = minimize(
        lambda w: np.dot(w.T, np.dot(cov_matrix, w)),
        w0, method="SLSQP",
        bounds=bounds, constraints=constraints,
        options={"ftol": 1e-12, "maxiter": 1000},
    )

    if result.success:
        return portfolio_performance(result.x, expected_returns,
                                     cov_matrix, risk_free_rate)
    # On failure, return best attempt
    return portfolio_performance(result.x, expected_returns,
                                 cov_matrix, risk_free_rate)


def find_min_variance_portfolio(expected_returns: np.ndarray,
                                cov_matrix: np.ndarray,
                                risk_free_rate: float = 0.045) -> PortfolioResult:
    """Find the global minimum variance portfolio (no target return constraint)."""
    n = len(expected_returns)
    w0 = np.ones(n) / n

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = tuple((0.0, 1.0) for _ in range(n))

    result = minimize(
        lambda w: np.dot(w.T, np.dot(cov_matrix, w)),
        w0, method="SLSQP",
        bounds=bounds, constraints=constraints,
        options={"ftol": 1e-12, "maxiter": 1000},
    )

    return portfolio_performance(result.x, expected_returns,
                                 cov_matrix, risk_free_rate)


def find_max_sharpe_portfolio(expected_returns: np.ndarray,
                              cov_matrix: np.ndarray,
                              risk_free_rate: float = 0.045) -> PortfolioResult:
    """Find the tangency portfolio (maximum Sharpe ratio)."""
    n = len(expected_returns)
    w0 = np.ones(n) / n

    def neg_sharpe(w):
        ret = np.dot(w, expected_returns)
        vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
        return -(ret - risk_free_rate) / vol if vol > 0 else 0.0

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = tuple((0.0, 1.0) for _ in range(n))

    result = minimize(
        neg_sharpe, w0, method="SLSQP",
        bounds=bounds, constraints=constraints,
        options={"ftol": 1e-12, "maxiter": 1000},
    )

    return portfolio_performance(result.x, expected_returns,
                                 cov_matrix, risk_free_rate)


def compute_efficient_frontier(expected_returns: np.ndarray,
                               cov_matrix: np.ndarray,
                               risk_free_rate: float = 0.045,
                               num_points: int = 100,
                               num_random: int = 5000) -> EfficientFrontierResult:
    """Compute the full efficient frontier and random portfolio cloud.

    1. Find min-variance and max-Sharpe portfolios
    2. Trace the frontier from min-var return to max achievable return
    3. Generate random Dirichlet-sampled portfolios for the scatter cloud
    """
    n = len(expected_returns)

    # Regularize covariance if near-singular
    if np.linalg.matrix_rank(cov_matrix) < n:
        cov_matrix = cov_matrix + 1e-8 * np.eye(n)

    # Key portfolios
    min_var = find_min_variance_portfolio(expected_returns, cov_matrix,
                                          risk_free_rate)
    max_sharpe = find_max_sharpe_portfolio(expected_returns, cov_matrix,
                                           risk_free_rate)

    # Trace the frontier
    min_ret = min_var.expected_return
    max_ret = float(np.max(expected_returns))
    # Extend slightly beyond max individual return
    target_returns = np.linspace(min_ret, max_ret, num_points)

    frontier_rets = []
    frontier_vols = []
    frontier_wts = []

    for target in target_returns:
        result = minimize_variance(expected_returns, cov_matrix,
                                   target, risk_free_rate)
        frontier_rets.append(result.expected_return)
        frontier_vols.append(result.volatility)
        frontier_wts.append(result.weights)

    # Random portfolios (Dirichlet gives uniform random weights summing to 1)
    random_weights = np.random.dirichlet(np.ones(n), size=num_random)
    random_rets = random_weights @ expected_returns
    random_vols = np.array([
        np.sqrt(w.T @ cov_matrix @ w) for w in random_weights
    ])
    random_sharpes = np.where(
        random_vols > 0,
        (random_rets - risk_free_rate) / random_vols,
        0.0,
    )

    return EfficientFrontierResult(
        frontier_returns=np.array(frontier_rets),
        frontier_volatilities=np.array(frontier_vols),
        frontier_weights=np.array(frontier_wts),
        min_variance_portfolio=min_var,
        max_sharpe_portfolio=max_sharpe,
        random_returns=random_rets,
        random_volatilities=random_vols,
        random_sharpes=random_sharpes,
    )


def interpolate_frontier(risk_appetite: float,
                         frontier: EfficientFrontierResult,
                         expected_returns: np.ndarray,
                         cov_matrix: np.ndarray,
                         risk_free_rate: float = 0.045) -> PortfolioResult:
    """Map a risk appetite (0.0–1.0) to a portfolio on the efficient frontier.

    0.0 = minimum variance, 1.0 = maximum return on the frontier.
    """
    risk_appetite = max(0.0, min(1.0, risk_appetite))
    min_ret = frontier.min_variance_portfolio.expected_return
    max_ret = float(frontier.frontier_returns[-1])
    target = min_ret + risk_appetite * (max_ret - min_ret)
    return minimize_variance(expected_returns, cov_matrix,
                             target, risk_free_rate)


def backtest_portfolio(weights: np.ndarray, returns_df: pd.DataFrame,
                       initial_value: float = 10000.0) -> pd.DataFrame:
    """Backtest a static allocation against historical returns.

    Returns DataFrame with Portfolio_Value, Drawdown, and per-asset columns.
    """
    # Weighted daily portfolio log returns
    port_daily = (returns_df * weights).sum(axis=1)

    # Cumulative value (log returns → exp for cumulative)
    cum_return = np.exp(port_daily.cumsum())
    portfolio_value = initial_value * cum_return

    # Drawdown
    peak = portfolio_value.cummax()
    drawdown = (portfolio_value - peak) / peak

    result = pd.DataFrame({
        "Portfolio_Value": portfolio_value,
        "Drawdown": drawdown,
    })

    # Individual asset cumulative values (proportional to weight)
    for i, ticker in enumerate(returns_df.columns):
        asset_cum = initial_value * weights[i] * np.exp(returns_df[ticker].cumsum())
        result[ticker] = asset_cum

    return result


def compute_portfolio_stats(weights: np.ndarray,
                            expected_returns: np.ndarray,
                            cov_matrix: np.ndarray,
                            returns_df: pd.DataFrame,
                            risk_free_rate: float = 0.045) -> dict:
    """Compute comprehensive portfolio statistics.

    Returns dict with: expected_return, volatility, sharpe_ratio,
    sortino_ratio, max_drawdown, var_95, cvar_95, risk_free_rate.
    """
    perf = portfolio_performance(weights, expected_returns,
                                 cov_matrix, risk_free_rate)

    # Daily portfolio returns for empirical stats
    port_daily = (returns_df * weights).sum(axis=1)

    # Max drawdown from backtest
    cum = np.exp(port_daily.cumsum())
    peak = cum.cummax()
    drawdowns = (cum - peak) / peak
    max_dd = float(drawdowns.min())

    # VaR 95% (daily, then annualized)
    var_95_daily = float(np.percentile(port_daily, 5))
    var_95 = var_95_daily * np.sqrt(TRADING_DAYS)

    # CVaR 95% (expected shortfall)
    tail = port_daily[port_daily <= np.percentile(port_daily, 5)]
    cvar_95 = float(tail.mean()) * np.sqrt(TRADING_DAYS) if len(tail) > 0 else var_95

    # Sortino ratio (downside deviation only)
    downside = port_daily[port_daily < 0]
    downside_std = float(downside.std() * np.sqrt(TRADING_DAYS)) if len(downside) > 1 else 0.0
    sortino = (perf.expected_return - risk_free_rate) / downside_std if downside_std > 0 else 0.0

    return {
        "expected_return": perf.expected_return,
        "volatility": perf.volatility,
        "sharpe_ratio": perf.sharpe_ratio,
        "sortino_ratio": sortino,
        "max_drawdown": max_dd,
        "var_95": var_95,
        "cvar_95": cvar_95,
        "risk_free_rate": risk_free_rate,
    }
