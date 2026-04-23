"""Diagnostic: distribution of winner vs. loser trade durations for cole_strategy.

Runs the strategy with the time stop effectively disabled (``max_bars`` set very
high) so the duration distribution reflects the price-reversion / RSI exit
behaviour rather than the arbitrary 8-bar cap. Useful for asking "is my time
stop cutting winners short or letting losers run?"

Run from the repo root::

    python trade_duration_study.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
import pandas as pd

from src.backtesting_execution.backtest import run
from src.backtesting_execution.strategy import cole_strategy
from src.data_handling.data import load_adjusted_close


TICKER = "SPY"
START = "1990-01-01"
END = "2010-01-01"
MAX_BARS = 10  # large enough to never trip the time stop


def trade_durations_in_bars(
    trades: pd.DataFrame,
    price_index: pd.DatetimeIndex,
) -> pd.Series:
    """Number of trading bars each trade was open (entry bar to exit bar)."""
    entry_i = price_index.get_indexer(trades["entry_date"])
    exit_i = price_index.get_indexer(trades["exit_date"])
    return pd.Series(exit_i - entry_i, index=trades.index, name="duration_bars")


def _describe(label: str, s: pd.Series) -> None:
    if s.empty:
        print(f"  {label:8s} (0 trades)")
        return
    print(
        f"  {label:8s} n={len(s):3d}  "
        f"mean={s.mean():5.1f}  median={s.median():5.1f}  "
        f"min={int(s.min()):3d}  max={int(s.max()):3d}  "
        f"p25={s.quantile(0.25):5.1f}  p75={s.quantile(0.75):5.1f}"
    )


def main() -> None:
    prices = load_adjusted_close(TICKER, START, END)

    signal = cole_strategy(prices, max_bars=MAX_BARS)
    result = run(prices, signal)
    trades = result["trades"].copy()

    if trades.empty:
        print("No trades produced; nothing to analyse.")
        return

    # Drop any still-open trade at end of data -- its duration reflects the data
    # boundary, not a strategy-driven exit.
    open_at_end = trades["exit_date"] == prices.index[-1]
    if open_at_end.any():
        trades = trades[~open_at_end]

    durations = trade_durations_in_bars(trades, prices.index)
    wins = trades["pct_pnl"] > 0
    winner_dur = durations[wins]
    loser_dur = durations[~wins]

    print(f"cole_strategy on {TICKER} {START} -> {END}, max_bars={MAX_BARS}")
    print(f"closed trades: {len(trades)}   win rate: {wins.mean():.1%}")
    _describe("winners", winner_dur)
    _describe("losers",  loser_dur)

    fig, ax = plt.subplots(figsize=(10, 5))
    bins = range(0, int(durations.max()) + 2)
    ax.hist(
        winner_dur, bins=bins, alpha=0.6,
        label=f"winners (n={len(winner_dur)})", color="tab:green",
    )
    ax.hist(
        loser_dur, bins=bins, alpha=0.6,
        label=f"losers (n={len(loser_dur)})", color="tab:red",
    )
    if not winner_dur.empty:
        ax.axvline(
            winner_dur.median(), color="tab:green", linestyle="--",
            alpha=0.8, label=f"winner median: {winner_dur.median():.0f}",
        )
    if not loser_dur.empty:
        ax.axvline(
            loser_dur.median(), color="tab:red", linestyle="--",
            alpha=0.8, label=f"loser median: {loser_dur.median():.0f}",
        )
    ax.set_xlabel("Trade duration (bars)")
    ax.set_ylabel("Count")
    ax.set_title(f"cole_strategy trade durations (max_bars={MAX_BARS})")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
