from typing import Union

import pandas as pd
import yfinance as yf


def get_stock_data(ticker: str, period: str = "5y") -> pd.DataFrame:
    stock = yf.Ticker(ticker)
    return stock.history(period=period)


def calculate_moving_averages(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["MA50"] = data["Close"].rolling(window=50).mean()
    data["MA200"] = data["Close"].rolling(window=200).mean()
    return data


def identify_golden_cross(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["GoldenCross"] = (data["MA50"] > data["MA200"]) & (
        data["MA50"].shift(1) <= data["MA200"].shift(1)
    )
    return data


def implement_strategy(data: pd.DataFrame) -> pd.DataFrame:
    positions = []

    # The first 200 rows cannot have a complete 200-day moving average.
    data = data.iloc[200:].copy()
    buy_dates = data.index[data["GoldenCross"]].tolist()

    for buy_date in buy_dates:
        buy_price = data.loc[buy_date, "Close"]
        target_price = buy_price * 1.15
        max_sell_date = buy_date + pd.Timedelta(days=60)
        sell_period = data.loc[buy_date:max_sell_date]
        target_reached = sell_period[sell_period["Close"] >= target_price]

        if not target_reached.empty:
            sell_date = target_reached.index[0]
            sell_price = target_reached.loc[sell_date, "Close"]
            sell_reason = "Target reached"
        elif not sell_period.empty:
            sell_date = sell_period.index[-1]
            sell_price = data.loc[sell_date, "Close"]
            sell_reason = "Max holding period"
        else:
            continue

        positions.append(
            {
                "BuyDate": buy_date,
                "BuyPrice": buy_price,
                "SellDate": sell_date,
                "SellPrice": sell_price,
                "HoldingDays": (sell_date - buy_date).days,
                "ProfitPct": (sell_price / buy_price - 1) * 100,
                "SellReason": sell_reason,
            }
        )

    return pd.DataFrame(
        positions,
        columns=[
            "BuyDate",
            "BuyPrice",
            "SellDate",
            "SellPrice",
            "HoldingDays",
            "ProfitPct",
            "SellReason",
        ],
    )


def analyze_results(positions: pd.DataFrame) -> Union[pd.DataFrame, str]:
    if positions.empty:
        print("No trading signals detected")
        return "No trading signals detected"

    total_trades = len(positions)
    win_trades = int((positions["ProfitPct"] > 0).sum())
    loss_trades = total_trades - win_trades
    win_rate = win_trades / total_trades * 100
    avg_profit = positions["ProfitPct"].mean()

    print("\n===== Trading Strategy Results (Golden Cross) =====")
    print(f"Total Trades: {total_trades}")
    print(f"Winning Trades: {win_trades} ({win_rate:.2f}%)")
    print(f"Losing Trades: {loss_trades}")
    print(f"Average Profit: {avg_profit:.2f}%")

    return positions


def main() -> pd.DataFrame:
    data = get_stock_data("MSFT")
    data = calculate_moving_averages(data)
    data = identify_golden_cross(data)
    positions = implement_strategy(data)
    analyze_results(positions)
    return positions


if __name__ == "__main__":
    positions = main()
    print("\nDetailed Trades:")
    print(positions.to_string(index=False))