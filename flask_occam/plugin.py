# -*- coding: utf-8 -*-
#
# Plugin Setup
#
# ------------------------------------------------


# imports
# -------
from functools import wraps
from flask import Flask, Blueprint, current_app, request
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
def autojsonify(func):
    """
    Automatically jsonify return payload if a dictionary
    is returned from the url handler. This removes some
    boilerplate associated with always needing to wrap
    json with `jsonify`.
    """
    @wraps(func)
    def _(*args, **kwargs):
        ret = func(*args, **kwargs)
        if isinstance(ret, dict):
            ret = jsonify(ret)
        elif isinstance(ret, tuple):
            if isinstance(ret[0], dict):
                ret = list(ret)
                ret[0] = jsonify(ret[0])
                ret = tuple(ret)
        return ret
    return _


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
            app.add_url_rule(rule, endpoint, autojsonify(obj), **options)

        # class-based definition
        else:
            instance = obj()
            methods = options.pop("methods", METHODS)
            for meth in methods:
                handler = meth.lower()
                if hasattr(instance, handler):
                    endpoint = handler + '_' + obj.__name__.lower()
                    options['methods'] = [meth]
                    func = autojsonify(getattr(instance, handler))
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
        self.app.config.setdefault('OCCAM_AUTODOC_ENABLED', True)
        self.app.config.setdefault('OCCAM_AUTODOC_PREFIX', '/docs')
        self.app.config.setdefault('OCCAM_LOG_USER_FORMAT', 'user')
        self.app.config.setdefault('OCCAM_LOG_DEFAULT_LEVEL', 'info')
        self.app.url_map.converters['id'] = ModelConverter
        self.app.register_error_handler(ValidationError, ValidationError.handler)

        # add auto-documentation if specified
        if self.app.config['OCCAM_AUTODOC_PREFIX']:

            @app.route(self.app.config['OCCAM_AUTODOC_PREFIX'] + '/<path:endpoint>')
            def autodoc(endpoint):
                # TODO: consider changing this to use GET for all documentation
                #       requests, and provide docstrings for all relevant methods
                #       -- also, re-evaluate the necessity of this. It might
                #       be too much (also security concerns)
                endpoint = '/' + endpoint
                adapter = current_app.url_map.bind(request.base_url)
                url = adapter.match(endpoint, method=request.method)
                func = current_app.view_functions[url[0]]
                if not func.__doc__:
                    return '', 204
                else:
                    return "<pre>\n" + func.__doc__ + "\n</pre>", 200

        return

    def init_db(self, db):
        self.db = db
        self.db.Model.__bases__ += (ModelMixin,)
        return
