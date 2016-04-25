# -*- coding: utf8 -*-

from __future__ import unicode_literals

import logging


class EchoHandler(object):
    """ Implement a dummy echo handler"""

    handlerKey = 'echo'

    def __init__(self, writeMessage):
        super(EchoHandler, self).__init__()

        self.writeMessage = writeMessage

    def onMessage(self, message):
        """
        Called when receiving a message.
        The message should hold the field 'content'.
        """
        logging.debug("Received: %s", str(message))
        self.writeMessage({
            'content': message['content']
        })
