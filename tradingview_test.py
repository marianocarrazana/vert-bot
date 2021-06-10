from tradingview_ta import TA_Handler, Interval, Exchange

tesla = TA_Handler(
    symbol="btcusdt",
    screener="crypto",
    exchange="binance",
    interval=Interval.INTERVAL_1_MINUTE
)
print(tesla.get_analysis().summary)
# Example output: {"RECOMMENDATION": "BUY", "BUY": 8, "NEUTRAL": 6, "SELL": 3}