# -*- coding: utf-8 -*-
#
# Plugin Setup
#
# ------------------------------------------------


# imports
# -------
import re
import os
import six
import yaml
from functools import wraps
from flask import Flask, Blueprint, Response, jsonify
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
MODELS = {}


# helpers
# -------
def document(obj):
    """
    Parse function or method and save documentation
    information in global DOCS data structure for
    auto-serving documentation.

    Args:
        obj (callable): Callable object with docstring.
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
            if isinstance(ret[0], (list, tuple, dict)):
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

            # document callable objects
            for name in dir(instance):
                func = getattr(instance, name)
                if name[0] != '_' and callable(func):
                    document(func)

            # parse/add url rules
            methods = options.pop("methods", METHODS)
            for meth in methods:
                handler = meth.lower()
                if hasattr(instance, handler):
                    endpoint = handler + '_' + obj.__name__.lower()
                    options['methods'] = [meth]
                    func = getattr(instance, handler)
                    app.add_url_rule(
                        rule, endpoint, autojsonify(func),
                        **options
                    )

        return obj
    return decorator


Blueprint.route = route


def gather_models():
    """
    Inspect sqlalchemy models from current context and set global
    dictionary to be used in url conversion.
    """
    global MODELS

    from flask import current_app
    if 'sqlalchemy' not in current_app.extensions:
        return

    # inspect current models and add to map
    db = current_app.extensions['sqlalchemy'].db
    for cls in db.Model._decl_class_registry.values():
        if isinstance(cls, type) and issubclass(cls, db.Model):
            MODELS[cls.__name__] = cls
            MODELS[cls.__table__.name] = cls
    return


class DataLoader(object):
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

    Additionally, this class supports defining multiple types of models
    in config files. If you want to load multiple types of models via
    config, you can use the following syntax in your config:

    .. code-block:: yaml

        Item:
            - name: item 1
              archived: True

        User:
            - name: test user
              email: email@email.com

    And load the data in your application via:

    .. code-block:: python

        db.seed('config.yml')

    """

    def __init__(self, model=None):
        self.model = model
        return

    def __call__(self, data, action=None):

        def load(filename):
            if hasattr(filename, 'read'):
                fi = filename
            else:
                if not os.path.exists(filename):
                    raise FileNotFoundError(filename)
                fi = open(filename, 'r')
            data = yaml.load(fi, Loader=yaml.FullLoader)
            fi.close()
            return data

        # gather models
        global MODELS
        if not MODELS:
            gather_models()

        # normalize inputs
        if isinstance(data, six.string_types):
            data = load(data)
        if not isinstance(data, (list, tuple)):
            data = [data]

        # format list for known model
        if self.model is not None:
            if not isinstance(self.model, six.string_types):
                model = self.model.__name__
            single = True
            create = [{self.model: data}]

        # format list for many embedded models
        else:
            if isinstance(data, dict):
                reformat = True
                for key in data:
                    if key not in MODELS:
                        reformat = False
                        break
                if reformat:
                    data = [{key: data[key]} for key in data]
            if not isinstance(data, (list, tuple)):
                raise AssertionError('Expected data to be in [{model: data}] format.')
            single = False
            create = data

        # iterate through create list and create the items
        db = {}
        for item in create:
            if not isinstance(item, dict):
                raise AssertionError('Invalid format for seed file, expected [{model: data}, ...]')

            # upsert the data
            model = list(item.keys())[0]
            if model not in MODELS:
                raise AssertionError('Model {} could not be found, or config in invalid format.'.format(model))
            results = MODELS[model].upsert(item[model])
            db[model] = results

            # run specified actions
            if action is not None:
                if not isinstance(results, (list, tuple)):
                    results = [results]
                for instance in results:
                    action(instance)

        return db if not single else db[list(db.keys())[0]]

    def __getattr__(self, attr):
        # invalid use case
        if self.model is not None:
            raise AssertionError('Please use db.load or db.load.table for loading data.')

        # gather models
        global MODELS
        if not MODELS:
            gather_models()

        if attr not in MODELS:
            raise AssertionError('Can not load data for table {}. Table does not exist.'.format(attr))

        return DataLoader(model=attr)


# plugin
# ------
class Occam(object):
    """
    Flask extension class for module, which sets up all flask-related
    capabilities provided by the module. This object can be initialized
    directly:

    .. code-block:: python

        from flask import Flask
        from flask_occam import Occam

        app = Flask(__name__)
        occam = Occam(app)

    Or lazily via factory pattern:

    .. code-block:: python

        occam = Occam()
        app = Flask(__name__)
        occam.init_app(app)

    For additional functionality, it is recommended that the extension
    be linked to the Flask-SQLAlchemy extension tied to the application:

    .. code-block:: python

        from flask_sqlalchemy import SQLAlchemy

        db = SQLAlchemy()
        occam = Occam(db)
        app = Flask(__name__)
        db.init_app(app)
        occam.init_app(app)
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

    def init_app(self, app, db=None):
        """
        Initialize application via lazy factory pattern.

        Args:
            app (Flask): Flask application.
            db (SQAlchemy): Flask SQLAlchemy extension.
        """
        if db is not None:
            self.init_db(db)

        self.app = app
        self.app.route = types.MethodType(route, self.app)
        self.app.config.setdefault('OCCAM_AUTODOC_ENABLED', True)
        self.app.config.setdefault('OCCAM_AUTODOC_PREFIX', '/docs')
        self.app.config.setdefault('OCCAM_LOG_USER_FORMAT', 'user')
        self.app.config.setdefault('OCCAM_LOG_DEFAULT_LEVEL', 'info')
        self.app.url_map.converters['id'] = ModelConverter
        self.app.register_error_handler(ValidationError, ValidationError.handler)

        # gather models for url converters
        @self.app.before_first_request
        def occam_db_init():
            from .converters import gather_models
            gather_models()

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
                    return "<pre>\n" + '\n---\n'.join(doc) + "\n</pre>\n", 200
                return '', 204

        return

    def init_db(self, db):
        """
        Initialize database model extensions.

        Args:
            db (SQAlchemy): Flask SQLAlchemy extension.
        """
        self.db = db
        self.db.Model.__bases__ += (ModelMixin,)
        self.db.load = DataLoader()
        return
