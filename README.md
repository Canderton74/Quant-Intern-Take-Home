## Part 2 — Subtle lookahead bias

**What I changed.** In `src/backtesting_execution/backtest.py`, on the `biased-lookahead` branch, this line:

```python
weights = signal.shift(2).fillna(0.0)
```

becomes:

```python
weights = signal.shift(1).fillna(0.0)
```

This is a lookahead bias as we are executing on T+1's close. That means we're harvesting the returns from T+1 close through day T+2. The `returns` series is a series of daily returns recorded as close T-1 to close T; Thus to align with this we don't want to shift `weights` by 1 (which might be intuitive for some as we are executing 1 day later), but 2 since we don't capture any PnL from the day of execution.

As a reminder weights is just the weighting of portfolio that we are in the stock.

**Results with bug (`shift(1)`):**

| Metric                | `buy_and_hold` | `trend_following` | `mean_reversion` | `cole_strategy` |
|-----------------------|---------------:|------------------:|-----------------:|----------------:|
| CAGR                  |         0.1367 |            0.0952 |           0.0506 |          0.0410 |
| Annualized volatility |         0.1705 |            0.1367 |           0.0846 |          0.0892 |
| Sharpe                |         0.8373 |            0.7340 |           0.6258 |          0.4960 |
| Max drawdown          |        -0.3372 |           -0.3372 |          -0.1509 |         -0.1889 |
| Max drawdown date     |     2020-03-23 |        2020-03-23 |       2011-08-08 |      2020-03-16 |
| Number of trades      |              1 |                 7 |              167 |              83 |
| Win rate              |         1.0000 |            0.5714 |           0.6826 |          0.6867 |

**Results without bug (correct `shift(2)`):**

| Metric                | `buy_and_hold` | `trend_following` | `mean_reversion` | `cole_strategy` |
|-----------------------|---------------:|------------------:|-----------------:|----------------:|
| CAGR                  |         0.1365 |            0.0907 |           0.0214 |          0.0359 |
| Annualized volatility |         0.1705 |            0.1376 |           0.0855 |          0.0956 |
| Sharpe                |         0.8363 |            0.6999 |           0.2905 |          0.4173 |
| Max drawdown          |        -0.3372 |           -0.3372 |          -0.2373 |         -0.2330 |
| Max drawdown date     |     2020-03-23 |        2020-03-23 |       2020-03-24 |      2020-03-23 |
| Number of trades      |              1 |                 7 |              167 |              78 |
| Win rate              |         1.0000 |            0.5714 |           0.6826 |          0.6923 |

This throws off the drawdown and sharpe ratio without changing the # of trades itself. In all but `mean_reversion` we see minor skewing (which is up to luck and variance) but `mean_reversion` sees a little over 100% increase in sharpe and about a 30% decrease in max drawdown. This is extremely dangerous as a researcher might use this backtesting engine and deploy a horrible strategy that they believe worked well. It also highlights the importance of incubating a strategy before full deployment.