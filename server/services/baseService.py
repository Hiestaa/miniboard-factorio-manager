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
        Note: override this function to enable schema-validation.
        It should return a dict where keys are expected document fields
        and values are set to True if the field is required, False otherwise
        """
        return {}

    def validate(self, query, strict=True):
        """
        Validate the query to ensure it matches the defined schema.
        If the schema method is overrode to return a valid schema
        object (a dict where keys are expected document fields, and values
        are set to True if the field is required, False otherwise),
        this function will check the query and ensure that there is no
        unexpected or missing required keys (by raising a ModelException).
        Returns the validated query.
        If strict is set to False, the required keys won't be tested. This
        can be useful to validate an update query, ensuring that the field
        updated is not out of the schema.
        """
        schema = self.schema()
        schema_keys = set(schema)
        # if there is no keys in the schema, exit
        if len(schema_keys) == 0:
            return query
        required_schema_keys = set([k for k in schema_keys if schema[k]])

        query_keys = set(query.keys())

        # no unexpected keys: all the keys of the queries exist
        # in the schema. An exception, the key _id, can be specified
        # even
        union = schema_keys | query_keys
        if len(union) > len(schema_keys):
            diff = query_keys - schema_keys
            if len(diff) > 1 or '_id' not in diff:
                raise ModelException(
                    "The keys: %s are unexpected in the validated query."
                    % str(query_keys - schema_keys))

        if not strict:
            return query

        # all required keys are here
        intersect = required_schema_keys & query_keys
        if len(intersect) < len(required_schema_keys):
            raise ModelException(
                "The required keys: %s are missing in the validated query"
                % str(required_schema_keys - query_keys))

        return query

    def getById(self, _id, fields=None):
        """
        Return a document specific to this id
        _id is the _id of the document
        fields is the list of fields to be returned (all by default)
        """
        cur = self._connection.cursor()
        if fields is None:
            cur.execute("SELECT * FROM %s WHERE _id=?"
                        % (self._tableName), _id)
            return cur.fetchone()

        projection = self.validate({f: True for f in fields})
        fields = ', '.join(projection)
        cur.execute("SELECT %s FROM %s WHERE _id=?"
                    % (fields, self._tableName), _id)
        return cur.fetchone()

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
        cur.execute("DELETE FROM %s WHERE _id=?" % (self._tableName), _id)
        self._connection.commit()

    def getAll(self):
        """
        Returns all documents available in this collection.
        """
        cur = self._connection.cursor()
        cur.execute("SELECT * FROM %s" % self._tableName)

    def set(self, _id, field, value):
        """
        If _id is a list, it will be used as a list of ids. All documents
        matching these ids
        will be
        """
        self.validate({field: value})
        cur = self._collection.cursor()
        cur.execute("UPDATE %s SET %s=? WHERE _id=?"
                    % (self._tableName, field), value, _id)
        self._connection.commit()
