from vars import client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from logger import log
import utils
import time 
import os
import websocket
import threading
import json

simulate = False
if os.environ.get('SIMULATE_ORDERS') == 'True':
    simulate = True
    log.debug("Simulate orders ON")

def market_buy(pair, amount, symbol_info, stop_loss, price):
    if simulate:
        price = float(price)
        profit = price * 1.003
        return utils.save(pair,
                {'pair':pair,'stop_loss':stop_loss,'qty':amount,
                'profit':profit,'purchase_price':price})
    try:
        order = client.order_market_buy(
            symbol=pair,
            quantity=amount)
    except BinanceAPIException as e:
        log.info(symbol_info)
        log.error(e)
        return utils.remove(pair)
    except BinanceOrderException as e:
        log.info(symbol_info)
        log.error(e)
        return utils.remove(pair)
    while True:
        log.debug(f"order_buy:{order}")
        if order['status'] == 'FILLED':
            price = float(order['fills'][0]['price'])
            profit = price * 1.003
            #stop_loss = price-diff
            log.debug(f"price:{price} stop_loss:{stop_loss}")
            utils.save(pair,
                {'pair':pair,'stop_loss':stop_loss,'qty':order['executedQty'],
                'profit':profit,'purchase_price':price})
            break
        time.sleep(1)
        order = client.get_order(symbol=pair,orderId=order['orderId'])

def market_sell(pair,qty):
    if simulate:
        utils.remove(pair)
        return
    try:
        log.debug(f'Selling: pair:{pair},qty:{qty}')
        order = client.order_market_sell(
            symbol=pair,
            quantity=qty)
        log.debug('Order created')
    except BinanceAPIException as e:
        log.error(e)
        utils.remove(pair)
        return
    except BinanceOrderException as e:
        log.error(e)
        utils.remove(pair)
        return
    log.info(f"Sell long order:{order}")
    n = 0
    while True:
        n += 1
        if n == 10:
            log.error("Long order cant be filled")
            log.debug(order)
        if order['status'] == 'FILLED':
            utils.remove(pair)
            break 
        time.sleep(1)
        order = client.get_order(symbol=pair,orderId=order['orderId'])

def open_book_socket(pair_book):
    log.debug(f'Opening book socket for {pair_book}')
    ws_book = websocket.WebSocketApp(
        f"wss://stream.binance.com:9443/ws/{pair_book}@bookTicker",
        on_message = handle_book_message,
        on_error = websocket_error)
    wst = threading.Thread(target=ws_book.run_forever)
    # wst.daemon = True
    wst.start()

def sell_long(long,price):
    purchase = long['purchase_price']
    state = "Profit" if price > purchase else 'Loss'
    stats = utils.load('stats')
    if state == 'Profit':
        stats['wins'] += 1
    else:
        stats['losses'] += 1
    utils.save('stats',stats)
    diff = utils.get_change(price, purchase)
    utils.telegramMsg(f"<b>{state}</b>\nPurchase price:{purchase}\nSale price:{price}\nDifference:{diff:.2f}%")
    market_sell(long['pair'],long['qty'])

def websocket_error(w,e):
    log.error(e)

handling_book = False
transactions = {'bids':[],'asks':[],'increasing':False}
def handle_book_message(ws, msg):
    global handling_book,transactions
    if handling_book:
        return
    handling_book = True
    msg = json.loads(msg)
    long = utils.load('long')
    if long is None:
        log.info('out long')
        ws.close()
        handling_book = False
        return
    elif long['profit'] is None:
        handling_book = False
        return
    bid = float(msg['b'])
    #ask = float(msg['a'])
    # transactions['bids'].append(bid)
    # tr_length = len(transactions['bids'])
    # if tr_length > 0:
    #     transactions['bids'].pop(0)
    #     transactions['increasing'] = transactions['bids'][0] < transactions['bids'][4]
        #log.debug(('up ' if transactions['increasing'] else 'down ') + msg['b'])
    # if bid >= long['profit']:# and not transactions['increasing']:
    #     bs = threading.Thread(target=sell_long,args=(long,bid))
    #     bs.start()
    #     handling_book = False
    #     ws.close()
    if bid < long['stop_loss']:
        bs = threading.Thread(target=sell_long,args=(long,bid))
        bs.start()
        handling_book = False
        ws.close()
    # transactions['asks'].append(ask)
    # if len(transactions['asks']) > 200:
    #     transactions['asks'].pop(0)
        #print(transactions['asks'])
    # diff = bid - ask
    # diff_percent = (diff / (bid / 100))
    #print(diff_percent)
    handling_book = False

checking_stop_loss = 0
def stop_loss_check():
    global checking_stop_loss
    if checking_stop_loss > 0 and checking_stop_loss < 29:
        return
    checking_stop_loss = checking_stop_loss + 1
    pairs = ['BTCUPUSDT','BTCDOWNUSDT']
    for pair in pairs:
        longDB = utils.load(pair)
        if longDB is None:
            continue
        ticker = client.get_orderbook_ticker(symbol=pair)
        price = float(ticker['bidPrice'])
        if price < longDB['stop_loss']:
            sell_long(longDB,price)
        time.sleep(0.12)
    checking_stop_loss = 0
