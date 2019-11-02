# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
import sys
import pytest
from flask_occam import validate, optional
from flask_occam import log
from flask_occam import transactional
from wtforms import Form, StringField, BooleanField, validators

from .fixtures import app, Item, logs


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

    @pytest.mark.skipif(sys.version_info[0] < 3, reason='Test python2 incompatible.')
    def test_url_logging(self, client):
        client.get('/log/0')
        assert 'test with 0' in str(logs.getvalue())
        return

    @pytest.mark.skipif(sys.version_info[0] < 3, reason='Test python2 incompatible.')
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


# validate tests
# --------------
class TestValidateDecorator(object):

    def test_integration(self, client):
        item = Item.create(name='validation-test').commit()

        # invalid
        response = client.put('/items/{}'.format(item.id), json=dict(
            name=1
        ))
        assert response.status_code == 422
        assert 'name' in response.json['errors']

        # valid
        response = client.put('/items/{}'.format(item.id), json=dict(
            name='test'
        ))
        assert response.status_code == 200
        return

    def test_validate_types(self):
        from flask import _request_ctx_stack
        _request_ctx_stack.pop()

        # function
        @validate(
            one=str, two=float,
            three=list,
            four=optional(dict(
                foo=str,
                bar=str,
            )),
            five=optional([str])
        )
        def test(one, two, three, four=None, five=None):
            pass

        # no exception
        test(one='test', two=1.5, three=[1])
        test(one='test', two=1.5, three=[1], four=dict(foo='foo', bar='bar'), five=['one', 'two'])

        # non-optional
        try:
            test(one=1, two='test', three=1)
            self.fail('ValueError not thrown')
        except ValueError as exc:
            message = str(exc)
            assert 'one:' in message
            assert 'two:' in message
            assert 'three:' in message

        # optional
        try:
            test(one='test', two=1.5, three=[1], four=dict(foo=1, bar='bar'), five=[1, 2])
            self.fail('ValueError not thrown')
        except ValueError as exc:
            message = str(exc)
            assert 'four:' in message
            assert 'five:' in message
        return

    def test_validate_validators(self):
        from flask import _request_ctx_stack
        _request_ctx_stack.pop()

        # function
        @validate(
            email=validators.Email(),
            check=optional(StringField('check', [
                validators.Length(min=3, max=10),
                validators.EqualTo('confirm')
            ])),
            confirm=optional(validators.Length(min=3, max=10))
        )
        def test(email, check, confirm):
            pass

        # raises error
        with pytest.raises(ValueError):
            test(email='test', check='test', confirm='test')

        # raises error
        with pytest.raises(ValueError):
            test(email='a@b.com', check='t', confirm='t')

        # raises error
        with pytest.raises(ValueError):
            test(email='a@b.com', check='test', confirm='aaaa')

        # no error
        assert test(email='a@b.com', check='test', confirm='test') is None
        return

    def test_validate_form(self):
        from flask import _request_ctx_stack
        _request_ctx_stack.pop()

        # form
        class ValidateForm(Form):
            string = StringField('String', [
                validators.DataRequired(),
                validators.Length(min=3, max=10)
            ])
            boolean = BooleanField('Boolean', [
                validators.DataRequired(),
            ])

        @validate(ValidateForm)
        def test(string, boolean):
            pass

        # raises error
        with pytest.raises(ValueError):
            test(string='a', boolean='test')

        # no error
        assert test(string='test', boolean=True) is None
        return

    def test_validate_mixed(self):
        from flask import _request_ctx_stack
        _request_ctx_stack.pop()

        # function
        @validate(
            email=validators.Email(),
            one=dict(length=validators.Length(min=3)),
            two=float
        )
        def test(email, one, two):
            pass

        # no error
        test(email='a@b.com', one=dict(length='test'), two=1.5)

        # nested error
        with pytest.raises(ValueError):
            test(email='a@b.com', one=dict(length='te'), two=1.5)
        return

    def test_validate_optional(self):
        from flask import _request_ctx_stack
        _request_ctx_stack.pop()

        # function
        @validate.optional(
            one=str,
            two=float,
        )
        def test(one='test', two=1.1):
            pass

        # no error
        test(one='str')
        test(two=5.5)

        # error
        with pytest.raises(ValueError):
            test(one=1)
        return
