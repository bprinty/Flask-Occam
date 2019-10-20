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
from flask_occam import transactional
from wtforms import Form, StringField, BooleanField, PasswordField, validators

from .fixtures import app, Item, ItemFactory, logs, logger

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


# paginate
# --------
class TestPaginateDecorator(object):

    def test_integration(self, client, items):

        # paginated request
        response = client.get('/items')
        assert response.status_code == 206
        assert len(response.json) == 2
        assert 'limit=2&offset=2' in response.headers['Link']
        assert 'rel="next"' in response.headers['Link']
        assert 'rel="last"' in response.headers['Link']

        # no pagination needed
        response = client.get('/items?limit=2000&offset=2')
        assert 'Link' not in response.headers
        assert len(response.json) > 0
        assert response.status_code == 200
        return


# transactional
# -------------
class TestTransactionalDecorator(object):

    @transactional
    def create_item(self):
        item = Item.create(name='transaction-okay')
        return item.id

    @transactional
    def create_item_error(self):
        item = Item.create(name='transaction-fail')
        raise AssertionError
        return item.id

    def test_transactions(self):
        # normal
        ident = self.create_item()
        assert Item.get(ident) is not None

        # rollback
        try:
            self.create_item_error()
        except AssertionError:
            pass
        assert Item.get(name='transaction-fail') is None
        return


# validate
# --------
# @validate(
#     one=str, two=float,
#     three=optional(int),
#     four=optional(dict(
#         foo=str,
#         bar=str,
#     )),
#     five=optional([str])
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
    string = StringField('String', [
        validators.DataRequired(),
        validators.Length(min=3, max=10)
    ])
    boolean = BooleanField('Boolean', [
        validators.DataRequired(),
    ])


@validate(ValidateForm)
def validate_form(string, boolean):
    pass


# validate tests
# --------------
class TestValidateDecorator(object):

    def test_integration(self, client):
        item = ItemFactory.create(name='test')
        response = client.put('/items/{}'.format(item.id), json=dict(
            name=1
        ))
        assert response.status_code == 422
        print(response.json)
        return

    # def test_validate_types(self):
    #     from flask import _request_ctx_stack
    #     _request_ctx_stack.pop()

    #     # no exception
    #     validate_types(one='test', two=1.5)
    #     validate_types(one='test', two=1.5, three=1, four=dict(foo='foo', bar='bar'), five=['one', 'two'])

    #     # non-optional
    #     with pytest.raises(ValueError) as exc:
    #         validate_types(one=1, two='test')
    #         # assert one, two wrong
    #         print(exc.message)

    #     # optional
    #     with pytest.raises(ValueError) as exc:
    #         validate_types(one=1, two='test', three='test', four=dict(foo=1, bar='bar'), five=[1, 2])
    #         # assert one, two, three, four.foo, and five wrong
    #         print(exc.message)

    #     return

    def test_validate_form(self):
        from flask import _request_ctx_stack
        _request_ctx_stack.pop()

        # raises error
        with pytest.raises(ValueError):
            validate_form(string='a', boolean='test')

        # no error
        assert validate_form(string='test', boolean=True) is None
        return

    # def test_query_new(self, client):
    #     # other open read permissions
    #     item = ItemFactory.create(name='test')
    #     response = client.get('/items/{}'.format(item.id))
    #     assert response.status_code == 200
    #     assert response.json['name'] == 'test'
    #     return
