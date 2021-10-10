from binance import Client, ThreadedWebsocketManager
import os

buying = False
api_key = os.environ.get('BINANCE_API')
api_secret = os.environ.get('BINANCE_SECRET')
client = Client(api_key, api_secret)
cryptoList = {
    "ADAUSDT":{"last_buy":0.0,'overbought':False,'high_risk':False},
    # "BTCDOWNUSDT":{"last_buy":0.0,'overbought':False,'high_risk':False}
    }
pid = os.getpid()
running_backtesting = False
