# -*- coding: utf8 -*-

from __future__ import unicode_literals

import logging
import time

from tornado.web import HTTPError
from tornado.ioloop import IOLoop

from server.model import getService
from tools import saves, factorio


instanceProcess = None


class ManageHandler(object):
    """Answers back to messages with resource usage information"""

    handlerKey = 'manage'

    def __init__(self, writeMessage, error):
        super(ManageHandler, self).__init__()

        self.writeMessage = writeMessage
        self.error = error
        self.instLogtimeout = None

        if instanceProcess is not None and not \
                instanceProcess.killed.value:
            self.instLogtimeout = IOLoop.current().add_timeout(
                time.time() + 2, self._logInstance)

    def execLoad(self, message):
        """
        Load the data for the given instance and return them as a list of dicts.
        The list may be of length 1 if the _id of an instance was given, or of
        any other possible length if '*' is given as an _id in which case all
        available instances will be returned.
        This action requires the field `_id` to be set.

        The message written back will have the following structure:
        * 'instances': list of instance documents as returned by the database
        * 'action': 'load' (string litteral)
        """
        _id = message['_id']
        if _id == '*':
            instances = getService('instance').getAll()
        else:
            instances = [getService('instance').getById(_id)]
        # print instances
        self.writeMessage({
            'instances': instances,
            'action': 'load'
        })

    def execListSaves(self, _):
        """
        Returns the list of existing saves on the server
        The message will have the following structure:
        * 'saves': list of saves (see tools.saves.list() doc)
        * 'action': 'listsaves'
        """
        self.writeMessage({
            'saves': saves.list(),
            'action': 'listsaves'
        })

    def execSave(self, message):
        """
        Save the instance from the given message data. The field `data`
        should be defined in the message and hold the following fields:
        * name: name of the instance
        * port: selected port for this instance
        * save: selected save for this instance
        If `_id` field is given as well, the instance will be updated instead.
        Note that updating a running instance will have no effect until it is
        restarted.
        Returned message will hold the fields:
        * 'action': 'save'
        * 'instances': [saved data as a list of a single element for
                        consistency with the `load` action.]
        """
        if '_id' in message['data']:
            _id = message['data']['_id']
            getService('instance').update(
                message['data']['_id'], name=message['data']['name'],
                save=message['data']['save'], port=message['data']['port'])
        else:
            _id = getService('instance').insert(
                name=message['data']['name'], save=message['data']['save'],
                port=message['data']['port'])
        self.writeMessage({
            'action': 'save',
            'instances': [getService('instance').getById(_id)]
        })

    def execDelete(self, message):
        """
        Delete the instance from given message id.
        The message should contain the `_id` of the instance to delete
        Write back a message with the field 'action' set to 'delete' and the
        field '_id' set to the deleted instance id.
        """
        getService('instance').deleteById(message['_id'])
        self.writeMessage({
            'action': 'delete',
            '_id': message['_id']
        })

    def _logInstance(self):
        if instanceProcess is None:
            return

        data = instanceProcess.read()
        if data is not None:
            logging.info('[Instance] %s' % data)
            self.writeMessage({
                'action': 'log',
                'message': data
            })

        if not instanceProcess.is_alive():
            logging.warning(
                "Cannot find instance log, process isn't alive anymore.")
            getService('instance').set(instanceProcess._id, 'status', 'stopped')
            self.writeMessage({
                'action': 'kill',
                'instances': [
                    getService('instance').getById(instanceProcess._id)]
            })
            self.error("Instance seems to have stopped unexpectedly and "
                       "prematurely.")
            return

        self.instLogtimeout = IOLoop.current().add_timeout(
            time.time() + 2, self._logInstance)

    def execStart(self, message):
        """
        Start a factorio instance.
        If a running instance is already existing, attempt to kill it first via
        ctrl+c to trigger data saving.
        There might be data loss when starting an instance while another one
        is running, use carefully.
        Requires the messsage to hold the field `_id` denoting which instance
        to start
        Write back the data for all instances in database
        """
        global instanceProcess
        if self.instLogtimeout:
            IOLoop.current().remove_timeout(self.instLogtimeout)
        if instanceProcess is not None and not \
                instanceProcess.killed.value:
            raise Exception(
                "An instance is already running (pid: %d, _id=%s)" % (
                    instanceProcess.subpid.value,
                    instanceProcess._id))
        data = getService('instance').getById(message['_id'])
        instanceProcess = factorio.Instance(
            data['port'], data['save'], data['_id'])
        instanceProcess.start()
        self.instLogtimeout = IOLoop.current().add_timeout(
            time.time() + 2, self._logInstance)
        getService('instance').set(message['_id'], 'status', 'running')
        self.writeMessage({
            'action': 'start',
            'instances': getService('instance').getAll()
        })

    def execKill(self, message):
        """
        Kill a running factorio instance.
        Requires the messsage to hold the field `_id` denoting which instance
        to kill
        Write back the data for all instances in database
        """
        getService('instance').set(message['_id'], 'status', 'stopped')

        if instanceProcess is None:
            self.writeMessage({
                'action': 'kill',
                'instances': getService('instance').getAll()
            })
            raise Exception("No running instance found")
        instanceProcess.kill()

        if self.instLogtimeout:
            IOLoop.current().remove_timeout(self.instLogtimeout)

        self.writeMessage({
            'action': 'kill',
            'instances': getService('instance').getAll()
        })

    def onMessage(self, message):
        """
        The message should hold the following field:
        * action: action to perform, can be any of 'load', 'save', 'kill',
          'start', 'listsaves'
        More fields may be required depending on the action. See corresponding
        method documentation for details.
        """
        logging.debug("Received: %s", str(message))
        actions = {
            'save': self.execSave,
            'delete': self.execDelete,
            'load': self.execLoad,
            'kill': self.execKill,
            'start': self.execStart,
            'listsaves': self.execListSaves
        }
        if message['action'] in actions:
            return actions[message['action']](message)
        raise HTTPError(404, "Not Found: %s" % message['action'])
