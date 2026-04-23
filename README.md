# Quant-Intern-Take-Home

Daily-bar backtest comparing buy-and-hold, trend-following, and mean-reversion strategies on SPY (2010–2024), with a personal variant (`cole_strategy`). Written for the Quant Research Intern take-home project.

## Project structure

```
Quant-Intern-Take-Home/
├── main.py                          Entry point: runs all strategies, prints summary, shows plots.
├── requirements.txt                 Python dependencies.
├── README.md
├── src/
│   ├── __init__.py
│   ├── analysis.py                  Performance metrics and plots (equity curve, drawdown).
│   ├── backtesting_execution/
│   │   ├── backtest.py              Execution engine: T+1 fills, fees/slippage, trade log.
│   │   └── strategy.py              Signal generators: buy_and_hold, trend_following,
│   │                                mean_reversion, cole_strategy.
│   └── data_handling/
│       ├── data.py                  yfinance wrapper returning a clean adjusted-close Series.
│       └── indicators.py            Technical indicators: sma, rsi (Wilder), bollinger.
└── tests/
    ├── test_backtest.py             Pytest: execution mechanics, cost application, trade log.
    └── test_strategy.py             Pytest: signal generation on synthetic price series.
```

## File roles

| File | Responsibility |
|---|---|
| `main.py` | Top-level script. Loads SPY, instantiates each strategy, runs the backtest, builds a side-by-side summary table, and renders the equity + drawdown dashboard. |
| `src/analysis.py` | All performance analytics: `cagr`, `ann_volatility`, `sharpe`, `drawdown_series`, `max_drawdown`, `num_trades`, `win_rate`, `summary`. Plus `plot_equity`, `plot_drawdown`, `plot_summary`. Consumes the dict returned by `backtest.run`. |
| `src/backtesting_execution/backtest.py` | The execution layer. Takes a price series and a target-weight signal, applies T+1 close-to-close execution with basis-point costs, produces an equity curve and a round-trip trade log. |
| `src/backtesting_execution/strategy.py` | Signal generators — pure functions from a price series to a target-weight series. Never peek at future data. |
| `src/data_handling/data.py` | Thin `yfinance` wrapper that returns a single-ticker adjusted-close Series with a named index. |
| `src/data_handling/indicators.py` | Technical indicators used by the strategies. Wilder's RSI, simple moving average, Bollinger Bands. |
| `tests/test_backtest.py` | Verifies execution mechanics with hand-crafted inputs: cost-on-flip, T+1 lag, path-dependent equity, trade-log alignment. |
| `tests/test_strategy.py` | Verifies each strategy's signal logic on synthetic deterministic series (no network required). |

## Setup

### 1. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

Dependencies: `pandas`, `numpy`, `yfinance`, `matplotlib`, `pytest`.

## Running the backtest

From the repo root:

```powershell
python main.py
```

This downloads SPY 2010–2024 via yfinance, runs `buy_and_hold`, `trend_following`, `mean_reversion`, and `cole_strategy`, prints a summary table (CAGR, annualized volatility, Sharpe, max drawdown + date, number of trades, win rate), and pops a matplotlib window with the overlaid equity curves and drawdowns.

The ticker, date range, fees, and capital are set at the top of `main.py` and can be edited directly.

## Running the tests

From the repo root:

```powershell
python -m pytest tests/ -v
```

Or run either file on its own:

```powershell
python tests/test_backtest.py
python tests/test_strategy.py
```

Both files include an `if __name__ == "__main__"` block that invokes pytest on themselves, so they work either way.

## Results of Backtest
               buy_and_hold trend_following mean_reversion cole_strategy
cagr                 0.1365          0.0907         0.0214        0.0359
ann_volatility       0.1705          0.1376         0.0855        0.0956
sharpe               0.8363          0.6999         0.2905        0.4173
max_drawdown        -0.3372         -0.3372        -0.2373       -0.2330
max_dd_date      2020-03-23      2020-03-23     2020-03-24    2020-03-23
num_trades                1               7            167            78
win_rate             1.0000          0.5714         0.6826        0.6923

## Why My Strategy

My strategy (`cole_strategy`) takes the `mean_reversion` and adds price closing below 2 standard deviations of the last 14 bar period as another requirement for entry (this is done through bollinger bands). This adds another filter and makes the entry stricter and more selective to capture sharp movements. This is because mean reversion is usually targetting a pricing inefficiency where the market over reacts or swings too low for xyz reason, and thus the asset is underpriced. This is usually indicated by a sharp move and the bollinger bands help ensure that.

For exit I got rid of the RSI>50 condition, as if the move back to the mean lasts a few days then it exits early. Instead, I replaced the exit with 2 options, which don't have to be met together to close the position. Exit 1 is when price reverts back to the mean over the last 14 days. Exit 2 is when the trade has gone on for 10 days.

I ran a study, `trade_duration_study.py`, to analyze how long winning trades are, and how long losing trades are. I discovered that in a crash, price doesn't meet the mean for a while and continues to fall. Almost every winning trade that successfully reverts to the mean does so within 10 days, thus my reasoning for exit 2. This was test on data from 1990 to 2010. If I wasn't testing the strategies on 2010-2025, I would have tested on pockets of data throughout recent years as the market structure and regime has changed since 2010. Since I couldn't do so the testing is biased on outdated data.

## Part 2

For part 2, please look into branch `broken-backtest`.
