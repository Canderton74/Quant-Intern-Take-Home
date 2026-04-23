"""Run all three strategies on SPY and print a side-by-side summary.

Usage
-----
    python main.py
"""

import matplotlib.pyplot as plt
import pandas as pd

from src.analysis import plot_summary, summary
from src.backtesting_execution.backtest import run
from src.backtesting_execution.strategy import (
    buy_and_hold,
    cole_strategy,
    mean_reversion,
    trend_following,
)
from src.data_handling.data import load_adjusted_close


TICKER = "SPY"
START = "2010-01-01"
END = "2025-01-01" # jan 1 2025 because end date is exclusive, so this is fetching last day of 2024
FEE_BPS = 1.0
SLIPPAGE_BPS = 0.0
CAPITAL = 100_000.0


def main() -> None:
    prices = load_adjusted_close(TICKER, START, END)
    print(f"Loaded {len(prices)} bars of {TICKER} from {START} to {END}\n")

    strategies = {
        "buy_and_hold":    buy_and_hold(prices),
        "trend_following": trend_following(prices),
        "mean_reversion":  mean_reversion(prices),
        "cole_strategy":   cole_strategy(prices),
    }

    results = {
        name: run(prices, signal, fee_bps=FEE_BPS,
                  slippage_bps=SLIPPAGE_BPS, capital=CAPITAL)
        for name, signal in strategies.items()
    }

    report = pd.DataFrame({name: summary(res) for name, res in results.items()})

    with pd.option_context("display.float_format", "{:,.4f}".format):
        print(report)

    plot_summary(results)
    plt.show()


if __name__ == "__main__":
    main()
