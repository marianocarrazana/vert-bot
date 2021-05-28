from tornado import ioloop
from tornado import web
from tornado import template
import threading
import pandas as pd 
import investing
import os,json,re,time
from binance import Client, ThreadedWebsocketManager
from binance.enums import SIDE_SELL,TIME_IN_FORCE_GTC
from binance.exceptions import BinanceAPIException, BinanceOrderException
import utils,strategies
from logger import log
import websocket
import web_handlers

#Global Variables
api_key = os.environ.get('BINANCE_API')
api_secret = os.environ.get('BINANCE_SECRET')
client = Client(api_key, api_secret)
if os.environ.get('BINANCE_TESTING') == 'True':
    client.API_URL = 'https://testnet.binance.vision/api'
cryptoList = None
multiplex_socket = None
book_socket = None
task_update = True
closed_connections = 0

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
    bars = client.get_klines(symbol=pair.upper(), interval=Client.KLINE_INTERVAL_5MINUTE, limit=250)
    dt = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
    return utils.candleStringsToNumbers(dt)

# def analyzeMarket():
#     lastCrypto = utils.load('lastCrypto') or 0
#     pairData = investing.CRYPTO[lastCrypto]
#     df = getDataFrame(pairData['binance_id'])
#     utils.calculateRSI(df)
#     strategies.RSI(df)
#     lastCrypto = lastCrypto + 1
#     if len(investing.CRYPTO) == lastCrypto:
#         lastCrypto = 0
#     utils.save('lastCrypto',lastCrypto)
ws_klines = []
def open_kline_stream(pair,index):
    global ws_klines
    stream_url = 'wss://stream.binance.com:9443/stream?streams=' + pair.lower() + '@kline_5m'
    ws_klines[index] = websocket.WebSocketApp(stream_url,
                              on_message = handle_socket_message,
                              on_error = websocket_error)
    wst = threading.Thread(target=ws_klines[index].run_forever)
    wst.daemon = True
    wst.start()

def generateCryptoList():
    global cryptoList,book_socket,multiplex_socket,ws_klines,closed_connections
    cryptoList= {}
    closed_connections = 0
    #streamList = []
    ws_klines = []
    i = 0
    for cr in investing.CRYPTO:
        ws_klines.append(None)
        cryptoList[cr['binance_id']] = {'dataFrame':None,'calculated':True,'investingId':cr['investing_id']}
        #streamList.append(cr['binance_id'].lower()+'@kline_1m')
        open_kline_stream(cr['binance_id'],i)
        i += 1
        time.sleep(1)
    #stream_url = 'wss://stream.binance.com:9443/stream?streams=' + '/'.join(streamList)
    #log.debug(stream_url)
    #websocket.enableTrace(True)
    
    #print(cr['binance_id'],client.get_symbol_info(cr['binance_id']))
    #time.sleep(2)
    # log.debug(streamList)
    # multiplex_socket = None
    # try:
    #     multiplex_socket = twm.start_multiplex_socket(callback=handle_socket_message,
    #                             streams=streamList)
    # except Exception as e:
    #     log.critical(e)

def websocket_error(w,e):
    log.error(e)
    w.close()
    time.sleep(60*60)

handling_book = False
#utils.save('long',{'pair':'XRPUSDT','profit':2,'stop_loss':1,'qty':'1'})
transactions = {'bids':[],'asks':[],'increasing':False}
def handle_book_message(ws, msg):
    global handling_book,book_socket,transactions,client,task_update
    if handling_book:
        log.debug('out')
        return
    handling_book = True
    msg = json.loads(msg)
    long = utils.load('long')
    if long is None:
        log.info('out long')
        # twm.stop_socket(book_socket)
        # twmRestart()
        ws.close()
        handling_book = False
        task_update = True
        #generateCryptoList()
        return
    elif long['profit'] is None:
        handling_book = False
        return
    bid = float(msg['b'])
    #ask = float(msg['a'])
    transactions['bids'].append(bid)
    tr_length = len(transactions['bids'])
    if tr_length > 300:
        transactions['bids'].pop(0)
        transactions['increasing'] = transactions['bids'][0] < transactions['bids'][299]
        #log.debug(('up ' if transactions['increasing'] else 'down ') + msg['b'])
        if bid > long['profit'] and not transactions['increasing']:
            utils.telegramMsg(f"<b>Profit</b>\nBid:{bid}\nExpected:{long['profit']}")
            try:
                order = client.order_market_sell(
                    symbol=long['pair'],
                    quantity=long['qty'])
            except BinanceAPIException as e:
                log.error(e)
                return utils.remove('long')
            except BinanceOrderException as e:
                log.error(e)
                return utils.remove('long')
            log.info(f"profit:{order}")
            while True:
                log.debug(f"order_buy:{order['status']}")
                if order['status'] == 'FILLED':
                    utils.remove('long')
                    break
                time.sleep(2)
                order = client.get_order(symbol=long['pair'],orderId=order['orderId'])
        elif bid <= long['stop_loss']:
            utils.telegramMsg(f"<b>Stop Loss</b>\nBid:{bid}\nExpected:{long['stop_loss']}")
            try:
                order = client.order_market_sell(
                    symbol=long['pair'],
                    quantity=long['qty'])
            except BinanceAPIException as e:
                log.error(e)
                return utils.remove('long')
            except BinanceOrderException as e:
                log.error(e)
                return utils.remove('long')
            log.info(f"stop_loss:{order}")
            while True:
                log.debug(f"order_buy:{order['status']}")
                if order['status'] == 'FILLED':
                    utils.remove('long')
                    break
                time.sleep(2)
                order = client.get_order(symbol=long['pair'],orderId=order['orderId'])
    # transactions['asks'].append(ask)
    # if len(transactions['asks']) > 200:
    #     transactions['asks'].pop(0)
        #print(transactions['asks'])
    # diff = bid - ask
    # diff_percent = (diff / (bid / 100))
    #print(diff_percent)
    handling_book = False
    
