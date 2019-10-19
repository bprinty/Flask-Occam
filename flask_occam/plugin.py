# -*- coding: utf-8 -*-
#
# Plugin Setup
#
# ------------------------------------------------


# imports
# -------
from flask import Flask, Blueprint
import types

from .converters import ModelConverter
from .mixins import ModelMixin
from .errors import ValidationError


# config
# ------
METHODS = [
    'GET',
    'HEAD',
    'POST',
    'PUT',
    'DELETE',
    'CONNECT',
    'OPTIONS',
    'TRACE',
    'PATCH'
]


# helpers
# -------
def route(self, rule, **options):
    """
    Decorator for registering view function for a given URL rule.
    This ovverrides the default Flask route decorator to be able
    to handle class-based definitions, where endpoints are specified as
    class methods. With this, you can define routes with a function
    like you normally do in Flask:

    .. code-block:: python

        @app.route('/')
        def index():
            return 'Hello World'


    Or, you can define them with a class:

    .. code-block:: python

        @app.route('/test')
        class Test:
            def get(self):
                return 'GET /test', 200
            def post(self):
                return 'POST /test', 201


    This class-based definition of handlers helps with code organization
    and documentation efforts.

    """
    def decorator(obj):

        # function-based definition
        endpoint = options.pop("endpoint", obj.__name__)
        app = self.app if hasattr(self, 'app') else self
        if isinstance(obj, types.FunctionType):
            app.add_url_rule(rule, endpoint, obj, **options)

        # class-based definition
        else:
            instance = obj()
            methods = options.pop("methods", METHODS)
            for meth in methods:
                handler = meth.lower()
                if hasattr(instance, handler):
                    endpoint = handler + '_' + obj.__name__.lower()
                    options['methods'] = [meth]
                    func = getattr(instance, handler)
                    app.add_url_rule(
                        rule, endpoint, func,
                        **options
                    )

        return obj
    return decorator


Blueprint.route = types.MethodType(route, Blueprint)


# plugin
# ------
class Occam(object):
    """
    Plugin for updating flask functions to handle class-based URL
    routing.
    """

    def __init__(self, app=None, db=None):
        self.Blueprint = Blueprint
        
        # arg mismatch
        if app is not None and \
           db is None and \
           not isinstance(app, Flask):
            self.init_db(app)
            app = None

        # proper spec
        if db is not None:
            self.init_db(db)
        
        # app is specified properly
        if app is not None:
            self.init_app(app)
        return

    def init_app(self, app):
        self.app = app
        self.app.route = types.MethodType(route, self.app)
        self.app.config.setdefault('OCCAM_LOG_USER_FORMAT', 'user')
        self.app.config.setdefault('OCCAM_LOG_DEFAULT_LEVEL', 'info')
        self.app.url_map.converters['id'] = ModelConverter
        self.app.register_error_handler(ValidationError, ValidationError.handler)
        return

    def init_db(self, db):
        self.db = db
        self.db.Model.__bases__ += (ModelMixin,)
        return
