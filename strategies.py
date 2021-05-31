import investing
import utils
import time
import os
import ta
#from binance.enums import TIME_IN_FORCE_GTC,SIDE_SELL
#from binance.helpers import round_step_size
from binance.exceptions import BinanceAPIException, BinanceOrderException
from decimal import Decimal as D#, ROUND_DOWN, ROUND_UP
#import decimal
from logger import log

def RSI(dataFrame, investing_id, pair, client):
    last = dataFrame["rsi"].iloc[-1]
    penultimate = dataFrame["rsi"].iloc[-2]
    log.debug(last,penultimate)
    # long(pair, dataFrame, client)#test
    # return False
    # if(penultimate < 30 and last >= 30):
    #     trigger = 'buy' if pair.lower().find('down') == -1 else 'sell'
    #     invest_state = investing.getTechnicalData(investing_id, '5mins').lower()
    #     print(pair,trigger,invest_state)
    #     if invest_state.find(trigger) != -1:
    #         long(pair, dataFrame, client)
    # elif(penultimate > 70 and last <= 70):
    #     trigger = 'buy' if pair.lower().find('down') != -1 else 'sell'
    #     invest_state = investing.getTechnicalData(investing_id, '5mins').lower()
    #     if invest_state.find(trigger) != -1:
    #         short(pair, dataFrame, client)

def dc_aroon(crypto_data,pair,client):
    df = crypto_data['dataFrame']
    if df['Close'].iloc[-2] < df['Open'].iloc[-2]:#red stick
        return
    if df['Close'].iloc[-1] < df['Open'].iloc[-1]:#red stick
        return
    period = 14
    dc_low = ta.volatility.donchian_channel_lband(
        df['High'], df['Low'], df['Close'], window=period, offset=0, fillna=False)
    if dc_low.iloc[-3] == df['Low'].iloc[-3]:#donchian channel touch the low of a stick
        dc_mid = ta.volatility.donchian_channel_mband(
            df['High'], df['Low'], df['Close'], window=period, offset=0, fillna=False)
        maximum = (dc_mid.iloc[-1] + dc_low.iloc[-1]) / 2#mid between dc low band and dc mid band
        if df['Close'].iloc[-1] < maximum:
            aroon = ta.trend.AroonIndicator(
                close = df['Close'], window = period, fillna = False)
            aroon_down = aroon.aroon_down()
            if aroon_down.iloc[-1] > 80:
                aroon_up = aroon.aroon_up()
                if aroon_up.iloc[-1] < 20:
                    sl_levels = maximum - dc_low.iloc[-1]
                    long(pair,df,client,dc_low.iloc[-1],sl_levels)

def long(pair, dataFrame, client, stop_loss, stop_levels):
    log.debug(f"LONG pair:{pair}, stop_loss:{stop_loss}, stop_levels:{stop_levels}")
    if utils.load('long') is not None:
        return
    utils.save('long',
        {'pair':pair,'stop_loss':stop_loss,'qty':'0','stop_levels':stop_levels,'purchase_price':None})
    symbol_info = utils.getSymbolInfo(pair,client)
    minimum = float(symbol_info['filters_dic']['LOT_SIZE']['minQty'])
    price_filter = float(symbol_info['filters_dic']['PRICE_FILTER']['tickSize'])
    log.debug(f"min:{minimum},price_filter:{price_filter}")
    #utils.calculateBB(dataFrame)
    row = dataFrame.iloc[-1]
    print(row)
    price = float(row['Close'])
    price = D.from_float(price).quantize(D(str(price_filter)))
    log.debug(str(price))
    #diff = row['bb_ma'] - row['bb_l']
    #print('diff:',diff,'price:',row['Close'],'bb_l',row['bb_l'],'bb_h',row['bb_h'])
    #profit = row['Close'] + diff
    #win_percent = (diff / (row['Close'] / 100))/100
    # if win_percent > 0.005:#0.5%
    balance = float(client.get_asset_balance(asset='USDT')['free'])
    max_investment = float(os.environ.get('MAX_INVESTMENT') or 20)
    amount = balance if balance < max_investment else max_investment
    amount = (amount*0.95) / row['Close']
    amount = D.from_float(amount).quantize(D(str(minimum)))
    log.debug(f"amount:{amount} minimum:{minimum}")
    if amount < minimum:
        log.warning('Need moar')
        utils.remove('long')
        time.sleep(30)
        return
    utils.telegramMsg(f"Buying {amount} of <b>{pair}</b> at {price}")
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
            #profit = price+diff
            #stop_loss = price-diff
            log.debug(f"price:{price} stop_loss:{stop_loss}")
            utils.save('long',
                {'pair':pair,'stop_loss':stop_loss,'qty':order['executedQty'],
                'stop_levels':stop_levels,'purchase_price':row['Close']})
            break
        time.sleep(2)
        order = client.get_order(symbol=pair,orderId=order['orderId'])
    # else:
    #     log.debug(f"win_percent: {win_percent}")
    #     utils.remove('long')
        
def short(pair, dataFrame, client):
    return True
