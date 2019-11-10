# -*- coding: utf-8 -*-
#
# Database mixins
#
# ------------------------------------------------


# imports
# -------
from flask import current_app


# helpers
# -------
def current_db():
    return current_app.extensions['sqlalchemy'].db


# mixins
# ------
class ModelMixin(object):
    """
    Example database mixin to be used in extension.
    """

    def __repr__(self):
        display = self.name if hasattr(self, 'name') else self.id
        return '<{}({})>'.format(self.__class__.__name__, display)

    def json(self):
        """
        Return dictionary with model properties. This
        method should be overriden by models to account
        for model-specific nuances in what to include
        in return payloads.
        """
        from sqlalchemy import inspect

        result = {}
        mapper = inspect(self.__class__)
        for column in mapper.attrs:
            result[column.key] = getattr(self, column.key)
        return result

    def commit(self):
        """
        Commit change using session and return item.
        """
        db = current_db()
        db.session.commit()
        return self

    @classmethod
    def get(cls, *args, **filters):
        """
        Get single item using filter_by query.
        """
        if len(args) == 1 and len(filters) == 0:
            filters['id'] = args[0]
        return cls.query.filter_by(**filters).first()

    def update(self, *args, **kwargs):
        """
        Update current item with specified data.
        """
        # normalize inputs
        if len(args) == 1 and isinstance(args[0], dict):
            kwargs.update(args[0])

        # use init method to include param parsing
        obj = self.__class__(**kwargs)

        # set params
        for key in kwargs:
            if hasattr(self, key):
                setattr(self, key, getattr(obj, key))
        del obj

        db = current_db()
        db.session.flush()
        return self

    @classmethod
    def create(cls, *args, **kwargs):
        """
        Create new record using specified arguments.
        """
        self = cls(*args, **kwargs)
        db = current_db()
        db.session.add(self)
        db.session.flush()
        return self

    def delete(self):
        """
        Delete current model object.
        """
        db = current_db()
        db.session.delete(self)
        db.session.flush()
        return

    @classmethod
    def all(cls, limit=None, offset=0):
        """
        Return all data with specified limit and offset
        """
        return cls.find(limit=limit, offset=offset)

    @classmethod
    def find(cls, limit=None, offset=0, **filters):
        """
        Search database with specified limit, offset,
        and filter criteria.
        """
        query = cls.query.filter_by(**filters).offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def count(cls):
        """
        Return total number of items in database.
        """
        return cls.query.count()

    @classmethod
    def upsert(cls, *args, **kwargs):
        """
        Upsert specified data into database. If the data
        doesn't exist in the database, it will be created,
        otherwise, the record will be updated. This method
        automatically detects unique keys by which to query
        the database for existing records.

        .. note:: The performance of this could be improved
                  by doing bulk operations for querying and
                  the create/update process.
        """
        from sqlalchemy import inspect

        # parse inputs
        data, multiple = [], True
        if len(kwargs):
            data.append(kwargs)
            multiple = False
        elif len(args) == 1 and isinstance(args[0], (list, tuple)):
            data = args[0]
        else:
            data = args

        # gather unique columns for querying existing data
        unique = []
        mapper = inspect(cls)
        for col in mapper.attrs:
            if hasattr(col, 'columns'):
                if col.columns[0].unique or col.columns[0].primary_key:
                    unique.append(col.key)

        # query for data and create or update
        result = []
        for record in data:

            # query using unique parameters
            params = {k: record[k] for k in unique if k in record}
            item = cls.get(**params) if len(params) else None

            # update if item exists
            if item is not None:
                item.update(**record)

            # create if it doesn't
            else:
                item = cls.create(**record)

            result.append(item)

        return result if multiple else result[0]

    @classmethod
    def load(cls, data, action=None):
        """
        Helper for loading data into application via config file. Using
        the following model definition as an example:

        .. code-block:: python

            class Item(db.Model):
                __tablename__ = 'item'

                # basic
                id = db.Column(db.Integer, primary_key=True)
                name = db.Column(db.String(255), nullable=False, unique=True, index=True)
                archived = db.Column(db.Boolean, default=False)

        You can seed data from the following config file:

        .. code-block:: yaml

            - name: item 1
              archived: True

            - name: item 2
              archived: False

        Into the application using:

        .. code-block:: python

            # via model directly
            User.seed('config.yml')

            # via db
            db.seed.users('config.yml')

        Arguments:
            data (str): File handle or path to config file.
            action (callable): Function to call on each loaded item.
                               Takes single created item as input.
        """
        db = current_db()
        loader = getattr(db.load, cls.__table__.name)
        return loader(data=data, action=action)
