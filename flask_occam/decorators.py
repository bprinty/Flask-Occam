# -*- coding: utf-8 -*-
#
# Common utilities for app
#
# ------------------------------------------------


# imports
# -------
import yaml
import inspect
import logging
from functools import wraps
from werkzeug.exceptions import ExpectationFailed
from werkzeug.datastructures import ImmutableMultiDict
from flask import request, current_app, Response, has_request_context
from wtforms import Form
from .errors import ValidationError

try:
    from flask_login import current_user
except ImportError:
    current_user = None


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
            varnames = list(inspect.signature(func).parameters.keys())
            data.update(dict(zip(varnames, args)))
            data = {k: v for k, v in data.items() if k not in ['cls', 'self']}
            data.setdefault(current_app.config['OCCAM_LOG_USER_FORMAT'], current_user)
            data.setdefault('kwargs', kwargs)
            logger(self.msg.format(**data))
            return func(*args, **kwargs)
        return inner

    @classmethod
    def debug(cls, msg):
        return cls(msg, level='debug')

    @classmethod
    def info(cls, msg):
        return cls(msg, level='info')

    @classmethod
    def warning(cls, msg):
        print(msg)
        return cls(msg, level='warning')

    @classmethod
    def error(cls, msg):
        return cls(msg, level='error')

    @classmethod
    def critical(cls, msg):
        return cls(msg, level='critical')


# pagination
# ----------
def paginate(**options):
    """
    Enable request pagination.

    MORE DOCS
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
from wtforms.fields.core import UnboundField, Field
from wtforms.fields.core import UnboundField, Field
from wtforms import FieldList
from wtforms import StringField, PasswordField, IntegerField
from wtforms import BooleanField, FloatField, DateField, DateTimeField
from wtforms import validators


class OptionalType:

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
        field (Field): Field to process validation options for.
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


def create_validator(contract):

    class ContractValidator(object):
        """
        Custom validator class that can handle both
        wtforms validators and nested type validation.
        """
        type_contract = {}
        form_contract = {}
        for key in contract:
            field = contract[key]
            if isinstance(field, (type, list, tuple, dict, OptionalType)):
                type_contract[key] = field
            elif isinstance(field, (Field, UnboundField)):
                form_contract[key] = field
            else:
                form_contract[key] = StringField(key, [
                    validators.DataRequired()
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
            if isinstance(expected, type):
                return isinstance(actual, expected)

            elif isinstance(expected, OptionalType):
                return isinstance(actual, expected.type)

            # dictionary of types
            elif isinstance(expected, dict):
                if not isinstance(actual, dict):
                    return False
                Validator = create_validator(expected)
                form = Validator(data=actual)
                return form.validate()

            # list of objects (expected structure should
            # have one entry representing shape of elements)
            elif isinstance(expected, list):
                if not isinstance(actual, list):
                    return False
                Validator = create_validator(expected[0])
                for entry in actual:
                    form = Validator(data=entry)
                    return form.validate()

            return True

        def check_form(self, actual, expected):
            class CustomValidator(Form):
                pass
            for key in expected:
                setattr(CustomValidator, key, expected[key])
            print(actual)
            form = CustomValidator(data=actual)
            form.process()
            valid = form.validate()
            self.errors.update(form.errors)
            return valid

        def process(self):
            # NOOP for parity with form validator
            return

        def validate(self):
            valid = True

            # process types in contract
            if self.type_contract:
                for key in self.type_contract:
                    expect = self.type_contract[key]

                    # check for required fields
                    if key not in self.data and not isinstance(expect, OptionalType):
                        self.errors[key] = ['Field required.']
                        valid = False

                    # check type and nested data
                    else:
                        tcheck = self.check_type(self.data.get(key), self.type_contract[key])
                        valid &= tcheck
                        if not tcheck:
                            self.errors[key] = ['Invalid type.']

            # process form validators in contract
            if self.form_contract:
                print('form!')
                # STOPPED HERE - NEED TO FIGURE OUT WHY FORM VALIDATION IS ERRORING OUT
                valid &= self.check_form(self.data, self.form_contract)

            return valid

    return ContractValidator


def validate(*vargs, **vkwargs):
    """
    Validate payload data inputted to request handler or
    API method.

    Examples:

        Using types with API method:

        .. code-block:: python

            @validate(
                email=str,
                password=str
            )
            def login(email, password):
                return

        Using nested types:

        .. code-block:: python

            @blueprint.route('/login', methods=['POST'])
            @validate(
                data=dict(
                    email=str,
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
    # validator class
    if len(vargs):
        Validator = vargs[0]

    # validator as keyword arguments
    elif len(vkwargs):
        Validator = create_validator(vkwargs)

    # incorrect arguments
    else:
        raise AssertionError('No validation rule supplied to @validate.')

    def decorator(func):
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
                varnames = list(inspect.signature(func).parameters.keys())
                data.update(dict(zip(varnames, args)))
                data = {k: v for k, v in data.items() if k not in ['cls', 'self']}

            # check for empty payload
            if not data:
                if in_request:
                    raise ExpectationFailed('No request payload specified.')
                else:
                    raise AssertionError('No arguments specified.')

            # run payload validation
            form = Validator(data=data)
            form.process()
            if not form.validate():
                if in_request:
                    raise ValidationError('Invalid request payload.', form.errors)
                else:
                    errors = yaml.dump(form.errors, indent=2).replace('\n', '\n  ') + '\n'
                    raise ValueError('Invalid arguments specified.\nErrors:\n  {}'.format(errors))

            # subset inputs by validators
            return func(*args, **kwargs)
        return inner
    return decorator
