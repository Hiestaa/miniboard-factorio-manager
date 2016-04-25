# -*- coding: utf8 -*-

from __future__ import unicode_literals

import logging
from threading import Lock
import sqlite3
import os
import errno

from conf import Conf
from server.services.instanceService import InstanceService


class ModelException(Exception):
    pass


# This class is the interface with the sqlite api.
class Model(object):
    """
    This class is the interface with the mongodb api.
    It is used to retrieve text to be used by the nlp algorithm from the loops
    collection and to cache items like account list, locations or
    generated reports
    It manages its own back-up system by creating DB dumps every week
    (or any configured delay)
    """
    def __init__(self):
        super(Model, self).__init__()
        self._server_process = None
        logging.info("Starting mongo client")
        # create db folder
        path = Conf['database']['name'].split('/')[:-1]
        path = os.path.join(*path)
        try:
            os.makedirs(path)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

        # create connection
        try:
            self._connection = sqlite3.connect(os.path.join(
                *Conf['database']['name'].split('/')))
        except:
            raise ModelException("Unable to connect sqlite database %s"
                                 % Conf['database']['name'])

        self._services = {
            'instance': InstanceService(self._connection),
        }

    def getService(self, service):
        if service in self._services:
            return self._services[service]
        raise ModelException('The service %s does not exist' % service)

    def disconnect(self):
        if self._server_process is not None:
            logging.info("Waiting for MongoDB server process to stop...")
            self._server_process.stop()
            # self._server_process.terminate()
            self._server_process.join()
            logging.info("MongoDB server stopped.")


# this module is a singleton
# This object should not be accessed directly, use getInstance instead.
_instance = None
# will be used to lock the instance while initializing it.
_lock = Lock()


def getInstance():
    global _instance
    global _lock
    if _instance is None:
        with _lock:
            # re-test the _instance value, avoiding the case where another
            # thread did the initialization between the previous test and the
            # lock
            if _instance is None:
                _instance = Model()
    return _instance


def getService(service):
    return getInstance().getService(service)
