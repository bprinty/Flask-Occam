# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
import pytest
from flask_occam import validate, optional
from flask_occam import log
from wtforms import Form, StringField, BooleanField, PasswordField, validators

from .fixtures import app, ItemFactory, logs, logger

from flask_occam.errors import ValidationError


# log
# ---
@log('test with {var} and {obj.__class__.__name__}')
def log_default(var, obj):
    pass


@log.info('test with {var} and {obj.__class__.__name__}')
def log_info(var, obj):
    pass


@log.error('test with {var} and {obj.__class__.__name__}')
def log_error(var, obj):
    pass


@app.route('/log/<int:var>')
@log.info('test with {var}')
def get_log(var):
    pass


class TestLogDecorator(object):

    def test_url_logging(self, client):
        client.get('/log/0')
        assert 'test with 0' in logs.getvalue()
        return

    def test_formatting(self):
        log_default(1, object())
        assert 'test with 1 and object' in logs.getvalue()

        log_info(2, object())
        assert 'test with 2 and object' in logs.getvalue()

        log_error(3, object())
        assert 'test with 3 and object' in logs.getvalue()
        return


# validate
# --------
# @validate(
#     one=str, two=float, three=optional(int),
#     four=dict(
#         foo=str,
#         bar=str,
#     ), five=[str]
# )
# def validate_types():
#     pass


# @validate(
#     field=validators.BooleanField(),
#     validator=StringField('Boolean', [
#         validators.DataRequired(),
#         validators.BooleanField(),
#     ]),
#     optional=optional(validators.BooleanField())
# )
# def validate_validators():
#     pass


class ValidateForm(Form):
    boolean = BooleanField('Boolean', [
        validators.DataRequired(),
    ])


@validate(ValidateForm)
def validate_form(boolean):
    pass


# validate tests
# --------------
class TestValidateDecorator(object):

    # def test_integration(self, client):
    #     item = ItemFactory.create(name='test')
    #     response = client.put('/items/{}'.format(item.id), json=dict(
    #         name=1,
    #         email='email@localhost.com'
    #     ))
    #     print(response.status_code)
    #     return

    # def test_validate_types(self, client, items):
    #     response = client.get('/items/{}'.format(items[0].id))
    #     assert response.status_code == 200
    #     assert response.json['name'] == items[0].name
    #     return

    def test_validate_form(self, client):
        # raises error
        with pytest.raises(ValidationError):
            validate_form(boolean='test')

        # no error
        assert validate_form(boolean=True) is None
        return

    # def test_query_new(self, client):
    #     # other open read permissions
    #     item = ItemFactory.create(name='test')
    #     response = client.get('/items/{}'.format(item.id))
    #     assert response.status_code == 200
    #     assert response.json['name'] == 'test'
    #     return
