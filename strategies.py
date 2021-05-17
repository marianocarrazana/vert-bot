#from datetime import datetime
import investing
import utils
import time
#from binance.enums import TIME_IN_FORCE_GTC,SIDE_SELL
#from binance.helpers import round_step_size
from decimal import Decimal as D#, ROUND_DOWN, ROUND_UP
#import decimal
from logger import log

def RSI(dataFrame, investing_id, pair, client):
    #now = datetime.now()
    #current_time = now.strftime("%H:%M:%S.%f")
    last = dataFrame["rsi"].iloc[-1]
    penultimate = dataFrame["rsi"].iloc[-2]
    # print(current_time,last,penultimate)
    #long(pair, dataFrame, client)#test
    return False
    if(penultimate < 30 and last >= 30):
        if investing.getTechnicalData(investing_id, '5mins') == 'Strong Buy':
            long(pair, dataFrame, client)
    elif(penultimate > 70 and last <= 70):
        if investing.getTechnicalData(investing_id, '5mins') == 'Strong Sell':
            short(pair, dataFrame)


def long(pair, dataFrame, client):
    utils.save('long',{'pair':pair,'profit':None,'stop_loss':None,'qty':'0'})
    symbol_info = utils.getSymbolInfo(pair,client)
    minimum = float(symbol_info['filters_dic']['LOT_SIZE']['minQty'])
    price_filter = float(symbol_info['filters_dic']['PRICE_FILTER']['tickSize'])
    utils.calculateBB(dataFrame)
    row = dataFrame.iloc[-1]
    price = float(row['Close'])
    price = D.from_float(price).quantize(D(str(price_filter)))
    diff = row['bb_ma'] - row['bb_l']
    #print('diff:',diff,'price:',row['Close'],'bb_l',row['bb_l'],'bb_h',row['bb_h'])
    profit = row['Close'] + diff
    win_percent = (diff / (row['Close'] / 100))/100
    if win_percent > 0.005:#0.5%
        balance = float(client.get_asset_balance(asset='USDT')['free'])
        amount = balance if balance < 20.0 else 20.0
        amount = (amount*0.9) / row['Close']
        amount = D.from_float(amount).quantize(D(str(minimum)))
        log.debug(f"amount:{amount} minimum:{minimum}")
        if amount < minimum:
            log.warning('Need moar')
            utils.remove('long')
            return
        order = client.order_market_buy(
            symbol=pair,
            quantity=amount)
        while True:
            log.debug(f"order_buy:{order}")
            if order['status'] == 'FILLED':
                price = float(order['fills'][0]['price'])
                profit = price+diff
                stop_loss = price-diff
                log.debug(f"price:{price} profit:{profit} stop_loss:{stop_loss}")
                utils.save('long',{'pair':pair,'profit':profit,'stop_loss':stop_loss,'qty':order['executedQty']})
                break
            time.sleep(2)
            order = client.get_order(symbol=pair,orderId=order['orderId'])
    else:
        log.debug(f"win_percent: {win_percent}")
        utils.remove('long')
        
def short(pair, dataFrame, client):
    return True
