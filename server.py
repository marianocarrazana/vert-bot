from tornado import ioloop
from tornado import web
from tornado import template
import pandas as pd 
import investing
import os,json,re,time
from binance import Client, ThreadedWebsocketManager
from binance.enums import SIDE_SELL,TIME_IN_FORCE_GTC
import utils,strategies

api_key = os.environ.get('BINANCE_API')
api_secret = os.environ.get('BINANCE_SECRET')
client = Client(api_key, api_secret)
client.API_URL = 'https://testnet.binance.vision/api'

minutes = lambda ns : ns*1000*60

class MainHandler(web.RequestHandler):
    def get(self):
        loader = template.Loader("./templates")
        account = client.get_account()
        print(account)
        self.write(loader.load("index.html").generate(json=account,body=""))

class PricesHandler(web.RequestHandler):
    def get(self, pair):
        loader = template.Loader("./templates")
        price = client.get_symbol_ticker(symbol=pair.upper())
        self.write(loader.load("index.html").generate(json=price,body=""))
    
class TestHandler(web.RequestHandler):
    def get(self, pair):
        loader = template.Loader("./templates")
        bars = client.get_historical_klines(pair.upper(), Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
        dt = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
        dt = utils.candleStringsToNumbers(dt)
        utils.calculateRSI(dt)
        utils.calculateBB(dt)
        penultimate = 50
        funds = 100.00
        proffit = None
        stop_loss = None
        wins = []
        losses = []
        win_percent = 0
        for index, row in dt.iterrows():
            if proffit is None:
                last = row['rsi'] or 50
                if penultimate < 30 and last >= 30 and row['bb_ma'] == row['bb_ma']:
                    print('short:',index,last,penultimate)
                    diff = row['bb_ma'] - row['bb_l']
                    print(diff,row['bb_ma'])
                    proffit = row['Open'] + diff
                    win_percent = (diff / (row['Close'] / 100))/100
                    stop_loss = row['Open'] - diff
            else:
                if proffit > row['Low'] and proffit < row['High']:
                    print('i:',index,proffit,win_percent)
                    wins.append(win_percent)
                    funds += funds * win_percent
                    proffit = None
                    print('win:',proffit)
                elif stop_loss > row['Low'] and stop_loss < row['High']:
                    losses.append(win_percent)
                    funds -= funds * win_percent
                    proffit = None
            penultimate = row['rsi'] or 50
        data = {'wins:':wins,'losses:':losses,'funds:':funds,
                'win_percent:':len(wins)/((len(wins)+len(losses))/100)}
        self.write(loader.load("index.html").generate(json=json.dumps(data),body=""))
        
class KlinesHandler(web.RequestHandler):
    def get(self,pair):
        dt = getDataFrame(pair)
        utils.calculateRSI(dt)
        utils.calculateBB(dt)
        #utils.plot(dt)
        loader = template.Loader("./templates")
        self.write(loader.load("index.html").generate(json=dt.to_json(),body=""))
        
class BuyHandler(web.RequestHandler):
    def get(self,pair,amount):
        balance = client.get_asset_balance(asset='USDT')
        buyOrder = client.order_market_buy(
            symbol=pair,
            quantity=amount)
        order = client.get_order(symbol=pair,orderId=buyOrder['orderId'])
        out = [balance,buyOrder,order]
        loader = template.Loader("./templates")
        self.write(loader.load("index.html").generate(json=out,body=""))
        
class ocoHandler(web.RequestHandler):
    def get(self,pair,stop_loss,proffit):
        sellOrder = client.create_oco_order(
                symbol=pair,
                side=SIDE_SELL,
                stopLimitTimeInForce=TIME_IN_FORCE_GTC,
                quantity=10,
                stopPrice=stop_loss,
                stopLimitPrice=stop_loss,
                price=proffit)
        loader = template.Loader("./templates")
        self.write(loader.load("index.html").generate(json=sellOrder,body=""))
        
class OrderHandler(web.RequestHandler):
    def get(self,pair,order_id):
        order = client.get_order(symbol=pair,orderId=order_id)
        loader = template.Loader("./templates")
        self.write(loader.load("index.html").generate(json=order,body=""))
        
def make_app():
    return web.Application([
        (r"/", MainHandler),
        (r"/price/(\w+)", PricesHandler),
        (r"/klines/(\w+)", KlinesHandler),
        (r"/test/(\w+)", TestHandler),
        (r"/buy/(\w+)/(\d+)", BuyHandler),
        (r"/oco/(\w+)/(\d+)/(\d+)", ocoHandler),
        (r"/order/(\w+)/(\d+)", OrderHandler),
    ])

def getDataFrame(pair):
    bars = client.get_klines(symbol=pair.upper(), interval=Client.KLINE_INTERVAL_1MINUTE, limit=250)
    dt = pd.DataFrame(bars, columns=utils.CANDLES_NAMES)
    return utils.candleStringsToNumbers(dt)

def long():
    print("buy")
    
def short():
    print("sell")

def analyzeMarket():
    lastCrypto = utils.load('lastCrypto') or 0
    pairData = investing.CRYPTO[lastCrypto]
    df = getDataFrame(pairData['binance_id'])
    utils.calculateRSI(df)
    strategies.RSI(df)
    lastCrypto = lastCrypto + 1
    if len(investing.CRYPTO) == lastCrypto:
        lastCrypto = 0
    utils.save('lastCrypto',lastCrypto)

cryptoList = {}
for cr in investing.CRYPTO:
    cryptoList[cr['binance_id']] = {'dataFrame':None,'calculated':True,'investingId':cr['investing_id']}
    #print(cr['binance_id'],client.get_symbol_info(cr['binance_id']))
    #time.sleep(2)
    
def handle_socket_message(msg):
    global cryptoList,client
    print(msg['stream'],msg['data']['e'])
    regex = r"(\w+)@"
    pair = re.search(regex, msg['stream'])[1].upper()
    if cryptoList[pair]['dataFrame'] is None and cryptoList[pair]['calculated']:
        cryptoList[pair]['calculated'] = False
        cryptoList[pair]['dataFrame'] = getDataFrame(pair)
        cryptoList[pair]['dataFrame'].set_index('Date', inplace=True)
        print("Calculated RSI for",pair)
        cryptoList[pair]['calculated'] = True
    kline = msg['data']['k'];
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
    #print(len(cryptoList[pair]['dataFrame']),cryptoList[pair]['dataFrame']['Close'].iloc[-1],cryptoList[pair]['dataFrame']['Close'].iloc[-2])
    if cryptoList[pair]['calculated'] and utils.load('oco') is None:
        cryptoList[pair]['calculated'] = False
        utils.calculateRSI(cryptoList[pair]['dataFrame'])
        strategies.RSI(cryptoList[pair]['dataFrame'],cryptoList[pair]['investingId'],pair,client)
        cryptoList[pair]['calculated'] = True
        print(cryptoList[pair]['dataFrame']["rsi"].iloc[-1],index)
    
def checkOcoOrder():
    oco = utils.load('oco')
    if oco is None:
        return False
    print('oco',oco)
    for order in oco['orders']:
        order = client.get_order(symbol=oco['pair'],orderId=order['orderId'])
        if order['status'] == "FILLED":
            utils.remove('oco')
    
if __name__ == "__main__":
    app = make_app()
    port = 8888
    app.listen(port)
    print("Server listening on http://localhost:%s" % port)
    clen = len(investing.CRYPTO)*2
    scheduler = ioloop.PeriodicCallback(checkOcoOrder, minutes(1))
    scheduler.start() 
    twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
    twm.start()
    #twm.start_kline_socket(callback=handle_socket_message, symbol=symbol)
    streamList = []
    for key in cryptoList:
        streamList.append(key+'@kline_1m')
    twm.start_multiplex_socket(callback=handle_socket_message,
                                streams=streamList)
    ioloop.IOLoop.current().start()
