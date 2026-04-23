"""Tests for src/backtest.py.

Run with:  pytest -q tests/test_backtest.py

These tests use hand-crafted price and signal series so we can verify the
execution mechanics exactly: T+1 fill, cost-on-flip, path-dependent equity,
and round-trip trade reconstruction.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest

from src.backtest import run


def _prices(values, start="2024-01-01") -> pd.Series:
    idx = pd.bdate_range(start=start, periods=len(values))
    return pd.Series(values, index=idx, dtype=float, name="price")


# --------------------------------------------------------------------------- #
# Equity mechanics
# --------------------------------------------------------------------------- #

def test_flat_zero_signal_stays_in_cash():
    """No signal → equity never moves and no trades are recorded."""
    prices = _prices([100, 101, 99, 102, 105])
    signal = pd.Series(0.0, index=prices.index)

    out = run(prices, signal, fee_bps=5.0, slippage_bps=5.0, capital=1_000.0)

    assert np.allclose(out["equity"].values, 1_000.0)
    assert out["trades"].empty


def test_buy_and_hold_zero_cost_tracks_price_ratio():
    """Fully long, zero cost: from the first invested bar onward, equity is
    just capital * price[t] / price[1] (we miss day 0 and day 1 because of
    the shift(2) execution lag)."""
    prices = _prices([100, 101, 102, 104, 103, 107])
    signal = pd.Series(1.0, index=prices.index)

    out = run(prices, signal, fee_bps=0.0, slippage_bps=0.0, capital=1_000.0)
    eq = out["equity"].values

    assert np.isclose(eq[0], 1_000.0)
    assert np.isclose(eq[1], 1_000.0)
    for i in range(2, len(prices)):
        assert np.isclose(eq[i], 1_000.0 * prices.iloc[i] / prices.iloc[1])


def test_weights_lag_two_bars():
    """Signal flips to 1 on day 2, so the new weight only earns from day 4."""
    prices = _prices([100, 110, 121, 133.1, 146.41])  # +10% per day
    signal = pd.Series([0, 0, 1, 1, 1], index=prices.index, dtype=float)

    out = run(prices, signal, fee_bps=0.0, slippage_bps=0.0, capital=1_000.0)
    eq = out["equity"].values

    assert np.allclose(eq[:4], 1_000.0)
    assert np.isclose(eq[4], 1_000.0 * 1.10)


# --------------------------------------------------------------------------- #
# Costs
# --------------------------------------------------------------------------- #

def test_cost_charged_on_bar_after_flip():
    """Flat prices isolate the cost drag: each flip debits cost_rate on T+1."""
    prices = _prices([100, 100, 100, 100, 100])
    signal = pd.Series([0, 1, 1, 0, 0], index=prices.index, dtype=float)

    out = run(prices, signal, fee_bps=10.0, slippage_bps=0.0, capital=1_000.0)
    eq = out["equity"].values

    cr = 10.0 / 10_000.0
    # Flip on day 1 → cost on day 2; flip on day 3 → cost on day 4.
    assert np.isclose(eq[0], 1_000.0)
    assert np.isclose(eq[1], 1_000.0)
    assert np.isclose(eq[2], 1_000.0 * (1 - cr))
    assert np.isclose(eq[3], 1_000.0 * (1 - cr))
    assert np.isclose(eq[4], 1_000.0 * (1 - cr) ** 2)


def test_costs_compound_against_reduced_capital():
    """Two sequential flips on flat prices should compound, not sum."""
    prices = _prices([100] * 6)
    # Two full round trips: flip on days 1, 2, 3, 4.
    signal = pd.Series([0, 1, 0, 1, 0, 0], index=prices.index, dtype=float)

    out = run(prices, signal, fee_bps=100.0, slippage_bps=0.0, capital=1_000.0)
    eq = out["equity"].values

    cr = 100.0 / 10_000.0  # 1% per flip
    # 4 flips → 4 cost charges, each multiplicative.
    # Compounded (1-cr)^4 != 1 - 4*cr, so if this passes we know equity is
    # being path-compounded rather than costs summed against initial capital.
    assert np.isclose(eq[-1], 1_000.0 * (1 - cr) ** 4)
    assert not np.isclose(eq[-1], 1_000.0 * (1 - 4 * cr))


# --------------------------------------------------------------------------- #
# Trade log
# --------------------------------------------------------------------------- #

def test_trade_log_round_trip_dates_and_prices():
    """Entry/exit dates land on the T+1 execution bar."""
    prices = _prices([100, 100, 110, 110, 115])
    # Enter on day 1 (exec day 2 @ 110), exit on day 3 (exec day 4 @ 115).
    signal = pd.Series([0, 1, 1, 0, 0], index=prices.index, dtype=float)

    out = run(prices, signal, fee_bps=0.0, slippage_bps=0.0, capital=1_000.0)
    trades = out["trades"]

    assert len(trades) == 1
    row = trades.iloc[0]
    assert row["entry_date"] == prices.index[2]
    assert row["exit_date"] == prices.index[4]
    assert row["entry_price"] == 110.0
    assert row["exit_price"] == 115.0
    assert np.isclose(row["pct_pnl"], (115 - 110) / 110)


def test_trade_log_pnl_includes_round_trip_cost():
    prices = _prices([100, 100, 110, 110, 121])
    signal = pd.Series([0, 1, 1, 0, 0], index=prices.index, dtype=float)

    out = run(prices, signal, fee_bps=10.0, slippage_bps=0.0, capital=1_000.0)
    row = out["trades"].iloc[0]

    cr = 10.0 / 10_000.0
    gross = (121 - 110) / 110
    assert np.isclose(row["pct_pnl"], gross - 2 * cr)
    assert np.isclose(row["dollar_pnl"], row["size_dollars"] * (gross - 2 * cr))


def test_open_trade_at_end_is_marked_to_market_with_entry_cost_only():
    prices = _prices([100, 100, 110, 115, 120])
    # Enter on day 1, never exit.
    signal = pd.Series([0, 1, 1, 1, 1], index=prices.index, dtype=float)

    out = run(prices, signal, fee_bps=5.0, slippage_bps=0.0, capital=1_000.0)
    trades = out["trades"]

    assert len(trades) == 1
    row = trades.iloc[0]
    assert row["entry_date"] == prices.index[2]
    assert row["exit_date"] == prices.index[-1]
    assert row["entry_price"] == 110.0
    assert row["exit_price"] == 120.0

    cr = 5.0 / 10_000.0
    gross = (120 - 110) / 110
    # Open trade: only the entry cost is charged, not the exit.
    assert np.isclose(row["pct_pnl"], gross - cr)


def test_signal_on_last_day_is_silently_dropped():
    """A flip on the final bar has no T+1 to execute on; it should not log."""
    prices = _prices([100, 101, 102, 103])
    signal = pd.Series([0, 0, 0, 1], index=prices.index, dtype=float)

    out = run(prices, signal, fee_bps=5.0, slippage_bps=0.0, capital=1_000.0)

    assert out["trades"].empty
    # Final bar's signal also shouldn't leak into weights (shift(2) drops it).
    assert np.allclose(out["equity"].values, 1_000.0)


# --------------------------------------------------------------------------- #
# Return shape
# --------------------------------------------------------------------------- #

def test_return_contract():
    prices = _prices([100, 101, 102])
    signal = pd.Series(1.0, index=prices.index)

    out = run(prices, signal)

    assert set(out.keys()) == {"equity", "trades"}
    assert isinstance(out["equity"], pd.Series)
    assert isinstance(out["trades"], pd.DataFrame)
    assert out["equity"].name == "equity"
    assert len(out["equity"]) == len(prices)


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
