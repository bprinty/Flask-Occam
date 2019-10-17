# -*- coding: utf-8 -*-
#
# Database mixins
#
# ------------------------------------------------


# imports
# -------
from flask import current_app


# mixins
# ------
class ModelMixin(object):
    """
    Example database mixin to be used in extension.
    """

    @property
    def __db__(self):
        return current_app.extensions['sqlalchemy'].db

    def __repr__(self):
        display = self.name if hasattr(self, 'name') else self.id
        return '<{}({})>'.format(self.__class__.__name__, display)

    @classmethod
    def get(cls, *args, **filters):
        if len(args) == 1 and len(filters) == 0:
            filters['id'] = args[0]
        return cls.query.filter_by(**filters).first()

    def update(self, *args, **kwargs):
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

        self.__db__.session.flush()
        return self

    @classmethod
    def create(cls, *args, **kwargs):
        self = cls(*args, **kwargs)
        self.__db__.session.add(self)
        self.__db__.session.flush()
        return self

    def delete(self):
        self.__db__.session.delete(self)
        self.__db__.session.flush()
        return

    @classmethod
    def find(cls, limit=None, offset=0, **filters):
        query = cls.query.filter_by(**filters).offset(offset)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    @classmethod
    def count(cls):
        return cls.query.count()

    @classmethod
    def seed(cls, *args, **kwargs):
        multiple = True

        # arg inputs
        if len(args) == 1:
            if isinstance(args[0], (list, tuple)):
                args = args[0]
            else:
                multiple = False

        # kwarg inputs
        elif len(kwargs):
            multiple = False
            args = [kwargs]

        # seed data
        result = []
        for item in args:
            obj = cls(**item)
            self.__db__.session.add(obj)
            result.append(obj)

        self.__db__.session.flush()

        return result if multiple else result[0]
