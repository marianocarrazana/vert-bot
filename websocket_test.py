import websocket

def on_message(ws, message):
    print(message)
    ws.close()

def on_error(ws, error):
    print(error)

if __name__ == "__main__":
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("wss://stream.binance.com:9443/ws/bnbbtc@depth",
                              on_message = on_message,
                              on_error = on_error)

    ws.run_forever()
    print("hello")