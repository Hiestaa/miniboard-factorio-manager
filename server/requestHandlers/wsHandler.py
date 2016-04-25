# -*- coding: utf8 -*-

from __future__ import unicode_literals

import logging
import json
from functools import partial
import time

from tornado.websocket import WebSocketHandler

from server.requestHandlers.websocketHandlers.echoHandler import EchoHandler
from server.requestHandlers.websocketHandlers.systemUsageHandler import \
    SystemUsageHandler
from tools import utils


class WSHandler(WebSocketHandler):
    """
    Entry point all websocket communications
    The websocket handlers (in the submodule `websocketHandlers`) will be
    instanciated and bound to a handlerKey.
    The classes in this module should have this `handlerKey` property
    available on the class level.
    Each message transmitted between the client and the server will have
    to send this value back and force to know which part of the application
    should handle the message. The messages will be json-encoded dict/objects
    that should hold this field.
    """
    def open(self):
        logging.info("WebSocket opened")
        self._handlers = {
            EchoHandler.handlerKey: EchoHandler(
                partial(self.writeMessage, handlerKey=EchoHandler.handlerKey)),
            SystemUsageHandler.handlerKey: SystemUsageHandler(
                partial(self.writeMessage,
                        handlerKey=SystemUsageHandler.handlerKey))
        }

    def writeMessage(self, message, handlerKey):
        """ Write a message for the handler given by `handlerKey` """
        message['handlerKey'] = handlerKey
        self.write_message(json.dumps(message))

    def on_message(self, message):
        t0 = time.time()
        message = json.loads(message)
        self._handlers[message['handlerKey']].onMessage(message)
        logging.info("Received message handler key: %s [%s]",
                     message['handlerKey'], utils.timeFormat(
                         time.time() - t0))

    def on_close(self):
        logging.info("WebSocket closed")
