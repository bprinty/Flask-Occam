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
from flask import request, current_app, Response
from wtforms import Form
from .errors import ValidationError

try:
    from flask_login import current_user
except:
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
        self.level = 'info' if not level else level
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
            varnames = inspect.getargspec(func)[0]
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



# validation
# ----------
from wtforms.fields.core import UnboundField, Field
from wtforms.fields.core import UnboundField, Field
from wtforms import FieldList
from wtforms import StringField, PasswordField, IntegerField
from wtforms import BooleanField, FloatField, DateField, DateTimeField
from wtforms import validators

def create_validator(typ):
    """
    Create validator from type object, using common
    type objects in python.
    """
    mapper = {
        'str': StringField,
        'bool': BooleanField,
        'float': FloatField,
        'int': IntegerField,
        'date': DateField,
        'datetime': DateTimeField
    }

    # handle list inputs
    if isinstance(typ, list):
        raise NotImplementedError('List types for validation not currently supported!')
        if len(typ) != 1:
            raise AssertionError('Lists specified for field validation must have exactly one element to validate on.')
        if isinstance(typ[0], Field):
            return [typ[0]]
        else:
            return [create_validator(typ[0])]

    # look for validation scheme in mapper
    if typ.__name__ not in mapper:
        raise AssertionError('No rule for validating on type {}'.format(typ))

    return mapper.get(typ.__name__)(typ.__name__, [validators.DataRequired()])


def optional(field):
    """
    Replace DataRequired validtion scheme with Optional
    validation scheme.

    Args:
        field (Field): Field to process validation options for.
    """
    # parse types as inputs
    if not isinstance(field, (Field, UnboundField)):
        field = create_validator(field)

    # # check for field list
    # field_list = isinstance(field, (list, tuple))
    # if field_list:
    #     field = field[0]

    # re-process field
    if len(field.args) < 2:
        raise AssertionError('Validator must have associated name and validation scheme (2 arguments)')
    name = field.args[0]
    checks = list(filter(
        lambda x: not isinstance(x, validators.DataRequired),
        field.args[1]
    ))
    checks.insert(0, validators.Optional())
    obj = field.field_class(name, checks)

    # return field or field list based on input
    return obj # if not field_list else [obj]


def validate(*vargs, **vkwargs):
    """
    Validate payload data inputted to request handler.

    Examples:

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

    TODO: documentation about how it can also be used with cli methods.

    TODO: INCLUDE PLACE FOR DOCUMENTATION URL IN REQUEST?

    """

    # validator class
    if len(vargs):
        Validator = vargs[0]

    # validator as keyword arguments
    elif len(vkwargs):
        class CustomValidator(Form):
            pass
        for kw in vkwargs:
            if not isinstance(vkwargs[kw], (Field, UnboundField)):
                vkwargs[kw] = create_validator(vkwargs[kw])
            setattr(CustomValidator, kw, vkwargs[kw])
        Validator = CustomValidator

    # incorrect arguments
    else:
        raise AssertionError('No validation rule supplied to @validate.')

    def decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            in_request = bool(request)

            # parse payload data from request or function arguments
            if in_request:
                data = request.json if request.json is not None else request.args
                if isinstance(data, ImmutableMultiDict):
                    data = data.to_dict()
            else:
                data = kwargs.copy()
                varnames = inspect.getargspec(func)[0]
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
            if not form.validate():
                if in_request:
                    raise ValidationError('Invalid request payload.', form.errors)
                else:
                    errors = yaml.dump(form.errors).replace('\n', '\n  ') + '\n'
                    raise ValueError('Invalid arguments specified. Errors: {}'.format(errors))

            # subset inputs by validators
            return func(*args, **kwargs)
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
