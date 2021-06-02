from vars import client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from logger import log
import utils
import time 
import os

simulate = False
if os.environ.get('SIMULATE_ORDERS') == 'True':
    simulate = True

def market_buy(pair, amount, symbol_info, stop_loss, price):
    if simulate:
        profit = price * 1.0029
        return utils.save('long',
                {'pair':pair,'stop_loss':stop_loss,'qty':amount,
                'profit':profit,'purchase_price':price})
    try:
        order = client.order_market_buy(
            symbol=pair,
            quantity=amount)
    except BinanceAPIException as e:
        log.info(symbol_info)
        log.error(e)
        return utils.remove('long')
    except BinanceOrderException as e:
        log.info(symbol_info)
        log.error(e)
        return utils.remove('long')
    while True:
        log.debug(f"order_buy:{order}")
        if order['status'] == 'FILLED':
            price = float(order['fills'][0]['price'])
            profit = price * 1.0029
            #stop_loss = price-diff
            log.debug(f"price:{price} stop_loss:{stop_loss}")
            utils.save('long',
                {'pair':pair,'stop_loss':stop_loss,'qty':order['executedQty'],
                'profit':profit,'purchase_price':price})
            break
        time.sleep(0.25)
        order = client.get_order(symbol=pair,orderId=order['orderId'])

def market_sell(pair,qty):
    if simulate:
        return utils.remove('long')
    try:
        log.debug(f'Selling: pair:{pair},qty:{qty}')
        order = client.order_market_sell(
            symbol=pair,
            quantity=qty)
        log.debug('Order created')
    except BinanceAPIException as e:
        log.error(e)
        utils.remove('long')
        return
    except BinanceOrderException as e:
        log.error(e)
        utils.remove('long')
        return
    log.info(f"Sell long order:{order}")
    n = 0
    while True:
        n += 1
        if n == 10:
            log.error("Long order cant be filled")
            log.debug(order)
        if order['status'] == 'FILLED':
            utils.remove('long')
            break 
        time.sleep(2)
        order = client.get_order(symbol=pair,orderId=order['orderId'])
