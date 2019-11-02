# -*- coding: utf-8 -*-
#
# Common utilities for app
#
# ------------------------------------------------


# imports
# -------
import sys
import yaml
import inspect
import logging
from functools import wraps
from wtforms.fields.core import UnboundField, Field
from wtforms import validators, Form, StringField
from werkzeug.exceptions import ExpectationFailed
from werkzeug.datastructures import MultiDict, ImmutableMultiDict
from flask import request, current_app, Response, has_request_context

from .errors import ValidationError

if sys.version_info[0] >= 3:
    unicode = str

try:
    from flask_login import current_user
except ImportError:
    current_user = None


# helpers
# -------
def argspec(func):
    if sys.version_info[0] >= 3:
        return list(inspect.signature(func).parameters.keys())
    else:
        return list(inspect.getargspec(func).args)


# logging
# -------
class log(object):
    """
    Decorator for adding default logging functionality
    to api methods.
    """

    def __init__(self, msg, level=None):
        self.msg = msg
        if current_app:
            default = current_app.config['OCCAM_LOG_DEFAULT_LEVEL']
        else:
            default = 'info'
        self.level = default if not level else level
        return

    def __call__(self, func):
        # config logger to use
        if current_app:
            logger = getattr(current_app.logger, self.level)
        else:
            logger = getattr(logging, self.level)

        # inner function to format message
        @wraps(func)
        def inner(*args, **kwargs):
            data = kwargs.copy()
            varnames = argspec(func)
            data.update(dict(zip(varnames, args)))
            data = {k: v for k, v in data.items() if k not in ['cls', 'self']}
            data.setdefault(current_app.config['OCCAM_LOG_USER_FORMAT'], current_user)
            data.setdefault('kwargs', kwargs)
            logger(self.msg.format(**data))
            return func(*args, **kwargs)
        return inner

    @classmethod
    def debug(cls, msg):
        """
        Log provided message with level DEBUG.
        """
        return cls(msg, level='debug')

    @classmethod
    def info(cls, msg):
        """
        Log provided message with level INFO.
        """
        return cls(msg, level='info')

    @classmethod
    def warning(cls, msg):
        """
        Log provided message with level WARNING.
        """
        return cls(msg, level='warning')

    @classmethod
    def error(cls, msg):
        """
        Log provided message with level ERROR.
        """
        return cls(msg, level='error')

    @classmethod
    def critical(cls, msg):
        """
        Log provided message with level CRITICAL.
        """
        return cls(msg, level='critical')


# pagination
# ----------
def paginate(**options):
    """
    Automatically force request pagination for endpoints
    that shouldn't return all items in the database directly.
    If this decorator is used, ``limit`` and ``offset`` request
    arguments are automatically included in the request. The
    burden is then on developers to do something with those
    ``limit`` and ``offset`` arguments. An example request header
    set by this decorator is as follows:

    .. code-block:: text

        Link: <https://localhost/items?limit=50&offset=50>; rel="next",
              <https://localhost/items?limit=50&offset=500>; rel="last"

    Args:
        limit (int): Number of entries to limit a query by.
        total (int, callable): Number or callable for determining
            the total number of records that can be returned
            for the request. This is used in determining the
            pagination header.
    """
    if 'total' not in options:
        raise AssertionError(
            '`@paginate` decorator requires `total=` parameter '
            'for determining total number of records to paginate. '
            'See the documentation for more details.')

    def decorator(func):

        @wraps(func)
        def inner(*args, **kwargs):

            # only paginate on get requests
            if request.method != 'GET':
                return func(*args, **kwargs)

            # format parameters
            limit = request.args.get('limit', options.get('limit'))
            offset = int(request.args.get('offset', options.get('offset', 0)))
            total = options['total']() if callable(options['total']) else options['total']
            url = options.get('url', request.base_url)

            # config request parameters
            request.args = request.args.copy()
            request.args.setdefault('limit', limit)
            request.args.setdefault('offset', offset)

            # if no need to paginate, return without setting headers
            if limit is None:
                return func(*args, **kwargs)
            limit = int(limit)

            # add next page link
            headers = {}
            next_page = '<{}?limit={}&offset={}>'.format(url, limit, offset + limit)
            headers['Link'] = '{}; rel="next"'.format(next_page)

            # add last page link and header
            if options['total'] is not None:
                total = options['total']() if callable(options['total']) else options['total']
                last_page = '<{}?limit={}&offset={}>'.format(url, limit, offset + limit)
                headers['Link'] += ', {}; rel="last"'.format(last_page)
                headers['X-Total-Count'] = str(total)

            # call the function and create response
            response = func(*args, **kwargs)

            # if a specific response has already been crafted, use it
            if isinstance(response, Response):
                return response

            # normalize response data
            if not isinstance(response, tuple):
                response = [response]
            response = list(response)
            if hasattr(response[0], 'json'):
                content_length = len(response[0].json)
            else:
                content_length = len(response[0])
            if len(response) == 1:
                response.append(200)
            if len(response) == 2:
                response.append({})

            # if the response data is equal to the pagination, it's
            # truncated and needs updated headers/status
            if content_length == limit:
                response[1] = 206
                response[2].update(headers)

            return tuple(response)
        return inner
    return decorator


