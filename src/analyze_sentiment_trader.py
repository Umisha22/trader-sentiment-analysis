from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "outputs"

HISTORICAL_PATH = DATA_DIR / "historical_data.csv"
SENTIMENT_PATH = DATA_DIR / "fear_greed_index.csv"


SENTIMENT_ORDER = ["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"]


def slug(name: str) -> str:
    return (
        name.strip()
        .lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("-", "_")
    )


def read_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not HISTORICAL_PATH.exists():
        raise FileNotFoundError(f"Missing {HISTORICAL_PATH}")
    if not SENTIMENT_PATH.exists():
        raise FileNotFoundError(f"Missing {SENTIMENT_PATH}")

    trades = pd.read_csv(HISTORICAL_PATH)
    sentiment = pd.read_csv(SENTIMENT_PATH)

    trades.columns = [slug(c) for c in trades.columns]
    sentiment.columns = [slug(c) for c in sentiment.columns]
    return trades, sentiment


def clean_and_merge(trades: pd.DataFrame, sentiment: pd.DataFrame) -> pd.DataFrame:
    trades = trades.copy()
    sentiment = sentiment.copy()

    trades["timestamp_ist"] = pd.to_datetime(
        trades["timestamp_ist"], dayfirst=True, errors="coerce"
    )
    trades["trade_date"] = trades["timestamp_ist"].dt.normalize()

    sentiment["date"] = pd.to_datetime(sentiment["date"], errors="coerce")
    sentiment = sentiment.rename(
        columns={"date": "trade_date", "value": "fear_greed_value"}
    )

    numeric_cols = [
        "execution_price",
        "size_tokens",
        "size_usd",
        "start_position",
        "closed_pnl",
        "fee",
    ]
    for col in numeric_cols:
        if col in trades.columns:
            trades[col] = pd.to_numeric(trades[col], errors="coerce")

    merged = trades.merge(
        sentiment[["trade_date", "fear_greed_value", "classification"]],
        on="trade_date",
        how="left",
    )

    merged["net_pnl"] = merged["closed_pnl"].fillna(0) - merged["fee"].fillna(0)
    merged["is_realized"] = merged["closed_pnl"].fillna(0).ne(0)
    merged["is_win"] = merged["closed_pnl"].fillna(0).gt(0)
    merged["pnl_per_1000_usd"] = np.where(
        merged["size_usd"].fillna(0).gt(0),
        merged["net_pnl"] / merged["size_usd"] * 1000,
        np.nan,
    )
    merged["position_abs"] = merged["start_position"].abs()
    merged["sentiment_bucket"] = pd.Categorical(
        merged["classification"], categories=SENTIMENT_ORDER, ordered=True
    )
    return merged


def grouped_metrics(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    grouped = df.groupby(keys, observed=True)
    out = grouped.agg(
        trades=("trade_id", "count"),
        accounts=("account", "nunique"),
        volume_usd=("size_usd", "sum"),
        gross_closed_pnl=("closed_pnl", "sum"),
        fees=("fee", "sum"),
        net_pnl=("net_pnl", "sum"),
        avg_net_pnl=("net_pnl", "mean"),
        median_net_pnl=("net_pnl", "median"),
        win_rate=("is_win", "mean"),
        avg_pnl_per_1000_usd=("pnl_per_1000_usd", "mean"),
        realized_trades=("is_realized", "sum"),
        avg_size_usd=("size_usd", "mean"),
        avg_start_position_abs=("position_abs", "mean"),
    )
    out["net_pnl_per_trade"] = out["net_pnl"] / out["trades"]
    out["fee_share_of_gross_abs_pnl"] = out["fees"] / out["gross_closed_pnl"].abs()
    return out.reset_index()


def save_tables(merged: pd.DataFrame) -> dict[str, pd.DataFrame]:
    OUTPUT_DIR.mkdir(exist_ok=True)

    matched = merged[merged["classification"].notna()].copy()
    realized = matched[matched["is_realized"]].copy()

    sentiment_summary = grouped_metrics(matched, ["sentiment_bucket"])
    direction_summary = grouped_metrics(matched, ["sentiment_bucket", "direction"])
    coin_summary = grouped_metrics(matched, ["sentiment_bucket", "coin"])
    account_summary = grouped_metrics(matched, ["account", "sentiment_bucket"])

    top_accounts = (
        account_summary.sort_values("net_pnl", ascending=False)
        .groupby("sentiment_bucket", observed=True)
        .head(5)
        .reset_index(drop=True)
    )

    realized_sentiment_summary = grouped_metrics(realized, ["sentiment_bucket"])

    tables = {
        "merged_sample": matched.head(100),
        "sentiment_summary": sentiment_summary,
        "realized_sentiment_summary": realized_sentiment_summary,
        "direction_summary": direction_summary,
        "coin_summary": coin_summary.sort_values("net_pnl", ascending=False).head(50),
        "top_accounts_by_sentiment": top_accounts,
    }
    for name, table in tables.items():
        table.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)
    return tables


