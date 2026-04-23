"""Tests for src/strategy.py.

Run with:  python -m pytest tests/test_strategy.py -v
       or: python tests/test_strategy.py

Uses synthetic price series so tests are deterministic and offline.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest

from src.strategy import buy_and_hold, trend_following, mean_reversion


def _prices(values, start="2024-01-01") -> pd.Series:
    idx = pd.bdate_range(start=start, periods=len(values))
    return pd.Series(values, index=idx, dtype=float, name="price")


# --------------------------------------------------------------------------- #
# buy_and_hold
# --------------------------------------------------------------------------- #

def test_buy_and_hold_is_always_long():
    prices = _prices([100, 101, 99, 105, 104])
    sig = buy_and_hold(prices)

    assert sig.name == "buy_and_hold"
    assert sig.index.equals(prices.index)
    assert np.allclose(sig.values, 1.0)


# --------------------------------------------------------------------------- #
# trend_following
# --------------------------------------------------------------------------- #

def test_trend_following_is_flat_during_warmup():
    """Before the slow SMA is defined, comparing with NaN yields False → 0."""
    prices = _prices(list(range(1, 10)))
    sig = trend_following(prices, fast=3, slow=5)
    # First (slow - 1) = 4 bars: slow SMA is NaN.
    assert np.allclose(sig.iloc[:4].values, 0.0)


def test_trend_following_longs_in_rising_market():
    prices = _prices(list(range(1, 21)))  # monotonically up
    sig = trend_following(prices, fast=3, slow=5)
    # After warmup, fast SMA sits above slow SMA on a rising series.
    assert np.all(sig.iloc[5:].values == 1.0)


def test_trend_following_is_flat_in_falling_market():
    prices = _prices(list(range(20, 0, -1)))  # monotonically down
    sig = trend_following(prices, fast=3, slow=5)
    assert np.all(sig.iloc[5:].values == 0.0)


def test_trend_following_output_is_binary():
    rng = np.random.RandomState(0)
    prices = _prices(rng.randn(200).cumsum() + 100)
    sig = trend_following(prices, fast=10, slow=30)
    assert set(np.unique(sig.values)).issubset({0.0, 1.0})


# --------------------------------------------------------------------------- #
# mean_reversion
# --------------------------------------------------------------------------- #

def test_mean_reversion_starts_in_cash():
    """RSI is NaN at t=0, neither threshold trips, ffill stays NaN → 0."""
    prices = _prices([100, 101, 102, 103])
    sig = mean_reversion(prices, length=2, entry=10.0, exit_=50.0)
    assert sig.iloc[0] == 0.0


def test_mean_reversion_enters_on_crash_and_exits_on_recovery():
    # Monotonic decline drives Wilder's RSI → 0, crossing below entry=10.
    # Monotonic rise drives RSI → 100, crossing above exit=50.
    crash = list(range(100, 79, -1))
    recovery = list(range(80, 120))
    prices = _prices(crash + recovery)

    sig = mean_reversion(prices, length=2, entry=10.0, exit_=50.0)

    # We must have been long at some point during the crash/early recovery...
    assert (sig == 1.0).any()
    # ...and ended in cash after the recovery pushed RSI well above exit.
    assert sig.iloc[-1] == 0.0


def test_mean_reversion_holds_position_between_thresholds():
    """Once long, stay long until RSI > exit_; a mid-range RSI should not flip us out."""
    # Crash first to trigger entry, then stabilise (RSI drifts but stays < 50).
    prices = _prices(list(range(100, 89, -1)) + [90, 91, 90, 91, 90, 91])
    sig = mean_reversion(prices, length=2, entry=10.0, exit_=50.0)

    # Find the first long bar; from there, we should stay long for a while
    # since prices are oscillating without a strong rally.
    first_long = sig[sig == 1.0].index[0]
    tail = sig.loc[first_long:].iloc[:3]
    assert np.all(tail.values == 1.0)


def test_mean_reversion_output_is_binary():
    rng = np.random.RandomState(1)
    prices = _prices(rng.randn(300).cumsum() + 100)
    sig = mean_reversion(prices, length=2, entry=10.0, exit_=50.0)
    assert set(np.unique(sig.values)).issubset({0.0, 1.0})


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
