import investing
import utils
import time
import os
import ta
#from binance.enums import TIME_IN_FORCE_GTC,SIDE_SELL
from binance.helpers import round_step_size
from binance.exceptions import BinanceAPIException, BinanceOrderException
from decimal import Decimal as D#, ROUND_DOWN, ROUND_UP
#import decimal
import pandas as pd 
from logger import log
from random import random
from vars import client
import vars
import orders
from tradingview_ta import Interval

def aroon():
    for pair in vars.cryptoList:
        if 'best_aroon' not in vars.cryptoList[pair].keys():
            return
        best_aroon = vars.cryptoList[pair]['best_aroon']
        longDB = utils.load(pair)
        try:
            bars3 = client.get_klines(symbol=pair, interval=client.KLINE_INTERVAL_3MINUTE, limit=150)
            time.sleep(1)
            bars15 = client.get_klines(symbol=pair, interval=client.KLINE_INTERVAL_15MINUTE, limit=150)
        except BinanceAPIException as e:
            log.error(f"status_code:{e.status_code}\nmessage:{e.message}")
            return
        df3 = pd.DataFrame(bars3, columns=utils.CANDLES_NAMES)
        df3 = utils.candleStringsToNumbers(df3)
        df15 = pd.DataFrame(bars15, columns=utils.CANDLES_NAMES)
        df15 = utils.candleStringsToNumbers(df15)
        utils.calculate_aroon(df3,best_aroon['aroon_period'])
        utils.calculate_aroon(df15,best_aroon['aroon_period'])
        price = df3['Close'].iloc[-1]
        row3 = df3.iloc[-1]
        row15 = df15.iloc[-1]
        # print('up:', row3['aroon_up'],'down', row3['aroon_down'], pair,'3m')
        # print('up:', row15['aroon_up'],'down', row15['aroon_down'], pair,'15m')
        if longDB is None:
            if row3['aroon_up'] < 20 and row3['aroon_down'] > 80 and row15['aroon_up'] < 20 and row15['aroon_down'] > 80:
                now = time.time()
                time_diff = now - vars.cryptoList[pair]['last_buy']
                if time_diff < 60*4:
                    continue
                vars.cryptoList[pair]['last_buy'] = now
                long(pair,price)
                return
        if longDB is not None:
            if row15['aroon_up'] > 80 and row15['aroon_down'] < 20:
                orders.sell_long(longDB,price)
                return
        time.sleep(1)

def flawless():
    for pair in vars.cryptoList:
        if 'best_flawless' not in vars.cryptoList[pair].keys():
            return
        best_flawless = vars.cryptoList[pair]['best_flawless']
        longDB = utils.load(pair)
        try:
            bars = client.get_klines(symbol=pair, interval=best_flawless['kline_time'], limit=150)
        except BinanceAPIException as e:
            log.error(f"status_code:{e.status_code}\nmessage:{e.message}")
            return
        df = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
        df = utils.candleStringsToNumbers(df)
        indicator_rsi = ta.momentum.RSIIndicator(
            close=df['Close'], window=14)
        df['rsi'] = indicator_rsi.rsi()
        indicator_bb1 = ta.volatility.BollingerBands(
            close=df["Close"], window=20, window_dev=1.0)
        df['upper1'] = indicator_bb1.bollinger_hband()
        df['lower1'] = indicator_bb1.bollinger_lband()
        indicator_bb2 = ta.volatility.BollingerBands(
            close=df["Close"], window=17, window_dev=1.0)
        df['upper2'] = indicator_bb2.bollinger_hband()
        df['lower2'] = indicator_bb2.bollinger_lband()
        price = df['Close'].iloc[-1]
        if longDB is None:
            BBBuyTrigger1 = price < df['lower1'].iloc[-1]
            rsiBuyGuard1 = df['rsi'].iloc[-1] > 42
            BBBuyTrigger2 = price < df['lower2'].iloc[-1]
            rsiBuyGuard2 = df['rsi'].iloc[-1] > 42
            
            if (BBBuyTrigger1 and rsiBuyGuard1) or (BBBuyTrigger2 and rsiBuyGuard2):
                now = time.time()
                time_diff = now - vars.cryptoList[pair]['last_buy']
                if time_diff < 60*4:
                    continue
                stop_loss = price - (price * (best_flawless['stop_loss']/100))
                take_profit = price + (price * (best_flawless['take_profit']/100))
                vars.cryptoList[pair]['last_buy'] = now
                long(pair,price,take_profit,stop_loss)
                return
        else:
            BBSellTrigger1 = price > df['upper1'].iloc[-1]
            rsiSellGuard1 = df['rsi'].iloc[-1] > 70
            BBSellTrigger2 = price > df['upper2'].iloc[-1]
            rsiSellGuard2 = df['rsi'].iloc[-1] > 76
            stop = price <= longDB['stop_loss'] or price >= longDB['take_profit']
            if (BBSellTrigger1 and rsiSellGuard1) or (BBSellTrigger2 and rsiSellGuard2) or stop:
                orders.sell_long(longDB,price)
                return
        time.sleep(1)

