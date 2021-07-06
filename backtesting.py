import utils
import vars
import pandas as pd
from binance import Client
from logger import log
from time import sleep
import datetime
from binance.exceptions import BinanceAPIException, BinanceOrderException
from lib import backtest
import ta

def test_dc(pair: str):
    date_range = "10 day ago UTC"
    kline_list = [
        # Client.KLINE_INTERVAL_1MINUTE,
        # Client.KLINE_INTERVAL_3MINUTE,
        Client.KLINE_INTERVAL_5MINUTE,
        Client.KLINE_INTERVAL_15MINUTE,
        Client.KLINE_INTERVAL_30MINUTE,
        Client.KLINE_INTERVAL_1HOUR
    ]
    best = {'funds':0}
    fees = 0.075
    for kline in kline_list:
        log.debug(f'Downloading data for {pair}[{kline}]...')
        try:
            bars = vars.client.get_historical_klines(pair.upper(), kline, date_range)
        except BinanceAPIException as e:
            log.error(f"status_code:{e.status_code}\nmessage:{e.message}")
            return None
        log.debug('Proccesing data...')
        df = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
        df = utils.candleStringsToNumbers(df)
        for dc_period in range(1, 22):
            sleep(0.1)
            for profit_val in range(10,11):
                dc = ta.volatility.DonchianChannel(
                    df['High'], df['Low'], df['Open'], window=dc_period, offset=0, fillna=True)
                df['dc_low'] = dc.donchian_channel_lband()
                penultimate = 0
                funds = 100.00
                purchase_price = None
                for index, row in df.iterrows():
                    last = row['dc_low']
                    if penultimate == 0 or last == 0:
                        penultimate = last
                        continue
                    price = backtest.get_price(row['Open'], row['Close']) 
                    if penultimate < last and purchase_price is None:
                        purchase_price = row['Close'] + (row['Close'] * (fees/100))
                    if purchase_price is not None:
                        if penultimate > last:
                            diff = backtest.get_change(price,purchase_price)
                            #print(funds,diff,price)
                            funds = backtest.get_funds(funds, diff, fees)
                            purchase_price = None
                    penultimate = last
                if funds > best['funds']:
                    best = {'funds':funds,'dc_period':dc_period,'profit':funds-100.0,'kline_time':kline}
                print('Funds:',funds,'Period DC:',dc_period)
        print(best)
    return best

def test_rsi(pair: str):
    log.debug(f'Downloading data for {pair}...')
    try:
        bars = vars.client.get_historical_klines(pair.upper(), Client.KLINE_INTERVAL_3MINUTE, "6 day ago UTC")
    except BinanceAPIException as e:
        log.error(f"status_code:{e.status_code}\nmessage:{e.message}")
        return None
    log.debug('Proccesing data...')
    df = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
    df = utils.candleStringsToNumbers(df)
    best = {'funds':0}
    for rsi_period in range(5, 18):
        #log.debug(f'Testing with period {rsi_period}')
        utils.calculateRSI(df,rsi_period)
        for i in range(20,71):
            sleep(0.1)
            penultimate = 50
            funds = 100.00
            stop_loss_percent = i/10
            purchase_price = None
            stop_loss = None
            fees = 0.075
            for index, row in df.iterrows():
                last = row['rsi'] or 50
                price = backtest.get_price(row['Open'], row['Close']) 
                if penultimate < 30 and last >= 30 and purchase_price is None:
                    purchase_price = price
                    stop_loss = backtest.get_stop_loss(price, stop_loss_percent)
                if purchase_price is not None:
                    if row['Low'] <= stop_loss:
                        price = stop_loss
                        last = 70
                        penultimate = 71
                    if (penultimate > 70 and last <= 70):
                        diff = backtest.get_change(price,purchase_price)
                        #print(funds,diff,price)
                        funds = backtest.get_funds(funds, diff, fees)
                        purchase_price = None
                penultimate = row['rsi'] or 50
            if funds > best['funds']:
                best = {'funds':funds,'rsi_period':rsi_period,'stop_loss':stop_loss_percent,'profit':funds-100.0}
        #print('Funds:',funds,'Period RSI:',rsi_period)
    print(best)
    return best

def load_data():
    now = datetime.datetime.now()
    data = {'last_check':now.day}
    for pair in vars.cryptoList:
        get_data = test_dc(pair)
        if get_data is not None:
            data[pair] = get_data
            vars.cryptoList[pair]['best_dc'] = get_data
        else:
            return
    utils.save('best_dc',data)
    utils.telegramMsg(f"{data}")

def check():
    best_dc = utils.load('best_dc')
    if best_dc is None:
        load_data()
    else:
        now = datetime.datetime.now()
        if best_dc['last_check'] != now.day and now.hour > 3:
            load_data()
        else:
            for pair in vars.cryptoList:
                vars.cryptoList[pair]['best_dc'] = best_dc[pair]

if __name__ == "__main__":
    check()