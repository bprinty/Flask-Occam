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
    Handler for urls like ``/model/:query``,
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
    Handler for urls like ``/model/:action``,
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


class UpdateHandler(object):
    """
    Handler for urls like ``/model/:resource``,
    where <resource> represents a resource to update
    via PUT request. This allows developers to define
    individual methods for performing model-specific
    updates instead of needing to manage that complexity
    in the get/put/post methods.
    """

    def put(self, **kwargs):
        """
        Overwrite put endpoint for handler.

        Args:
            ident (int): Identifier for model.
            resource (str): String for resource to update.
        """
        action = kwargs.pop('resource', None)
        if not action or not hasattr(self, action):
            raise NotFound
        return getattr(self, action)(**kwargs)
