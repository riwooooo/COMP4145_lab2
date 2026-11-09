# MSFT Golden Cross Backtest

A Streamlit dashboard for exploring a five-year MSFT golden-cross backtest.

The app has three views:

- **Price chart:** daily closing price, 50-day and 200-day moving averages, and buy/sell markers.
- **Trade statistics:** trade count, win rate, average return, and average holding period.
- **Detailed trades:** buy/sell dates and prices, return, holding period, and exit reason.

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The dashboard downloads historical prices through `yfinance` when it runs. The backtest buys when the 50-day moving average crosses above the 200-day moving average, and sells at a 15% target or after up to 60 calendar days.

This project is for educational purposes only and is not investment advice.
