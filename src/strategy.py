"""
Each function returns a pd.Series of *target weights* for day T, computed
using data through day T only. The backtest layer is responsible for
T+1 execution (shifting signals forward by one bar before applying returns).

This allows us to use weighted position sizing without the system being blind to costs of slippage/fees.
"""

import pandas as pd

from src.data_handling.indicators import rsi, sma


def buy_and_hold(prices: pd.Series) -> pd.Series:
    """Baseline: always 100% long."""
    return pd.Series(1.0, index=prices.index, name="buy_and_hold")


def trend_following(
    prices: pd.Series,
    fast: int = 50,
    slow: int = 200,
) -> pd.Series:
    """Long when the fast SMA is above the slow SMA, otherwise in cash.

    During the warmup window (before both SMAs are defined) the comparison
    with NaN evaluates to False, so the signal is 0.0 -- i.e. we stay in
    cash until both moving averages are available.
    """
    fast_ma = sma(prices, fast)
    slow_ma = sma(prices, slow)
    signal = (fast_ma > slow_ma).astype(float)
    return signal


def mean_reversion(
    prices: pd.Series,
    length: int = 2,
    entry: float = 10.0,
    exit_: float = 50.0,
) -> pd.Series:
    """Connors-style RSI mean reversion.

    Enter long the day the ``length``-day RSI closes below ``entry``.
    Stay long until RSI closes above ``exit_``, then return to cash.
    While RSI is between the two thresholds, hold the existing position.
    """
    r = rsi(prices, length=length)

    raw = pd.Series(float("nan"), index=prices.index)
    raw[r < entry] = 1.0
    raw[r > exit_] = 0.0

    signal = raw.ffill().fillna(0.0)
    return signal
