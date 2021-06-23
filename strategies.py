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

def RSI(dataFrame, investing_id, pair, client):
    last = dataFrame["rsi"].iloc[-1]
    penultimate = dataFrame["rsi"].iloc[-2]
    log.debug(last,penultimate)
    # long(pair, dataFrame, client)#test
    # return False
    # if(penultimate < 30 and last >= 30):
    #     trigger = 'buy' if pair.lower().find('down') == -1 else 'sell'
    #     invest_state = investing.getTechnicalData(investing_id, '5mins').lower()
    #     print(pair,trigger,invest_state)
    #     if invest_state.find(trigger) != -1:
    #         long(pair, dataFrame, client)
    # elif(penultimate > 70 and last <= 70):
    #     trigger = 'buy' if pair.lower().find('down') != -1 else 'sell'
    #     invest_state = investing.getTechnicalData(investing_id, '5mins').lower()
    #     if invest_state.find(trigger) != -1:
    #         short(pair, dataFrame, client)

def dc_aroon(crypto_data,pair,client):
    df = crypto_data['dataFrame']
    if utils.get_change(df['Close'].iloc[-2], df['Open'].iloc[-2]) < 0.02:
        return
    if utils.get_change(df['Close'].iloc[-1], df['Open'].iloc[-1]) < 0.01:
        return
    if df['Low'].iloc[-2] > df['Low'].iloc[-1]:
        return
    period = 14
    dc_low = ta.volatility.donchian_channel_lband(
        df['High'], df['Low'], df['Close'], window=period, offset=0, fillna=False)
    if dc_low.iloc[-3] == df['Low'].iloc[-3]:#donchian channel touch the low of a stick
        dc_mid = ta.volatility.donchian_channel_mband(
            df['High'], df['Low'], df['Close'], window=period, offset=0, fillna=False)
        #difference = dc_mid.iloc[-1] - dc_low.iloc[-1]#diff between dc mid and low band
        maximum = dc_mid.iloc[-1] #dc_low.iloc[-1] + (difference * 0.51)
        if df['Close'].iloc[-1] < maximum:
            # aroon = ta.trend.AroonIndicator(
            #     close = df['Close'], window = period, fillna = False)
            # aroon_down = aroon.aroon_down()
            # if aroon_down.iloc[-1] > 80:
            #     aroon_up = aroon.aroon_up()
            #     if aroon_up.iloc[-1] < 20:
            sl_levels = None # difference / 2
            long(pair,df,client,df['Low'].iloc[-2],sl_levels)

def book_depth(bid_list,ask_list,pair):
    if len(bid_list) != 20 or len(ask_list) != 20:
        return
    bid_max = 0.0
    bid_max_index = 0
    ratios = []
    bid_total = 0.0
    ask_total = 0.0
    for i in range(10):
        bids = 0.0
        asks = 0.0
        for e in range(2):
            n = i * 2 + e
            bid = float(bid_list[n][1])
            asks += float(ask_list[n][1])
            bids += bid
            if bid > bid_max:
                bid_max = bid
                bid_max_index = n
        if asks > 0.0:
            diff = bids/asks
            ratios.append(round(diff))
            min_diff = 1.0
            if diff < min_diff:
                return
        else:
            return
        bid_total += bids
        ask_total += asks
    total_ratio = bid_total/ask_total
    if total_ratio > 100:
        #utils.telegramMsg(f"Buy wall on {pair}")
        log.debug(f"Buy wall on {pair} at {bid_list[bid_max_index][0]}, diff:{ratios}")
        price = float(ask_list[n][0])
        sl = price - (price * 0.003)
        #long(pair, None, vars.client, sl, price)

best_bet = {'pair':None}
def examine_market():
    global best_bet
    if best_bet['pair'] is not None:
        ticker = vars.client.get_orderbook_ticker(symbol=best_bet['pair'])
        diff = utils.get_change(float(ticker['bidPrice']),float(best_bet['price']))
        utils.telegramMsg(f"Selling <b>{best_bet['pair']}</b> at {best_bet['price']}\nDifference:{diff:.2f}%")
    best_bet = {'pair':None,'ratio':1.0,'price':''}
    for cr in investing.CRYPTO:
        book = vars.client.get_order_book(symbol=cr['binance_id'],limit=1000)
        max_ask = float(book["asks"][0][0]) * 1.02
        min_bid = float(book["bids"][0][0])
        min_bid = min_bid - (min_bid*0.02)
        bid_list = []
        ask_list = []
        total_ask = 0.0
        total_bid = 0.0
        for a in book["asks"]:
            if float(a[0]) <= max_ask:
                price = float(a[0])
                qty = float(a[1])
                total_ask += qty
                ask_list.append([price,qty])
        for b in book["bids"]:
            if float(b[0]) >= min_bid:
                price = float(b[0])
                qty = float(b[1])
                total_bid += qty
                bid_list.append([price,qty])
        ratio = total_bid/total_ask
        if ratio > best_bet['ratio']:
            best_bet = {'pair':cr['binance_id'],'ratio':ratio,'price':book["asks"][0][0]}
        # print(cr['binance_id'],len(ask_list),len(bid_list),ratio)
        time.sleep(1)
    if best_bet['pair'] is not None:
        utils.telegramMsg(f"Buying <b>{best_bet['pair']}</b> at {best_bet['price']}")
        #long(best_bet['pair'])

