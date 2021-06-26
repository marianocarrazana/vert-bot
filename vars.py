from binance import Client, ThreadedWebsocketManager
import os

buying = False
api_key = os.environ.get('BINANCE_API')
api_secret = os.environ.get('BINANCE_SECRET')
client = Client(api_key, api_secret)
cryptoList = {"BTCUPUSDT":{"last_buy":0.0},"BTCDOWNUSDT":{"last_buy":0.0}}
pid = os.getpid()
