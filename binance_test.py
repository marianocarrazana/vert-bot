from binance import ThreadedWebsocketManager

api_key = 'api_key'
api_secret = 'api_secret'

def main():
    symbol = 'BNBBTC'
    twm = ThreadedWebsocketManager(api_key=api_key, api_secret=api_secret)
    twm.start()
    def handle_socket_message(msg):
        print(f"message type: {msg['e']}")
        print(msg)
    twm.start_depth_socket(callback=handle_socket_message, symbol=symbol)

if __name__ == "__main__":
   main()