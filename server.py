from tornado import ioloop
from tornado import web
from tornado import template
import threading
import pandas as pd 
import ta
import investing
import os,json,re,time
from binance import Client, ThreadedWebsocketManager
from binance.enums import SIDE_SELL,TIME_IN_FORCE_GTC
import utils,strategies
from logger import log
import websocket
import web_handlers
import vars
from vars import client
import orders
#Global Variables
# if os.environ.get('BINANCE_TESTING') == 'True':
#     client.API_URL = 'https://testnet.binance.vision/api'
cryptoList = None
multiplex_socket = None
book_socket = None
task_update = True
closed_connections = 0
stop_loss = 0.0
stop_levels = 0.0
next_stop = 0.0

def minutes(m): return m*1000*60
        
def make_app():
    return web.Application([
        (r"/", web_handlers.MainHandler),
        (r"/log", web_handlers.LogHandler),
        # (r"/price/(\w+)", web_handlers.PricesHandler),
        # (r"/klines/(\w+)", web_handlers.KlinesHandler),
        # (r"/test/(\w+)", web_handlers.TestHandler),
        # (r"/buy/(\w+)/(\d+)", web_handlers.BuyHandler),
        # (r"/oco/(\w+)/([\.\d]+)/([\.\d]+)", web_handlers.OcoHandler),
        # (r"/order/(\w+)/(\d+)", web_handlers.OrderHandler),
    ])

def getDataFrame(pair):
    bars = client.get_klines(symbol=pair.upper(), interval=Client.KLINE_INTERVAL_1MINUTE, limit=220)
    dt = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
    return utils.candleStringsToNumbers(dt)

def update_kline(df,pair,msg):
    if df is None:
        df = getDataFrame(pair)
        df.set_index('Date', inplace=True)
    kline = msg['data']['k']
    index = kline['t']
    row = [[index,kline['o'],kline['h'],kline['l'],kline['c'],0,0,0,0,0,0,0]]
    newDF = pd.DataFrame(row, columns=utils.CANDLES_NAMES)
    newDF = utils.candleStringsToNumbers(newDF)
    newDF.set_index('Date', inplace=True)
    if index in df.index:
        df.loc[index] = newDF.loc[index]
    else:
        df = df.append(newDF)
        df = df.drop(df.index[0])
    return df

ws_klines = []
def open_kline_stream(pair,index):
    global ws_klines
    stream_url = 'wss://stream.binance.com:9443/stream?streams=' + pair.lower() + '@depth20@100ms'
    ws_klines[index] = websocket.WebSocketApp(stream_url,
                              on_message = handle_book_depth,
                              on_error = websocket_error)
    wst = threading.Thread(target=ws_klines[index].run_forever)
    wst.daemon = True
    wst.start()

def generateCryptoList():
    global cryptoList,book_socket,multiplex_socket,ws_klines,closed_connections
    cryptoList= {}
    closed_connections = 0
    ws_klines = []
    i = 0
    for cr in investing.CRYPTO:
        ws_klines.append(None)
        cryptoList[cr['binance_id']] = {'dataFrame':None,'calculated':True,'investingId':cr['investing_id']}
        open_kline_stream(cr['binance_id'],i)
        i += 1
        time.sleep(1)

def websocket_error(w,e):
    log.error(e)
    #w.close()

def handle_book_depth(ws,msg):
    global cryptoList,client,book_socket,multiplex_socket,closed_connections,task_update
    long = utils.load('long')
    if long is not None:
        if long['purchase_price'] is not None:
            ws.close()
            closed_connections += 1
            if(closed_connections == len(cryptoList)):
                log.debug(f"Opening websocket for {long['pair']}")
                task_update = True
        return
    msg = json.loads(msg)
    regex = r"(\w+)@"
    pair = re.search(regex, msg['stream'])[1].upper()
    if not cryptoList[pair]['calculated']:
        return
    cryptoList[pair]['calculated'] = False
    strategies.book_depth(msg['data']['bids'],msg['data']['asks'],pair)
    cryptoList[pair]['calculated'] = True

def handle_socket_message(ws, msg):
    global cryptoList,client,book_socket,multiplex_socket,closed_connections,task_update
    long = utils.load('long')
    if long is not None:
        if long['purchase_price'] is not None:
            ws.close()
            closed_connections += 1
            if(closed_connections == len(cryptoList)):
                log.debug(f"Opening websocket for {long['pair']}")
                task_update = True
        return
    msg = json.loads(msg)
    pair = msg['data']['s']
    if not cryptoList[pair]['calculated']:
        return
    cryptoList[pair]['calculated'] = False
    cryptoList[pair]['dataFrame'] = update_kline(cryptoList[pair]['dataFrame'],pair,msg)
    strategies.dc_aroon(cryptoList[pair],pair,client)
    cryptoList[pair]['calculated'] = True

handling_long = False
long_dataframe = None
def handle_long_message(ws, msg):
    global handling_long,client,task_update,stop_levels,stop_loss,next_stop,long_dataframe
    if handling_long:
        return
    handling_long = True
    long = utils.load('long')
    if long is None:
        log.info('out long')
        ws.close()
        handling_long = False
        task_update = True
        return
    msg = json.loads(msg)
    pair = msg['data']['s']
    long_dataframe = update_kline(long_dataframe,pair,msg)
    last_price = long_dataframe['Close'].iloc[-1]
    if last_price > next_stop:
        stop_loss += stop_levels
        next_stop += stop_levels 
    if last_price < stop_loss:
        orders.sell_long(long,last_price)
        handling_long = False
        return
    period = 14
    a_up = ta.trend.aroon_up(long_dataframe['Close'], window=period, fillna=False)
    if a_up.iloc[-1] > 95:
        orders.sell_long(long,last_price)
        handling_long = False
        return
    handling_long = False

def checkOcoOrder():
    oco = utils.load('oco')
    if oco is None:
        return False
    log.debug(f"oco,{oco}")
    for order in oco['orders']:
        order = client.get_order(symbol=oco['pair'],orderId=order['orderId'])
        if order['status'] == "FILLED":
            utils.remove('oco')

def update_database():
    global cryptoList
    longDB = utils.load('long')
    if longDB is None:
        for key in cryptoList:
            if cryptoList[key]['dataFrame'] is not None:
                if 'rsi' in cryptoList[key]['dataFrame']:
                    utils.save(f'RSI{key}',cryptoList[key]['dataFrame']['rsi'].iloc[-31:-1].tolist())

async def check_task():
    longDB = utils.load('long')
    #vars.buying = False
    if longDB is not None:
        orders.open_book_socket(longDB['pair'].lower())

if __name__ == "__main__":
    if utils.load('stats') is None:
        utils.save('stats',{'wins':0,'losses':0})
    app = make_app()
    port = 8888
    app.listen(port)
    log.info(f"Tornado listening on http://localhost:{port}")
    # tsks = ioloop.PeriodicCallback(strategies.volume_check, minutes(30))
    # tsks.start() 
    exam_btc = ioloop.PeriodicCallback(strategies.supertrend, 11003)
    exam_btc.start() 
    #ioloop.IOLoop.current().spawn_callback(strategies.donchian_btc)
    # ioloop.IOLoop.current().spawn_callback(strategies.volume_check)
    ioloop.IOLoop.current().start()#run forever
