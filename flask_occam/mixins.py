# -*- coding: utf-8 -*-
#
# Database mixins
#
# ------------------------------------------------


# imports
# -------
from flask import current_app
from sqlalchemy import inspect


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
        Return dictionary with model properties.
        """
        result = {}
        mapper = inspect(self.__class__)
        for column in mapper.attrs:
            result[column.key] = getattr(self, column.key)
        return result

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

    # @classmethod
    # def seed(cls, *args, **kwargs):
    #     """
    #     Create a list of objects, checking if
    #     objects ex
    #     """
    #     multiple = True

    #     # arg inputs
    #     if len(args) == 1:
    #         if isinstance(args[0], (list, tuple)):
    #             args = args[0]
    #         else:
    #             multiple = False

    #     # kwarg inputs
    #     elif len(kwargs):
    #         multiple = False
    #         args = [kwargs]

    #     # seed data
    #     db = current_db()
    #     result = []
    #     for item in args:
    #         obj = cls(**item)
    #         db.session.add(obj)
    #         result.append(obj)

    #     db.session.flush()

    #     return result if multiple else result[0]
