# -*- coding: utf8 -*-
from __future__ import unicode_literals

import logging
from uuid import uuid4

from baseService import Service

"""
Schema:
    * _id:string id of the instance
    * name:string name of the instance
    * save:string name of the save this instance is running
    * port:string, port this instance is listening on
    * status:string, current status of the instance ('running' or 'stopped')
"""


class InstanceService(Service):
    """
    Provides helper functions related to the tags collection
    of the database.
    """
    def __init__(self, connection):
        super(InstanceService, self).__init__(connection, 'instances')

    def createTable(self):
        self._connection.execute(
            "CREATE TABLE %s (_id text, name text, save text, port text, "
            "status text)" % self._tableName)

    def schema(self):
        return [
            ('_id', 'whatever'),
            ('name', True),
            ('save', False),
            ('port', True),
            ('status', False),
        ]

    def insert(self, name, save=None, port=None, status='stopped', _id=None):
        logging.debug("Saving new instance: %s" % (name))
        if _id is None:
            _id = str(uuid4())

        cur = self._connection.cursor()
        cur.execute("INSERT INTO %s VALUES (?, ?, ?, ?, ?)" % self._tableName,
                    (_id, name, save, port, status))
        self._connection.commit()
        return _id

    def update(self, _id, name, save, port):
        """
        Update all the above in one request.
        Call `set` to set only a single field.
        """
        cur = self._connection.cursor()
        cur.execute(
            "UPDATE %s SET name=?, save=?, port=? WHERE _id=?"
            % (self._tableName), (name, save, port, _id))
        self._connection.commit()
