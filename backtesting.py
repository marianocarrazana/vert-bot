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
import threading

def test_aroon(pair: str):
    date_range = "7 day ago UTC"
    kline_list = [
        Client.KLINE_INTERVAL_1MINUTE,
        # Client.KLINE_INTERVAL_3MINUTE,
        # Client.KLINE_INTERVAL_5MINUTE,
        # Client.KLINE_INTERVAL_15MINUTE,
        # Client.KLINE_INTERVAL_30MINUTE,
        # Client.KLINE_INTERVAL_1HOUR
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
        for aroon_period in range(30, 50):
            utils.calculate_aroon(df,aroon_period)
            for bottom in range(-80, -59):
                for top in range(60,81):
                    sleep(0.1)
                    funds = 100.0
                    purchase_price = None
                    for index, row in df.iterrows():
                        price = backtest.get_price(row['Open'], row['Close']) 
                        if row['aroon_osc'] <= bottom and purchase_price is None:
                                purchase_price = row['Close'] + (row['Close'] * (fees/100))
                        if purchase_price is not None:
                            if row['aroon_osc'] >= top:
                                diff = backtest.get_change(price,purchase_price)
                                funds = backtest.get_funds(funds, diff, fees)
                                purchase_price = None
                    if funds > best['funds']:
                        best = {'funds':funds,'aroon_period':aroon_period,'profit':funds-100.0,'top':top,'bottom':bottom,'kline_time':kline}
                    # print('Funds:',funds,'Period DC:',aroon_period,top,bottom)
    return best

def test_aroon_multi(pair:str):
    date_range = "5 day ago UTC"
    try:
        log.debug(f'Downloading data for {pair}[3m]...')
        bars3 = vars.client.get_historical_klines(pair.upper(), Client.KLINE_INTERVAL_3MINUTE, date_range)
        sleep(1)
        log.debug(f'Downloading data for {pair}[15m]...')
        bars15 = vars.client.get_historical_klines(pair.upper(), Client.KLINE_INTERVAL_15MINUTE, date_range)
    except BinanceAPIException as e:
        log.error(f"status_code:{e.status_code}\nmessage:{e.message}")
        return None
    log.debug('Proccesing data...')
    df15 = pd.DataFrame(bars15, columns=utils.CANDLES_NAMES)
    df15 = utils.candleStringsToNumbers(df15)
    df3 = pd.DataFrame(bars3, columns=utils.CANDLES_NAMES)
    df3 = utils.candleStringsToNumbers(df3)
    df3.set_index('Date', inplace=True)
    best = {'funds':0}
    fees = 0.075
    for aroon_period in range(6,30):
        sleep(0.1)
        utils.calculate_aroon(df3,aroon_period)
        utils.calculate_aroon(df15,aroon_period)
        funds = 100.0
        purchase_price = None
        for index, row15 in df15.iterrows():
            row3 = df3.loc[row15['Date']]
            if purchase_price is None:
                if row3['aroon_up'] < 20 and row3['aroon_down'] > 80 and row15['aroon_up'] < 20 and row15['aroon_down'] > 80:
                    purchase_price = row3['Open'] + (row3['Open'] * (fees/100))
                    continue
            else:
                if row15['aroon_up'] > 80 and row15['aroon_down'] < 20:
                    diff = backtest.get_change(row3['Open'],purchase_price)
                    funds = backtest.get_funds(funds, diff, fees)
                    purchase_price = None
                    continue
        if funds > best['funds']:
            best = {'funds':funds,'profit':funds-100.0,'aroon_period':aroon_period}
        #print(funds,aroon_period)
    return best

def test_flawless(pair: str):
    date_range = "5 day ago UTC"
    kline_list = [
        # Client.KLINE_INTERVAL_1MINUTE,
        Client.KLINE_INTERVAL_3MINUTE,
        Client.KLINE_INTERVAL_5MINUTE,
        Client.KLINE_INTERVAL_15MINUTE,
        # Client.KLINE_INTERVAL_30MINUTE,
        #Client.KLINE_INTERVAL_1HOUR
    ]
    best = {'funds':0}
    fees = 0.1
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
        utils.calculateRSI(df,14)
        indicator_bb1 = ta.volatility.BollingerBands(
            close=df["Close"], window=20, window_dev=1.0)
        df['upper1'] = indicator_bb1.bollinger_hband()
        df['lower1'] = indicator_bb1.bollinger_lband()
        indicator_bb2 = ta.volatility.BollingerBands(
            close=df["Close"], window=17, window_dev=1.0)
        df['upper2'] = indicator_bb2.bollinger_hband()
        df['lower2'] = indicator_bb2.bollinger_lband()
        RSILowerLevel1 = 42
        RSIUpperLevel1 = 70
        RSILowerLevel2 = 42
        RSIUpperLevel2 = 76
        for sl in range(10,101):
            stop_loss_percent = sl / 10
            for tp in range(4,60):
                sleep(0.07)
                take_profit_percent = tp / 10
                funds = 100.0
                purchase_price = None
                take_profit = None
                stop_loss = None
                for index, row in df.iterrows():
                    if take_profit is not None and stop_loss is not None:
                        if row['High'] > take_profit:
                            diff = backtest.get_change(take_profit,purchase_price)
                            funds = backtest.get_funds(funds, diff, fees)
                            purchase_price = None
                            take_profit = None
                            stop_loss = None
                            continue
                        elif row['Low'] < stop_loss:
                            diff = backtest.get_change(stop_loss,purchase_price)
                            funds = backtest.get_funds(funds, diff, fees)
                            purchase_price = None
                            take_profit = None
                            stop_loss = None
                            continue
                    #triggers 1
                    BBBuyTrigger1 = row['Open'] < row['lower1']
                    BBSellTrigger1 = row['Open'] > row['upper1']
                    rsiBuyGuard1 = row['rsi'] > RSILowerLevel1
                    rsiSellGuard1 = row['rsi'] > RSIUpperLevel1

                    if purchase_price is None:
                        if BBBuyTrigger1 and rsiBuyGuard1:
                            purchase_price = row['Open'] + (row['Open'] * (fees/100))
                            take_profit = None
                            stop_loss = None
                            continue
                    else:
                        if BBSellTrigger1 and rsiSellGuard1:
                            diff = backtest.get_change(row['Open'],purchase_price)
                            funds = backtest.get_funds(funds, diff, fees)
                            purchase_price = None
                            take_profit = None
                            stop_loss = None
                            continue
                    #triggers 2
                    BBBuyTrigger2 = row['Open'] < row['lower2']
                    BBSellTrigger2 = row['Open'] > row['upper2']
                    rsiBuyGuard2 = row['rsi'] > RSILowerLevel2
                    rsiSellGuard2 = row['rsi'] > RSIUpperLevel2

                    if purchase_price is None:
                        if BBBuyTrigger2 and rsiBuyGuard2:
                            purchase_price = row['Open'] + (row['Open'] * (fees/100))
                            take_profit = purchase_price + (purchase_price*(take_profit_percent/100))
                            stop_loss = purchase_price - (purchase_price*(stop_loss_percent/100))
                    else:
                        if BBSellTrigger2 and rsiSellGuard2:
                            diff = backtest.get_change(row['Open'],purchase_price)
                            funds = backtest.get_funds(funds, diff, fees)
                            purchase_price = None
                            take_profit = None
                            stop_loss = None
                            continue
                if funds > best['funds']:
                    best = {'funds':funds,'profit':funds-100.0,'kline_time':kline,'stop_loss':stop_loss_percent,'take_profit':take_profit_percent}
                #print('Funds:',funds,'stop_loss:',stop_loss_percent,'take_profit:',take_profit_percent)
    return best

def test_dc(pair: str):
    date_range = "10 day ago UTC"
    kline_list = [
        # Client.KLINE_INTERVAL_1MINUTE,
        Client.KLINE_INTERVAL_3MINUTE,
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
        get_data = test_aroon(pair)
        if get_data is not None:
            data[pair] = get_data
            vars.cryptoList[pair]['best_aroon'] = get_data
        else:
            return
    utils.save('best_aroon',data)
    utils.telegramMsg(f"{data}")

def check():
    best_aroon = utils.load('best_aroon')
    if best_aroon is None:
        load_data()
    else:
        now = datetime.datetime.now()
        if best_aroon['last_check'] != now.day and now.hour > 3:
            load_data()
        else:
            for pair in vars.cryptoList:
                vars.cryptoList[pair]['best_aroon'] = best_aroon[pair]
    vars.running_backtesting = False

def run_background():
    if vars.running_backtesting:
        return
    vars.running_backtesting = True
    back_thread = threading.Thread(target=check)
    back_thread.start()

if __name__ == "__main__":
    check()