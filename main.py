#!.env/bin/python
# -*- coding: utf8 -*-

from __future__ import unicode_literals

import argparse
import logging
from threading import Thread

import tornado
from tornado.web import Application

from conf import Conf
import log
from server.model import Model
from server.requestHandlers.templatesHandler import TemplatesHandler
from server.requestHandlers.defaultHandler import DefaultHandler
from server.requestHandlers.assetsHandler import AssetsHandler


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run the server for the web-ui report",
        prog="server.py")
    parser.add_argument('--verbose', '-v', action="count",
                        help="Set console logging verbosity level. Default \
displays only ERROR messages, -v enable WARNING messages, -vv enable INFO \
messages and -vvv enable DEBUG messages. Ignored if started using daemon.",
                        default=0)
    parser.add_argument('-q', '--quiet', action="store_true",
                        help="Remove ALL logging messages from the console.")
    return parser.parse_args()


class Server(Thread):
    """
    Create the server.
    """
    def __init__(self, ns):
        """
        Create the server. Call the 'run' function to start the server
        synchroneously, call the 'start' function to start the server
        on its own thread.
        * ns: configuration of the server (see: parse_args function)
        """
        super(Server, self).__init__()
        self._ns = ns

    def stop(self):
        ioloop = tornado.ioloop.IOLoop.instance()
        ioloop.add_callback(lambda x: x.stop(), ioloop)
        logging.info("Requested tornado server to stop.")

    """
    Run the server. This function will be called when the server's daemon
    start, but can also be called on the current process if server is not
    started as a daemon.
    """
    def run(self):
        # initialize log
        log.init(
            self._ns.verbose, self._ns.quiet,
            filename="server.log", colored=False)

        # create model, that hold services for database collection
        # and memory, a wrapper object over the manipulation of the shared
        # persistent memory between queries
        model = Model()

        # define server settings and server routes
        server_settings = {
            "cookie_secret": "101010",  # todo: generate a more secure token
            "template_path": "http/templates/",
            # allow to recompile templates on each request, enable autoreload
            # and some other useful features on debug. See:
            # http://www.tornadoweb.org/en/stable/guide/running.html#debug-mode
            "debug": Conf['state'] == 'DEBUG'
        }
        # /assets/... will send the corresponding static asset
        # /[whatever] will display the corresponding template
        # other routes will display 404
        server_routes = [
            (r"/assets/([a-zA-Z0-9_\/\.-]+)/?", AssetsHandler),
            (r"/([a-zA-Z0-9_/\.=-]*)/?", TemplatesHandler),
            (r"/(.+)/?", DefaultHandler)
        ]

        # start the server.
        logging.info("Server Starts - %s state - %s:%s"
                     % (Conf['state'], 'localhost', Conf['server']['port']))
        logging.debug("Debugging message enabled.")
        application = Application(server_routes, **server_settings)
        application.listen(Conf['server']['port'])
        logging.info(
            "Connected to database: %s"
            % Conf['database']['name'])

        # start listening
        try:
            tornado.ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            logging.info("Stopping server...")

        model.disconnect()

if __name__ == '__main__':
    Server(parse_args()).run()