def handle_socket_message(ws, msg):
    global cryptoList,client,book_socket,multiplex_socket,closed_connections,task_update
    long = utils.load('long')
    if long is not None:
        if long['profit'] is not None:
            ws.close()
            closed_connections += 1
            if(closed_connections == len(cryptoList)):
                log.debug(f"Opening websocket for {long}")
                task_update = True
        return
    msg = json.loads(msg)
    #print(msg)
    regex = r"(\w+)@"
    pair = re.search(regex, msg['stream'])[1].upper()
    if cryptoList[pair]['dataFrame'] is None and cryptoList[pair]['calculated']:
        cryptoList[pair]['calculated'] = False
        cryptoList[pair]['dataFrame'] = getDataFrame(pair)
        #log.debug(cryptoList[pair]['dataFrame'])
        cryptoList[pair]['dataFrame'].set_index('Date', inplace=True)
        #log.debug(f"Calculated RSI for {pair}")
        cryptoList[pair]['calculated'] = True
    kline = msg['data']['k']
    index = kline['t']
    row = [[index,kline['o'],kline['h'],kline['l'],kline['c'],0,0,0,0,0,0,0]]
    newDF = pd.DataFrame(row, columns=utils.CANDLES_NAMES)
    newDF = utils.candleStringsToNumbers(newDF)
    newDF.set_index('Date', inplace=True)
    if index in cryptoList[pair]['dataFrame'].index:
        cryptoList[pair]['dataFrame'].loc[index] = newDF.loc[index]
    else:
        cryptoList[pair]['dataFrame'] = cryptoList[pair]['dataFrame'].append(newDF)
        cryptoList[pair]['dataFrame'] = cryptoList[pair]['dataFrame'].drop(cryptoList[pair]['dataFrame'].index[0])
    if cryptoList[pair]['calculated']:
        cryptoList[pair]['calculated'] = False
        utils.calculateRSI(cryptoList[pair]['dataFrame'])
        strategies.RSI(cryptoList[pair]['dataFrame'],cryptoList[pair]['investingId'],pair,client)
        cryptoList[pair]['calculated'] = True
        #log.debug(f"{cryptoList[pair]['dataFrame']['rsi'].iloc[-1]},{index}")
    
def checkOcoOrder():
    oco = utils.load('oco')
    if oco is None:
        return False
    log.debug(f"oco,{oco}")
    for order in oco['orders']:
        order = client.get_order(symbol=oco['pair'],orderId=order['orderId'])
        if order['status'] == "FILLED":
            utils.remove('oco')
    
# def twmRestart():
#     global twm,api_key,api_secret
#     twm.stop()
#     twm = None
#     time.sleep(1)
#     twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
#     twm.start()
def open_book_socket(pair_book):
    ws_book = websocket.WebSocketApp(f"wss://stream.binance.com:9443/ws/{pair_book}@bookTicker",
                                on_message = handle_book_message,
                                on_error = websocket_error)
    wst = threading.Thread(target=ws_book.run_forever)
    wst.daemon = True
    wst.start()

def update_database():
    global cryptoList
    longDB = utils.load('long')
    if longDB is None:
        for key in cryptoList:
            if cryptoList[key]['dataFrame'] is not None:
                if 'rsi' in cryptoList[key]['dataFrame']:
                    utils.save(f'RSI{key}',cryptoList[key]['dataFrame']['rsi'].iloc[-31:-1].tolist())


async def check_task():
    global task_update
    if not task_update:
        return
    task_update = False
    longDB = utils.load('long')
    if longDB is None:
        log.debug('Examining market...')
        generateCryptoList()
    else:
        log.debug('Selling crypto...')
        open_book_socket(longDB['pair'].lower())

if __name__ == "__main__":
    #twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
    #twm.start_kline_socket(callback=handle_socket_message, symbol=symbol)
    #twm.start()
    #log.debug(twm)
    # while True:
    #     log.debug('Starting loop')
    #     longDB = utils.load('long')
    #     if longDB is None:
    #         generateCryptoList()
    #     else:
    #         pair_book = longDB['pair'].lower()
    #         wss = websocket.WebSocketApp(f"wss://stream.binance.com:9443/ws/{pair_book}@bookTicker",
    #                             on_message = handle_book_message,
    #                             on_error = websocket_error)

    #         wss.run_forever()
    #     log.debug('Ending loop')
        #book_socket = twm.start_symbol_book_ticker_socket(callback=handle_book_message,symbol=longDB['pair'])
    #if os.environ.get('TORNADO_ENABLED') == 'f':
    app = make_app()
    port = 8888
    app.listen(port)
    log.info(f"Tornado listening on http://localhost:{port}")
    #clen = len(investing.CRYPTO)*2
    tsks = ioloop.PeriodicCallback(check_task, 1)
    tsks.start() 
    # updateDB = ioloop.PeriodicCallback(update_database, 5)
    # updateDB.start() 
    #ioloop.IOLoop.current().spawn_callback(check_task)
    ioloop.IOLoop.current().start()#run forever
