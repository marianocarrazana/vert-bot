#import finplot as fplt
import ta
import requests
import urllib.parse
from tinydb import TinyDB, Query
from logger import log
from vars import client

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


def calculateBB(dataFrame):
    indicator_bb = ta.volatility.BollingerBands(
        close=dataFrame["Close"], window=21, window_dev=2)
    dataFrame['bb_h'] = indicator_bb.bollinger_hband()
    dataFrame['bb_ma'] = indicator_bb.bollinger_mavg()
    dataFrame['bb_l'] = indicator_bb.bollinger_lband()

def calculateRSI(dataFrame):
    # if 'rsi' in dataFrame:
    #     del dataFrame['rsi']
    indicator_rsi = ta.momentum.RSIIndicator(
        close=dataFrame['Close'], window=14)
    dataFrame['rsi'] = indicator_rsi.rsi()

def telegramMsg(message,error=False):
    log.debug(f"Sending message:{message}")
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

def get_pandas_range(df,min_,max_):
    min_index = df.index.get_loc(min_, method ='nearest')
    max_index = df.index.get_loc(max_, method ='nearest') + 1
    return df.iloc[min_index:max_index]
