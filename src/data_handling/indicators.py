"""Technical indicators: SMA and Wilder's RSI."""

import pandas as pd


def sma(close: pd.Series, length: int) -> pd.Series:
    """Simple moving average over `length` days."""
    return close.rolling(length).mean()


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    """Wilder's RSI, matching TradingView / pandas_ta output.

    Uses close-to-close changes, splits into gain and loss magnitudes,
    smooths each with Wilder's moving average (EMA with alpha = 1/length),
    and returns ``100 - 100 / (1 + RS)`` where ``RS = avg_gain / avg_loss``.
    """
    change = close.diff()
    gain = change.clip(lower=0)
    loss = (-change).clip(lower=0)

    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)
