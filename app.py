import altair as alt
import pandas as pd
import streamlit as st

from trading_strategy import (
    calculate_moving_averages,
    get_stock_data,
    identify_golden_cross,
    implement_strategy,
)


@st.cache_data(ttl=3600)
def load_backtest() -> tuple[pd.DataFrame, pd.DataFrame]:
    data = get_stock_data("MSFT")
    if data.empty:
        raise ValueError("No market data was returned for MSFT.")

    data = identify_golden_cross(calculate_moving_averages(data))
    trades = implement_strategy(data)
    return data, trades


def build_statistics(trades: pd.DataFrame) -> dict[str, float | int]:
    total = len(trades)
    winners = int((trades["ProfitPct"] > 0).sum())
    return {
        "total": total,
        "winners": winners,
        "losers": total - winners,
        "win_rate": winners / total * 100 if total else 0,
        "average_profit": trades["ProfitPct"].mean() if total else 0,
        "average_holding": trades["HoldingDays"].mean() if total else 0,
    }


def render_price_chart(data: pd.DataFrame, trades: pd.DataFrame) -> None:
    chart_data = data[["Close", "MA50", "MA200"]].copy()
    chart_data.index = pd.DatetimeIndex(chart_data.index).tz_localize(None)
    chart_data.index.name = "Date"
    long_prices = (
        chart_data.reset_index()
        .melt(id_vars="Date", var_name="Series", value_name="Price")
        .dropna(subset=["Price"])
    )
    long_prices["Series"] = long_prices["Series"].map(
        {"Close": "Closing price", "MA50": "50-day MA", "MA200": "200-day MA"}
    )
    long_prices["Signal"] = None

    marker_rows = []
    for trade in trades.to_dict(orient="records"):
        buy_date = pd.Timestamp(trade["BuyDate"])
        sell_date = pd.Timestamp(trade["SellDate"])
        marker_rows.extend(
            [
                {
                    "Date": buy_date.tz_localize(None) if buy_date.tzinfo else buy_date,
                    "Price": trade["BuyPrice"],
                    "Series": None,
                    "Signal": "Buy",
                },
                {
                    "Date": (
                        sell_date.tz_localize(None) if sell_date.tzinfo else sell_date
                    ),
                    "Price": trade["SellPrice"],
                    "Series": None,
                    "Signal": "Sell",
                },
            ]
        )

    chart_data = pd.concat(
        [long_prices, pd.DataFrame(marker_rows)], ignore_index=True
    )
    line = (
        alt.Chart(chart_data)
        .transform_filter(alt.datum.Series != None)
        .mark_line()
        .encode(
            x=alt.X("Date:T", title=None),
            y=alt.Y("Price:Q", title="Price (USD)", scale=alt.Scale(zero=False)),
            color=alt.Color(
                "Series:N",
                title=None,
                scale=alt.Scale(
                    domain=["Closing price", "50-day MA", "200-day MA"],
                    range=["#70a7ff", "#4dd6bd", "#f5b75e"],
                ),
            ),
            tooltip=[
                alt.Tooltip("Date:T", title="Date"),
                alt.Tooltip("Series:N", title="Series"),
                alt.Tooltip("Price:Q", title="Price", format="$.2f"),
            ],
        )
    )

    chart = line
    if marker_rows:
        markers = (
            alt.Chart(chart_data)
            .transform_filter(alt.datum.Signal != None)
            .mark_point(filled=True, size=100, stroke="#121a27", strokeWidth=1.5)
            .encode(
                x=alt.X("Date:T"),
                y=alt.Y("Price:Q"),
                color=alt.Color(
                    "Signal:N",
                    title="Trade",
                    scale=alt.Scale(
                        domain=["Buy", "Sell"], range=["#64d89b", "#ff7b82"]
                    ),
                ),
                tooltip=[
                    alt.Tooltip("Signal:N"),
                    alt.Tooltip("Date:T", title="Date"),
                    alt.Tooltip("Price:Q", title="Price", format="$.2f"),
                ],
            )
        )
        chart = alt.layer(line, markers).resolve_scale(color="independent")

    st.altair_chart(chart.properties(height=480), use_container_width=True)
    st.caption(
        "Buy and sell dots mark the strategy's recorded trade prices. "
        "Past performance is not a guarantee of future results."
    )


def render_statistics(trades: pd.DataFrame, stats: dict[str, float | int]) -> None:
    columns = st.columns(5)
    metrics = [
        ("Total trades", f"{stats['total']}", "Completed round trips"),
        ("Winning trades", f"{stats['winners']}", f"{stats['win_rate']:.1f}% win rate"),
        ("Losing trades", f"{stats['losers']}", "Return at or below 0%"),
        ("Average return", f"{stats['average_profit']:.2f}%", "Per completed trade"),
        ("Average holding", f"{stats['average_holding']:.1f} days", "Calendar days"),
    ]
    for column, (label, value, help_text) in zip(columns, metrics):
        column.metric(label, value, help=help_text)

    st.subheader("Backtest summary")
    st.write(
        f"The backtest produced **{stats['total']} trades**. "
        f"**{stats['winners']}** were profitable ({stats['win_rate']:.1f}%), "
        f"with an average return of **{stats['average_profit']:.2f}%** per trade. "
        "The strategy buys when the 50-day moving average crosses above the "
        "200-day average, then exits at a 15% target or after up to 60 calendar days."
    )


def render_trade_table(trades: pd.DataFrame) -> None:
    st.subheader("Trade history")
    if trades.empty:
        st.info("No trades were generated for this period.")
        return

    table = trades.rename(
        columns={
            "BuyDate": "Buy date",
            "BuyPrice": "Buy price",
            "SellDate": "Sell date",
            "SellPrice": "Sell price",
            "HoldingDays": "Holding (days)",
            "ProfitPct": "Return (%)",
            "SellReason": "Sell reason",
        }
    ).copy()
    table.index = pd.RangeIndex(1, len(table) + 1, name="Trade")
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=False,
        column_config={
            "Buy price": st.column_config.NumberColumn(format="$%.2f"),
            "Sell price": st.column_config.NumberColumn(format="$%.2f"),
            "Return (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )


def main() -> None:
    st.set_page_config(
        page_title="MSFT Golden Cross Backtest",
        page_icon="📈",
        layout="wide",
    )
    st.title("Golden Cross Strategy")
    st.caption("MSFT · Daily prices · 5-year backtest")

    data, trades = load_backtest()

    page = st.radio(
        "Dashboard page",
        ["Price chart", "Trade statistics", "Detailed trades"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if page == "Price chart":
        st.subheader("Closing price & moving averages")
        render_price_chart(data, trades)
    elif page == "Trade statistics":
        render_statistics(trades, build_statistics(trades))
    else:
        render_trade_table(trades)

    st.divider()
    st.caption(
        "Signals use daily closing prices. For educational purposes only; "
        "not investment advice."
    )


if __name__ == "__main__":
    main()
