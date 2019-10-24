# -*- coding: utf-8 -*-
#
# Custom handlers for simplifying code related
# to url processing.
#
# ------------------------------------------------


# imports
# -------
from werkzeug.exceptions import NotFound


# handlers
# --------
class QueryHandler(object):
    """
    Handler for urls like ``/model/:id/:query``,
    where <query> represents a GET request. This
    allows developers to define individual methods
    for performing model-specific queries instead
    of needing to manage that complexity in the
    get/put/post methods.
    """

    def get(self, **kwargs):
        """
        Overwrite get endpoint for handler.

        Args:
            ident (int): Identifier for model.
            query (str): String for query to perform.
        """
        query = kwargs.pop('query', None)
        if not query or not hasattr(self, query):
            raise NotFound
        return getattr(self, query)(**kwargs)


class ActionHandler(object):
    """
    Handler for urls like ``/model/:id/:action``,
    where <action> represents a POST request. This
    allows developers to define individual methods
    for performing model-specific actions instead
    of needing to manage that complexity in the
    get/put/post methods.
    """

    def post(self, **kwargs):
        """
        Overwrite post endpoint for handler.

        Args:
            ident (int): Identifier for model.
            action (str): String for action to perform.
        """
        action = kwargs.pop('action', None)
        if not action or not hasattr(self, action):
            raise NotFound
        return getattr(self, action)(**kwargs)
