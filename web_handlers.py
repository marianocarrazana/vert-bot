from tornado import web
from tornado import template
from server import client
from server import getDataFrame
from binance import Client
from binance.enums import SIDE_SELL,TIME_IN_FORCE_GTC
import utils
import pandas as pd 
import json

class MainHandler(web.RequestHandler):
    def get(self):
        self.write(str(utils.load('long')))
        # loader = template.Loader("./templates")
        # account = client.get_account()
        # log.debug(account)
        # self.write(loader.load("index.html").generate(json=account,body=""))

class LogHandler(web.RequestHandler):
    def get(self):
        f = open("debug.log", "r").read()
        self.write(f.replace("\n","<br>"))

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
                    diff = row['bb_ma'] - row['bb_l']
                    proffit = row['Open'] + diff
                    win_percent = (diff / (row['Close'] / 100))/100
                    stop_loss = row['Open'] - diff
            else:
                if proffit > row['Low'] and proffit < row['High']:
                    wins.append(win_percent)
                    funds += funds * win_percent
                    proffit = None
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
        
class OcoHandler(web.RequestHandler):
    def get(self,pair,stop_loss,profit):
        sellOrder = client.create_oco_order(
                symbol=pair,
                side=SIDE_SELL,
                stopLimitTimeInForce=TIME_IN_FORCE_GTC,
                quantity=10,
                stopPrice=stop_loss,
                stopLimitPrice=stop_loss,
                price=profit)
        loader = template.Loader("./templates")
        self.write(loader.load("index.html").generate(json=sellOrder,body=""))
        
class OrderHandler(web.RequestHandler):
    def get(self,pair,order_id):
        order = client.get_order(symbol=pair,orderId=order_id)
        loader = template.Loader("./templates")
        self.write(loader.load("index.html").generate(json=order,body=""))
