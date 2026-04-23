import pandas as pd


def sma(close: pd.Series, length: int) -> pd.Series:
    """Simple moving average over `length` days."""
    return close.rolling(length).mean()


def rsi(close: pd.Series, length: int) -> pd.Series:
    """
    I use Wilder's RSI since that's what TradingView and pandas_ta use.

    It's formula is: 
    RSI = 100 - 100 / (1 + RS)
    where RS = avg_gain / avg_loss
    and avg_gain = average of gains over the last `length` periods
    and avg_loss = average of losses over the last `length` periods

    The averages are calculated using an exponential moving average with a smoothing factor of 1/n.
    """
    change = close.diff()
    gain = change.clip(lower=0)
    loss = (-change).clip(lower=0)

    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def bollinger(close: pd.Series, length: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands: SMA +/- num_std * rolling standard deviation.

    Returns a DataFrame with columns ``mid``, ``upper``, ``lower`` indexed the
    same as ``close``. During the warmup window (first ``length - 1`` bars)
    all three columns are NaN, so any comparison against them evaluates to
    False -- a strategy built on top will naturally sit in cash.

    ``ddof=0`` (population std) is used to match pandas_ta / TradingView
    defaults; for typical lengths the sample/population difference is tiny.
    """
    mid = close.rolling(length).mean()
    std = close.rolling(length).std(ddof=0)
    upper = mid + num_std * std
    lower = mid - num_std * std
    return pd.DataFrame({"mid": mid, "upper": upper, "lower": lower})
