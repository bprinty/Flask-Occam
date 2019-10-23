# -*- coding: utf-8 -*-
#
# Plugin Setup
#
# ------------------------------------------------


# imports
# -------
import re
from functools import wraps
from flask import Flask, Blueprint, Response, current_app, request, jsonify
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
DOCS = {}


# helpers
# -------
def document(obj):
    """
    Parse function or method and save documentation
    information in global DOCS data structure for
    auto-serving documentation.
    """
    global DOCS, METHODS
    if obj.__doc__:
        m = re.search(r"({})\s+(/.+?)\s".format('|'.join(METHODS)), obj.__doc__)
        if m:
            method, endpoint = m.group(1), m.group(2)
            if endpoint not in DOCS:
                DOCS[endpoint] = {}
            DOCS[endpoint][method] = obj.__doc__
    return


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
        if isinstance(ret, tuple):
            if not isinstance(ret[0], Response):
                ret = list(ret)
                ret[0] = jsonify(ret[0])
                ret = tuple(ret)
        elif not isinstance(ret, Response):
            ret = jsonify(ret)
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
            document(obj)
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
                    func = getattr(instance, handler)
                    document(func)
                    app.add_url_rule(
                        rule, endpoint, autojsonify(func),
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
                endpoint = '/' + endpoint
                if endpoint in DOCS:
                    doc = []
                    for method in METHODS:
                        if method in DOCS[endpoint]:
                            doc.append(DOCS[endpoint][method])
                    return "<pre>\n" + '\n---\n'.join(doc) + "\n</pre>", 200
                return '', 204

        return

    def init_db(self, db):
        self.db = db
        self.db.Model.__bases__ += (ModelMixin,)
        return