def examine_btc():
    long_data = utils.load('long')
    data = investing.getTechnicalData('btcusdt',Interval.INTERVAL_1_MINUTE)
    if data == 'Strong Buy':
        if long_data is None:
            pair = 'BTCUPUSDT'
            ticker = vars.client.get_orderbook_ticker(symbol=pair)
            price = float(ticker['askPrice'])
            stop_loss = price - (price*0.005)
            long(pair,None,None,stop_loss,price)
        else:
            if long_data['pair'] == 'BTCDOWNUSDT':
                pair = 'BTCDOWNUSDT'
                ticker = vars.client.get_orderbook_ticker(symbol=pair)
                price = float(ticker['askPrice'])
                orders.sell_long(long_data,price)
                utils.remove('long')
    elif data == 'Buy' and long_data is not None:
        if long_data['pair'] == 'BTCDOWNUSDT':
            pair = 'BTCDOWNUSDT'
            ticker = vars.client.get_orderbook_ticker(symbol=pair)
            price = float(ticker['bidPrice'])
            orders.sell_long(long_data,price)
            utils.remove('long')
    elif data == 'Strong Sell':
        if long_data is None:
            pair = 'BTCDOWNUSDT'
            ticker = vars.client.get_orderbook_ticker(symbol=pair)
            price = float(ticker['askPrice'])
            stop_loss = price - (price*0.005)
            long(pair,None,None,stop_loss,price)
        else:
            if long_data['pair'] == 'BTCUPUSDT':
                pair = 'BTCUPUSDT'
                ticker = vars.client.get_orderbook_ticker(symbol=pair)
                price = float(ticker['askPrice'])
                orders.sell_long(long_data,price)
                utils.remove('long')
    elif data == 'Sell' and long_data is not None:
        if long_data['pair'] == 'BTCUPUSDT':
            pair = 'BTCUPUSDT'
            ticker = vars.client.get_orderbook_ticker(symbol=pair)
            price = float(ticker['bidPrice'])
            orders.sell_long(long_data,price)
            utils.remove('long')

def donchian_btc():
    pairs = ['BTCUPUSDT','BTCDOWNUSDT']
    for pair in pairs:
        longDB = utils.load(pair)
        bars = client.get_klines(symbol=pair, interval=client.KLINE_INTERVAL_1MINUTE, limit=200)
        df = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
        df = utils.candleStringsToNumbers(df)
        period = 14
        dc_low = ta.volatility.donchian_channel_lband(
        df['High'], df['Low'], df['Close'], window=period, offset=0, fillna=False)
        v = dc_low.unique()
        if longDB is None and v[-1] > v[-2] and v[-2] < v[-3] and v[-3] < v[-4]:
            long(pair,None,None,v[-1],df['Close'].iloc[-1])
            return
        if longDB is not None:
            if longDB['stop_loss'] < v[-2]:
                longDB['stop_loss'] = v[-2]
                utils.save(pair,longDB)
                return
        time.sleep(1.24)


def long(pair, dataFrame, old_client, stop_loss, price_f):
    if vars.buying:
        return
    log.debug(f"LONG pair:{pair}, stop_loss:{stop_loss}, stop_levels:0")
    if utils.load(pair) is not None:
        return
    vars.buying = True
    utils.save(pair,
        {'pair':pair,'stop_loss':stop_loss,'qty':'0','profit':None,'purchase_price':None})
    symbol_info = utils.getSymbolInfo(pair)
    minimum = float(symbol_info['filters_dic']['LOT_SIZE']['minQty'])
    step_size = float(symbol_info['filters_dic']['LOT_SIZE']['stepSize'])
    price_filter = float(symbol_info['filters_dic']['PRICE_FILTER']['tickSize'])
    log.debug(f"min:{minimum},price_filter:{price_filter}")
    if dataFrame is not None:
        row = dataFrame.iloc[-1]
        print(row)
        price_f = float(row['Close'])
    price = D.from_float(price_f).quantize(D(str(price_filter)))
    log.debug(str(price))
    #diff = row['bb_ma'] - row['bb_l']
    #print('diff:',diff,'price:',row['Close'],'bb_l',row['bb_l'],'bb_h',row['bb_h'])
    #profit = row['Close'] + diff
    #win_percent = (diff / (row['Close'] / 100))/100
    # if win_percent > 0.005:#0.5%
    balance = float(client.get_asset_balance(asset='USDT')['free'])
    max_investment = float(os.environ.get('MAX_INVESTMENT') or 20)
    amount = balance if balance < max_investment else max_investment
    account_percent = 0.48
    if utils.load('BTCUPUSDT') is not None and utils.load('BTCDOWNUSDT') is not None:
        account_percent = 0.96
    amount = (amount*account_percent) / price_f
    amount = D.from_float(amount).quantize(D(str(minimum)))
    amount = round_step_size(amount, step_size)
    log.debug(f"amount:{amount} minimum:{minimum}")
    if amount < minimum:
        log.warning('Need moar')
        utils.remove(pair)
        time.sleep(2)
        return
    utils.telegramMsg(f"Buying {amount} of <b>{pair}</b> at {price}")
    orders.market_buy(pair,amount,symbol_info,stop_loss,price)
    #orders.open_book_socket(pair)
    vars.buying = False
        
def short(pair, dataFrame, client):
    return True
