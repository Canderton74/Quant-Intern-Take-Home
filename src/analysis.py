"""Performance analytics for a backtest result.

All metrics operate on the dict returned by ``backtesting_execution.backtest.run``::

    {"equity": pd.Series, "trades": pd.DataFrame}

Conventions
-----------
- Returns are simple (equity.pct_change()), to match the backtest layer.
- Annualization uses 252 trading days.
- Risk-free rate is assumed to be 0, so Sharpe = mean / std * sqrt(252).
- Max drawdown is reported as a negative number (e.g. -0.23 for a 23% DD).
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

TRADING_DAYS = 252


def _daily_returns(equity: pd.Series) -> pd.Series:
    return equity.pct_change().dropna()


def cagr(equity: pd.Series) -> float:
    """Compound annual growth rate, annualized on a 252-trading-day basis."""
    n = len(equity) - 1  # number of return periods
    if n <= 0 or equity.iloc[0] <= 0:
        return float("nan")
    total_growth = equity.iloc[-1] / equity.iloc[0]
    return total_growth ** (TRADING_DAYS / n) - 1.0


def ann_volatility(equity: pd.Series) -> float:
    """Annualized standard deviation of daily returns (sample std, ddof=1)."""
    r = _daily_returns(equity)
    if len(r) < 2:
        return float("nan")
    return r.std(ddof=1) * np.sqrt(TRADING_DAYS)


def sharpe(equity: pd.Series) -> float:
    """Annualized Sharpe ratio with rf = 0."""
    r = _daily_returns(equity)
    if len(r) < 2 or r.std(ddof=1) == 0:
        return float("nan")
    return r.mean() / r.std(ddof=1) * np.sqrt(TRADING_DAYS)


def drawdown_series(equity: pd.Series) -> pd.Series:
    """Underwater curve: fractional drawdown from the running peak at each bar.

    Values are <= 0. A fresh all-time high sits at 0.0; the most negative
    value is the worst drawdown. Useful on its own for underwater plots.
    """
    running_peak = equity.cummax()
    dd = equity / running_peak - 1.0
    dd.name = "drawdown"
    return dd


def max_drawdown(equity: pd.Series) -> tuple[float, pd.Timestamp | None]:
    """Return ``(max_dd, trough_date)`` where ``max_dd`` is negative.

    A flat or monotonically rising curve returns ``(0.0, first_index)``.
    """
    if equity.empty:
        return float("nan"), None
    dd = drawdown_series(equity)
    return float(dd.min()), dd.idxmin()


def num_trades(trades: pd.DataFrame) -> int:
    return int(len(trades))


def win_rate(trades: pd.DataFrame) -> float:
    """Fraction of trades with positive net PnL. NaN if there are no trades."""
    if trades.empty:
        return float("nan")
    return float((trades["pct_pnl"] > 0).mean())


def summary(result: dict) -> pd.Series:
    """One-line report card combining all metrics.

    Returned as a ``pd.Series`` so multiple strategies can be concatenated
    column-wise into a DataFrame for side-by-side comparison.
    """
    equity = result["equity"]
    trades = result["trades"]

    dd, dd_date = max_drawdown(equity)

    return pd.Series(
        {
            "cagr":           cagr(equity),
            "ann_volatility": ann_volatility(equity),
            "sharpe":         sharpe(equity),
            "max_drawdown":   dd,
            "max_dd_date":    dd_date.date() if dd_date is not None else None,
            "num_trades":     num_trades(trades),
            "win_rate":       win_rate(trades),
        }
    )


# --------------------------------------------------------------------------- #
# Plots
#
# Every plot takes a dict ``{name: result}`` so multiple strategies naturally
# overlay on the same axes. For a single strategy, pass ``{"my_strat": res}``.
# Plots return the Figure without calling plt.show() / savefig -- the caller
# decides what to do with it.
# --------------------------------------------------------------------------- #

def _as_pct(x, _pos):
    return f"{x:.0%}"


def plot_equity(
    results: dict,
    log_scale: bool = False,
    title: str = "Equity curves",
) -> Figure:
    """Overlay equity curves for one or more strategies."""
    fig, ax = plt.subplots(figsize=(10, 5))
    for name, res in results.items():
        ax.plot(res["equity"].index, res["equity"].values, label=name)
    if log_scale:
        ax.set_yscale("log")
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    return fig


def plot_drawdown(results: dict, title: str = "Drawdown") -> Figure:
    """Underwater chart drawn as lines, one per strategy."""
    fig, ax = plt.subplots(figsize=(10, 4))
    for name, res in results.items():
        dd = drawdown_series(res["equity"])
        ax.plot(dd.index, dd.values, label=name)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown")
    ax.yaxis.set_major_formatter(FuncFormatter(_as_pct))
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    fig.tight_layout()
    return fig


def plot_summary(results: dict) -> Figure:
    """Stacked equity + drawdown panels sharing the x-axis."""
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    for name, res in results.items():
        axes[0].plot(res["equity"].index, res["equity"].values, label=name)
    axes[0].set_title("Equity")
    axes[0].set_ylabel("Equity")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best")

    for name, res in results.items():
        dd = drawdown_series(res["equity"])
        axes[1].plot(dd.index, dd.values, label=name)
    axes[1].axhline(0, color="black", linewidth=0.5)
    axes[1].set_title("Drawdown")
    axes[1].set_xlabel("Date")
    axes[1].set_ylabel("Drawdown")
    axes[1].yaxis.set_major_formatter(FuncFormatter(_as_pct))
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best")

    fig.tight_layout()
    return fig