# def RSI():
#     for pair in vars.cryptoList:
#         best_rsi = vars.cryptoList[pair]['best_rsi']
#         if best_rsi is None:
#             return
#         longDB = utils.load(pair)
#         try:
#             bars = client.get_klines(symbol=pair, interval=client.KLINE_INTERVAL_3MINUTE, limit=200)
#         except BinanceAPIException as e:
#             log.error(f"status_code:{e.status_code}\nmessage:{e.message}")
#             return
#         df = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
#         df = utils.candleStringsToNumbers(df)
#         period = best_rsi['rsi_period']
#         utils.calculateRSI(df,period)
#         last = df["rsi"].iloc[-1]
#         penultimate = df["rsi"].iloc[-2]
#         price = df['Close'].iloc[-1]
#         if longDB is None and penultimate < 30 and last >= 30:
#             now = time.time()
#             time_diff = now - vars.cryptoList[pair]['last_buy']
#             if time_diff < 60*4:
#                 continue
#             stop_loss = price - (price * (best_rsi['stop_loss']/100))
#             vars.cryptoList[pair]['last_buy'] = now
#             long(pair,None,None,stop_loss,price)
#             return
#         elif longDB is not None:
#             if (penultimate > 70 and last <= 70) or price <= longDB['stop_loss']:
#                 orders.sell_long(longDB,price)
#                 return
#         time.sleep(2)

# def donchian_btc():
#     for pair in vars.cryptoList:
#         best_dc = vars.cryptoList[pair]['best_dc']
#         if best_dc is None:
#             return
#         longDB = utils.load(pair)
#         try:
#             bars = client.get_klines(symbol=pair, interval=best_dc['kline_time'], limit=50)
#         except BinanceAPIException as e:
#             log.error(f"status_code:{e.status_code}\nmessage:{e.message}")
#             return
#         df = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
#         df = utils.candleStringsToNumbers(df)
#         period = best_dc['dc_period']
        #volume = df['Volume'].iloc[-21:-1].sum()
        #price = (df['Close'].iloc[-21] + df['Close'].iloc[-1]) / 2
        #vars.cryptoList[pair]['volume_30m'] = volume * price
        # dc_low = ta.volatility.donchian_channel_lband(
        # df['High'], df['Low'], df['Close'], window=period, offset=0, fillna=False)
        # v = dc_low.iloc[-45:-4].unique()
        # if longDB is None and dc_low.iloc[-1] >= dc_low.iloc[-2] and dc_low.iloc[-2] > dc_low.iloc[-3] and v[-1] < v[-2]:
        #     now = time.time()
        #     time_diff = now - vars.cryptoList[pair]['last_buy']
        #     if time_diff < 60*4:
        #         continue
        #     vars.cryptoList[pair]['last_buy'] = now
        #     print('Price Diff',vars.cryptoList[pair]['high_risk'])
        #     log.debug(f"{pair} Donchian values:{dc_low.iloc[-1]},{dc_low.iloc[-2]}")
        #     long(pair,None,None,v[-1],df['Close'].iloc[-1])
        #     return
        # if longDB is not None:
        #     if df['Low'].iloc[-1] < dc_low.iloc[-2]:
        #         log.debug(f"{pair} Stop loss: {df['Low'].iloc[-1]},{dc_low.iloc[-2]}")
        #         orders.sell_long(longDB,df['Close'].iloc[-1])
        #         return
        # time.sleep(2)

def long(pair:str, price_f:float,take_profit:float = None, stop_loss:float = None):
    if vars.buying:
        print("Cancel buy")
        return
    log.debug(f"LONG pair:{pair}, stop_loss:{stop_loss}, stop_levels:0")
    if utils.load(pair) is not None:
        return
    vars.buying = True
    symbol_info = utils.getSymbolInfo(pair)
    minimum = float(symbol_info['filters_dic']['LOT_SIZE']['minQty'])
    step_size = float(symbol_info['filters_dic']['LOT_SIZE']['stepSize'])
    price_filter = float(symbol_info['filters_dic']['PRICE_FILTER']['tickSize'])
    #log.debug(f"min:{minimum},price_filter:{price_filter}")
    price = D.from_float(price_f).quantize(D(str(price_filter)))
    #log.debug(str(price))
    #diff = row['bb_ma'] - row['bb_l']
    #print('diff:',diff,'price:',row['Close'],'bb_l',row['bb_l'],'bb_h',row['bb_h'])
    #profit = row['Close'] + diff
    #win_percent = (diff / (row['Close'] / 100))/100
    # if win_percent > 0.005:#0.5%
    balance = float(client.get_asset_balance(asset='USDT')['free'])
    max_investment = float(os.environ.get('MAX_INVESTMENT') or 20)
    amount = balance if balance < max_investment else max_investment
    account_percent = 0.49
    if utils.load('BTCUPUSDT') is not None or utils.load('BTCDOWNUSDT') is not None:
        account_percent = 0.96
    amount = (amount*account_percent) / price_f
    amount = D.from_float(amount).quantize(D(str(minimum)))
    amount = round_step_size(amount, step_size)
    #log.debug(f"amount:{amount} minimum:{minimum}")
    if amount < minimum:
        log.warning('Need moar')
        utils.remove(pair)
        time.sleep(2)
        return
    utils.telegramMsg(f"Buying {amount} of <b>{pair}</b> at {price}")
    orders.market_buy(pair,amount,symbol_info,stop_loss,take_profit,price)
    #orders.open_book_socket(pair)
    vars.buying = False
    # output = []
    # for ind in vars.cryptoList:
    #     vol = vars.cryptoList[ind]['volume_30m'] or 0.0
    #     output.append(f"{ind} Vol:\n{vol:.1f}")
    # utils.telegramMsg('\n'.join(output))
        
def short(pair, dataFrame, client):
    return True
