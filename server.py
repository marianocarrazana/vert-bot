from tornado import ioloop
from tornado import web
from datetime import datetime

minutes = lambda ns : ns*1000*60

class MainHandler(web.RequestHandler):
    def get(self):
        self.write("Hello, world")

def make_app():
    return web.Application([
        (r"/", MainHandler),
    ])

def call():
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S.%f")
    print("Current Time =", current_time)

if __name__ == "__main__":
    app = make_app()
    port = 8888
    app.listen(port)
    print("Server listening on http://localhost:%s" % port)
    scheduler = ioloop.PeriodicCallback(call, minutes(0.01))
    scheduler.start() 
    ioloop.IOLoop.current().start()
