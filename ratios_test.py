import investing
import vars
import time

for cr in investing.CRYPTO:
    book = vars.client.get_order_book(symbol=cr['binance_id'],limit=1000)
    max_ask = float(book["asks"][0][0]) * 1.02
    min_bid = float(book["bids"][0][0])
    min_bid = min_bid - (min_bid*0.02)
    bid_list = []
    ask_list = []
    total_ask = 0.0
    total_bid = 0.0
    for a in book["asks"]:
        if float(a[0]) <= max_ask:
            price = float(a[0])
            qty = float(a[1])
            total_ask += qty
            ask_list.append([price,qty])
    for b in book["bids"]:
        if float(b[0]) >= min_bid:
            price = float(b[0])
            qty = float(b[1])
            total_bid += qty
            bid_list.append([price,qty])
    ratio = total_bid/total_ask
    print(cr['binance_id'],len(ask_list),len(bid_list),ratio)
    time.sleep(1)