def plot_bar(
    df: pd.DataFrame,
    metric: str,
    title: str,
    ylabel: str,
    filename: str,
    color: str,
) -> None:
    chart_df = df.dropna(subset=["sentiment_bucket"]).copy()
    chart_df["sentiment_bucket"] = chart_df["sentiment_bucket"].astype(str)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(chart_df["sentiment_bucket"], chart_df[metric], color=color)
    ax.set_title(title, fontsize=13, pad=12)
    ax.set_xlabel("Market sentiment")
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.25)
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / filename, dpi=160)
    plt.close(fig)


def plot_direction_heatmap(direction_summary: pd.DataFrame) -> None:
    pivot = direction_summary.pivot_table(
        index="direction",
        columns="sentiment_bucket",
        values="net_pnl_per_trade",
        observed=True,
    ).reindex(columns=SENTIMENT_ORDER)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    data = pivot.to_numpy(dtype=float)
    im = ax.imshow(data, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([str(c) for c in pivot.columns], rotation=20, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_title("Average net PnL per trade by direction and sentiment", fontsize=13)

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            if np.isfinite(val):
                ax.text(j, i, f"{val:,.2f}", ha="center", va="center", fontsize=9)

    fig.colorbar(im, ax=ax, label="Net PnL per trade")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "direction_sentiment_heatmap.png", dpi=160)
    plt.close(fig)


def save_charts(tables: dict[str, pd.DataFrame]) -> None:
    sentiment_summary = tables["sentiment_summary"]
    realized_summary = tables["realized_sentiment_summary"]

    plot_bar(
        sentiment_summary,
        "net_pnl_per_trade",
        "Net PnL per trade changes across market sentiment",
        "Net PnL per trade",
        "net_pnl_per_trade_by_sentiment.png",
        "#2f6f73",
    )
    plot_bar(
        realized_summary,
        "win_rate",
        "Win rate on realized trades by sentiment",
        "Win rate",
        "realized_win_rate_by_sentiment.png",
        "#8064a2",
    )
    plot_bar(
        sentiment_summary,
        "volume_usd",
        "Trading volume by sentiment",
        "Volume in USD",
        "volume_by_sentiment.png",
        "#c97b32",
    )
    plot_direction_heatmap(tables["direction_summary"])


def write_summary(merged: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> None:
    matched = merged[merged["classification"].notna()]
    unmatched = len(merged) - len(matched)
    realized = matched[matched["is_realized"]]

    sentiment_summary = tables["sentiment_summary"].copy()
    best = sentiment_summary.sort_values("net_pnl_per_trade", ascending=False).iloc[0]
    worst = sentiment_summary.sort_values("net_pnl_per_trade").iloc[0]
    most_volume = sentiment_summary.sort_values("volume_usd", ascending=False).iloc[0]

    direction_summary = tables["direction_summary"].copy()
    best_direction = direction_summary.sort_values(
        "net_pnl_per_trade", ascending=False
    ).iloc[0]

    lines = [
        "# Analysis Summary",
        "",
        "## Data checks",
        f"- Historical trades loaded: {len(merged):,}",
        f"- Trades matched with sentiment: {len(matched):,}",
        f"- Trades without a matching sentiment date: {unmatched:,}",
        f"- Realized PnL rows, where Closed PnL is non-zero: {len(realized):,}",
        f"- Date range used: {matched['trade_date'].min().date()} to {matched['trade_date'].max().date()}",
        "",
        "## Main findings",
        (
            f"- Best average result came during **{best['sentiment_bucket']}**: "
            f"{best['net_pnl_per_trade']:,.2f} net PnL per trade."
        ),
        (
            f"- Weakest average result came during **{worst['sentiment_bucket']}**: "
            f"{worst['net_pnl_per_trade']:,.2f} net PnL per trade."
        ),
        (
            f"- The most trading activity happened during **{most_volume['sentiment_bucket']}** "
            f"with {most_volume['volume_usd']:,.0f} USD in traded notional."
        ),
        (
            f"- The strongest direction/sentiment pair was **{best_direction['direction']}** "
            f"during **{best_direction['sentiment_bucket']}**, averaging "
            f"{best_direction['net_pnl_per_trade']:,.2f} net PnL per trade."
        ),
        "",
        "## Strategy angle",
        "- Sentiment should not be used as a standalone signal. It is more useful as a risk filter layered on top of direction, position size, and trader-level consistency.",
        "- The cleaner strategy idea is to reduce size in the weakest sentiment bucket and prioritize the direction/sentiment pairs that show positive realized edge.",
        "- Fees matter because they turn many flat or small winning executions into negative net trades, so sizing and trade frequency need to be controlled.",
        "",
        "Detailed tables and plots are saved in the `outputs/` folder.",
    ]
    (OUTPUT_DIR / "analysis_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    trades, sentiment = read_inputs()
    merged = clean_and_merge(trades, sentiment)
    tables = save_tables(merged)
    save_charts(tables)
    write_summary(merged, tables)
    print(f"Saved analysis outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
