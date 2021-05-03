import time
import requests, hmac, hashlib
from datetime import datetime
import ta
import pandas as pd 
import urllib.parse
from tinydb import TinyDB, Query
import logging
import threading

logging.basicConfig(filename='debug.log', level=logging.DEBUG)
db = TinyDB('db.json')

config = Query().name
funds = db.get(config == 'funds')

if not funds:
	db.insert({'name': 'funds', 'data': 100.00})
	funds = db.get(config == 'funds')

api_url = "https://api.binance.com/"
api_key = "bcAQOCmtDZzlftttfxNfOr71YhKstYT7tt6iY88meCziWidrD79LeALUfxEoykTq"
api_secret = b"E9F4qncSrYt7X644Hcc06uszC5JHUfNcRyXlWj6bkn4SQBxKubYWncVvOf8Fz6zc"
headers = {'X-MBX-APIKEY': api_key}
r = requests.get(api_url+"api/v3/ping",headers=headers)
#print(r.headers)
r.text
def binanceMessage(msg,time):
    h = hmac.new( api_secret, msg, hashlib.sha256 )
    return h.hexdigest()

stamp = datetime.now()
binanceMessage(b"hola",stamp)
def binanceGet(url):
	req = requests.get(api_url+url,headers=headers)
	if int(req.headers["x-mbx-used-weight"]) > 120:
		sleep(30)
	return req
    
# exchangeInfo = binanceGet("api/v3/exchangeInfo").json()
# for exchange in exchangeInfo["symbols"]:
#     if exchange["quoteAsset"]=="USDT":
#         print(exchange)
#orderBook = binanceGet("api/v3/depth?symbol=YFIIUSDT&limit=10").json()
#print(orderBook)
markets = binanceGet("api/v3/ticker/24hr").json()
goodMarkets = []
for market in markets:
	if(float(market['quoteVolume'])>5000000 and market['symbol'].endswith('USDT')):
		goodMarkets.append(market['symbol'])
logging.info(goodMarkets)

def checkMarket(symbol):
	candles = binanceGet("api/v3/klines?symbol="+symbol+"&interval=1m&limit=400").json()
	# df = {}
	# for candle in candles:
	# 	df[candle[0]] = {
	# 	'open':candle[1],'high':candle[2],'low':candle[3],'close':candle[4],'volume':candle[5],
	# 	'closetime':candle[6],'quoteasset':candle[7],'numbertrades':candle[8],'takerbaseasset':candle[9],
	# 	'takerquoteasset':candle[10],'ignore':candle[11]
	# 	}
	df = []
	for candle in candles:
		df.append([candle[0],float(candle[1]),float(candle[2]),float(candle[3]),float(candle[4]),
			candle[5],candle[6],candle[7],candle[8],candle[9],candle[10],candle[11]])
	df = pd.DataFrame(df,columns=['opentime', 'open','high','low','close','volume','closetime','quoteasset','numbertrades','takerbaseasset','takerquoteasset','ignore']) 
	df = ta.utils.dropna(df)
	indicator_rsi = ta.momentum.RSIIndicator(close= df['close'], window = 14, fillna = True)
	df['rsi'] = indicator_rsi.rsi()

	logging.info(symbol,df["rsi"].iloc[-1],df["rsi"].iloc[0])
	if(df["rsi"].iloc[-1]<30):
		buy(symbol)
	elif(df["rsi"].iloc[-1]>70):
		sell(symbol)

def sendTLMessage(message):
	token = "1321535286:AAEpm9JB4zDhkANld8C4ct1-fUyAwkPCOHI"
	channel = "@crybottesting"
	message = urllib.parse.quote(message)
	requests.get("https://api.telegram.org/bot"+token+"/sendMessage?chat_id="+channel+"&text="+message)

def buy(symbol):
	price = binanceGet("api/v3/ticker/24hr?symbol="+symbol).json()
	price = price["askPrice"]
	sendTLMessage("Buy "+symbol+" at $"+price)
	threading.Thread(target=seller,args=(symbol,)).start()

def sell(symbol):
	price = binanceGet("api/v3/ticker/24hr?symbol="+symbol).json()
	price = price["bidPrice"]
	sendTLMessage("Sell "+symbol+" at $"+price)

def finder():
	for m in goodMarkets:
		if m == "BNBUSDT":
			continue
		checkMarket(m)
		time.sleep(1)
		logging.debug("Threads:"+str(threading.activeCount()))

def seller(symbol):
	logging.debug("Seller: "+symbol)
	logging.debug("Threads in seller:"+str(threading.activeCount()))

nthreads = 2

threading.Thread(target=finder).start()