# db-related
# ----------
def transactional(func):
    """
    Decorator for wrapping transactional support around
    a request handler or API method. By wrapping a method
    in ``@transactional``, any exception thrown will force
    a session rollback. Otherwise, the session will be
    committed.
    """
    @wraps(func)
    def inner(*args, **kwargs):
        if 'sqlalchemy' not in current_app.extensions:
            raise AssertionError('Cannot use @transactional if Flask-SQLAlchemy extension has not been registered!')
        db = current_app.extensions['sqlalchemy'].db
        try:
            ret = func(*args, **kwargs)
            db.session.commit()
            return ret
        except Exception as e:
            db.session.rollback()
            raise e
    return inner


# validation
# ----------
class OptionalType:
    """
    Proxy for making a type optional. Used
    internally within the module.
    """

    def __init__(self, typ):
        self.type = typ
        return

    def __call__(self, item):
        return self.type(item)


def optional(field):
    """
    Replace DataRequired validtion scheme with Optional
    validation scheme.

    Args:
        field (type, Field): Field to process validation options for.
    """
    # parse types as inputs
    if isinstance(field, (type, list, tuple, dict)):
        return OptionalType(field)

    # handle validators directly
    elif not isinstance(field, (Field, UnboundField)):
        return StringField(field.__class__.__name__, [validators.Optional(), field])

    # handle wtform input class
    else:
        if len(field.args) < 2:
            raise AssertionError('Validator must have associated name and validation scheme (2 arguments)')
        name = field.args[0]
        checks = list(filter(
            lambda x: not isinstance(x, (validators.DataRequired, validators.InputRequired)),
            field.args[1]
        ))
        checks.insert(0, validators.Optional())
        obj = field.field_class(name, checks)
        return obj


def create_validator(contract, force_optional=False):
    """
    Factory pattern for creating custom validator in the style
    of WTForms. This function takes the contract needed to validate
    against and returns a ``Form`` object that can perform
    the validation according to validation rules in the contract.

    Args:
        contract (dict): Dictionary with key value mappings for
                         payload contract to validate.
        force_optional (bool): Force all validators in contract
                               to be wrapped with optional().
    """

    class ContractValidator(object):
        """
        Custom validator class that can handle both
        wtforms validators and nested type validation.
        """
        type_contract = {}
        form_contract = {}
        for key in contract:
            field = contract[key]
            if force_optional and not isinstance(field, OptionalType):
                field = optional(field)
            if isinstance(field, (type, list, tuple, dict, OptionalType)):
                type_contract[key] = field
            elif isinstance(field, (Field, UnboundField)):
                form_contract[key] = field
            else:
                form_contract[key] = StringField(key, [
                    validators.DataRequired(),
                    field
                ])

        def __init__(self, data):
            self.data = data
            self.errors = {}
            return

        def check_type(self, actual, expected):
            # missing parameter (checked in api methods)
            if actual is None:
                return True

            # types
            if isinstance(expected, OptionalType):
                expected = expected.type

            if isinstance(expected, type):
                if expected == str:
                    return isinstance(actual, (str, unicode))
                else:
                    return isinstance(actual, expected)

            # dictionary of types
            elif isinstance(expected, dict):
                if not isinstance(actual, dict):
                    return False
                Validator = create_validator(expected)
                form = Validator(MultiDict(actual))
                return form.validate()

            # list of objects (expected structure should
            # have one entry representing shape of elements)
            elif isinstance(expected, list):
                if not isinstance(actual, list):
                    return False
                if isinstance(expected[0], type):
                    for entry in actual:
                        if not self.check_type(entry, expected[0]):
                            return False
                else:
                    Validator = create_validator(expected[0])
                    for entry in actual:
                        form = Validator(MultiDict(entry))
                        if not form.validate():
                            return False

            return True

        def check_form(self, actual, expected):
            class CustomValidator(Form):
                pass
            for key in expected:
                setattr(CustomValidator, key, expected[key])
            form = CustomValidator(MultiDict(actual))
            valid = form.validate()
            self.errors.update(form.errors)
            return valid

        def validate(self):
            """
            Run validation for composite form object.
            """
            valid = True

            # process types in contract
            if self.type_contract:
                for key in self.type_contract:
                    expect = self.type_contract[key]

                    # check for required fields
                    if key not in self.data and not isinstance(expect, OptionalType):
                        self.errors[key] = ['This field is required.']
                        valid = False

                    # check type and nested data
                    else:
                        tcheck = self.check_type(self.data.get(key), expect)
                        valid &= tcheck
                        if not tcheck:
                            typ = expect if not isinstance(expect, OptionalType) else expect.type
                            self.errors[key] = ['Invalid type. Expecting `{}`.'.format(typ)]

            # process form validators in contract
            if self.form_contract:
                valid &= self.check_form(self.data, self.form_contract)

            return valid

    return ContractValidator


