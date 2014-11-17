import seplis.play.handlers.play
import tornado.web
import tornado.ioloop
import tornado.httpserver
from seplis import config


class Application(tornado.web.Application):

    def __init__(self, **args):
        settings = dict(
            debug=seplis.config['debug'],
            autoescape=None,
            xsrf_cookies=False,
        )
        urls = [
            (r'/(.*)/media/(.*)', seplis.play.handlers.play.Hls_file_handler),
            (r'/(.*)/cancel', seplis.play.handlers.play.Hls_cancel_handler),

            (r'/transcode', seplis.play.handlers.play.Transcode_handler),
            (r'/play', seplis.play.handlers.play.Play_handler),
            
            (r'/metadata', seplis.play.handlers.play.Metadata_handler),
        ]
        tornado.web.Application.__init__(self, urls, **settings)

def main():
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(config['play']['port'])
    tornado.ioloop.IOLoop.instance().start()