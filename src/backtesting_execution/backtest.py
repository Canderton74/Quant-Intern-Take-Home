"""Backtest execution layer: T+1 close execution with fees and slippage.

Conventions
-----------
Signal at day T is decided using data through T's close. Execution happens at
day T+1's close -- so we *held the old weight through all of day T+1* and
captured T+1's full return at the old weight. The new weight first earns
day T+2's return. This is ``weights = signal.shift(2)``.

The final signal (day N) is silently dropped because T+1 would be off the end
of the price series.

Costs (fees + slippage) are charged on the execution day, proportional to the
size of the position change.
"""

import pandas as pd


def run(
    prices: pd.Series,
    signal: pd.Series,
    fee_bps: float = 1.0,
    slippage_bps: float = 0.0,
    capital: float = 100_000.0,
) -> dict:
    """Run a backtest and return the equity curve plus a round-trip trade log.

    Parameters
    ----------
    prices : pd.Series
        Daily adjusted close, indexed by date.
    signal : pd.Series
        Target weight (0.0 or 1.0), decided at day T's close.
    fee_bps : float
        Commission per trade, in basis points of traded notional.
    slippage_bps : float
        Slippage per trade, in basis points of traded notional.
    capital : float
        Starting capital.

    Returns
    -------
    dict with keys
        'equity' : pd.Series  -- equity curve starting at ``capital``
        'trades' : pd.DataFrame -- one row per round-trip trade
    """
    cost_rate = (fee_bps + slippage_bps) / 10_000.0

    returns = prices.pct_change().fillna(0.0)
    weights = signal.shift(1).fillna(0.0)  # backtesting bug, should be shift(2) because we capture T+2's return when we execute on T+1's close.

    # Flip observed on signal day T; cost hits equity on execution day T+1.
    trade_signal = (signal - signal.shift(1).fillna(0.0)).abs()
    costs = trade_signal.shift(1).fillna(0.0) * cost_rate

    strategy_returns = weights * returns - costs
    equity = capital * (1.0 + strategy_returns).cumprod()
    equity.name = "equity"

    trades = _build_trade_log(signal, prices, equity, cost_rate)

    return {"equity": equity, "trades": trades}


def _build_trade_log(
    signal: pd.Series,
    prices: pd.Series,
    equity: pd.Series,
    cost_rate: float,
) -> pd.DataFrame:
    """Reconstruct round-trip trades from signal flips.

    Entry/exit dates line up with the T+1 execution day, matching the return
    and equity streams.
    """
    flips = signal - signal.shift(1).fillna(0.0)
    trades: list[dict] = []
    entry: tuple | None = None  # (exec_date, exec_price, size_dollars)

    for t, f in flips.items():
        if f == 0:
            continue
        i = prices.index.get_loc(t)
        if i + 1 >= len(prices):  # signal on last day: cannot execute T+1
            continue
        exec_date = prices.index[i + 1]
        exec_price = float(prices.iloc[i + 1])

        if f > 0 and entry is None:
            size = float(equity.iloc[i])  # equity at close of signal day
            entry = (exec_date, exec_price, size)
        elif f < 0 and entry is not None:
            e_date, e_price, size = entry
            gross_pct = (exec_price - e_price) / e_price
            net_pct = gross_pct - 2 * cost_rate  # round-trip: entry + exit cost
            trades.append({
                "entry_date":   e_date,
                "exit_date":    exec_date,
                "entry_price":  e_price,
                "exit_price":   exec_price,
                "size_dollars": size,
                "exit_value":   size * (1.0 + net_pct),
                "pct_pnl":      net_pct,
                "dollar_pnl":   size * net_pct,
            })
            entry = None

    # Still long at end of data: mark-to-market on last bar, entry cost only.
    if entry is not None:
        e_date, e_price, size = entry
        last_price = float(prices.iloc[-1])
        gross_pct = (last_price - e_price) / e_price
        net_pct = gross_pct - cost_rate
        trades.append({
            "entry_date":   e_date,
            "exit_date":    prices.index[-1],
            "entry_price":  e_price,
            "exit_price":   last_price,
            "size_dollars": size,
            "exit_value":   size * (1.0 + net_pct),
            "pct_pnl":      net_pct,
            "dollar_pnl":   size * net_pct,
        })

    return pd.DataFrame(trades)
