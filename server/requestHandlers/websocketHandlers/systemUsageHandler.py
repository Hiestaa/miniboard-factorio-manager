# -*- coding: utf8 -*-

from __future__ import unicode_literals

import logging

import psutil

psutil.cpu_percent(interval=0.1)


class SystemUsageHandler(object):
    """Answers back to messages with resource usage information"""

    handlerKey = 'system-usage'

    def __init__(self, writeMessage):
        super(SystemUsageHandler, self).__init__()

        self.writeMessage = writeMessage

    def systemUsage(self):
        return {
            'CPU': psutil.cpu_percent(),
            'MEM': psutil.virtual_memory().percent
        }

    def onMessage(self, message):
        """
        The message should hold the field 'detailed' as a boolean.
        If true, all the following information will be available:
        <TODO>
        If false, only the following information will be available:
        * `CPU`:float, cpu usage percentage
        * `MEM`:float memory usage percentage
        """
        logging.debug("Received: %s", str(message))
        if message['detailed']:
            self.writeMessage(self.detailedSystemUsage())
        else:
            self.writeMessage(self.systemUsage())
