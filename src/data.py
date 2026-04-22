"""Market data loading utilities."""

import pandas as pd
import yfinance as yf


def load_adjusted_close(ticker: str, start: str, end: str) -> pd.Series:
    """Download daily adjusted close prices for a single `ticker` as a pandas Series.

    Parameters
    ----------
    ticker : str
        Yahoo Finance ticker symbol (e.g. ``"SPY"``).
    start : str
        Inclusive start date, ``"YYYY-MM-DD"``.
    end : str
        Exclusive end date, ``"YYYY-MM-DD"``. To include 2024-12-31, pass
        ``"2025-01-01"``.
    """
    df = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
    )

    prices = df["Adj Close"]
    prices.name = ticker
    prices.index.name = "date"
    return prices
