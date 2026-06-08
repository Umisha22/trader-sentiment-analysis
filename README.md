# Trader Performance vs Market Sentiment

This project explores whether Bitcoin market sentiment has any visible relationship with Hyperliquid trader performance. I used the Fear & Greed index as the daily sentiment layer and joined it with the historical trader execution data on trade date.

## What I Looked At

The analysis focuses on a few practical trading questions:

- Do traders perform differently during Fear, Greed, and Extreme Greed periods?
- Is the relationship stronger for realized PnL rows compared with all execution rows?
- Which direction/sentiment combinations show better or weaker outcomes?
- Are there specific accounts or coins that drive most of the PnL?
- Can sentiment be used as a risk filter instead of a standalone trading signal?

## Project Structure

```text
data/
  fear_greed_index.csv
  historical_data.csv
outputs/
  analysis_summary.md
  sentiment_summary.csv
  realized_sentiment_summary.csv
  direction_summary.csv
  top_accounts_by_sentiment.csv
  *.png
src/
  analyze_sentiment_trader.py
README.md
requirements.txt
```

## How To Run

Install the dependencies:

```bash
pip install -r requirements.txt
```

Run the analysis:

```bash
python src/analyze_sentiment_trader.py
```

The script writes all charts and summary tables to the `outputs/` folder.

## Data Preparation

I cleaned the column names, converted the trader timestamp from IST into a daily trade date, and joined it with the sentiment file on date.

One important choice: I calculated metrics on both all execution rows and realized rows where `Closed PnL != 0`. This matters because many trade logs include open, scale-in, or adjustment rows where `Closed PnL` is zero. Looking only at all rows can make performance look flatter than it actually is.

## Key Findings

The dataset contains **211,224 trades**, and **211,218 trades** matched to a Fear & Greed sentiment date. Only 6 rows did not match, so the merge quality is strong.

Across all matched trade rows, the best average net result came during **Extreme Greed**, with about **67.22 net PnL per trade**. The weakest average result was during **Neutral** sentiment, with about **33.26 net PnL per trade**.

On realized PnL rows, the same pattern becomes clearer:

| Sentiment | Realized trades | Net PnL / trade | Win rate |
|---|---:|---:|---:|
| Extreme Fear | 10,406 | 69.85 | 76.22% |
| Fear | 29,808 | 111.05 | 87.29% |
| Neutral | 18,159 | 69.97 | 82.39% |
| Greed | 25,176 | 84.23 | 76.89% |
| Extreme Greed | 20,853 | 129.55 | 89.17% |

The largest trading volume appeared during **Fear**, with roughly **483.3M USD** in traded notional. That suggests traders were most active when market conditions were uncertain, not when sentiment was most bullish.

Direction-level results show that some rare event categories, such as Auto-Deleveraging, can create very large averages. I would not treat those as normal trading signals. For strategy work, I would focus more on repeatable directions such as Close Long, Close Short, Buy, and Sell.

## Strategy Insight

My main takeaway is that sentiment should be used as a **risk filter**, not as a direct buy/sell signal.

Extreme Greed and Fear both showed stronger realized performance than Neutral. This could mean traders find clearer opportunities when the market is emotionally stretched. Neutral markets may be less directional, which can reduce edge and make fees more important.

A practical trading rule from this analysis would be:

- keep normal or higher conviction sizing only in sentiment buckets with historically positive realized edge;
- reduce size or trade frequency in weaker buckets, especially Neutral;
- monitor fees closely because many small or flat trades become negative after fees;
- evaluate trader-level consistency separately, since a few accounts contribute a large share of total PnL.

## Outputs

Main charts:

- `outputs/net_pnl_per_trade_by_sentiment.png`
- `outputs/realized_win_rate_by_sentiment.png`
- `outputs/volume_by_sentiment.png`
- `outputs/direction_sentiment_heatmap.png`

Main tables:

- `outputs/sentiment_summary.csv`
- `outputs/realized_sentiment_summary.csv`
- `outputs/direction_summary.csv`
- `outputs/top_accounts_by_sentiment.csv`

## Conclusion

The relationship between sentiment and trader performance is visible, but it is not simple. Stronger results appear in emotional market regimes, especially Extreme Greed and Fear, while Neutral sentiment looks weaker on average. The best use of this insight is not to trade sentiment alone, but to combine it with trader behavior, direction, fees, and position sizing.
