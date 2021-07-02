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

def RSI():
    for pair in vars.cryptoList:
        best_rsi = vars.cryptoList[pair]['best_rsi']
        if best_rsi is None:
            return
        longDB = utils.load(pair)
        try:
            bars = client.get_klines(symbol=pair, interval=client.KLINE_INTERVAL_3MINUTE, limit=200)
        except BinanceAPIException as e:
            log.error(f"status_code:{e.status_code}\nmessage:{e.message}")
            return
        df = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
        df = utils.candleStringsToNumbers(df)
        period = best_rsi['rsi_period']
        utils.calculateRSI(df,period)
        last = df["rsi"].iloc[-1]
        penultimate = df["rsi"].iloc[-2]
        price = df['Close'].iloc[-1]
        if longDB is None and penultimate < 30 and last >= 30:
            now = time.time()
            time_diff = now - vars.cryptoList[pair]['last_buy']
            if time_diff < 60*4:
                continue
            stop_loss = price - (price * (best_rsi['stop_loss']/100))
            vars.cryptoList[pair]['last_buy'] = now
            long(pair,None,None,stop_loss,price)
            return
        elif longDB is not None:
            if (penultimate > 70 and last <= 70) or price <= longDB['stop_loss']:
                orders.sell_long(longDB,price)
                return
        time.sleep(2)

def donchian_btc():
    for pair in vars.cryptoList:
        longDB = utils.load(pair)
        try:
            bars = client.get_klines(symbol=pair, interval=client.KLINE_INTERVAL_3MINUTE, limit=200)
        except BinanceAPIException as e:
            log.error(f"status_code:{e.status_code}\nmessage:{e.message}")
            return
        df = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
        df = utils.candleStringsToNumbers(df)
        utils.calculateRSI(df)
        period = 10 if longDB is None else 14
        if period == 14 and vars.cryptoList[pair]['high_risk']:
            period = 8
        volume = df['Volume'].iloc[-21:-1].sum()
        price = (df['Close'].iloc[-21] + df['Close'].iloc[-1]) / 2
        vars.cryptoList[pair]['volume_30m'] = volume * price
        dc_low = ta.volatility.donchian_channel_lband(
        df['High'], df['Low'], df['Close'], window=period, offset=0, fillna=False)
        v = dc_low.iloc[-50:-4].unique()
        if longDB is None and dc_low.iloc[-1] >= dc_low.iloc[-2] and dc_low.iloc[-2] > dc_low.iloc[-3] and dc_low.iloc[-3] == v[-1] and v[-1] < v[-2]:
            vars.cryptoList[pair]['overbought'] = False
            now = time.time()
            time_diff = now - vars.cryptoList[pair]['last_buy']
            if time_diff < 60*5:
                continue
            vars.cryptoList[pair]['last_buy'] = now
            #price_diff = utils.get_change(df['Close'].iloc[-1],dc_low.iloc[-1])
            vars.cryptoList[pair]['high_risk'] = df['rsi'].iloc[-1] > 50
            print('Price Diff',vars.cryptoList[pair]['high_risk'],df['rsi'].iloc[-1])
            log.debug(f"{pair} Donchian values:{dc_low.iloc[-1]},{v[-2]},{v[-3]},{v[-4]}")
            long(pair,None,None,v[-1],df['Close'].iloc[-1])
            return
        if longDB is not None:
            if df['rsi'].iloc[-2] >= 70:
                vars.cryptoList[pair]['overbought'] = True
            if vars.cryptoList[pair]['overbought']:
                dc_low = ta.volatility.donchian_channel_lband(
                    df['High'], df['Low'], df['Close'], window=6, offset=0, fillna=False)
            if df['Low'].iloc[-1] < dc_low.iloc[-2]:
                vars.cryptoList[pair]['high_risk'] = False
                log.debug(f"{pair} Stop loss: {df['Low'].iloc[-1]},{dc_low.iloc[-2]}")
                orders.sell_long(longDB,df['Close'].iloc[-1])
                return
        time.sleep(2)

def long(pair, dataFrame, old_client, stop_loss, price_f):
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
    if dataFrame is not None:
        row = dataFrame.iloc[-1]
        price_f = float(row['Close'])
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
    if utils.load('BTCUPUSDT') is not None and utils.load('BTCDOWNUSDT') is not None:
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
    orders.market_buy(pair,amount,symbol_info,stop_loss,price)
    #orders.open_book_socket(pair)
    vars.buying = False
    # output = []
    # for ind in vars.cryptoList:
    #     vol = vars.cryptoList[ind]['volume_30m'] or 0.0
    #     output.append(f"{ind} Vol:\n{vol:.1f}")
    # utils.telegramMsg('\n'.join(output))
        
def short(pair, dataFrame, client):
    return True
