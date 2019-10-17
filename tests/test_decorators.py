# -*- coding: utf-8 -*-
#
# Testing for pl
#
# ------------------------------------------------


# imports
# -------
import pytest
from flask_occam import validate, optional
from wtforms import Form, StringField, BooleanField, PasswordField, validators

from .fixtures import ItemFactory

from flask_occam.errors import ValidationError


# validators
# ----------
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


# validation tests
# ----------------
class TestValidateHandler(object):

    def test_integration(self, client):
        item = ItemFactory.create(name='test')
        response = client.put('/items/{}'.format(item.id), json=dict(
            name=1,
            email='email@localhost.com'
        ))
        print(response.status_code)
        return

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
