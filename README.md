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

##Part 2

For part 2, please look into branch `broken-backtest`.
