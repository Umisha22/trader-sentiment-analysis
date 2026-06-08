# Analysis Summary

## Data checks
- Historical trades loaded: 211,224
- Trades matched with sentiment: 211,218
- Trades without a matching sentiment date: 6
- Realized PnL rows, where Closed PnL is non-zero: 104,402
- Date range used: 2023-05-01 to 2025-05-01

## Main findings
- Best average result came during **Extreme Greed**: 67.22 net PnL per trade.
- Weakest average result came during **Neutral**: 33.26 net PnL per trade.
- The most trading activity happened during **Fear** with 483,324,790 USD in traded notional.
- The strongest direction/sentiment pair was **Auto-Deleveraging** during **Greed**, averaging 7,184.81 net PnL per trade.

## Strategy angle
- Sentiment should not be used as a standalone signal. It is more useful as a risk filter layered on top of direction, position size, and trader-level consistency.
- The cleaner strategy idea is to reduce size in the weakest sentiment bucket and prioritize the direction/sentiment pairs that show positive realized edge.
- Fees matter because they turn many flat or small winning executions into negative net trades, so sizing and trade frequency need to be controlled.

Detailed tables and plots are saved in the `outputs/` folder.