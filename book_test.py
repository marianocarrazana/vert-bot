import websocket
import json
from utils import get_change

def on_message(ws, msg):
    msg = json.loads(msg)
    bids = msg['b']
    bid_list = []
    total_bid = 0.0
    asks = msg['a']
    ask_list = []
    total_ask = 0.0
    max_ask = float(asks[0][0])*1.005
    min_bid = float(bids[0][0])
    min_bid = min_bid - (min_bid*0.005)
    for a in asks:
        if float(a[0]) <= max_ask:
            price = float(a[0])
            qty = float(a[1])
            total_ask += qty
            ask_list.append([price,qty])
    for b in bids:
        if float(b[0]) >= min_bid:
            price = float(b[0])
            qty = float(b[1])
            total_bid += qty
            bid_list.append([price,qty])
    #print(len(bids),len(asks))
    ratio = total_bid/total_ask
    if ratio > 1.0:
        color = '\33[32m'
    else:
        color = '\33[31m'
    print(color+str(get_change(ask_list[0][0],ask_list[-1][0])),
        get_change(bid_list[0][0],bid_list[-1][0]),
        ratio)

def on_error(ws, error):
    ws.close()

if __name__ == "__main__":
    ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/ethusdt@depth@1000ms",
                              on_message = on_message,
                              on_error = on_error)

    ws.run_forever()
