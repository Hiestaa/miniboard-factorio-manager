# -*- coding: utf8 -*-
from __future__ import unicode_literals


class ModelException(Exception):
    pass


class Service(object):
    """
    Base class of any service, provide some abstraction of common functions
    """
    def __init__(self, connection, tableName):
        super(Service, self).__init__()
        self._connection = connection
        self._tableName = tableName
        try:
            self.createTable()
        except NotImplementedError:
            raise
        except:
            pass

    def createTable(self):
        """
        Override this function to execute the statement that create your
        table.
        """
        raise NotImplementedError()

    def schema(self):
        """
        Note: override this function to return the schema of the table.
        It should return a list of tuples containing expected document field
        associated with a values set to whatever you like (still tbd)
        """
        return []

    def itm2dict(self, itm):
        """
        Use the schema to build a dict from the item, where keys are fields
        (column names) and values are cell values.
        itm should be a list of values in column order.
        """
        data = {}
        for i, (k, v) in enumerate(self.schema()):
            data[k] = itm[i]
        return data

    def getById(self, _id, fields=None):
        """
        Return a document specific to this id
        _id is the _id of the document
        fields is the list of fields to be returned (all by default)
        """
        cur = self._connection.cursor()
        if fields is None:
            cur.execute("SELECT * FROM %s WHERE _id=?" % (self._tableName),
                        (_id, ))
            return self.itm2dict(cur.fetchone())

        fields = ', '.join(fields)
        cur.execute("SELECT %s FROM %s WHERE _id=?"
                    % (fields, self._tableName), (_id,))
        return self.itm2dict(cur.fetchone())

    def getOverallCount(self):
        cur = self._connection.cursor()
        cur.execute("SELECT COUNT(_id) AS count FROM %s" % self._tableName)
        return cur.fetchone()[0]

    def deleteAll(self):
        """
        Warning: will delete ALL the documents in this collection
        """
        cur = self._connection.cursor()
        cur.execute("DELETE FROM %s" % self._tableName)
        self._connection.commit()

    def deleteById(self, _id):
        cur = self._connection.cursor()
        cur.execute("DELETE FROM %s WHERE _id=?" % (self._tableName), (_id,))
        self._connection.commit()

    def getAll(self):
        """
        Returns all documents available in this collection.
        """
        cur = self._connection.cursor()
        cur.execute("SELECT * FROM %s" % self._tableName)
        return map(self.itm2dict, cur.fetchall())

    def set(self, _id, field, value):
        """
        If _id is a list, it will be used as a list of ids. All documents
        matching these ids
        will be
        """
        cur = self._connection.cursor()
        cur.execute("UPDATE %s SET %s=? WHERE _id=?"
                    % (self._tableName, field), (value, _id))
        self._connection.commit()
