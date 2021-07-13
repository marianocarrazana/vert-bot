#import finplot as fplt
import ta
import requests
import urllib.parse
import pandas as pd 
from tinydb import TinyDB, Query
from logger import log
from vars import client
from math import sqrt

CANDLES_NAMES = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'closetime',
                 'quoteasset', 'numbertrades', 'takerbaseasset', 'takerquoteasset', 'ignore']


def candleStringsToNumbers(bars):
    return bars.astype({'Date': int,
                        'Volume': 'float',
                        'Open': 'float', 'High': 'float',
                        'Low': 'float', 'Close': 'float',
                        'quoteasset': 'float', 'takerbaseasset': 'float',
                        'takerquoteasset': 'float', 'ignore': 'float',
                        'closetime': int})


def plot(dt):
    return True
    # ax, ax2 = fplt.create_plot("plot", rows=2)
    # fplt.candlestick_ochl(dt[['Date', 'Open', 'Close', 'High', 'Low']], ax=ax)
    # volumes = dt[['Date', 'Open', 'Close', 'Volume']]
    # fplt.volume_ocv(volumes, ax=ax.overlay())
    # fplt.plot(dt['Date'], dt['Close'].rolling(
    #     25).mean(), ax=ax, legend='ma-25')
    # fplt.plot(dt['bb_h'], color='#4e4ef1')
    # fplt.plot(dt['bb_ma'], color='#fe4e41')
    # fplt.plot(dt['bb_l'], color='#4efe41')
    # fplt.plot(dt['Date'], dt['rsi'], ax=ax2, color='#927', legend='rsi')
    # fplt.set_y_range(0, 100, ax=ax2)
    # fplt.add_band(25, 75, ax=ax)
    # fplt.show()

def calculate_aroon(data_frame,period=14):
    data_frame['aroon_up'] = aroon_up(data_frame['High'],period)
    data_frame['aroon_down'] = aroon_down(data_frame['Low'],period)

def aroon_up(series,period=14):
    up = 100 * series.rolling(period+1).apply(lambda x: x.argmax()) / period
    return up

def aroon_down(series,period=14):
    down = 100 * series.rolling(period+1).apply(lambda x: x.argmin()) / period
    return down

def calculateBB(dataFrame,period=21,mult=2.0):
    indicator_bb = ta.volatility.BollingerBands(
        close=dataFrame["Close"], window=period, window_dev=mult)
    dataFrame['bb_h'] = indicator_bb.bollinger_hband()
    dataFrame['bb_ma'] = indicator_bb.bollinger_mavg()
    dataFrame['bb_l'] = indicator_bb.bollinger_lband()

def calculateRSI(dataFrame,period=14):
    # if 'rsi' in dataFrame:
    #     del dataFrame['rsi']
    indicator_rsi = ta.momentum.RSIIndicator(
        close=dataFrame['Open'], window=period)
    dataFrame['rsi'] = indicator_rsi.rsi()

def calculate_supertrend(data_frame,atr_period=9,atr_multiplier=3.0):
    atr = ta.volatility.AverageTrueRange(data_frame['High'], data_frame['Low'], data_frame['Close'],window=atr_period,fillna=True)
    data_frame['atr'] = atr.average_true_range()
    empty_arr = [0] * len(data_frame)
    data_frame['up'] = empty_arr
    data_frame['down'] = empty_arr
    data_frame['st'] = empty_arr
    for index, row in data_frame.iterrows():
        if index == 0:
            data_frame.loc[index,'st'] = 0
            continue
        last_close = data_frame.loc[index-1,'Close']
        up = row['Open']-(atr_multiplier*row['atr'])
        up1 = data_frame.loc[index-1,'up'] or up
        data_frame.loc[index,'up'] = max(up,up1) if last_close > up1 else up
        down = row['Open']+(atr_multiplier*row['atr'])
        down1 = data_frame['down'].loc[index-1] or down
        data_frame.loc[index,'down'] = min(down, down1) if last_close < down1 else down
        trend = 1
        trend = data_frame['st'].loc[index-1] or trend
        if trend == -1 and row['Close'] > down1:
            trend = 1
        elif trend == 1 and row['Close'] < up1:
            trend = -1
        data_frame.loc[index,'st'] = trend

def calculate_rma(data_frame, length: int):
    empty_arr = [0] * len(data_frame)
    data_frame['rma'] = empty_arr
    alpha = 1/length
    indicator = ta.trend.SMAIndicator(
        close=data_frame['Open'], window=length, fillna=True)
    data_frame['sma'] = indicator.sma_indicator()
    for index, row in data_frame.iterrows():
        if index == 0:
            data_frame.loc[index,'rma'] = row['sma']
            continue
        data_frame.loc[index,'rma'] = alpha * row['Open'] + (1 - alpha) * data_frame['rma'].loc[index-1]

def calculate_stdev(data_frame, length: int, df_name = 'stdev'):
    empty_arr = [0] * len(data_frame)
    data_frame[df_name] = empty_arr
    indicator = ta.trend.SMAIndicator(
        close=data_frame['Open'], window=length, fillna=True)
    data_frame['sma'] = indicator.sma_indicator()
    for index, row in data_frame.iterrows():
        if index < length:
            data_frame.loc[index,df_name] = 0.0
            continue
        sumOfSquareDeviations = 0.0
        for i in range(0,length):
            sum1 = SUM(data_frame['Open'].loc[index - i], -row['sma'])
            sumOfSquareDeviations = sumOfSquareDeviations + sum1 * sum1
        data_frame.loc[index,df_name] = sqrt(sumOfSquareDeviations / length)

def isZero(val,eps): return abs(val) <= eps

def SUM(fst, snd):
    eps = 1e-10
    res = fst + snd
    if isZero(res, eps):
        return 0
    else:
        if not isZero(res, 1e-4):
            return res
        else:
            return 15

def telegramMsg(message,error=False):
    #log.debug(f"Sending message:{message}")
    token = "1321535286:AAEpm9JB4zDhkANld8C4ct1-fUyAwkPCOHI"
    channel = "@crybottesting"
    message = urllib.parse.quote(message)
    requests.get(f"https://api.telegram.org/bot{token}/sendMessage?chat_id={channel}&text={message}&parse_mode=html")
    
db = TinyDB('./db.json')
query = Query()

def save(varName,data):
    global db,query
    if len(db.search(query.name == varName)) == 0:
        db.insert({'name':varName,'data':data})
    else:
        db.update({'name':varName,'data':data}, query.name == varName)
    
def load(varName):
    global db,query
    s = db.search(query.name == varName)
    if len(s) != 0:
        return s[0]['data']
    else:
        return None

def remove(varName):
    global db,query
    db.remove(query.name == varName)
    
def getSymbolInfo(pair):
    symbol_info = client.get_symbol_info(pair)
    symbol_info['filters_dic'] = {}
    for filters in symbol_info['filters']:
        symbol_info['filters_dic'][filters['filterType']] = filters
    return symbol_info

def get_change(current, previous):
    if current == previous:
        return 0
    try:
        return ((current - previous) / previous) * 100.0
    except ZeroDivisionError:
        return float('inf')
