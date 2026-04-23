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

**Results with bug:**
               buy_and_hold trend_following mean_reversion cole_strategy
cagr                 0.1367          0.0952         0.0506        0.0474
ann_volatility       0.1705          0.1367         0.0846        0.0912
sharpe               0.8373          0.7340         0.6258        0.5538
max_drawdown        -0.3372         -0.3372        -0.1509       -0.1870
max_dd_date      2020-03-23      2020-03-23     2011-08-08    2020-03-16
num_trades                1               7            167            97
win_rate             1.0000          0.5714         0.6826        0.7113

**Results without bug (working backtest):**
               buy_and_hold trend_following mean_reversion cole_strategy
cagr                 0.1365          0.0907         0.0214        0.0504
ann_volatility       0.1705          0.1376         0.0855        0.0909
sharpe               0.8363          0.6999         0.2905        0.5868
max_drawdown        -0.3372         -0.3372        -0.2373       -0.1685
max_dd_date      2020-03-23      2020-03-23     2020-03-24    2020-03-16
num_trades                1               7            167            97
win_rate             1.0000          0.5714         0.6826        0.7113

This throws off the drawdown and sharpe ratio without changing the # of trades itself. In all but `mean_reversion` we see minor skewing (which is up to luck and variance) but `mean_reversion` sees a little over 50% drop in sharpe and about a 50% increase in max drawdoown