#from datetime import datetime
import investing
import utils
import time
from binance.enums import TIME_IN_FORCE_GTC,SIDE_SELL
from binance.helpers import round_step_size
from decimal import Decimal

def RSI(dataFrame, investing_id, pair, client):
    #now = datetime.now()
    #current_time = now.strftime("%H:%M:%S.%f")
    last = dataFrame["rsi"].iloc[-1]
    penultimate = dataFrame["rsi"].iloc[-2]
    # print(current_time,last,penultimate)
    long(pair, dataFrame, client)#test
    return False
    if(penultimate < 30 and last >= 30):
        if investing.getTechnicalData(investing_id, '5mins') == 'Strong Buy':
            long(pair, dataFrame, client)
    elif(penultimate > 70 and last <= 70):
        if investing.getTechnicalData(investing_id, '5mins') == 'Strong Sell':
            short(pair, dataFrame)


def long(pair, dataFrame, client):
    utils.save('oco',{'pair':pair,'orders':[]})
    symbol_info = utils.getSymbolInfo(pair,client)
    minimun = float(symbol_info['filters_dic']['LOT_SIZE']['minQty'])
    stepSize = float(symbol_info['filters_dic']['LOT_SIZE']['stepSize'])
    utils.calculateBB(dataFrame)
    row = dataFrame.iloc[-1]
    diff = row['bb_ma'] - row['bb_l']
    print('diff',diff)
    profit = round_step_size(row['Open'] + diff,stepSize)
    print('profit',profit)
    win_percent = (diff / (row['Close'] / 100))/100
    print('win_percent',win_percent)
    stop_loss = round_step_size(row['Open'] - diff,stepSize)
    print('stop_loss:',stop_loss)
    if win_percent > 0.004:
        balance = float(client.get_asset_balance(asset='USDT')['free'])
        amount = balance if balance < 20.0 else 20.0
        amount = (amount*0.9) / row['Close']
        print('minimum:',amount,minimun,amount>minimun)
        amount = round_step_size(amount,stepSize)
        print(amount)
        buyOrder = client.order_market_buy(
            symbol=pair,
            quantity=amount)
        print(buyOrder)
        while True:
            time.sleep(1)
            order = client.get_order(symbol=pair,orderId=buyOrder['orderId'])
            print(order)
            if order['status'] == 'FILLED':
                ocoOrder = client.create_oco_order(
                symbol=pair,
                side=SIDE_SELL,
                stopLimitTimeInForce=TIME_IN_FORCE_GTC,
                quantity=order['executedQty'],
                stopPrice=stop_loss,
                stopLimitPrice=stop_loss,
                price=profit)
                print(ocoOrder)
                utils.save('oco',{'pair':pair,'orders':ocoOrder['orders']})
                break

def short(pair, dataFrame, client):
    return True