class validate(object):
    """
    Validate payload data inputted to request handler or
    API method. This decorator can take any arbitrary
    data structure and determine rules to validate inputs with.
    It can be run within the context of a flask request, or
    for an api method directly. See the examples below for
    details.

    .. note:: In a request context, a ``ValidationError`` will be
              thrown (HTTP 422 Unprocessable Entity). Outside of a
              request, a ``ValueError`` will be raised.

    Examples:

        Using types with API method:

        .. code-block:: python

            @validate(
                email=str,
                password=str
            )
            def login(email, password):
                return

        Using nested types (mixing types and validators):

        .. code-block:: python

            from wtforms import validators

            @blueprint.route('/login', methods=['POST'])
            @validate(
                data=dict(
                    email=validators.Email(),
                    password=str
                )
            )
            def login():
                return

        With pre-defined validation object:

        .. code-block:: python

            from wtforms import validators, Form, BooleanField
            from wtforms import StringField, PasswordField
            class LoginValidator(Form):
                email = StringField('Email Address', [
                    validators.DataRequired(),
                    validators.Email(),
                ])
                password = PasswordField('Password', [
                    validators.DataRequired(),
                    validators.Length(min=4, max=25)
                ])

            @blueprint.route('/login', methods=['POST'])
            @validate(LoginForm)
            def login():
                return

        Logic specified into decorator:

        .. code-block:: python

            @blueprint.route('/login', methods=['POST'])
            @validate(
                email = StringField('Email Address', [
                    validators.DataRequired(),
                    validators.Email(),
                ])
                password = PasswordField('Password', [
                    validators.DataRequired(),
                    validators.Length(min=4, max=25)
                ])
            )
            def login():
                return
    """

    def __init__(self, *args, **kwargs):
        # validator class
        if len(args):
            self.Validator = args[0]

        # validator as keyword arguments
        elif len(kwargs):
            self.Validator = create_validator(kwargs, force_optional=kwargs.get('force_optional', False))

        # incorrect arguments
        else:
            raise AssertionError('No validation rule supplied to @validate.')
        return

    def __call__(self, func):

        @wraps(func)
        def inner(*args, **kwargs):
            in_request = has_request_context()

            # parse payload data from request or function arguments
            if in_request:
                data = request.json if request.json is not None else request.args
                if isinstance(data, ImmutableMultiDict):
                    data = data.to_dict()
            else:
                data = kwargs.copy()
                varnames = argspec(func)
                data.update(dict(zip(varnames, args)))
                data = {k: v for k, v in data.items() if k not in ['cls', 'self']}

            # check for empty payload
            if not data:
                if in_request:
                    raise ExpectationFailed('No request payload specified.')
                else:
                    raise AssertionError('No arguments specified.')

            # instantiate validator with data (changes based
            # on normal vs dynamic validator)
            if isinstance(self.Validator, Form):
                form = self.Validator(MultiDict(data))
            else:
                form = self.Validator(data=data)

            # run payload validation
            if not form.validate():
                if in_request:
                    raise ValidationError('Invalid request payload.', form.errors)
                else:
                    errors = yaml.dump(form.errors, indent=2)
                    errors = errors.replace('\n', '\n  ').replace('- ', '  - ') + '\n'
                    raise ValueError('Invalid arguments specified.\n\nErrors:\n\n  {}'.format(errors))

            # subset inputs by validators
            return func(*args, **kwargs)
        return inner

    @classmethod
    def optional(cls, *args, **kwargs):
        """
        Force all specified parameters to be wrapped with
        optional() declaration.
        """
        kwargs['force_optional'] = True
        return cls(*args, **kwargs)
