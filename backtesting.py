import utils
import vars
import pandas as pd
from binance import Client
from logger import log
from time import sleep
import datetime
from binance.exceptions import BinanceAPIException, BinanceOrderException
from lib import backtest

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
        get_data = test_rsi(pair)
        if get_data is not None:
            data[pair] = get_data
            vars.cryptoList[pair]['best_rsi'] = get_data
        else:
            return
    utils.save('best_rsi',data)
    utils.telegramMsg(f"{data}")

def check():
    best_rsi = utils.load('best_rsi')
    if best_rsi is None:
        load_data()
    else:
        now = datetime.datetime.now()
        if best_rsi['last_check'] != now.day:
            load_data()
        else:
            for pair in vars.cryptoList:
                vars.cryptoList[pair]['best_rsi'] = best_rsi[pair]
