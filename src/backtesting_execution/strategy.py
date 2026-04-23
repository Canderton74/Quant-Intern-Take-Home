"""
Each function returns a pd.Series of *target weights* for day T, computed
using data through day T only. The backtest layer is responsible for
T+1 execution (shifting signals forward). Technically we do a shift of 2 bars to account for the fact that the signal is applied on the close of day T, but the position is executed on the close of day T+1.

This allows us to use weighted position sizing without the system being blind to costs of slippage/fees.
"""

import pandas as pd

from src.data_handling.indicators import bollinger, rsi, sma


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

    RSI is calculated using ewm average, with alpha = 1/length, as wilder's designed RSI to be calculated.
    """
    r = rsi(prices, length=length)

    raw = pd.Series(float("nan"), index=prices.index)
    raw[r < entry] = 1.0
    raw[r > exit_] = 0.0

    signal = raw.ffill().fillna(0.0)
    return signal


def cole_strategy(
    prices: pd.Series,
    rsi_length: int = 14,
    bb_length: int = 14,
    bb_std: float = 2.0,
    sma_length: int = 14,
    max_bars: int = 6,
) -> pd.Series:
    """Bollinger + RSI mean-reversion with a time stop.

    Targets price inefficiencies from strong overreactions: we only enter
    when price is stretched below its lower Bollinger Band *and* RSI
    confirms the move is oversold.

    Entry:
        close < lower Bollinger Band

    Exit (any one triggers):
        close >= SMA(sma_length)     -- reverted to mean
        held >= max_bars             -- half-life of mean reversions

    This strategy has to be written as loop since exit depends on multiple conditions. Can't be vectorised.
    """
    bb = bollinger(prices, length=bb_length, num_std=bb_std)
    target = sma(prices, length=sma_length)

    # Comparisons against NaN are False, so warmup naturally keeps us flat.
    entry_cond = (prices < bb["lower"])
    exit_cond = (prices >= target)

    signal = pd.Series(0.0, index=prices.index, name="cole_strategy")
    in_pos = False
    bars_held = 0

    for i in range(len(prices)):
        if in_pos:
            if bool(exit_cond.iloc[i]) or bars_held >= max_bars:
                in_pos = False
                bars_held = 0
                # signal.iloc[i] stays 0.0 -- we're flat at this close
            else:
                signal.iloc[i] = 1.0
                bars_held += 1
        else:
            if bool(entry_cond.iloc[i]):
                in_pos = True
                signal.iloc[i] = 1.0
                bars_held = 1  # counting this bar as the first held bar

    return signal