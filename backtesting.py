import utils
import vars
import pandas as pd
from binance import Client

print('Downloading data...')
bars = vars.client.get_historical_klines("BTCDOWNUSDT", Client.KLINE_INTERVAL_1MINUTE, "2 day ago UTC")
print('Proccesing data...')
df = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
df = utils.candleStringsToNumbers(df)
for rsi_period in range(5, 17):
    utils.calculateRSI(df,rsi_period)
    best = {'funds':0}
    for i in range(10,71):
        penultimate = 50
        funds = 100.00
        stop_loss_percent = i/10
        wins = []
        losses = []
        win_percent = 0
        purchase_price = None
        stop_loss = None
        fees = 0.075
        for index, row in df.iterrows():
            last = row['rsi'] or 50
            price = (row['Open'] + (row['Open'] + row['Close']) / 2) / 2
            if penultimate < 30 and last >= 30 and purchase_price is None:
                purchase_price = price
                stop_loss = price - (price*(stop_loss_percent/100))
            if purchase_price is not None:
                if row['Low'] <= stop_loss:
                    price = stop_loss
                    last = 70
                    penultimate = 71
                if (penultimate > 70 and last <= 70):
                    diff = utils.get_change(price,purchase_price)
                    #print(funds,diff,price)
                    funds = funds + (funds*(diff/100))
                    funds = funds - (funds*(fees/100))
                    purchase_price = None
            penultimate = row['rsi'] or 50
        #print('Funds:',funds,'Period RSI:',rsi_period)
        if funds > best['funds']:
            best = {'funds':funds,'rsi_period':rsi_period,'stop_loss':stop_loss_percent,'profit':funds-100.0}
    print(best)